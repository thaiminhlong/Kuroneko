"""
Application styling and theme definitions.
Dark theme with orange accent.
"""


class Colors:
    """Color palette for the application."""
    # Base colors
    BG_DARKEST = "#0D0D0D"
    BG_DARKER = "#121212"
    BG_DARK = "#1A1A1A"
    BG_MEDIUM = "#1E1E1E"
    BG_LIGHT = "#252525"
    BG_LIGHTER = "#2D2D2D"
    BG_HOVER = "#333333"
    
    # Text colors
    TEXT_PRIMARY = "#FFFFFF"
    TEXT_SECONDARY = "#B0B0B0"
    TEXT_MUTED = "#707070"
    TEXT_DISABLED = "#505050"
    
    # Accent colors
    ACCENT = "#FF7A18"
    ACCENT_HOVER = "#FF9A48"
    ACCENT_PRESSED = "#E56A10"
    ACCENT_MUTED = "#663300"
    
    # Status colors
    SUCCESS = "#4CAF50"
    WARNING = "#FFC107"
    ERROR = "#F44336"
    INFO = "#2196F3"
    
    # Border colors
    BORDER = "#3A3A3A"
    BORDER_LIGHT = "#4A4A4A"
    BORDER_FOCUS = ACCENT
    
    # Progress bar
    PROGRESS_BG = "#2D2D2D"
    PROGRESS_FG = ACCENT


