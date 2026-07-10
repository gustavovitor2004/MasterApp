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
    file_skipped = Signal(int, str)            # [NOVO] job_id, reason - "Não suportado" (individual mode only)
    merge_finished = Signal(bool, str)         # [NOVO] success, output_path or error message (merge mode only)
    all_finished = Signal()

    def __init__(self, jobs, output_dir: str, target_ext: str, merge: bool = False,
                 skip_ids=None, output_name: str = None, parent=None):
        """`jobs` is a list of (job_id, path) tuples, in display order.
        `merge=True` converts every job to PDF and merges them into a
        single output file named `output_name` instead of converting them
        individually."""
        super().__init__(parent)
        self.jobs = jobs
        self.output_dir = output_dir
        self.target_ext = target_ext
        self.merge = merge
        self.skip_ids = skip_ids if skip_ids is not None else set()
        self.output_name = output_name

    def run(self):
        if self.merge:
            self._run_merge()
        else:
            self._run_individual()

    def _run_individual(self):
        for job_id, path in self.jobs:
            if job_id in self.skip_ids:
                # [NOVO] item removido da lista pelo usuário enquanto a
                # conversão estava rodando - pula sem erro, sem sinal (o
                # widget correspondente já foi removido da UI).
                continue

            ext, _ = doc_converter.detect_format(path)
            # [CORRIGIDO] antes o dropdown já bloqueava combinações
            # inválidas para a lista inteira; agora ele mostra qualquer
            # formato válido para PELO MENOS UM arquivo, então cada arquivo
            # individual precisa ser checado aqui - os que não suportam o
            # destino escolhido são marcados "Não suportado" e pulados, sem
            # contar como erro.
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
        # [NOVO] modo de mesclagem: converte tudo em PDF e junta em um
        # único arquivo, na ordem recebida (que reflete a ordem da lista,
        # incluindo qualquer reordenação feita por arrastar-e-soltar).
        remaining_paths = [path for job_id, path in self.jobs if job_id not in self.skip_ids]
        try:
            out_path = doc_converter.merge_to_pdf(remaining_paths, self.output_dir, self.output_name)
            self.merge_finished.emit(True, out_path)
        except Exception as exc:  # noqa: BLE001 - surface everything to the UI, never crash silently
            self.merge_finished.emit(False, str(exc))
        self.all_finished.emit()
