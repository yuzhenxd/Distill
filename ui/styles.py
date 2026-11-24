import sys

BG = "#FAF9F5"
SIDEBAR = "#F0EEE6"
SIDEBAR_LINE = "#E5E3DA"
SURFACE = "#FFFFFF"
BORDER = "#E2E0D8"
ACCENT = "#D97757"
ACCENT_HOVER = "#C66546"
TEXT = "#1A1915"
TEXT_2 = "#6B6960"

PRIORITY_COLORS = {  # (文字色, 背景色)
    "高": ("#B4442A", "#FBE7DF"),
    "中": ("#9A6B12", "#FAF0D7"),
    "低": ("#4D7A55", "#E5F0E3"),
}
STATUS_COLORS = {"To Do": "#8B887E", "In Progress": ACCENT, "Done": "#5C8F67"}

if sys.platform == "win32":
    FONT_FAMILY = '"Microsoft YaHei UI", "Segoe UI"'
elif sys.platform == "darwin":
    FONT_FAMILY = '"PingFang SC", "Helvetica Neue"'
else:
    FONT_FAMILY = '"Noto Sans CJK SC", "Noto Sans"'

STYLESHEET = f"""
* {{
    font-family: {FONT_FAMILY};
    color: {TEXT};
    font-size: 14px;
}}
QMainWindow, QWidget#Workspace, QWidget#Page, QScrollArea, QScrollArea > QWidget > QWidget {{
    background: {BG};
}}
QScrollArea {{ border: none; }}
QToolTip {{
    background: {TEXT}; color: {BG}; border: none; padding: 6px 8px; border-radius: 6px;
}}

/* ---------- 侧边栏 ---------- */
QFrame#Sidebar {{
    background: {SIDEBAR};
    border-right: 1px solid {SIDEBAR_LINE};
}}
QLabel#Logo {{ font-size: 17px; font-weight: 600; }}
QLabel#SideSection {{ color: {TEXT_2}; font-size: 12px; padding: 4px 10px; }}
QPushButton#NavButton {{
    text-align: left; padding: 9px 12px; border: none; border-radius: 8px;
    background: transparent; font-size: 14px;
}}
QPushButton#NavButton:hover {{ background: #E6E3D8; }}
QPushButton#NavButton:checked {{ background: {SURFACE}; color: {ACCENT}; font-weight: 600; }}
QPushButton#IconButton {{
    border: none; border-radius: 8px; background: transparent; font-size: 16px;
    color: {TEXT_2}; padding: 4px;
}}
QPushButton#IconButton:hover {{ background: #E6E3D8; color: {TEXT}; }}
QListWidget#History {{
    background: transparent; border: none; outline: none;
}}
QListWidget#History::item {{
    padding: 7px 10px; border-radius: 8px; color: {TEXT};
}}
QListWidget#History::item:hover {{ background: #E6E3D8; }}
QListWidget#History::item:selected {{ background: {SURFACE}; color: {TEXT}; }}

/* ---------- 文字层级 ---------- */
QLabel#H1 {{ font-size: 30px; font-weight: 600; }}
QLabel#H2 {{ font-size: 22px; font-weight: 600; }}
QLabel#H3 {{ font-size: 16px; font-weight: 600; }}
QLabel#Muted {{ color: {TEXT_2}; }}
QLabel#Small {{ color: {TEXT_2}; font-size: 12px; }}
QLabel#Body {{ font-size: 14px; line-height: 160%; }}

/* ---------- 卡片 ---------- */
QFrame#Card {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px;
}}
QFrame#TaskCard {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 10px;
}}
QFrame#TaskCard:hover {{ border-color: #CFCBBF; }}
QFrame#Column {{
    background: #F3F1EA; border: 1px solid {SIDEBAR_LINE}; border-radius: 12px;
}}
QFrame#DropZone {{
    background: {SURFACE}; border: 2px dashed #D6D3C8; border-radius: 16px;
}}
QFrame#DropZone[hover="true"] {{ border-color: {ACCENT}; background: #FDF6F2; }}

/* ---------- 按钮 ---------- */
QPushButton {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 8px;
    padding: 7px 14px;
}}
QPushButton:hover {{ background: #F5F3EC; }}
QPushButton:disabled {{ color: #B5B2A8; }}
QPushButton#Primary {{
    background: {ACCENT}; color: #FFFFFF; border: none; font-weight: 600; padding: 8px 18px;
}}
QPushButton#Primary:hover {{ background: {ACCENT_HOVER}; }}
QPushButton#Primary:disabled {{ background: #E8B9A8; color: #FFFFFF; }}
QPushButton#Pill {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 17px;
    padding: 7px 18px; color: {TEXT};
}}
QPushButton#Pill:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}
QPushButton#Ghost {{
    background: transparent; border: none; color: {TEXT_2}; padding: 4px 8px;
}}
QPushButton#Ghost:hover {{ color: {ACCENT}; }}
QPushButton#Danger {{
    background: transparent; border: none; color: #A8A59B; padding: 2px 6px; font-size: 13px;
}}
QPushButton#Danger:hover {{ color: #C0392B; }}

/* ---------- 输入控件 ---------- */
QLineEdit, QComboBox, QPlainTextEdit, QTextEdit, QDateEdit {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 8px;
    padding: 7px 10px; selection-background-color: #F4D3C5; selection-color: {TEXT};
}}
QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus, QTextEdit:focus {{
    border: 1px solid {ACCENT};
}}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 8px; padding: 4px;
    selection-background-color: #F5EDE7; selection-color: {TEXT}; outline: none;
}}
QComboBox#StatusBox {{ padding: 3px 8px; font-size: 12px; border-radius: 6px; }}
QRadioButton {{ spacing: 8px; }}
QRadioButton::indicator {{
    width: 12px; height: 12px; border-radius: 8px; border: 2px solid #C9C6BB; background: {SURFACE};
}}
QRadioButton::indicator:checked {{
    border: 2px solid {ACCENT};
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
        stop:0 {ACCENT}, stop:0.55 {ACCENT}, stop:0.65 {SURFACE});
}}

/* ---------- 进度条 ---------- */
QProgressBar {{
    background: #ECE9E0; border: none; border-radius: 3px; max-height: 6px;
}}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 3px; }}

/* ---------- 滚动条 ---------- */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #D9D6CC; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #C5C1B5; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #D9D6CC; border-radius: 4px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QMessageBox, QDialog {{ background: {BG}; }}
"""
