"""
ui.py

All GUI components, built with PySide6:
- MainWindow: header, tab bar, URL input, quality/folder controls, download
  queue list, queue controls.
- QueueItemWidget: one row in the download queue (thumbnail, title,
  platform/quality, progress bar, action button).
- SettingsDialog: everything in settings.Settings, editable and persisted.

The GUI never touches yt-dlp directly - all of that goes through
`downloader.DownloadManager`, which emits Qt signals that this module
listens to. Because DownloadManager's worker threads emit those signals,
and Qt auto-queues cross-thread signal/slot connections, none of the code
below has to worry about thread safety.

Theming is entirely centralized in `theme.py` - this module never sets an
inline stylesheet for color/appearance purposes. Every widget that needs to
reflect a changing state (a queue row's status, say) does it by setting a
Qt dynamic property (`status`) and calling `theme.repolish()`, which lets
the one stylesheet installed by `theme.apply_theme()` pick up the change.
"""

import os

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPlainTextEdit, QPushButton, QComboBox, QListWidget,
    QListWidgetItem, QProgressBar, QFileDialog, QDialog, QSpinBox, QCheckBox,
    QMessageBox, QFrame, QTabWidget,
)

from downloader import DownloadItem, DownloadManager
from converter import (
    ConversionItem, ConversionManager, CATEGORY_LABELS, available_targets,
)
from documentos.tab_documentos import DocumentosTab
from settings import Settings, QUALITY_CHOICES, save_settings
from theme import apply_theme as set_app_theme, repolish
from utils import split_urls, platform_icon, find_ffmpeg, ffmpeg_is_working

THUMB_SIZE = QSize(96, 54)
CATEGORY_ICONS = {"video": "🎞", "audio": "🎵", "image": "🖼"}


# ---------------------------------------------------------------------------
# Small shared row-building helpers (consolidates boilerplate that used to
# be duplicated verbatim between QueueItemWidget and ConversionItemWidget)
# ---------------------------------------------------------------------------

def make_progress_bar() -> QProgressBar:
    bar = QProgressBar()
    bar.setRange(0, 100)
    bar.setValue(0)
    bar.setTextVisible(False)
    bar.setFixedHeight(6)
    return bar


def make_row_action_button(on_click) -> QPushButton:
    btn = QPushButton("✕ Cancelar")
    btn.setObjectName("Danger")
    btn.setFixedWidth(140)
    btn.clicked.connect(on_click)
    return btn


def set_card_status(frame: QFrame, status: str) -> None:
    """Set the dynamic "status" property theme.py's QSS uses to color a
    Card row's left border (waiting/active/done/error)."""
    frame.setProperty("status", status)
    repolish(frame)