STYLES = f"""
/* ==================== Global ==================== */
QWidget {{
    background-color: {Colors.BG_DARKER};
    color: {Colors.TEXT_PRIMARY};
    font-family: "Segoe UI", "SF Pro Display", "Helvetica Neue", sans-serif;
    font-size: 13px;
}}

QMainWindow {{
    background-color: {Colors.BG_DARKEST};
}}

/* ==================== Sidebar ==================== */
#sidebar {{
    background-color: {Colors.BG_DARKEST};
    border-right: 1px solid {Colors.BORDER};
    min-width: 200px;
    max-width: 200px;
}}

#sidebar_title {{
    font-size: 18px;
    font-weight: 600;
    color: {Colors.ACCENT};
    padding: 20px 15px 10px 15px;
}}

#nav_button {{
    background-color: transparent;
    border: none;
    border-radius: 6px;
    padding: 12px 15px;
    text-align: left;
    color: {Colors.TEXT_SECONDARY};
    font-size: 14px;
    margin: 2px 8px;
}}

#nav_button:hover {{
    background-color: {Colors.BG_HOVER};
    color: {Colors.TEXT_PRIMARY};
}}

#nav_button:checked {{
    background-color: {Colors.ACCENT_MUTED};
    color: {Colors.ACCENT};
    font-weight: 500;
}}

/* ==================== Content Area ==================== */
#content_area {{
    background-color: {Colors.BG_DARKER};
}}

#page_title {{
    font-size: 24px;
    font-weight: 600;
    color: {Colors.TEXT_PRIMARY};
    padding: 20px 25px 10px 25px;
}}

/* ==================== Cards/Panels ==================== */
#card {{
    background-color: {Colors.BG_DARK};
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
    padding: 15px;
}}

#panel {{
    background-color: {Colors.BG_MEDIUM};
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
}}

/* ==================== Buttons ==================== */
QPushButton {{
    background-color: {Colors.BG_LIGHT};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    padding: 8px 16px;
    color: {Colors.TEXT_PRIMARY};
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: {Colors.BG_HOVER};
    border-color: {Colors.BORDER_LIGHT};
}}

QPushButton:pressed {{
    background-color: {Colors.BG_LIGHTER};
}}

QPushButton:disabled {{
    background-color: {Colors.BG_DARK};
    color: {Colors.TEXT_DISABLED};
    border-color: {Colors.BG_LIGHT};
}}

#primary_button {{
    background-color: {Colors.ACCENT};
    border: none;
    color: {Colors.BG_DARKEST};
    font-weight: 600;
}}

#primary_button:hover {{
    background-color: {Colors.ACCENT_HOVER};
}}

#primary_button:pressed {{
    background-color: {Colors.ACCENT_PRESSED};
}}

#primary_button:disabled {{
    background-color: {Colors.ACCENT_MUTED};
    color: {Colors.TEXT_MUTED};
}}

#danger_button {{
    background-color: transparent;
    border: 1px solid {Colors.ERROR};
    color: {Colors.ERROR};
}}

#danger_button:hover {{
    background-color: {Colors.ERROR};
    color: {Colors.TEXT_PRIMARY};
}}

/* ==================== Inputs ==================== */
QLineEdit, QSpinBox, QDoubleSpinBox {{
    background-color: {Colors.BG_LIGHT};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    padding: 8px 12px;
    color: {Colors.TEXT_PRIMARY};
    selection-background-color: {Colors.ACCENT};
}}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {Colors.ACCENT};
}}

QLineEdit:disabled {{
    background-color: {Colors.BG_DARK};
    color: {Colors.TEXT_DISABLED};
}}

QTextEdit, QPlainTextEdit {{
    background-color: {Colors.BG_LIGHT};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    padding: 10px;
    color: {Colors.TEXT_PRIMARY};
    selection-background-color: {Colors.ACCENT};
}}

QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {Colors.ACCENT};
}}

/* ==================== ComboBox ==================== */
QComboBox {{
    background-color: {Colors.BG_LIGHT};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    padding: 8px 12px;
    color: {Colors.TEXT_PRIMARY};
    min-width: 120px;
}}

QComboBox:hover {{
    border-color: {Colors.BORDER_LIGHT};
}}

QComboBox:focus {{
    border-color: {Colors.ACCENT};
}}

QComboBox::drop-down {{
    border: none;
    width: 30px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {Colors.TEXT_SECONDARY};
    margin-right: 10px;
}}

QComboBox QAbstractItemView {{
    background-color: {Colors.BG_MEDIUM};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    padding: 4px;
    selection-background-color: {Colors.ACCENT_MUTED};
}}

/* ==================== Table/List ==================== */
QTableWidget, QTableView {{
    background-color: {Colors.BG_DARK};
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
    gridline-color: {Colors.BORDER};
    selection-background-color: {Colors.ACCENT_MUTED};
}}

QTableWidget::item, QTableView::item {{
    padding: 8px;
    border-bottom: 1px solid {Colors.BORDER};
}}

QTableWidget::item:selected, QTableView::item:selected {{
    background-color: {Colors.ACCENT_MUTED};
    color: {Colors.ACCENT};
}}

QTableWidget::item:hover, QTableView::item:hover {{
    background-color: {Colors.BG_HOVER};
}}

QHeaderView::section {{
    background-color: {Colors.BG_MEDIUM};
    color: {Colors.TEXT_SECONDARY};
    padding: 10px 8px;
    border: none;
    border-bottom: 1px solid {Colors.BORDER};
    font-weight: 600;
}}

QListWidget {{
    background-color: {Colors.BG_DARK};
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
    padding: 4px;
}}

QListWidget::item {{
    padding: 10px;
    border-radius: 4px;
    margin: 2px;
}}

QListWidget::item:selected {{
    background-color: {Colors.ACCENT_MUTED};
    color: {Colors.ACCENT};
}}

QListWidget::item:hover {{
    background-color: {Colors.BG_HOVER};
}}

/* ==================== Progress Bar ==================== */
QProgressBar {{
    background-color: {Colors.PROGRESS_BG};
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {Colors.ACCENT};
    border-radius: 4px;
}}

/* ==================== Scroll Bars ==================== */
QScrollBar:vertical {{
    background-color: {Colors.BG_DARK};
    width: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:vertical {{
    background-color: {Colors.BG_LIGHTER};
    border-radius: 6px;
    min-height: 30px;
    margin: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {Colors.BG_HOVER};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background-color: {Colors.BG_DARK};
    height: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:horizontal {{
    background-color: {Colors.BG_LIGHTER};
    border-radius: 6px;
    min-width: 30px;
    margin: 2px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {Colors.BG_HOVER};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* ==================== Splitter ==================== */
QSplitter::handle {{
    background-color: {Colors.BORDER};
}}

QSplitter::handle:horizontal {{
    width: 2px;
}}

QSplitter::handle:vertical {{
    height: 2px;
}}

/* ==================== Tab Widget ==================== */
QTabWidget::pane {{
    background-color: {Colors.BG_DARK};
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
    padding: 10px;
}}

QTabBar::tab {{
    background-color: {Colors.BG_MEDIUM};
    border: none;
    padding: 10px 20px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    color: {Colors.TEXT_SECONDARY};
}}

QTabBar::tab:selected {{
    background-color: {Colors.BG_DARK};
    color: {Colors.ACCENT};
}}

QTabBar::tab:hover:!selected {{
    background-color: {Colors.BG_HOVER};
}}

/* ==================== Labels ==================== */
#section_label {{
    font-size: 12px;
    font-weight: 600;
    color: {Colors.TEXT_MUTED};
    text-transform: uppercase;
    letter-spacing: 1px;
}}

#value_label {{
    color: {Colors.TEXT_PRIMARY};
    font-size: 14px;
}}

/* ==================== Log Console ==================== */
#log_console {{
    background-color: {Colors.BG_DARKEST};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    font-family: "Cascadia Code", "Fira Code", "Consolas", monospace;
    font-size: 12px;
    padding: 10px;
}}

/* ==================== Toggle Switch ==================== */
#toggle {{
    background-color: {Colors.BG_LIGHT};
    border: none;
    border-radius: 12px;
    min-width: 44px;
    max-width: 44px;
    min-height: 24px;
    max-height: 24px;
}}

#toggle:checked {{
    background-color: {Colors.ACCENT};
}}

/* ==================== Tooltips ==================== */
QToolTip {{
    background-color: {Colors.BG_MEDIUM};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BORDER};
    border-radius: 4px;
    padding: 6px 10px;
}}

/* ==================== Status Badges ==================== */
#badge_queued {{
    background-color: {Colors.TEXT_MUTED};
    color: {Colors.TEXT_PRIMARY};
    border-radius: 10px;
    padding: 2px 8px;
    font-size: 11px;
}}

#badge_downloading {{
    background-color: {Colors.INFO};
    color: {Colors.TEXT_PRIMARY};
    border-radius: 10px;
    padding: 2px 8px;
    font-size: 11px;
}}

#badge_completed {{
    background-color: {Colors.SUCCESS};
    color: {Colors.TEXT_PRIMARY};
    border-radius: 10px;
    padding: 2px 8px;
    font-size: 11px;
}}

#badge_failed {{
    background-color: {Colors.ERROR};
    color: {Colors.TEXT_PRIMARY};
    border-radius: 10px;
    padding: 2px 8px;
    font-size: 11px;
}}

/* ==================== CheckBox ==================== */
QCheckBox {{
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid {Colors.BORDER};
    background-color: {Colors.BG_LIGHT};
}}

QCheckBox::indicator:checked {{
    background-color: {Colors.ACCENT};
    border-color: {Colors.ACCENT};
}}

QCheckBox::indicator:hover {{
    border-color: {Colors.ACCENT};
}}
"""
