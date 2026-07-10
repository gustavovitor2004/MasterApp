"""
documentos/workers.py

QThread-based background workers for the Documentos tab: one for OCR
digitization, one for batch format conversion.

Note on threading style: the rest of the app (downloader.py, the top-level
converter.py) uses a persistent QObject "manager" running plain
threading.Thread workers behind a small dispatcher loop, because those
features manage an ongoing, pause/resume-able download or conversion
*queue*. The Documentos tab's OCR and conversion actions are one-shot,
started-by-a-button operations with a simple start -> progress -> finished
lifecycle, so a QThread per action (started fresh each click) is the
simpler, equally thread-safe fit here - QThread's signals are marshaled to
the GUI thread exactly like the QObject signals used elsewhere in the app.
"""

import os
import time

from PySide6.QtCore import QThread, Signal

from documentos import ocr_engine
from documentos import converter as doc_converter


class OcrWorker(QThread):
    page_progress = Signal(int, int)   # current page, total pages
    finished_ok = Signal(str, float)   # extracted text, elapsed seconds
    failed = Signal(str)

    def __init__(self, file_path: str, lang: str, tesseract_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.lang = lang
        self.tesseract_path = tesseract_path

    def run(self):
        start = time.monotonic()
        try:
            ext = os.path.splitext(self.file_path)[1].lower().lstrip(".")
            if ext == "pdf":
                text = ocr_engine.ocr_pdf(
                    self.file_path, self.lang, self.tesseract_path,
                    progress_cb=lambda current, total: self.page_progress.emit(current, total),
                )
            else:
                self.page_progress.emit(1, 1)
                text = ocr_engine.ocr_image(self.file_path, self.lang, self.tesseract_path)
            elapsed = time.monotonic() - start
            self.finished_ok.emit(text, elapsed)
        except Exception as exc:  # noqa: BLE001 - surface everything to the UI, never crash silently
            self.failed.emit(str(exc))


class ConversionWorker(QThread):
    file_started = Signal(int)               # index into the job list
    file_finished = Signal(int, bool, str)    # index, success, message (output path or error)
    all_finished = Signal()

    def __init__(self, jobs, output_dir: str, merge_images: bool = False, parent=None):
        """`jobs` is a list of source file paths, all converted to the same
        target format (set via set_target_ext). `merge_images=True` merges
        every job into a single output PDF instead of converting them
        individually - only meaningful when every job is an image and the
        target format is PDF."""
        super().__init__(parent)
        self.jobs = jobs
        self.target_ext = None
        self.output_dir = output_dir
        self.merge_images = merge_images
        self._cancelled = False

    def set_target_ext(self, target_ext: str):
        self.target_ext = target_ext

    def cancel(self):
        self._cancelled = True

    def run(self):
        if self.merge_images:
            self.file_started.emit(0)
            try:
                out_paths = doc_converter.merge_images_to_pdf(self.jobs, self.output_dir)
                message = out_paths[0] if out_paths else self.output_dir
                self.file_finished.emit(0, True, message)
            except Exception as exc:  # noqa: BLE001
                self.file_finished.emit(0, False, str(exc))
            self.all_finished.emit()
            return

        for index, source_path in enumerate(self.jobs):
            if self._cancelled:
                break
            self.file_started.emit(index)
            try:
                out_paths = doc_converter.convert_file(source_path, self.target_ext, self.output_dir)
                message = out_paths[0] if len(out_paths) == 1 else f"{len(out_paths)} arquivos gerados"
                self.file_finished.emit(index, True, message)
            except Exception as exc:  # noqa: BLE001 - surface everything to the UI, never crash silently
                self.file_finished.emit(index, False, str(exc))
        self.all_finished.emit()