class QueueItemWidget(QFrame):
    """One row inside the download queue list."""

    def __init__(self, item_id: int, manager: DownloadManager, parent=None):
        super().__init__(parent)
        self.item_id = item_id
        self.manager = manager
        self.setObjectName("Card")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 8, 10, 8)
        outer.setSpacing(4)

        top_row = QHBoxLayout()
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(THUMB_SIZE)
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setStyleSheet("background-color: rgba(255,255,255,15); border-radius: 4px;")
        self.thumb_label.setText("🎬")
        top_row.addWidget(self.thumb_label)

        text_col = QVBoxLayout()
        self.title_label = QLabel("...")
        self.title_label.setStyleSheet("font-weight: 600;")
        self.title_label.setWordWrap(True)
        text_col.addWidget(self.title_label)

        self.meta_label = QLabel("")
        self.meta_label.setObjectName("Dim")
        text_col.addWidget(self.meta_label)
        top_row.addLayout(text_col, stretch=1)

        self.action_btn = make_row_action_button(self._on_action_clicked)
        top_row.addWidget(self.action_btn, alignment=Qt.AlignTop)

        outer.addLayout(top_row)

        bottom_row = QHBoxLayout()
        self.progress_bar = make_progress_bar()
        bottom_row.addWidget(self.progress_bar, stretch=1)

        self.status_label = QLabel(DownloadItem.STATUS_WAITING)
        self.status_label.setFixedWidth(260)
        bottom_row.addWidget(self.status_label)

        outer.addLayout(bottom_row)

    def refresh(self, item: DownloadItem):
        self.title_label.setText(item.title)
        icon = platform_icon(item.platform)
        quality_text = item.actual_quality or item.quality
        self.meta_label.setText(f"{icon} {item.platform}   ·   {quality_text}")

        if item.thumbnail_bytes and self.thumb_label.pixmap() is None:
            pixmap = QPixmap()
            if pixmap.loadFromData(item.thumbnail_bytes):
                scaled = pixmap.scaled(THUMB_SIZE, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                self.thumb_label.setPixmap(scaled)
                self.thumb_label.setText("")

        self.progress_bar.setValue(int(item.progress))

        status = item.status
        if status == DownloadItem.STATUS_DOWNLOADING:
            detail = f"{status}  {int(item.progress)}%"
            if item.speed_text:
                detail += f"   {item.speed_text}"
            if item.eta_text:
                detail += f"   ETA {item.eta_text}"
            self.status_label.setText(detail)
            self.status_label.setObjectName("")
            self.action_btn.setText("✕ Cancelar")
            self.action_btn.setEnabled(True)
            self.progress_bar.setVisible(True)
            set_card_status(self, "active")
        elif status == DownloadItem.STATUS_MERGING:
            self.status_label.setText(status)
            self.action_btn.setText("✕ Cancelar")
            self.action_btn.setEnabled(True)
            self.progress_bar.setVisible(True)
            set_card_status(self, "active")
        elif status == DownloadItem.STATUS_DONE:
            self.status_label.setText(status)
            self.status_label.setObjectName("StatusDone")
            self.action_btn.setText("🗑 Remover")
            self.action_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            set_card_status(self, "done")
        elif status in (DownloadItem.STATUS_ERROR, DownloadItem.STATUS_UNAVAILABLE):
            text = status
            if item.error_message:
                text += f" — {item.error_message[:80]}"
            self.status_label.setText(text)
            self.status_label.setObjectName("StatusError")
            self.action_btn.setText("↻ Tentar novamente")
            self.action_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            set_card_status(self, "error")
        elif status == DownloadItem.STATUS_CANCELLED:
            self.status_label.setText(status)
            self.action_btn.setText("🗑 Remover")
            self.action_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            set_card_status(self, "waiting")
        elif status == DownloadItem.STATUS_FETCHING:
            self.status_label.setText(status)
            self.action_btn.setText("✕ Cancelar")
            self.action_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            set_card_status(self, "active")
        else:  # WAITING
            self.status_label.setText(status)
            self.action_btn.setText("✕ Cancelar")
            self.action_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            set_card_status(self, "waiting")

        repolish(self.status_label)

    def _on_action_clicked(self):
        item = self.manager.get_item(self.item_id)
        if item is None:
            return
        if item.status in (DownloadItem.STATUS_ERROR, DownloadItem.STATUS_UNAVAILABLE):
            self.manager.retry_item(self.item_id)
        elif item.status in (DownloadItem.STATUS_DONE, DownloadItem.STATUS_CANCELLED):
            self.manager.items.pop(self.item_id, None)
            if self.item_id in self.manager.order:
                self.manager.order.remove(self.item_id)
            self.manager.item_removed.emit(self.item_id)
        else:
            self.manager.cancel_item(self.item_id)


class DropZone(QFrame):
    """A drag-and-drop target for the converter tab. Accepts one or more
    local files dropped from Windows Explorer and forwards their paths."""

    def __init__(self, on_files_dropped, parent=None):
        super().__init__(parent)
        self._on_files_dropped = on_files_dropped
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(46)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        label = QLabel("📥 Arraste arquivos aqui, ou clique em \"Selecionar arquivo(s)\"")
        label.setObjectName("Dim")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            self._on_files_dropped(paths)


class ConversionItemWidget(QFrame):
    """One row inside the file-conversion queue list."""

    def __init__(self, item_id: int, manager: ConversionManager, parent=None):
        super().__init__(parent)
        self.item_id = item_id
        self.manager = manager
        self.setObjectName("Card")

        item = manager.get_item(item_id)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 8, 10, 8)
        outer.setSpacing(4)

        top_row = QHBoxLayout()
        icon_label = QLabel(CATEGORY_ICONS.get(item.category, "📄"))
        icon_label.setFixedSize(THUMB_SIZE)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet(
            "background-color: rgba(255,255,255,15); border-radius: 4px; font-size: 22pt;"
        )
        top_row.addWidget(icon_label)

        text_col = QVBoxLayout()
        self.title_label = QLabel(item.filename)
        self.title_label.setStyleSheet("font-weight: 600;")
        self.title_label.setWordWrap(True)
        text_col.addWidget(self.title_label)
        self.meta_label = QLabel("")
        self.meta_label.setObjectName("Dim")
        text_col.addWidget(self.meta_label)
        top_row.addLayout(text_col, stretch=1)

        self.format_combo = QComboBox()
        self.format_combo.setFixedWidth(110)
        if item.category:
            self.format_combo.addItems([f.upper() for f in available_targets(item.category, item.source_ext)])
            idx = self.format_combo.findText(item.target_ext.upper())
            if idx >= 0:
                self.format_combo.setCurrentIndex(idx)
        else:
            self.format_combo.addItem("--")
            self.format_combo.setEnabled(False)
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
        top_row.addWidget(self.format_combo)

        self.action_btn = make_row_action_button(self._on_action_clicked)
        top_row.addWidget(self.action_btn, alignment=Qt.AlignTop)

        outer.addLayout(top_row)

        bottom_row = QHBoxLayout()
        self.progress_bar = make_progress_bar()
        bottom_row.addWidget(self.progress_bar, stretch=1)

        self.status_label = QLabel(item.status)
        self.status_label.setFixedWidth(260)
        bottom_row.addWidget(self.status_label)

        outer.addLayout(bottom_row)

        self.refresh(item)

    def _on_format_changed(self, text):
        if not text or text == "--":
            return
        self.manager.set_target_format(self.item_id, text.lower())

    def refresh(self, item: ConversionItem):
        icon = CATEGORY_ICONS.get(item.category, "📄")
        category_label = CATEGORY_LABELS.get(item.category, "")
        if item.category:
            self.meta_label.setText(f"{icon} {category_label}   ·   .{item.source_ext} → .{item.target_ext}")
        else:
            self.meta_label.setText(f"{icon} .{item.source_ext}")

        self.progress_bar.setValue(int(item.progress))
        self.format_combo.setEnabled(item.status == ConversionItem.STATUS_WAITING and item.category is not None)

        status = item.status
        if status == ConversionItem.STATUS_CONVERTING:
            self.status_label.setText(f"{status}  {int(item.progress)}%")
            self.status_label.setObjectName("")
            self.action_btn.setText("✕ Cancelar")
            self.action_btn.setEnabled(True)
            self.progress_bar.setVisible(True)
            set_card_status(self, "active")
        elif status == ConversionItem.STATUS_DONE:
            self.status_label.setText(status)
            self.status_label.setObjectName("StatusDone")
            self.action_btn.setText("🗑 Remover")
            self.action_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            set_card_status(self, "done")
        elif status in (ConversionItem.STATUS_ERROR, ConversionItem.STATUS_UNSUPPORTED):
            text = status
            if item.error_message:
                text += f" — {item.error_message[:80]}"
            self.status_label.setText(text)
            self.status_label.setObjectName("StatusError")
            self.action_btn.setText(
                "↻ Tentar novamente" if status == ConversionItem.STATUS_ERROR else "🗑 Remover"
            )
            self.action_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            set_card_status(self, "error" if status == ConversionItem.STATUS_ERROR else "waiting")
        elif status == ConversionItem.STATUS_CANCELLED:
            self.status_label.setText(status)
            self.action_btn.setText("🗑 Remover")
            self.action_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            set_card_status(self, "waiting")
        else:  # WAITING
            self.status_label.setText(status)
            self.action_btn.setText("✕ Cancelar")
            self.action_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            set_card_status(self, "waiting")

        repolish(self.status_label)

    def _on_action_clicked(self):
        item = self.manager.get_item(self.item_id)
        if item is None:
            return
        if item.status == ConversionItem.STATUS_ERROR:
            self.manager.retry_item(self.item_id)
        elif item.status in (ConversionItem.STATUS_DONE, ConversionItem.STATUS_CANCELLED,
                              ConversionItem.STATUS_UNSUPPORTED):
            self.manager.items.pop(self.item_id, None)
            if self.item_id in self.manager.order:
                self.manager.order.remove(self.item_id)
            self.manager.item_removed.emit(self.item_id)
        else:
            self.manager.cancel_item(self.item_id)


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurações")
        self.setMinimumWidth(460)
        self.settings = settings

        layout = QVBoxLayout(self)
        grid = QGridLayout()
        grid.setVerticalSpacing(10)
        grid.setHorizontalSpacing(8)
        row = 0

        grid.addWidget(QLabel("Pasta de destino:"), row, 0)
        self.folder_edit = QLineEdit(settings.output_dir)
        self.folder_edit.setReadOnly(True)
        grid.addWidget(self.folder_edit, row, 1)
        browse_btn = QPushButton("📁 Escolher")
        browse_btn.setObjectName("Secondary")
        browse_btn.clicked.connect(self._choose_folder)
        grid.addWidget(browse_btn, row, 2)
        row += 1

        grid.addWidget(QLabel("Qualidade padrão:"), row, 0)
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(QUALITY_CHOICES)
        self.quality_combo.setCurrentText(settings.default_quality)
        grid.addWidget(self.quality_combo, row, 1, 1, 2)
        row += 1

        grid.addWidget(QLabel("Downloads simultâneos:"), row, 0)
        self.max_spin = QSpinBox()
        self.max_spin.setRange(1, 3)
        self.max_spin.setValue(settings.max_simultaneous)
        grid.addWidget(self.max_spin, row, 1, 1, 2)
        row += 1

        grid.addWidget(QLabel("Tema:"), row, 0)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light"])
        self.theme_combo.setCurrentText(settings.theme)
        grid.addWidget(self.theme_combo, row, 1, 1, 2)
        row += 1

        self.ffmpeg_check = QCheckBox("Usar ffmpeg para mesclar áudio/vídeo")
        self.ffmpeg_check.setChecked(settings.use_ffmpeg_merge)
        grid.addWidget(self.ffmpeg_check, row, 0, 1, 3)
        row += 1

        self.thumb_check = QCheckBox("Salvar thumbnail junto com o vídeo")
        self.thumb_check.setChecked(settings.save_thumbnail)
        grid.addWidget(self.thumb_check, row, 0, 1, 3)
        row += 1

        self.meta_check = QCheckBox("Salvar metadados do vídeo (.info.json)")
        self.meta_check.setChecked(settings.save_metadata)
        grid.addWidget(self.meta_check, row, 0, 1, 3)
        row += 1

        grid.addWidget(QLabel("Caminho customizado do ffmpeg:"), row, 0)
        self.ffmpeg_path_edit = QLineEdit(settings.ffmpeg_path)
        self.ffmpeg_path_edit.setPlaceholderText("Deixe em branco para usar o PATH do sistema")
        grid.addWidget(self.ffmpeg_path_edit, row, 1)
        ffmpeg_browse_btn = QPushButton("📁")
        ffmpeg_browse_btn.setObjectName("Secondary")
        ffmpeg_browse_btn.setFixedWidth(40)
        ffmpeg_browse_btn.clicked.connect(self._choose_ffmpeg)
        grid.addWidget(ffmpeg_browse_btn, row, 2)
        row += 1

        layout.addLayout(grid)

        self.ffmpeg_status_label = QLabel()
        layout.addWidget(self.ffmpeg_status_label)
        self._refresh_ffmpeg_status()

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setObjectName("Ghost")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Salvar")
        save_btn.setObjectName("Primary")
        save_btn.clicked.connect(self.accept)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _refresh_ffmpeg_status(self):
        path = find_ffmpeg(self.ffmpeg_path_edit.text().strip())
        if ffmpeg_is_working(path):
            self.ffmpeg_status_label.setText(f"✓ ffmpeg encontrado: {path}")
            self.ffmpeg_status_label.setObjectName("StatusDone")
        else:
            self.ffmpeg_status_label.setText(
                "⚠ ffmpeg não encontrado. Instale-o e adicione ao PATH, ou informe o caminho acima."
            )
            self.ffmpeg_status_label.setObjectName("StatusError")
        repolish(self.ffmpeg_status_label)

    def _choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Escolher pasta de destino", self.folder_edit.text())
        if folder:
            self.folder_edit.setText(folder)

    def _choose_ffmpeg(self):
        path, _ = QFileDialog.getOpenFileName(self, "Selecionar executável do ffmpeg")
        if path:
            self.ffmpeg_path_edit.setText(path)
            self._refresh_ffmpeg_status()

    def apply_to(self, settings: Settings):
        settings.output_dir = self.folder_edit.text().strip() or settings.output_dir
        settings.default_quality = self.quality_combo.currentText()
        settings.max_simultaneous = self.max_spin.value()
        settings.theme = self.theme_combo.currentText()
        settings.use_ffmpeg_merge = self.ffmpeg_check.isChecked()
        settings.save_thumbnail = self.thumb_check.isChecked()
        settings.save_metadata = self.meta_check.isChecked()
        settings.ffmpeg_path = self.ffmpeg_path_edit.text().strip()


