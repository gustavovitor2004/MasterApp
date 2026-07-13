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
    """Batch document conversion. Jobs are identified by a stable integer
    id (not list position) so the UI can delete queued-but-not-yet-reached
    items mid-run without any index-shifting bugs - deleted ids just get
    added to `skip_ids` (a set shared by reference with the UI) and this
    worker skips them when it gets to them."""

    file_started = Signal(int)                # job_id (individual mode only)
    file_finished = Signal(int, bool, str)     # job_id, success, message (individual mode only)
    file_skipped = Signal(int, str)            # job_id, reason - "Não suportado" (individual mode only)
    merge_finished = Signal(bool, str)         # success, output_path or error message (merge mode only)
    all_finished = Signal()
    # Emitted (with Qt.ConnectionType.BlockingQueuedConnection) when
    # merge_to_pdf() running on THIS thread hits an encrypted PDF with no
    # known password - the slot connected to this, on the GUI thread, must
    # store the password in self.password_response before returning. Since
    # the connection is blocking, this thread waits for the user to type
    # the password, but the app window keeps responding normally (only
    # this worker thread would ever be blocked, never the GUI).
    password_requested = Signal(str)

    def __init__(self, jobs, output_dir: str, target_ext: str, merge: bool = False,
                 skip_ids=None, output_name: str = None, passwords: dict = None, parent=None):
        """`jobs` is a list of (job_id, path) tuples, in display order.
        `merge=True` converts every job to PDF and merges them into a
        single output file named `output_name` instead of converting them
        individually. `passwords` is an optional {path: password} map with
        passwords already known upfront - any encrypted PDF not covered by
        it triggers `password_requested` instead."""
        super().__init__(parent)
        self.jobs = jobs
        self.output_dir = output_dir
        self.target_ext = target_ext
        self.merge = merge
        self.skip_ids = skip_ids if skip_ids is not None else set()
        self.output_name = output_name
        self.passwords = passwords or {}
        self.password_response = None

    def _ask_password(self, path: str):
        # Runs on THIS thread (the conversion one) - the emit() below only
        # returns after the slot connected on the GUI thread has already
        # run and filled in self.password_response, thanks to the blocking
        # connection.
        self.password_response = None
        self.password_requested.emit(path)
        return self.password_response

    def run(self):
        if self.merge:
            self._run_merge()
        else:
            self._run_individual()

    def _run_individual(self):
        for job_id, path in self.jobs:
            if job_id in self.skip_ids:
                # Item removed from the list by the user while the
                # conversion was running - skip silently, no signal (the
                # corresponding widget has already been removed from the UI).
                continue

            ext, _ = doc_converter.detect_format(path)
            # The dropdown shows any format valid for AT LEAST ONE file in
            # the list, so each individual file still needs to be checked
            # here - ones that don't support the chosen target are marked
            # "Não suportado" and skipped, without counting as an error.
            if not doc_converter.can_convert(ext, self.target_ext):
                self.file_skipped.emit(job_id, "Não suportado")
                continue

            self.file_started.emit(job_id)
            try:
                out_paths = doc_converter.convert_file(path, self.target_ext, self.output_dir)
                message = out_paths[0] if len(out_paths) == 1 else f"{len(out_paths)} arquivos gerados"
                self.file_finished.emit(job_id, True, message)
            except Exception as exc:  # noqa: BLE001 - surface everything to the UI, never crash silently
                self.file_finished.emit(job_id, False, str(exc))
        self.all_finished.emit()

    def _run_merge(self):
        # Merge mode: converts everything to PDF and joins it into a single
        # file, in the order received (which reflects the list's order,
        # including any drag-and-drop reordering).
        remaining_paths = [path for job_id, path in self.jobs if job_id not in self.skip_ids]
        try:
            out_path = doc_converter.merge_to_pdf(
                remaining_paths, self.output_dir, self.output_name,
                passwords=self.passwords, password_callback=self._ask_password,
            )
            self.merge_finished.emit(True, out_path)
        except Exception as exc:  # noqa: BLE001 - surface everything to the UI, never crash silently
            self.merge_finished.emit(False, str(exc))
        self.all_finished.emit()
