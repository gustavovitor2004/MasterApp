"""
documentos/tab_documentos.py

The "Documentos" tab widget: registers two sub-tabs, "Digitalizar" (OCR)
and "Converter Formato" (local document conversion). Deliberately reuses
the same visual patterns already established in ui.py - QFrame#Card,
QPushButton#Primary/#Danger, QLabel#Dim/#ErrorLabel/#StatusDone/#StatusError
- so it inherits the app's theme (dark/light) automatically through the
same app-wide stylesheet MainWindow.apply_theme() already sets, with no
Documentos-specific styling needed.
"""

import os

from PIL import Image
from PySide6.QtCore import Qt, QSize, QUrl
from PySide6.QtGui import QDesktopServices, QImage, QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QListWidget, QListWidgetItem, QProgressBar, QFileDialog, QCheckBox,
    QMessageBox, QFrame, QTextEdit, QTabWidget, QApplication,
)

from documentos import ocr_engine
from documentos import converter as doc_converter
from documentos.workers import OcrWorker, ConversionWorker
from settings import save_settings
from utils import format_size

PREVIEW_SIZE = QSize(270, 280)


class OcrSubTab(QWidget):
    """Feature 1 - Digitalização (OCR): pick an image or scanned PDF, run
    OCR in a background QThread, edit and export the extracted text."""

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.current_file = None
        self.worker = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # --- left column: preview + controls ---------------------------------
        left_card = QFrame()
        left_card.setObjectName("Card")
        left_card.setFixedWidth(300)
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)

        self.preview_label = QLabel("📄\n\nNenhum arquivo selecionado")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setFixedSize(PREVIEW_SIZE)
        self.preview_label.setStyleSheet("background-color: rgba(255,255,255,15); border-radius: 6px;")
        self.preview_label.setWordWrap(True)
        left_layout.addWidget(self.preview_label)

        self.select_btn = QPushButton("📂 Selecionar Arquivo")
        self.select_btn.clicked.connect(self.on_select_file)
        left_layout.addWidget(self.select_btn)

        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel("Idioma:"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(list(ocr_engine.LANGUAGE_CHOICES.keys()))
        lang_row.addWidget(self.lang_combo, stretch=1)
        left_layout.addLayout(lang_row)

        self.digitize_btn = QPushButton("🔍 Digitalizar")
        self.digitize_btn.setObjectName("Primary")
        self.digitize_btn.setEnabled(False)
        self.digitize_btn.clicked.connect(self.on_digitize_clicked)
        left_layout.addWidget(self.digitize_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setObjectName("Dim")
        self.status_label.setWordWrap(True)
        left_layout.addWidget(self.status_label)

        left_layout.addStretch(1)
        layout.addWidget(left_card)

        # --- right column: extracted text -------------------------------------
        right_card = QFrame()
        right_card.setObjectName("Card")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(8)

        right_layout.addWidget(QLabel("Texto extraído:"))
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(
            "O texto digitalizado vai aparecer aqui e pode ser editado antes de salvar."
        )
        right_layout.addWidget(self.text_edit, stretch=1)

        buttons_row = QHBoxLayout()
        self.copy_btn = QPushButton("📋 Copiar Texto")
        self.copy_btn.setEnabled(False)
        self.copy_btn.clicked.connect(self.on_copy_text)
        buttons_row.addWidget(self.copy_btn)

        self.save_txt_btn = QPushButton("💾 Salvar como .TXT")
        self.save_txt_btn.setEnabled(False)
        self.save_txt_btn.clicked.connect(lambda: self.on_save_as("txt"))
        buttons_row.addWidget(self.save_txt_btn)

        self.save_docx_btn = QPushButton("💾 Salvar como .DOCX")
        self.save_docx_btn.setEnabled(False)
        self.save_docx_btn.clicked.connect(lambda: self.on_save_as("docx"))
        buttons_row.addWidget(self.save_docx_btn)

        self.save_pdf_btn = QPushButton("💾 Salvar como .PDF")
        self.save_pdf_btn.setEnabled(False)
        self.save_pdf_btn.clicked.connect(lambda: self.on_save_as("pdf"))
        buttons_row.addWidget(self.save_pdf_btn)

        right_layout.addLayout(buttons_row)
        layout.addWidget(right_card, stretch=1)

        self._check_tesseract_on_start()

    # ------------------------------------------------------------------
    # Startup check
    # ------------------------------------------------------------------

    def _check_tesseract_on_start(self):
        path = ocr_engine.find_tesseract()
        if not ocr_engine.tesseract_is_working(path):
            QMessageBox.warning(
                self,
                "Tesseract OCR não encontrado",
                "O Tesseract OCR não foi encontrado neste computador.\n\n"
                "Ele é necessário para a função de Digitalização (OCR) "
                "funcionar - sem ele, o botão \"Digitalizar\" vai mostrar "
                "erro.\n\n"
                "Windows: baixe o instalador em\n"
                "https://github.com/UB-Mannheim/tesseract/wiki\n\n"
                "Durante a instalação, marque os pacotes de idioma "
                "Português e Inglês. Depois, adicione a pasta de instalação "
                "(normalmente C:\\Program Files\\Tesseract-OCR) ao PATH do "
                "Windows - ou apenas reinicie o app após instalar, ele "
                "detecta esse caminho padrão automaticamente.",
            )

    # ------------------------------------------------------------------
    # File selection + preview
    # ------------------------------------------------------------------

    def on_select_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar arquivo para digitalizar",
            "",
            "Imagens e PDFs (*.jpg *.jpeg *.png *.bmp *.tiff *.webp *.pdf)",
        )
        if not path:
            return
        self.current_file = path
        self.digitize_btn.setEnabled(True)
        self.status_label.setText(os.path.basename(path))
        self._update_preview(path)

    def _update_preview(self, path):
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        try:
            if ext == "pdf":
                from pdf2image import convert_from_path
                pages = convert_from_path(path, dpi=100, first_page=1, last_page=1)
                if pages:
                    self._set_preview_image(pages[0])
                    return
            else:
                self._set_preview_image(Image.open(path))
                return
        except Exception:
            pass  # preview is a nice-to-have, never fatal
        self.preview_label.setPixmap(QPixmap())
        self.preview_label.setText(f"📄\n\n{os.path.basename(path)}")

    def _set_preview_image(self, pil_image):
        pil_image = pil_image.convert("RGB")
        data = pil_image.tobytes("raw", "RGB")
        qimage = QImage(data, pil_image.width, pil_image.height, pil_image.width * 3, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimage).scaled(
            self.preview_label.width(), self.preview_label.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        self.preview_label.setText("")
        self.preview_label.setPixmap(pixmap)

    # ------------------------------------------------------------------
    # OCR run
    # ------------------------------------------------------------------

    def on_digitize_clicked(self):
        if not self.current_file:
            return
        tesseract_path = ocr_engine.find_tesseract()
        if not ocr_engine.tesseract_is_working(tesseract_path):
            QMessageBox.warning(
                self,
                "Tesseract OCR não encontrado",
                "Instale o Tesseract OCR antes de digitalizar "
                "(https://github.com/UB-Mannheim/tesseract/wiki) e "
                "reinicie o app.",
            )
            return

        lang_label = self.lang_combo.currentText()
        lang_code = ocr_engine.LANGUAGE_CHOICES.get(lang_label, "por+eng")

        self.digitize_btn.setEnabled(False)
        self.select_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # indeterminate "spinner" until we know the page count
        self.status_label.setText("Digitalizando...")

        self.worker = OcrWorker(self.current_file, lang_code, tesseract_path)
        self.worker.page_progress.connect(self._on_page_progress)
        self.worker.finished_ok.connect(self._on_ocr_finished)
        self.worker.failed.connect(self._on_ocr_failed)
        self.worker.start()

    def _on_page_progress(self, current, total):
        if total > 1:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)
            self.status_label.setText(f"Página {current} de {total}...")
        else:
            self.status_label.setText("Digitalizando...")

    def _on_ocr_finished(self, text, elapsed):
        self.text_edit.setPlainText(text)
        self.progress_bar.setVisible(False)
        self.digitize_btn.setEnabled(True)
        self.select_btn.setEnabled(True)
        has_text = bool(text.strip())
        self.copy_btn.setEnabled(has_text)
        self.save_txt_btn.setEnabled(has_text)
        self.save_docx_btn.setEnabled(has_text)
        self.save_pdf_btn.setEnabled(has_text)
        self.status_label.setText(f"Concluído em {elapsed:.1f}s")

    def _on_ocr_failed(self, message):
        self.progress_bar.setVisible(False)
        self.digitize_btn.setEnabled(True)
        self.select_btn.setEnabled(True)
        self.status_label.setText("Erro na digitalização")
        QMessageBox.critical(self, "Erro na digitalização", message)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def on_copy_text(self):
        QApplication.clipboard().setText(self.text_edit.toPlainText())

    def on_save_as(self, fmt):
        text = self.text_edit.toPlainText()
        if not text.strip():
            return
        base_name = os.path.splitext(os.path.basename(self.current_file or "documento"))[0]
        output_dir = self.settings.ocr_output_dir
        try:
            if fmt == "txt":
                out_path = ocr_engine.save_as_txt(text, output_dir, base_name)
            elif fmt == "docx":
                out_path = ocr_engine.save_as_docx(text, output_dir, base_name)
            else:
                out_path = ocr_engine.save_as_pdf(text, output_dir, base_name)
            QMessageBox.information(self, "Salvo", f"Arquivo salvo em:\n{out_path}")
        except Exception as exc:  # noqa: BLE001 - never crash silently
            QMessageBox.critical(self, "Erro ao salvar", str(exc))


class DocConversionItemWidget(QFrame):
    """One row inside the document-conversion file list."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)

        self.name_label = QLabel("")
        self.name_label.setStyleSheet("font-weight: 600;")
        layout.addWidget(self.name_label, stretch=1)

        self.format_label = QLabel("")
        self.format_label.setObjectName("Dim")
        self.format_label.setFixedWidth(60)
        layout.addWidget(self.format_label)

        self.size_label = QLabel("")
        self.size_label.setObjectName("Dim")
        self.size_label.setFixedWidth(90)
        layout.addWidget(self.size_label)

        self.status_label = QLabel("Aguardando")
        self.status_label.setFixedWidth(180)
        layout.addWidget(self.status_label)

    def set_file(self, path):
        try:
            size = os.path.getsize(path)
        except OSError:
            size = 0
        self.name_label.setText(os.path.basename(path))
        self.format_label.setText(os.path.splitext(path)[1].lstrip(".").upper())
        self.size_label.setText(format_size(size))

    def set_status(self, text, kind=""):
        self.status_label.setText(text)
        self.status_label.setObjectName(kind)
        self.style().unpolish(self.status_label)
        self.style().polish(self.status_label)


class ConvertSubTab(QWidget):
    """Feature 2 - Conversão de Formato: batch-convert images, PDFs and
    DOCX files locally, in a background QThread."""

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.jobs = []
        self._item_widgets = {}
        self._completed = 0
        self._merge_active = False
        self.worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        top_row = QHBoxLayout()
        add_btn = QPushButton("+ Adicionar arquivos")
        add_btn.setObjectName("Primary")
        add_btn.clicked.connect(self.on_add_files)
        top_row.addWidget(add_btn)

        top_row.addWidget(QLabel("Converter para:"))
        self.target_combo = QComboBox()
        self.target_combo.setEnabled(False)
        self.target_combo.currentTextChanged.connect(self._on_target_changed)
        top_row.addWidget(self.target_combo)

        top_row.addStretch(1)
        self.convert_btn = QPushButton("▶ Converter")
        self.convert_btn.setObjectName("Primary")
        self.convert_btn.setEnabled(False)
        self.convert_btn.clicked.connect(self.on_convert_clicked)
        top_row.addWidget(self.convert_btn)
        layout.addLayout(top_row)

        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel("Salvar em:"))
        self.folder_label = QLabel(self.settings.doc_convert_output_dir)
        self.folder_label.setObjectName("Dim")
        folder_row.addWidget(self.folder_label, stretch=1)
        folder_btn = QPushButton("📁 Escolher")
        folder_btn.clicked.connect(self.on_choose_folder)
        folder_row.addWidget(folder_btn)
        layout.addLayout(folder_row)

        self.merge_checkbox = QCheckBox("Mesclar todas as imagens em um único PDF")
        self.merge_checkbox.setVisible(False)
        layout.addWidget(self.merge_checkbox)

        self.error_label = QLabel("")
        self.error_label.setObjectName("ErrorLabel")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        self.file_list = QListWidget()
        self.file_list.setSpacing(4)
        self.file_list.setSelectionMode(QListWidget.NoSelection)
        self.file_list.setFocusPolicy(Qt.NoFocus)
        layout.addWidget(self.file_list, stretch=1)

        bottom_row = QHBoxLayout()
        self.overall_progress = QProgressBar()
        self.overall_progress.setTextVisible(False)
        bottom_row.addWidget(self.overall_progress, stretch=1)
        self.overall_status_label = QLabel("")
        self.overall_status_label.setObjectName("Dim")
        bottom_row.addWidget(self.overall_status_label)
        layout.addLayout(bottom_row)

        self.open_folder_btn = QPushButton("📂 Abrir pasta de saída")
        self.open_folder_btn.setEnabled(False)
        self.open_folder_btn.clicked.connect(self.on_open_folder)
        layout.addWidget(self.open_folder_btn)

    # ------------------------------------------------------------------
    # File selection
    # ------------------------------------------------------------------

    def on_add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Selecionar arquivo(s)",
            "",
            "Documentos (*.jpg *.jpeg *.png *.bmp *.webp *.tiff *.pdf *.docx)",
        )
        if not paths:
            return
        self.error_label.setVisible(False)
        for path in paths:
            if path in self.jobs:
                continue
            _, category = doc_converter.detect_format(path)
            if category is None:
                continue
            self.jobs.append(path)
            widget = DocConversionItemWidget()
            widget.set_file(path)
            list_item = QListWidgetItem()
            list_item.setSizeHint(QSize(0, 50))
            self.file_list.addItem(list_item)
            self.file_list.setItemWidget(list_item, widget)
            self._item_widgets[len(self.jobs) - 1] = widget
        self._refresh_target_options()

    def _refresh_target_options(self):
        self.target_combo.blockSignals(True)
        self.target_combo.clear()

        if not self.jobs:
            self.target_combo.setEnabled(False)
            self.convert_btn.setEnabled(False)
            self.target_combo.blockSignals(False)
            self._update_merge_visibility()
            return

        common = None
        for path in self.jobs:
            ext, _ = doc_converter.detect_format(path)
            options = set(doc_converter.available_targets(ext))
            common = options if common is None else (common & options)
        common = sorted(common) if common else []

        if common:
            self.target_combo.addItems([f.upper() for f in common])
            self.target_combo.setEnabled(True)
            self.convert_btn.setEnabled(True)
            self.error_label.setVisible(False)
        else:
            self.target_combo.setEnabled(False)
            self.convert_btn.setEnabled(False)
            self.error_label.setText("Os arquivos selecionados não têm um formato de destino em comum.")
            self.error_label.setVisible(True)

        self.target_combo.blockSignals(False)
        self._update_merge_visibility()

    def _on_target_changed(self, _text):
        self._update_merge_visibility()

    def _update_merge_visibility(self):
        all_images = bool(self.jobs) and all(
            doc_converter.detect_format(path)[1] == "image" for path in self.jobs
        )
        target_is_pdf = self.target_combo.currentText().upper() == "PDF"
        show = all_images and target_is_pdf and len(self.jobs) > 1
        self.merge_checkbox.setVisible(show)
        if not show:
            self.merge_checkbox.setChecked(False)

    def on_choose_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Escolher pasta de destino", self.settings.doc_convert_output_dir
        )
        if folder:
            self.settings.doc_convert_output_dir = folder
            self.folder_label.setText(folder)
            save_settings(self.settings)

    # ------------------------------------------------------------------
    # Conversion run
    # ------------------------------------------------------------------

    def on_convert_clicked(self):
        if not self.jobs or not self.target_combo.currentText():
            return
        target_ext = self.target_combo.currentText().lower()
        output_dir = self.settings.doc_convert_output_dir
        os.makedirs(output_dir, exist_ok=True)

        self._merge_active = self.merge_checkbox.isVisible() and self.merge_checkbox.isChecked()
        self._completed = 0
        self.convert_btn.setEnabled(False)
        self.open_folder_btn.setEnabled(False)

        for widget in self._item_widgets.values():
            widget.set_status("Aguardando")

        self.overall_progress.setRange(0, 1 if self._merge_active else len(self.jobs))
        self.overall_progress.setValue(0)
        self.overall_status_label.setText("Convertendo...")

        self.worker = ConversionWorker(list(self.jobs), output_dir, merge_images=self._merge_active)
        self.worker.set_target_ext(target_ext)
        self.worker.file_started.connect(self._on_file_started)
        self.worker.file_finished.connect(self._on_file_finished)
        self.worker.all_finished.connect(self._on_all_finished)
        self.worker.start()

    def _on_file_started(self, index):
        if self._merge_active:
            return
        widget = self._item_widgets.get(index)
        if widget:
            widget.set_status("Convertendo...")

    def _on_file_finished(self, index, success, message):
        if self._merge_active:
            self.overall_progress.setValue(1)
            if success:
                self.overall_status_label.setText(f"PDF mesclado gerado: {os.path.basename(message)}")
            else:
                self.overall_status_label.setText(f"Erro ao mesclar: {message[:120]}")
            return

        widget = self._item_widgets.get(index)
        if widget:
            if success:
                widget.set_status("Concluído ✓", "StatusDone")
            else:
                widget.set_status(f"Erro ✗ — {message[:60]}", "StatusError")

        self._completed += 1
        self.overall_progress.setValue(self._completed)
        self.overall_status_label.setText(f"{self._completed} de {len(self.jobs)} arquivos convertidos")

    def _on_all_finished(self):
        self.convert_btn.setEnabled(True)
        self.open_folder_btn.setEnabled(True)

    def on_open_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.settings.doc_convert_output_dir))


class DocumentosTab(QWidget):
    """Top-level widget registered as the "Documentos" tab in MainWindow."""

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        sub_tabs = QTabWidget()
        sub_tabs.addTab(OcrSubTab(settings), "🔍 Digitalizar")
        sub_tabs.addTab(ConvertSubTab(settings), "🔄 Converter Formato")
        layout.addWidget(sub_tabs)