class UrlInput(QPlainTextEdit):
    """A QPlainTextEdit dressed up to look/behave like a single-line field,
    but that still accepts multi-line paste (one URL per line) and submits
    on Enter."""

    def __init__(self, on_submit, parent=None):
        super().__init__(parent)
        self._on_submit = on_submit
        self.setPlaceholderText("Cole o link aqui... (um por linha para vários vídeos)")
        self.setFixedHeight(40)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (event.modifiers() & Qt.ShiftModifier):
            self._on_submit()
            return
        super().keyPressEvent(event)


class MainWindow(QMainWindow):
    def __init__(self, manager: DownloadManager, conversion_manager: ConversionManager, settings: Settings):
        super().__init__()
        self.manager = manager
        self.conversion_manager = conversion_manager
        self.settings = settings
        self._widgets: dict[int, QueueItemWidget] = {}
        self._list_items: dict[int, QListWidgetItem] = {}
        self._conv_widgets: dict[int, ConversionItemWidget] = {}
        self._conv_list_items: dict[int, QListWidgetItem] = {}
        self._ffmpeg_warned = False

        self.setWindowTitle("MasterApp")
        self.resize(900, 650)
        self.setMinimumSize(700, 500)

        self._build_ui()
        self._connect_manager_signals()
        self.apply_theme(settings.theme)
        self._check_ffmpeg_on_start()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_downloads_tab(), "⬇ Downloads")
        self.tabs.addTab(self._build_converter_tab(), "🔄 Converter Arquivos")
        self.tabs.addTab(DocumentosTab(self.settings), "📄 Documentos")
        root.addWidget(self.tabs, stretch=1)

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("Header")
        header.setFixedHeight(52)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 0, 16, 0)
        layout.setSpacing(10)

        logo = QLabel("🟥")
        layout.addWidget(logo)
        title = QLabel("MasterApp")
        title.setObjectName("HeaderTitle")
        layout.addWidget(title)
        layout.addStretch(1)

        self.theme_btn = QPushButton()
        self.theme_btn.setObjectName("Ghost")
        self.theme_btn.clicked.connect(self.toggle_theme)
        layout.addWidget(self.theme_btn)

        settings_btn = QPushButton("⚙ Config")
        settings_btn.setObjectName("Secondary")
        settings_btn.clicked.connect(self.open_settings)
        layout.addWidget(settings_btn)

        about_btn = QPushButton("?")
        about_btn.setObjectName("Ghost")
        about_btn.setFixedWidth(36)
        about_btn.clicked.connect(self.show_about)
        layout.addWidget(about_btn)

        self._refresh_theme_button()
        return header

    def _build_queue_footer(self, start_text, on_start, on_pause, on_clear):
        """Shared skeleton for the Downloads/Converter tabs' bottom control
        row: a Primary start button, a Ghost pause button, a Ghost clear
        button, and a status label pinned to the right. Returns the layout
        plus the three widgets callers need to keep mutating."""
        row = QHBoxLayout()
        start_btn = QPushButton(start_text)
        start_btn.setObjectName("Primary")
        start_btn.clicked.connect(on_start)
        row.addWidget(start_btn)

        pause_btn = QPushButton("⏸ Pausar")
        pause_btn.setObjectName("Ghost")
        pause_btn.clicked.connect(on_pause)
        row.addWidget(pause_btn)

        clear_btn = QPushButton("🗑 Limpar concluídos")
        clear_btn.setObjectName("Ghost")
        clear_btn.clicked.connect(on_clear)
        row.addWidget(clear_btn)

        row.addStretch(1)
        status_label = QLabel("")
        status_label.setObjectName("Dim")
        row.addWidget(status_label)

        return row, pause_btn, status_label

    def _build_downloads_tab(self) -> QWidget:
        tab = QWidget()
        body = QVBoxLayout(tab)
        body.setContentsMargins(16, 12, 16, 12)
        body.setSpacing(10)

        # --- URL input row -------------------------------------------------
        input_row = QHBoxLayout()
        self.url_input = UrlInput(self.on_add_clicked)
        input_row.addWidget(self.url_input, stretch=1)
        add_btn = QPushButton("▶ Adicionar")
        add_btn.setObjectName("Primary")
        add_btn.setFixedWidth(110)
        add_btn.clicked.connect(self.on_add_clicked)
        input_row.addWidget(add_btn)
        body.addLayout(input_row)

        self.error_label = QLabel("")
        self.error_label.setObjectName("ErrorLabel")
        self.error_label.setVisible(False)
        body.addWidget(self.error_label)

        # --- quality / folder row ------------------------------------------
        options_row = QHBoxLayout()
        options_row.addWidget(QLabel("Qualidade:"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(QUALITY_CHOICES)
        self.quality_combo.setCurrentText(self.settings.default_quality)
        options_row.addWidget(self.quality_combo)

        options_row.addSpacing(20)
        options_row.addWidget(QLabel("Pasta:"))
        self.folder_label = QLabel(self.settings.output_dir)
        self.folder_label.setObjectName("Dim")
        options_row.addWidget(self.folder_label, stretch=1)
        folder_btn = QPushButton("📁 Escolher")
        folder_btn.setObjectName("Secondary")
        folder_btn.clicked.connect(self.choose_output_folder)
        options_row.addWidget(folder_btn)
        body.addLayout(options_row)

        # --- queue section ---------------------------------------------------
        queue_label = QLabel("FILA DE DOWNLOADS")
        queue_label.setObjectName("SectionLabel")
        body.addWidget(queue_label)

        self.queue_list = QListWidget()
        self.queue_list.setSpacing(6)
        self.queue_list.setSelectionMode(QListWidget.NoSelection)
        self.queue_list.setFocusPolicy(Qt.NoFocus)
        body.addWidget(self.queue_list, stretch=1)

        # --- bottom controls ---------------------------------------------------
        footer, self.pause_btn, self.status_bar_label = self._build_queue_footer(
            "▶ Iniciar tudo", self.on_start_all, self.on_pause, self.manager.clear_completed,
        )
        body.addLayout(footer)
        return tab

    def _build_converter_tab(self) -> QWidget:
        tab = QWidget()
        body = QVBoxLayout(tab)
        body.setContentsMargins(16, 12, 16, 12)
        body.setSpacing(10)

        # --- file picker / drop zone row ------------------------------------
        input_row = QHBoxLayout()
        select_btn = QPushButton("🗂 Selecionar arquivo(s)")
        select_btn.setObjectName("Primary")
        select_btn.clicked.connect(self.on_select_conversion_files)
        input_row.addWidget(select_btn)
        self.drop_zone = DropZone(self.on_files_dropped)
        input_row.addWidget(self.drop_zone, stretch=1)
        body.addLayout(input_row)

        self.conv_error_label = QLabel("")
        self.conv_error_label.setObjectName("ErrorLabel")
        self.conv_error_label.setVisible(False)
        body.addWidget(self.conv_error_label)

        # --- folder row ------------------------------------------------------
        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel("Pasta de destino:"))
        self.conv_folder_label = QLabel(self.settings.output_dir)
        self.conv_folder_label.setObjectName("Dim")
        folder_row.addWidget(self.conv_folder_label, stretch=1)
        conv_folder_btn = QPushButton("📁 Escolher")
        conv_folder_btn.setObjectName("Secondary")
        conv_folder_btn.clicked.connect(self.choose_output_folder)
        folder_row.addWidget(conv_folder_btn)
        body.addLayout(folder_row)

        # --- queue section -----------------------------------------------------
        queue_label = QLabel("ARQUIVOS PARA CONVERTER")
        queue_label.setObjectName("SectionLabel")
        body.addWidget(queue_label)

        self.conv_queue_list = QListWidget()
        self.conv_queue_list.setSpacing(6)
        self.conv_queue_list.setSelectionMode(QListWidget.NoSelection)
        self.conv_queue_list.setFocusPolicy(Qt.NoFocus)
        body.addWidget(self.conv_queue_list, stretch=1)

        # --- bottom controls -----------------------------------------------------
        footer, self.conv_pause_btn, self.conv_status_label = self._build_queue_footer(
            "▶ Converter tudo", self.on_start_all_conversions, self.on_pause_conversions,
            self.conversion_manager.clear_completed,
        )
        body.addLayout(footer)
        return tab

    def _connect_manager_signals(self):
        self.manager.item_added.connect(self._on_item_added)
        self.manager.item_updated.connect(self._on_item_updated)
        self.manager.item_removed.connect(self._on_item_removed)
        self.manager.queue_idle.connect(self._on_queue_idle)
        self.manager.ffmpeg_missing.connect(self._on_ffmpeg_missing)

        self.conversion_manager.item_added.connect(self._on_conv_item_added)
        self.conversion_manager.item_updated.connect(self._on_conv_item_updated)
        self.conversion_manager.item_removed.connect(self._on_conv_item_removed)
        self.conversion_manager.queue_idle.connect(self._on_conv_queue_idle)
        self.conversion_manager.ffmpeg_missing.connect(self._on_ffmpeg_missing)

    # ------------------------------------------------------------------
    # URL input handling
    # ------------------------------------------------------------------

    def on_add_clicked(self):
        text = self.url_input.toPlainText().strip()
        if not text:
            self._show_error("Cole um link antes de adicionar.")
            return

        urls = split_urls(text)
        if not urls:
            self._show_error("URL inválida. Verifique o link e tente novamente.")
            return

        quality = self.quality_combo.currentText()
        for url in urls:
            self.manager.add_url(url, quality)

        self.url_input.clear()
        self.error_label.setVisible(False)

    def _show_error(self, message: str):
        self.error_label.setText(message)
        self.error_label.setVisible(True)

    # ------------------------------------------------------------------
    # Queue signal handlers
    # ------------------------------------------------------------------

    def _on_item_added(self, item_id: int):
        item = self.manager.get_item(item_id)
        if item is None:
            return
        widget = QueueItemWidget(item_id, self.manager)
        widget.refresh(item)

        list_item = QListWidgetItem()
        list_item.setSizeHint(QSize(0, 100))
        self.queue_list.addItem(list_item)
        self.queue_list.setItemWidget(list_item, widget)

        self._widgets[item_id] = widget
        self._list_items[item_id] = list_item

    def _on_item_updated(self, item_id: int):
        item = self.manager.get_item(item_id)
        widget = self._widgets.get(item_id)
        if item is None or widget is None:
            return
        widget.refresh(item)

    def _on_item_removed(self, item_id: int):
        list_item = self._list_items.pop(item_id, None)
        self._widgets.pop(item_id, None)
        if list_item is not None:
            row = self.queue_list.row(list_item)
            if row >= 0:
                self.queue_list.takeItem(row)

    def _on_queue_idle(self):
        self.status_bar_label.setText("Fila concluída.")

    # ------------------------------------------------------------------
    # Converter tab handling
    # ------------------------------------------------------------------

    def on_select_conversion_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Selecionar arquivo(s) para converter")
        if paths:
            self.on_files_dropped(paths)

    def on_files_dropped(self, paths):
        self.conv_error_label.setVisible(False)
        added = 0
        for path in paths:
            if os.path.isfile(path):
                self.conversion_manager.add_file(path)
                added += 1
        if added == 0:
            self.conv_error_label.setText("Nenhum arquivo válido foi selecionado.")
            self.conv_error_label.setVisible(True)

    def on_start_all_conversions(self):
        self.conversion_manager.start_all()
        self.conv_status_label.setText("Convertendo...")

    def on_pause_conversions(self):
        if self.conversion_manager.paused:
            self.conversion_manager.paused = False
            self.conv_pause_btn.setText("⏸ Pausar")
            self.conv_status_label.setText("Convertendo...")
        else:
            self.conversion_manager.pause()
            self.conv_pause_btn.setText("▶ Retomar")
            self.conv_status_label.setText("Pausado (conversões em andamento serão concluídas).")

    def _on_conv_item_added(self, item_id: int):
        item = self.conversion_manager.get_item(item_id)
        if item is None:
            return
        widget = ConversionItemWidget(item_id, self.conversion_manager)

        list_item = QListWidgetItem()
        list_item.setSizeHint(QSize(0, 100))
        self.conv_queue_list.addItem(list_item)
        self.conv_queue_list.setItemWidget(list_item, widget)

        self._conv_widgets[item_id] = widget
        self._conv_list_items[item_id] = list_item

    def _on_conv_item_updated(self, item_id: int):
        item = self.conversion_manager.get_item(item_id)
        widget = self._conv_widgets.get(item_id)
        if item is None or widget is None:
            return
        widget.refresh(item)

    def _on_conv_item_removed(self, item_id: int):
        list_item = self._conv_list_items.pop(item_id, None)
        self._conv_widgets.pop(item_id, None)
        if list_item is not None:
            row = self.conv_queue_list.row(list_item)
            if row >= 0:
                self.conv_queue_list.takeItem(row)

    def _on_conv_queue_idle(self):
        self.conv_status_label.setText("Conversões concluídas.")

    def _on_ffmpeg_missing(self):
        if self._ffmpeg_warned:
            return
        self._ffmpeg_warned = True
        QMessageBox.warning(
            self,
            "ffmpeg não encontrado",
            "O ffmpeg não foi encontrado no PATH do sistema.\n\n"
            "Ele é necessário para mesclar vídeo+áudio em qualidades acima de "
            "360p e para extrair áudio em MP3.\n\n"
            "Baixe em https://ffmpeg.org/download.html, adicione ao PATH do "
            "Windows, ou informe o caminho do executável em "
            "Configurações → Caminho customizado do ffmpeg.",
        )

    # ------------------------------------------------------------------
    # Toolbar / bottom actions
    # ------------------------------------------------------------------

    def choose_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Escolher pasta de destino", self.settings.output_dir)
        if folder:
            self.settings.output_dir = folder
            self.folder_label.setText(folder)
            self.conv_folder_label.setText(folder)
            save_settings(self.settings)

    def on_start_all(self):
        self.manager.start_all()
        self.status_bar_label.setText("Baixando...")

    def on_pause(self):
        if self.manager.paused:
            self.manager.paused = False
            self.pause_btn.setText("⏸ Pausar")
            self.status_bar_label.setText("Baixando...")
        else:
            self.manager.pause()
            self.pause_btn.setText("▶ Retomar")
            self.status_bar_label.setText("Pausado (downloads em andamento serão concluídos).")

    def open_settings(self):
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec() == QDialog.Accepted:
            old_theme = self.settings.theme
            dialog.apply_to(self.settings)
            save_settings(self.settings)
            self.folder_label.setText(self.settings.output_dir)
            self.conv_folder_label.setText(self.settings.output_dir)
            if self.settings.theme != old_theme:
                self.apply_theme(self.settings.theme)
                self._refresh_theme_button()

    def show_about(self):
        QMessageBox.information(
            self,
            "Sobre",
            "MasterApp\n\n"
            "Baixe vídeos do YouTube, Instagram, Twitter/X, TikTok e mais, "
            "usando yt-dlp.\n\n"
            "Cole um link, escolha a qualidade e clique em Adicionar. "
            "Depois, clique em 'Iniciar tudo' para começar a fila.\n\n"
            "Na aba 'Converter Arquivos', envie um arquivo de vídeo, áudio "
            "ou imagem já salvo no seu PC e escolha para qual formato "
            "convertê-lo.",
        )

    def _check_ffmpeg_on_start(self):
        path = find_ffmpeg(self.settings.ffmpeg_path)
        if not ffmpeg_is_working(path):
            self._on_ffmpeg_missing()

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def toggle_theme(self):
        self.settings.theme = "light" if self.settings.theme == "dark" else "dark"
        save_settings(self.settings)
        self.apply_theme(self.settings.theme)
        self._refresh_theme_button()

    def _refresh_theme_button(self):
        # Label shows the icon/word for what clicking will switch TO.
        self.theme_btn.setText("☀ Claro" if self.settings.theme == "dark" else "🌙 Escuro")

    def apply_theme(self, theme_name: str):
        set_app_theme(QApplication.instance(), theme_name)

    def closeEvent(self, event):
        self.manager.shutdown()
        self.conversion_manager.shutdown()
        super().closeEvent(event)
