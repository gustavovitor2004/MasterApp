"""
documentos/converter.py

All format-conversion logic for the "Converter Formato" sub-tab: images,
PDFs, DOCX and TXT files converted locally, no internet connection
required. This is a separate, document-focused converter from the
top-level converter.py (which handles video/audio/image conversion via
ffmpeg for the Downloads workflow) - they don't share code on purpose,
matching how downloader.py and the top-level converter.py already keep
their own small private helpers instead of sharing a base class.
"""

import os
import shutil
import subprocess
import tempfile

from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from documentos.ocr_engine import wrap_poppler_error
from utils import safe_filename

IMAGE_EXTS = ["jpg", "jpeg", "png", "bmp", "webp", "tiff"]

# [CORRIGIDO] tabela de conversão explícita, igual à matriz pedida - cada
# formato lista só os destinos que de fato tem uma implementação abaixo.
# Não inclui o próprio formato de origem (ex: "pdf" não lista "pdf"): a
# opção de manter o mesmo formato é tratada à parte, como passthrough/cópia,
# em vez de aparecer como "conversão" normal.
CONVERSION_MATRIX = {
    "jpg": ["pdf", "png", "bmp", "webp", "tiff"],
    "jpeg": ["pdf", "png", "bmp", "webp", "tiff"],
    "png": ["pdf", "jpg", "bmp", "webp", "tiff"],
    "bmp": ["pdf", "jpg", "png", "webp", "tiff"],
    "webp": ["pdf", "jpg", "png", "bmp", "tiff"],
    "tiff": ["pdf", "jpg", "png", "bmp", "webp"],
    "pdf": ["jpg", "png", "txt", "docx"],
    "docx": ["pdf", "txt"],
    "txt": ["pdf", "docx"],
}


def detect_format(file_path: str):
    """Return (extension, category). category is one of "image", "pdf",
    "docx", "txt", or None if unsupported."""
    ext = os.path.splitext(file_path)[1].lower().lstrip(".")
    if ext in IMAGE_EXTS:
        return ext, "image"
    if ext == "pdf":
        return ext, "pdf"
    if ext == "docx":
        return ext, "docx"
    if ext == "txt":
        return ext, "txt"
    return ext, None


def available_targets(source_ext: str):
    return list(CONVERSION_MATRIX.get(source_ext.lower(), []))


def can_convert(source_ext: str, target_ext: str) -> bool:
    """Whether a specific file can reach a specific target format - either
    via a real conversion, or via the same-format passthrough copy."""
    source_ext = source_ext.lower()
    target_ext = target_ext.lower()
    if source_ext == target_ext:
        return True
    return target_ext in available_targets(source_ext)


def is_pdf_encrypted(path: str) -> bool:
    # [NOVO] detecta PDFs protegidos por senha, usados pela mesclagem para
    # saber quais arquivos precisam de senha antes de tentar ler as páginas.
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        return PdfReader(path).is_encrypted
    except PdfReadError:
        return False


def convert_file(source_path: str, target_ext: str, output_dir: str, progress_cb=None):
    """Convert a single file, returning a list of output paths (usually one,
    except PDF->image which produces one file per page)."""
    ext = os.path.splitext(source_path)[1].lower().lstrip(".")
    target_ext = target_ext.lower()
    os.makedirs(output_dir, exist_ok=True)

    # [CORRIGIDO] passthrough para mesmo formato: antes não existia nenhum
    # branch para "origem == destino" (ex: um PDF que já está na lista e o
    # destino escolhido também é PDF), então convert_file() estourava
    # ValueError. Agora isso é tratado como uma cópia simples.
    if ext == target_ext:
        return [_copy_passthrough(source_path, output_dir)]

    if ext in IMAGE_EXTS and target_ext == "pdf":
        return [_image_to_pdf(source_path, output_dir)]
    if ext in IMAGE_EXTS and target_ext in IMAGE_EXTS:
        return [_image_to_image(source_path, target_ext, output_dir)]
    if ext == "pdf" and target_ext in ("jpg", "png"):
        return _pdf_to_images(source_path, target_ext, output_dir, progress_cb)
    if ext == "pdf" and target_ext == "docx":
        return [_pdf_to_docx(source_path, output_dir)]
    if ext == "pdf" and target_ext == "txt":
        return [_pdf_to_txt(source_path, output_dir, progress_cb)]
    if ext == "docx" and target_ext == "pdf":
        return [_docx_to_pdf(source_path, output_dir)]
    if ext == "docx" and target_ext == "txt":
        # [NOVO] DOCX -> TXT
        return [_docx_to_txt(source_path, output_dir)]
    if ext == "txt" and target_ext == "pdf":
        # [NOVO] TXT -> PDF
        return [_txt_to_pdf(source_path, output_dir)]
    if ext == "txt" and target_ext == "docx":
        # [NOVO] TXT -> DOCX
        return [_txt_to_docx(source_path, output_dir)]

    raise ValueError(f"Conversão de .{ext} para .{target_ext} não é suportada.")


