"""Кольори та стилі (QSS) для темної й світлої теми."""

PALETTES = {
    "dark": {
        "bg": "#0B0F17", "sidebar": "#0E131D", "surface": "#141A26", "surface2": "#1A2131",
        "hover": "#202939", "border": "#242D3F", "text": "#E7EBF3", "muted": "#8B95A9",
        "faint": "#5D677B", "accent": "#3B82F6", "accent2": "#22D3EE", "accent_text": "#FFFFFF",
        "success": "#22C55E", "warning": "#F59E0B", "danger": "#EF4444",
        "success_bg": "#12301F", "warning_bg": "#33260D", "danger_bg": "#3A1518", "accent_bg": "#16264A",
        "track": "#232B3B",
    },
    "light": {
        "bg": "#F3F5F9", "sidebar": "#FFFFFF", "surface": "#FFFFFF", "surface2": "#F1F4F9",
        "hover": "#E9EEF6", "border": "#E1E6EE", "text": "#131A27", "muted": "#5F6B7F",
        "faint": "#98A2B3", "accent": "#2563EB", "accent2": "#0891B2", "accent_text": "#FFFFFF",
        "success": "#16A34A", "warning": "#D97706", "danger": "#DC2626",
        "success_bg": "#DCFCE7", "warning_bg": "#FEF3C7", "danger_bg": "#FEE2E2", "accent_bg": "#DBEAFE",
        "track": "#E4E9F1",
    },
}


class Theme:
    """Поточна палітра; віджети з власним малюванням читають кольори звідси."""
    name = "dark"
    c = PALETTES["dark"]

    @classmethod
    def set(cls, name):
        cls.name = name if name in PALETTES else "dark"
        cls.c = PALETTES[cls.name]


