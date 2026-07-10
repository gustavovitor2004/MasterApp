"""
documentos/converter.py

All format-conversion logic for the "Converter Formato" sub-tab: images,
PDFs and DOCX files converted locally, no internet connection required.
This is a separate, document-focused converter from the top-level
converter.py (which handles video/audio/image conversion via ffmpeg for
the Downloads workflow) - they don't share code on purpose, matching how
downloader.py and the top-level converter.py already keep their own small
private helpers instead of sharing a base class.
"""

import os
import shutil
import subprocess

from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from documentos.ocr_engine import wrap_poppler_error
from utils import safe_filename

IMAGE_EXTS = ["jpg", "jpeg", "png", "bmp", "webp", "tiff"]


def detect_format(file_path: str):
    """Return (extension, category). category is one of "image", "pdf",
    "docx", or None if unsupported."""
    ext = os.path.splitext(file_path)[1].lower().lstrip(".")
    if ext in IMAGE_EXTS:
        return ext, "image"
    if ext == "pdf":
        return ext, "pdf"
    if ext == "docx":
        return ext, "docx"
    return ext, None


def available_targets(source_ext: str):
    ext = source_ext.lower()
    if ext == "pdf":
        return ["jpg", "png", "docx", "txt"]
    if ext == "docx":
        return ["pdf"]
    if ext in IMAGE_EXTS:
        return ["pdf"] + [e for e in IMAGE_EXTS if e != ext]
    return []


def convert_file(source_path: str, target_ext: str, output_dir: str, progress_cb=None):
    """Convert a single file, returning a list of output paths (usually one,
    except PDF->image which produces one file per page)."""
    ext = os.path.splitext(source_path)[1].lower().lstrip(".")
    target_ext = target_ext.lower()
    os.makedirs(output_dir, exist_ok=True)

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

    raise ValueError(f"Conversão de .{ext} para .{target_ext} não é suportada.")


def merge_images_to_pdf(paths, output_dir: str):
    """Merge several images into a single multi-page PDF, one image per
    page. Returns a list with the single output path."""
    if not paths:
        return []
    os.makedirs(output_dir, exist_ok=True)
    out_path = _unique_path(output_dir, "imagens_mescladas", "pdf")
    page_w, page_h = A4

    c = canvas.Canvas(out_path, pagesize=A4)
    for path in paths:
        image = Image.open(path)
        image = image.convert("RGB")
        draw_w, draw_h, x, y = _fit_to_page(image.size, (page_w, page_h))
        c.drawImage(ImageReader(image), x, y, width=draw_w, height=draw_h)
        c.showPage()
    c.save()
    return [out_path]


# ---------------------------------------------------------------------------
# Individual conversions
# ---------------------------------------------------------------------------

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