# [NOVO] merge de PDFs - substitui o antigo merge_images_to_pdf (que só
# aceitava imagens). Agora aceita QUALQUER mistura de formatos suportados:
# cada arquivo não-PDF é primeiro convertido para um PDF individual em uma
# pasta temporária (apagada ao final), e todos os PDFs (originais + gerados)
# são unidos, na ordem recebida, com pypdf.
def merge_to_pdf(paths, output_dir: str, output_name: str = None, passwords: dict = None) -> str:
    """Merge several files (images, PDFs, DOCX, TXT - any mix) into a
    single PDF, one source file's pages appended after another, in the
    given order. Returns the output path.

    `passwords` is an optional {path: password} map - [NOVO] used to open
    password-protected PDFs so they can be merged like any other file."""
    from pypdf import PdfReader, PdfWriter

    if not paths:
        raise ValueError("Nenhum arquivo para mesclar.")
    passwords = passwords or {}

    os.makedirs(output_dir, exist_ok=True)
    writer = PdfWriter()
    temp_dir = tempfile.mkdtemp(prefix="docmerge_")
    try:
        for path in paths:
            ext = os.path.splitext(path)[1].lower().lstrip(".")
            if ext == "pdf":
                # [NOVO] PDFs protegidos por senha são descriptografados
                # antes de serem anexados - sem isso, pypdf recusa ler as
                # páginas de um PDF criptografado.
                reader = PdfReader(path)
                if reader.is_encrypted:
                    password = passwords.get(path, "")
                    if reader.decrypt(password) == 0:
                        raise ValueError(
                            f"Senha incorreta (ou não informada) para o arquivo protegido "
                            f"\"{os.path.basename(path)}\"."
                        )
                writer.append(reader)
            else:
                pdf_path = convert_file(path, "pdf", temp_dir)[0]
                writer.append(pdf_path)

        base_name = safe_filename(os.path.splitext(output_name)[0]) if output_name else "documento_mesclado"
        out_path = _unique_path(output_dir, base_name, "pdf")
        with open(out_path, "wb") as f:
            writer.write(f)
    finally:
        writer.close()
        shutil.rmtree(temp_dir, ignore_errors=True)

    return out_path


# ---------------------------------------------------------------------------
# Individual conversions
# ---------------------------------------------------------------------------

def _copy_passthrough(path: str, output_dir: str) -> str:
    """Same-format "conversion": just copy the file to the output folder
    under a non-colliding name."""
    base = safe_filename(os.path.splitext(os.path.basename(path))[0])
    ext = os.path.splitext(path)[1].lstrip(".")
    out_path = _unique_path(output_dir, base, ext)
    shutil.copy2(path, out_path)
    return out_path


def _image_to_pdf(path: str, output_dir: str) -> str:
    image = Image.open(path).convert("RGB")
    page_w, page_h = A4
    draw_w, draw_h, x, y = _fit_to_page(image.size, (page_w, page_h))

    base = safe_filename(os.path.splitext(os.path.basename(path))[0])
    out_path = _unique_path(output_dir, base, "pdf")
    c = canvas.Canvas(out_path, pagesize=A4)
    c.drawImage(ImageReader(image), x, y, width=draw_w, height=draw_h)
    c.save()
    return out_path


def _image_to_image(path: str, target_ext: str, output_dir: str) -> str:
    image = Image.open(path)
    if target_ext in ("jpg", "jpeg") and image.mode in ("RGBA", "P"):
        image = image.convert("RGB")
    save_format = "JPEG" if target_ext in ("jpg", "jpeg") else target_ext.upper()

    base = safe_filename(os.path.splitext(os.path.basename(path))[0])
    out_path = _unique_path(output_dir, base, target_ext)
    image.save(out_path, save_format)
    return out_path


