"""
theme.py

Centralized theme system for MasterApp: two complete color palettes (dark
default, light alternate), a single stylesheet builder, and one
`apply_theme()` entry point the rest of the app calls instead of ever
setting an inline per-widget stylesheet for theming purposes.

Also home to `repolish()`, a tiny Qt-styling helper shared by every widget
that recolors itself based on a dynamic property (status-colored queue
rows, status-colored labels) - Qt caches style results per widget and
won't notice a property change on its own, so every one of those call
sites needs this exact two-line dance. Centralizing it here means it's
written once instead of four times.
"""

from PySide6.QtWidgets import QApplication

# ---------------------------------------------------------------------------
# Palettes
# ---------------------------------------------------------------------------

DARK = {
    "bg_primary":     "#0f0f0f",   # main window background
    "bg_secondary":   "#1a1a1a",   # tab content background
    "bg_surface":     "#242424",   # cards, list rows, input fields
    "bg_hover":       "#2e2e2e",   # hover state
    "bg_active":      "#333333",   # pressed/active state
    "accent":         "#e63946",   # primary red - main CTAs
    "accent_hover":   "#c1121f",   # darker red on hover
    "accent_alt":     "#f4a261",   # orange - secondary actions
    "success":        "#2dc653",   # green - completed status
    "warning":        "#f4a261",   # orange - warnings
    "error":          "#e63946",   # red - errors
    "text_primary":   "#f2f2f2",   # main text
    "text_secondary": "#a0a0a0",   # labels, hints
    "text_disabled":  "#555555",   # disabled elements
    "border":         "#2e2e2e",   # subtle borders
    "border_strong":  "#444444",   # visible separators
    "tab_active":     "#e63946",   # active tab underline
}

LIGHT = {
    "bg_primary":     "#f5f5f5",
    "bg_secondary":   "#ffffff",
    "bg_surface":     "#ebebeb",
    "bg_hover":       "#e0e0e0",
    "bg_active":      "#d5d5d5",
    "accent":         "#d62828",
    "accent_hover":   "#a31621",
    "accent_alt":     "#e76f51",
    "success":        "#2d6a4f",
    "warning":        "#e76f51",
    "error":          "#d62828",
    "text_primary":   "#1a1a1a",
    "text_secondary": "#555555",
    "text_disabled":  "#aaaaaa",
    "border":         "#d0d0d0",
    "border_strong":  "#b0b0b0",
    "tab_active":     "#d62828",
}

THEMES = {"dark": DARK, "light": LIGHT}

# Status values understood by the QFrame#Card[status=...] selectors below.
# Every queue/file-list row widget sets one of these via
# `widget.setProperty("status", ...)` + `repolish(widget)`.
STATUS_WAITING = "waiting"
STATUS_ACTIVE = "active"
STATUS_DONE = "done"
STATUS_ERROR = "error"


