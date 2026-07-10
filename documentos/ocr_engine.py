"""
documentos/ocr_engine.py

All pytesseract / pdf2image logic for the "Digitalizar" (OCR) feature, plus
helpers to export the extracted text as .txt, .docx or a (searchable,
real-text) .pdf. Mirrors utils.find_ffmpeg / utils.ffmpeg_is_working for
detecting the Tesseract binary.
"""

import os
import shutil
import subprocess

import pytesseract
from PIL import Image

from utils import safe_filename

LANGUAGE_CHOICES = {
    "Português": "por",
    "Inglês": "eng",
    "Espanhol": "spa",
    "Automático": "por+eng",
}

IMAGE_EXTS = ["jpg", "jpeg", "png", "bmp", "tiff", "webp"]

POPPLER_INSTALL_MESSAGE = (
    "O poppler não foi encontrado neste computador. Ele é necessário para "
    "processar arquivos PDF (digitalização e conversão de/para PDF).\n\n"
    "Windows: baixe em "
    "https://github.com/oschwartz10612/poppler-windows/releases, extraia o "
    ".zip e adicione a pasta \"Library\\bin\" ao PATH do Windows."
)


def find_tesseract(custom_path: str = "") -> str:
    """Return a usable tesseract executable path/name, or '' if none found."""
    if custom_path:
        candidate = custom_path
        if os.path.isdir(candidate):
            candidate = os.path.join(candidate, "tesseract.exe" if os.name == "nt" else "tesseract")
        if os.path.isfile(candidate):
            return candidate

    found = shutil.which("tesseract")
    if found:
        return found

    if os.name == "nt":
        default_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if os.path.isfile(default_path):
            return default_path

    return ""


def tesseract_is_working(tesseract_path: str) -> bool:
    """Actually try to run tesseract --version to confirm it's a real binary."""
    if not tesseract_path:
        return False
    try:
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        proc = subprocess.run(
            [tesseract_path, "--version"],
            capture_output=True,
            timeout=5,
            creationflags=creationflags,
        )
        return proc.returncode == 0
    except Exception:
        return False


def wrap_poppler_error(exc: Exception) -> Exception:
    """Normalize a pdf2image failure into a clear PT-BR message when it's
    caused by poppler being missing - reused by documentos/converter.py's
    PDF-to-image conversion, which hits the exact same failure mode."""
    message = str(exc)
    if "poppler" in message.lower() or exc.__class__.__name__ == "PDFInfoNotInstalledError":
        return RuntimeError(POPPLER_INSTALL_MESSAGE)
    return exc


def ocr_image(file_path: str, lang: str, tesseract_path: str = "") -> str:
    """Run OCR on a single image file and return the extracted text."""
    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
    image = Image.open(file_path)
    return pytesseract.image_to_string(image, lang=lang)


def ocr_pdf(file_path: str, lang: str, tesseract_path: str = "", progress_cb=None) -> str:
    """Render every page of a (scanned) PDF to an image and OCR each one,
    reporting (current_page, total_pages) via progress_cb as it goes."""
    from pdf2image import convert_from_path

    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path

    try:
        pages = convert_from_path(file_path, dpi=200)
    except Exception as exc:  # noqa: BLE001 - normalize to a clear PT-BR message
        raise wrap_poppler_error(exc)

    texts = []
    total = len(pages)
    for index, page in enumerate(pages, start=1):
        texts.append(pytesseract.image_to_string(page, lang=lang))
        if progress_cb:
            progress_cb(index, total)
    return "\n\n".join(texts)


def save_as_txt(text: str, output_dir: str, base_name: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    out_path = _unique_path(output_dir, safe_filename(base_name), "txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    return out_path


def save_as_docx(text: str, output_dir: str, base_name: str) -> str:
    from docx import Document

    os.makedirs(output_dir, exist_ok=True)
    out_path = _unique_path(output_dir, safe_filename(base_name), "docx")
    document = Document()
    for paragraph in text.split("\n"):
        document.add_paragraph(paragraph)
    document.save(out_path)
    return out_path


def save_as_pdf(text: str, output_dir: str, base_name: str) -> str:
    """Render the text as real, selectable PDF text (not an image), which
    makes it inherently searchable - no extra OCR layer needed."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    os.makedirs(output_dir, exist_ok=True)
    out_path = _unique_path(output_dir, safe_filename(base_name), "pdf")
    page_w, page_h = A4
    margin = 40
    line_height = 14

    c = canvas.Canvas(out_path, pagesize=A4)
    c.setFont("Helvetica", 10)
    y = page_h - margin
    for raw_line in text.split("\n"):
        for line in _wrap_line(raw_line, 95):
            if y < margin:
                c.showPage()
                c.setFont("Helvetica", 10)
                y = page_h - margin
            c.drawString(margin, y, line)
            y -= line_height
    c.save()
    return out_path


def _wrap_line(line: str, width: int):
    if not line:
        return [""]
    words = line.split(" ")
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [""]


def _unique_path(directory: str, base_name: str, ext: str) -> str:
    candidate = os.path.join(directory, f"{base_name}.{ext}")
    counter = 1
    while os.path.exists(candidate):
        candidate = os.path.join(directory, f"{base_name} ({counter}).{ext}")
        counter += 1
    return candidate