def _pdf_to_images(path: str, target_ext: str, output_dir: str, progress_cb=None):
    from pdf2image import convert_from_path

    try:
        pages = convert_from_path(path, dpi=200)
    except Exception as exc:  # noqa: BLE001 - normalize to a clear PT-BR message
        raise wrap_poppler_error(exc)

    save_format = "JPEG" if target_ext in ("jpg", "jpeg") else target_ext.upper()
    base = safe_filename(os.path.splitext(os.path.basename(path))[0])
    out_paths = []
    total = len(pages)
    for index, page in enumerate(pages, start=1):
        out_path = _unique_path(output_dir, f"{base}_pg{index}", target_ext)
        if target_ext in ("jpg", "jpeg"):
            page = page.convert("RGB")
        page.save(out_path, save_format)
        out_paths.append(out_path)
        if progress_cb:
            progress_cb(index, total)
    return out_paths


def _pdf_to_docx(path: str, output_dir: str) -> str:
    from pdf2docx import Converter

    base = safe_filename(os.path.splitext(os.path.basename(path))[0])
    out_path = _unique_path(output_dir, base, "docx")
    converter = Converter(path)
    try:
        converter.convert(out_path)
    finally:
        converter.close()
    return out_path


def _pdf_to_txt(path: str, output_dir: str, progress_cb=None) -> str:
    import pdfplumber

    base = safe_filename(os.path.splitext(os.path.basename(path))[0])
    out_path = _unique_path(output_dir, base, "txt")
    lines = []
    with pdfplumber.open(path) as pdf:
        total = len(pdf.pages)
        for index, page in enumerate(pdf.pages, start=1):
            lines.append(page.extract_text() or "")
            if progress_cb:
                progress_cb(index, total)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(lines))
    return out_path


def _docx_to_pdf(path: str, output_dir: str) -> str:
    base = safe_filename(os.path.splitext(os.path.basename(path))[0])
    out_path = _unique_path(output_dir, base, "pdf")

    try:
        from docx2pdf import convert as docx2pdf_convert
        docx2pdf_convert(path, out_path)
        if os.path.exists(out_path):
            return out_path
    except Exception:
        pass  # fall through to the LibreOffice fallback below

    libreoffice = shutil.which("soffice") or shutil.which("libreoffice")
    if libreoffice:
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        subprocess.run(
            [libreoffice, "--headless", "--convert-to", "pdf", "--outdir", output_dir, path],
            capture_output=True,
            timeout=120,
            creationflags=creationflags,
        )
        if os.path.exists(out_path):
            return out_path

    raise RuntimeError(
        "Não foi possível converter DOCX para PDF: é necessário ter o Microsoft "
        "Word instalado (Windows) ou o LibreOffice instalado no sistema."
    )


def _docx_to_txt(path: str, output_dir: str) -> str:
    # [NOVO]
    from docx import Document

    base = safe_filename(os.path.splitext(os.path.basename(path))[0])
    out_path = _unique_path(output_dir, base, "txt")
    document = Document(path)
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    return out_path


def _txt_to_pdf(path: str, output_dir: str) -> str:
    # [NOVO] reaproveita o exportador de texto->PDF já usado pelo OCR
    # (produz um PDF com texto real/pesquisável, não uma imagem).
    from documentos.ocr_engine import save_as_pdf

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    base = safe_filename(os.path.splitext(os.path.basename(path))[0])
    return save_as_pdf(text, output_dir, base)


def _txt_to_docx(path: str, output_dir: str) -> str:
    # [NOVO]
    from documentos.ocr_engine import save_as_docx

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    base = safe_filename(os.path.splitext(os.path.basename(path))[0])
    return save_as_docx(text, output_dir, base)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _fit_to_page(image_size, page_size):
    """Scale an image to fit centered inside a page, preserving aspect
    ratio. Returns (draw_width, draw_height, x, y)."""
    img_w, img_h = image_size
    page_w, page_h = page_size
    scale = min(page_w / img_w, page_h / img_h)
    draw_w, draw_h = img_w * scale, img_h * scale
    x = (page_w - draw_w) / 2
    y = (page_h - draw_h) / 2
    return draw_w, draw_h, x, y


def _unique_path(directory: str, base_name: str, ext: str) -> str:
    candidate = os.path.join(directory, f"{base_name}.{ext}")
    counter = 1
    while os.path.exists(candidate):
        candidate = os.path.join(directory, f"{base_name} ({counter}).{ext}")
        counter += 1
    return candidate