def build_stylesheet(theme_name: str) -> str:
    c = THEMES.get(theme_name, DARK)
    return f"""
    QWidget {{
        background-color: {c['bg_primary']};
        color: {c['text_primary']};
        font-family: "Segoe UI", Arial, sans-serif;
        font-size: 10pt;
    }}
    QMainWindow {{
        background-color: {c['bg_primary']};
    }}

    /* --- Header ------------------------------------------------------- */
    QFrame#Header {{
        background-color: {c['bg_primary']};
        border-bottom: 1px solid {c['border']};
    }}
    QLabel#HeaderTitle {{
        font-size: 18pt;
        font-weight: bold;
        color: {c['text_primary']};
    }}
    QLabel#SectionLabel {{
        font-size: 10pt;
        font-weight: 600;
        color: {c['text_secondary']};
    }}

    /* --- Cards / queue rows -------------------------------------------- */
    /* Status is set dynamically per row via setProperty("status", ...) so
       the left border color always reflects the item's current state
       without any inline setStyleSheet() call anywhere in the codebase. */
    QFrame#Card {{
        background-color: {c['bg_surface']};
        border-radius: 8px;
        border: none;
        border-left: 4px solid {c['border']};
    }}
    QFrame#Card[status="waiting"] {{ border-left: 4px solid {c['border']}; }}
    QFrame#Card[status="active"]  {{ border-left: 4px solid {c['accent']}; }}
    QFrame#Card[status="done"]    {{ border-left: 4px solid {c['success']}; }}
    QFrame#Card[status="error"]   {{ border-left: 4px solid {c['error']}; }}

    /* --- Inputs --------------------------------------------------------- */
    QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QSpinBox {{
        background-color: {c['bg_surface']};
        border: 1px solid {c['border_strong']};
        border-radius: 6px;
        padding: 6px;
        color: {c['text_primary']};
    }}
    QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus {{
        border: 1px solid {c['accent']};
    }}
    QCheckBox {{
        color: {c['text_primary']};
    }}

    /* --- Buttons: 4 distinct variants ------------------------------------ */
    QPushButton {{
        background-color: {c['bg_surface']};
        color: {c['text_primary']};
        border: 1px solid {c['border_strong']};
        border-radius: 6px;
        padding: 8px 20px;
    }}
    QPushButton:hover {{
        background-color: {c['bg_hover']};
    }}
    QPushButton:disabled {{
        background-color: {c['bg_surface']};
        color: {c['text_disabled']};
        border-color: {c['border']};
    }}

    /* Primary: main action - Adicionar, Converter, Iniciar tudo */
    QPushButton#Primary {{
        background-color: {c['accent']};
        color: #ffffff;
        font-weight: bold;
        border: none;
    }}
    QPushButton#Primary:hover {{
        background-color: {c['accent_hover']};
    }}
    QPushButton#Primary:disabled {{
        background-color: {c['bg_surface']};
        color: {c['text_disabled']};
    }}

    /* Secondary: support actions - Escolher pasta, Remover todos, Config */
    QPushButton#Secondary {{
        background-color: {c['bg_surface']};
        color: {c['text_primary']};
        border: 1px solid {c['border_strong']};
    }}
    QPushButton#Secondary:hover {{
        background-color: {c['bg_hover']};
    }}

    /* Ghost: low priority - Pausar, Limpar concluidos, ? about */
    QPushButton#Ghost {{
        background-color: transparent;
        color: {c['text_secondary']};
        border: 1px solid {c['border']};
    }}
    QPushButton#Ghost:hover {{
        background-color: {c['bg_surface']};
        color: {c['text_primary']};
    }}

    /* Danger: destructive - per-row [X] delete/cancel button */
    QPushButton#Danger {{
        background-color: transparent;
        color: {c['error']};
        border: 1px solid transparent;
        border-radius: 4px;
    }}
    QPushButton#Danger:hover {{
        background-color: rgba(230, 57, 70, 0.15);
        border: 1px solid {c['error']};
    }}

    /* --- Lists / scroll areas --------------------------------------------- */
    QListWidget {{
        background-color: transparent;
        border: none;
    }}
    QScrollArea {{
        border: none;
    }}

    /* --- Progress bar: slim, rounded, accent fill --------------------------- */
    QProgressBar {{
        background-color: {c['bg_surface']};
        border-radius: 3px;
        text-align: center;
        color: {c['text_primary']};
        height: 6px;
    }}
    QProgressBar::chunk {{
        background-color: {c['accent']};
        border-radius: 3px;
    }}

    /* --- Status/caption labels --------------------------------------------- */
    QLabel#ErrorLabel {{ color: {c['error']}; }}
    QLabel#StatusDone {{ color: {c['success']}; }}
    QLabel#StatusError {{ color: {c['error']}; }}
    QLabel#Dim {{ color: {c['text_secondary']}; font-size: 8pt; }}

    /* --- Tab bar: flat, underline-only active indicator --------------------- */
    QTabWidget::pane {{
        border: none;
        background-color: {c['bg_primary']};
    }}
    QTabBar {{
        background-color: {c['bg_primary']};
    }}
    QTabBar::tab {{
        background-color: transparent;
        color: {c['text_secondary']};
        padding: 10px 18px;
        margin-right: 4px;
        border: none;
        border-bottom: 3px solid transparent;
        font-size: 10pt;
    }}
    QTabBar::tab:selected {{
        color: {c['text_primary']};
        border-bottom: 3px solid {c['tab_active']};
        font-weight: 600;
    }}
    QTabBar::tab:hover {{
        color: {c['text_primary']};
    }}

    /* --- Drag-and-drop zone ------------------------------------------------- */
    QFrame#DropZone {{
        background-color: {c['bg_surface']};
        border: 2px dashed {c['border_strong']};
        border-radius: 8px;
    }}
    QFrame#DropZone:hover {{
        border: 2px dashed {c['accent']};
    }}
    """


def apply_theme(app: QApplication, theme_name: str) -> None:
    """The single place that pushes a stylesheet onto the whole
    application. Call this once (on startup, and again whenever the user
    toggles the theme) - never set an inline stylesheet on a widget just
    to theme it."""
    app.setStyleSheet(build_stylesheet(theme_name))


def repolish(widget) -> None:
    """Force a widget to re-evaluate its stylesheet after a dynamic
    property (e.g. Card's "status") changed - Qt caches style results per
    widget and won't notice the property change on its own."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)