def stylesheet(check_icon="", arrow_icon=""):
    c = Theme.c
    check = f"image: url({check_icon});" if check_icon else ""
    arrow = f"image: url({arrow_icon});" if arrow_icon else ""
    return f"""
* {{ font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif; font-size: 10pt; color: {c['text']}; }}
QMainWindow, QDialog, #central {{ background: {c['bg']}; }}
QWidget#page {{ background: {c['bg']}; }}
QToolTip {{ background: {c['surface2']}; color: {c['text']}; border: 1px solid {c['border']};
    padding: 6px 8px; border-radius: 6px; }}

/* ── бокова панель ── */
#sidebar {{ background: {c['sidebar']}; border-right: 1px solid {c['border']}; }}
#brandTitle {{ font-size: 13pt; font-weight: 700; }}
#brandSub {{ color: {c['muted']}; font-size: 8.5pt; }}
#navSection {{ color: {c['faint']}; font-size: 8pt; font-weight: 600; letter-spacing: 1px;
    padding: 12px 14px 4px 14px; }}
QPushButton#nav {{ text-align: left; padding: 9px 14px; border: none; border-radius: 9px;
    background: transparent; color: {c['muted']}; font-weight: 500; }}
QPushButton#nav:hover {{ background: {c['hover']}; color: {c['text']}; }}
QPushButton#nav:checked {{ background: {c['accent_bg']}; color: {c['text']}; font-weight: 600; }}
#connBox {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 12px; }}
#connTitle {{ font-weight: 600; }}
#connSub {{ color: {c['muted']}; font-size: 8.5pt; }}

/* ── заголовок сторінки ── */
#pageTitle {{ font-size: 19pt; font-weight: 700; }}
#pageSub {{ color: {c['muted']}; }}

/* ── картки ── */
#card {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 14px; }}
#cardTitle {{ font-size: 11pt; font-weight: 600; }}
#cardSub, #muted {{ color: {c['muted']}; }}
#faint {{ color: {c['faint']}; font-size: 8.5pt; }}
#tile {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 14px; }}
#tile[selected="true"] {{ border: 1px solid {c['accent']}; background: {c['surface2']}; }}
#tileLabel {{ color: {c['muted']}; font-size: 9pt; }}
#tileValue {{ font-size: 20pt; font-weight: 700; }}
#tileUnit {{ color: {c['muted']}; font-size: 9pt; }}
#heroTitle {{ font-size: 17pt; font-weight: 700; }}
#mono {{ font-family: "Cascadia Mono", Consolas, monospace; }}
#vin {{ font-family: "Cascadia Mono", Consolas, monospace; font-size: 13pt; font-weight: 600;
    letter-spacing: 1px; }}
#hint {{ background: {c['surface2']}; border: 1px solid {c['border']}; border-radius: 10px;
    padding: 10px 12px; color: {c['muted']}; }}
#banner {{ background: {c['danger_bg']}; border-radius: 10px; padding: 10px 12px; }}

/* ── кнопки ── */
QPushButton {{ background: {c['surface2']}; border: 1px solid {c['border']}; border-radius: 9px;
    padding: 8px 16px; font-weight: 600; }}
QPushButton:hover {{ background: {c['hover']}; }}
QPushButton:pressed {{ background: {c['border']}; }}
QPushButton:disabled {{ color: {c['faint']}; background: {c['surface']}; }}
QPushButton#primary {{ background: {c['accent']}; border: 1px solid {c['accent']}; color: {c['accent_text']}; }}
QPushButton#primary:hover {{ background: {c['accent2']}; border-color: {c['accent2']}; }}
QPushButton#primary:disabled {{ background: {c['surface2']}; border-color: {c['border']}; color: {c['faint']}; }}
QPushButton#danger {{ background: transparent; border: 1px solid {c['danger']}; color: {c['danger']}; }}
QPushButton#danger:hover {{ background: {c['danger_bg']}; }}
QPushButton#danger:disabled {{ border-color: {c['border']}; color: {c['faint']}; }}
QPushButton#ghost {{ background: transparent; border: none; color: {c['muted']}; padding: 6px 10px; }}
QPushButton#ghost:hover {{ color: {c['text']}; background: {c['hover']}; }}
QPushButton#choice {{ border-radius: 12px; background: {c['surface']}; }}
QPushButton#choice:checked {{ border: 2px solid {c['accent']}; background: {c['accent_bg']}; }}
#choiceTitle {{ font-weight: 600; background: transparent; }}
#choiceText {{ color: {c['muted']}; font-size: 9pt; background: transparent; }}
QPushButton#seg {{ border-radius: 8px; padding: 6px 14px; background: transparent; border: none; color: {c['muted']}; }}
QPushButton#seg:checked {{ background: {c['surface']}; color: {c['text']}; border: 1px solid {c['border']}; }}
#segBox {{ background: {c['surface2']}; border: 1px solid {c['border']}; border-radius: 10px; }}

/* ── поля вводу ── */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{ background: {c['surface2']}; border: 1px solid {c['border']};
    border-radius: 8px; padding: 6px 10px; min-height: 20px; selection-background-color: {c['accent']}; }}
QLineEdit:focus, QComboBox:focus {{ border: 1px solid {c['accent']}; }}
QComboBox {{ padding-right: 30px; }}
QComboBox:hover {{ border: 1px solid {c['faint']}; }}
QComboBox::drop-down {{ border: none; width: 30px; subcontrol-origin: padding; subcontrol-position: center right; }}
QComboBox::down-arrow {{ width: 14px; height: 14px; {arrow} }}
QComboBox QAbstractItemView {{ background: {c['surface']}; border: 1px solid {c['border']};
    selection-background-color: {c['accent_bg']}; selection-color: {c['text']}; outline: 0; padding: 4px; }}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 5px; border: 1px solid {c['faint']};
    background: {c['surface2']}; }}
QCheckBox::indicator:checked {{ background: {c['accent']}; border-color: {c['accent']}; {check} }}
QListWidget::indicator {{ width: 18px; height: 18px; border-radius: 5px; border: 1px solid {c['faint']};
    background: {c['surface2']}; }}
QListWidget::indicator:checked {{ background: {c['accent']}; border-color: {c['accent']}; {check} }}

/* ── таблиці й списки ── */
QTableWidget, QListWidget, QTreeWidget {{ background: {c['surface']}; border: none; border-radius: 12px;
    gridline-color: transparent; alternate-background-color: {c['surface2']}; outline: 0; }}
QTableWidget::item, QListWidget::item {{ padding: 6px 8px; border-bottom: 1px solid {c['border']}; }}
QTableWidget::item:selected, QListWidget::item:selected {{ background: {c['accent_bg']}; color: {c['text']}; }}
QHeaderView::section {{ background: {c['surface']}; color: {c['muted']}; border: none;
    border-bottom: 1px solid {c['border']}; padding: 8px; font-weight: 600; }}
QTableCornerButton::section {{ background: {c['surface']}; border: none; }}
QPlainTextEdit, QTextEdit {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 12px;
    padding: 8px; selection-background-color: {c['accent']}; }}

/* ── прокрутка ── */
QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {c['border']}; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {c['faint']}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {c['border']}; border-radius: 4px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QProgressBar {{ background: transparent; border: none; max-height: 3px; }}
QProgressBar::chunk {{ background: {c['accent']}; border-radius: 1px; }}
QTabWidget::pane {{ border: none; }}
QTabBar {{ background: transparent; border: none; }}
QTabBar::tab {{ background: transparent; color: {c['muted']}; padding: 8px 14px; border: none;
    border-bottom: 2px solid transparent; font-weight: 600; }}
QTabBar::tab:selected {{ color: {c['text']}; border-bottom: 2px solid {c['accent']}; }}
QMessageBox {{ background: {c['surface']}; }}
QMessageBox QLabel {{ min-width: 340px; }}
#statusBar {{ background: {c['sidebar']}; border-top: 1px solid {c['border']}; }}
#statusText {{ color: {c['muted']}; font-size: 9pt; }}
"""
