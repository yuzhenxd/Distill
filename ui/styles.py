import sys

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

# 配色方案：日间仿 Claude 桌面端的暖白，夜间为暖灰深色
THEMES = {
    "light": {
        "BG": "#FAF9F5", "SIDEBAR": "#F0EEE6", "SIDEBAR_LINE": "#E5E3DA", "SURFACE": "#FFFFFF",
        "BORDER": "#E2E0D8", "ACCENT": "#D97757", "ACCENT_HOVER": "#C66546", "TEXT": "#1A1915",
        "TEXT_2": "#6B6960", "HOVER": "#E6E3D8", "BUTTON_HOVER": "#F5F3EC", "COLUMN": "#F3F1EA",
        "TASK_HOVER": "#CFCBBF", "DROP_BORDER": "#D6D3C8", "DROP_HOVER": "#FDF6F2",
        "DISABLED": "#B5B2A8", "PRIMARY_DISABLED": "#E8B9A8", "DANGER": "#A8A59B",
        "DANGER_HOVER": "#C0392B", "SELECTION": "#F4D3C5", "POPUP_SELECT": "#F5EDE7",
        "RADIO": "#C9C6BB", "TRACK": "#ECE9E0", "SCROLL": "#D9D6CC", "SCROLL_HOVER": "#C5C1B5",
        "DIVIDER": "#EFEDE6", "TOAST_BG": "#1A1915", "TOAST_FG": "#FAF9F5",
        "TRANSLATION": "#C66546", "SUCCESS": "#4D7A55", "FAILURE": "#B4442A",
        # 标签：(文字色, 背景色)
        "high": ("#B4442A", "#FBE7DF"), "mid": ("#9A6B12", "#FAF0D7"),
        "low": ("#4D7A55", "#E5F0E3"), "neutral": ("#3D3B35", "#EFEDE6"),
    },
    "dark": {
        "BG": "#262624", "SIDEBAR": "#1F1E1D", "SIDEBAR_LINE": "#34332F", "SURFACE": "#30302D",
        "BORDER": "#42413C", "ACCENT": "#D97757", "ACCENT_HOVER": "#E38A6C", "TEXT": "#F0EEE6",
        "TEXT_2": "#A6A39A", "HOVER": "#2E2D2A", "BUTTON_HOVER": "#393834", "COLUMN": "#2B2A28",
        "TASK_HOVER": "#5A5852", "DROP_BORDER": "#4F4D48", "DROP_HOVER": "#3A2E29",
        "DISABLED": "#6E6B63", "PRIMARY_DISABLED": "#7A4B3B", "DANGER": "#807D74",
        "DANGER_HOVER": "#EE7A66", "SELECTION": "#6B4232", "POPUP_SELECT": "#4A3A32",
        "RADIO": "#625F58", "TRACK": "#3A3936", "SCROLL": "#4C4A45", "SCROLL_HOVER": "#5E5C56",
        "DIVIDER": "#383733", "TOAST_BG": "#F0EEE6", "TOAST_FG": "#1A1915",
        "TRANSLATION": "#EBA085", "SUCCESS": "#8CC294", "FAILURE": "#EE8A72",
        "high": ("#F2A48E", "#4A2B23"), "mid": ("#E6C27C", "#41361F"),
        "low": ("#9DCCA1", "#273B2B"), "neutral": ("#D8D5CB", "#3A3936"),
    },
}
THEME_NAMES = [("日间", "light"), ("夜间", "dark")]

# 状态圆点用中间调，两套配色下都看得清
STATUS_COLORS = {"To Do": "#8B887E", "In Progress": "#D97757", "Done": "#5C8F67"}

if sys.platform == "win32":
    FONT_FAMILY = '"Microsoft YaHei UI", "Segoe UI"'
elif sys.platform == "darwin":
    FONT_FAMILY = '"PingFang SC", "Helvetica Neue"'
else:
    FONT_FAMILY = '"Noto Sans CJK SC", "Noto Sans"'


def apply_theme(app: QApplication, name: str) -> None:
    """同时设置调色板和样式表：只设样式表时，下拉列表、菜单、对话框会沿用系统深色模式的调色板，出现黑底。"""
    c = THEMES.get(name, THEMES["light"])
    app.setPalette(_palette(c))
    app.setStyleSheet(_stylesheet(c))


def _palette(c: dict) -> QPalette:
    p = QPalette()
    for role, key in (
        (QPalette.Window, "BG"), (QPalette.WindowText, "TEXT"), (QPalette.Base, "SURFACE"),
        (QPalette.AlternateBase, "BG"), (QPalette.Text, "TEXT"), (QPalette.Button, "SURFACE"),
        (QPalette.ButtonText, "TEXT"), (QPalette.Highlight, "POPUP_SELECT"),
        (QPalette.HighlightedText, "TEXT"), (QPalette.ToolTipBase, "TOAST_BG"),
        (QPalette.ToolTipText, "TOAST_FG"), (QPalette.PlaceholderText, "TEXT_2"),
        (QPalette.Link, "ACCENT"), (QPalette.BrightText, "TEXT"),
    ):
        p.setColor(role, QColor(c[key]))
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        p.setColor(QPalette.Disabled, role, QColor(c["DISABLED"]))
    return p


def _stylesheet(c: dict) -> str:
    badges = "\n".join(
        f'QLabel#Badge[kind="{k}"] {{ color: {c[k][0]}; background: {c[k][1]}; }}'
        for k in ("high", "mid", "low", "neutral")
    )
    return f"""
* {{
    font-family: {FONT_FAMILY};
    color: {c['TEXT']};
    font-size: 14px;
}}
QMainWindow, QWidget#Workspace, QWidget#Page, QScrollArea, QScrollArea > QWidget > QWidget {{
    background: {c['BG']};
}}
QScrollArea {{ border: none; }}
QToolTip {{
    background: {c['TOAST_BG']}; color: {c['TOAST_FG']}; border: none; padding: 6px 8px; border-radius: 6px;
}}
QLabel#Toast {{
    background: {c['TOAST_BG']}; color: {c['TOAST_FG']}; border-radius: 10px; padding: 10px 16px; font-size: 13px;
}}

/* ---------- 侧边栏 ---------- */
QFrame#Sidebar {{
    background: {c['SIDEBAR']};
    border-right: 1px solid {c['SIDEBAR_LINE']};
}}
QLabel#Logo {{ font-size: 17px; font-weight: 600; }}
QLabel#SideSection {{ color: {c['TEXT_2']}; font-size: 12px; padding: 4px 10px; }}
QPushButton#NavButton {{
    text-align: left; padding: 9px 12px; border: none; border-radius: 8px;
    background: transparent; font-size: 14px;
}}
QPushButton#NavButton:hover {{ background: {c['HOVER']}; }}
QPushButton#NavButton:checked {{ background: {c['SURFACE']}; color: {c['ACCENT']}; font-weight: 600; }}
QPushButton#IconButton {{
    border: none; border-radius: 8px; background: transparent; font-size: 16px;
    color: {c['TEXT_2']}; padding: 4px;
}}
QPushButton#IconButton:hover {{ background: {c['HOVER']}; color: {c['TEXT']}; }}
QListWidget#History {{
    background: transparent; border: none; outline: none;
}}
QListWidget#History::item {{
    padding: 7px 10px; border-radius: 8px; color: {c['TEXT']};
}}
QListWidget#History::item:hover {{ background: {c['HOVER']}; }}
QListWidget#History::item:selected {{ background: {c['SURFACE']}; color: {c['TEXT']}; }}

/* ---------- 文字层级 ---------- */
QLabel#H1 {{ font-size: 30px; font-weight: 600; }}
QLabel#H2 {{ font-size: 22px; font-weight: 600; }}
QLabel#H3 {{ font-size: 16px; font-weight: 600; }}
QLabel#Muted {{ color: {c['TEXT_2']}; }}
QLabel#Small {{ color: {c['TEXT_2']}; font-size: 12px; }}
QLabel#Body {{ font-size: 14px; line-height: 160%; }}
QLabel#Translation {{ color: {c['TRANSLATION']}; font-size: 14px; }}
QLabel#Success {{ color: {c['SUCCESS']}; font-size: 12px; }}
QLabel#Failure {{ color: {c['FAILURE']}; font-size: 12px; }}
QLabel#Badge {{ border-radius: 9px; padding: 2px 8px; font-size: 12px; }}
{badges}

/* ---------- 卡片 ---------- */
QFrame#Card {{
    background: {c['SURFACE']}; border: 1px solid {c['BORDER']}; border-radius: 12px;
}}
QFrame#TaskCard {{
    background: {c['SURFACE']}; border: 1px solid {c['BORDER']}; border-radius: 10px;
}}
QFrame#TaskCard:hover {{ border-color: {c['TASK_HOVER']}; }}
QFrame#TaskRow {{ border-top: 1px solid {c['DIVIDER']}; }}
QFrame#Divider {{ background: {c['DIVIDER']}; }}
QFrame#Column {{
    background: {c['COLUMN']}; border: 1px solid {c['SIDEBAR_LINE']}; border-radius: 12px;
}}
QFrame#DropZone {{
    background: {c['SURFACE']}; border: 2px dashed {c['DROP_BORDER']}; border-radius: 16px;
}}
QFrame#DropZone[hover="true"] {{ border-color: {c['ACCENT']}; background: {c['DROP_HOVER']}; }}

/* ---------- 按钮 ---------- */
QPushButton {{
    background: {c['SURFACE']}; border: 1px solid {c['BORDER']}; border-radius: 8px;
    padding: 7px 14px;
}}
QPushButton:hover {{ background: {c['BUTTON_HOVER']}; }}
QPushButton:disabled {{ color: {c['DISABLED']}; }}
QPushButton#Primary {{
    background: {c['ACCENT']}; color: #FFFFFF; border: none; font-weight: 600; padding: 8px 18px;
}}
QPushButton#Primary:hover {{ background: {c['ACCENT_HOVER']}; }}
QPushButton#Primary:disabled {{ background: {c['PRIMARY_DISABLED']}; color: #FFFFFF; }}
QPushButton#Pill {{
    background: {c['SURFACE']}; border: 1px solid {c['BORDER']}; border-radius: 17px;
    padding: 7px 18px; color: {c['TEXT']};
}}
QPushButton#Pill:hover, QPushButton#Pill[selected="true"] {{ border-color: {c['ACCENT']}; color: {c['ACCENT']}; }}
QPushButton#Pill[selected="true"] {{ font-weight: 600; }}
QPushButton#Ghost {{
    background: transparent; border: none; color: {c['TEXT_2']}; padding: 4px 8px;
}}
QPushButton#Ghost:hover {{ color: {c['ACCENT']}; }}
QPushButton#Danger {{
    background: transparent; border: none; color: {c['DANGER']}; padding: 2px 6px; font-size: 13px;
}}
QPushButton#Danger:hover {{ color: {c['DANGER_HOVER']}; }}

/* ---------- 输入控件 ---------- */
QLineEdit, QComboBox, QPlainTextEdit, QTextEdit, QDateEdit {{
    background: {c['SURFACE']}; border: 1px solid {c['BORDER']}; border-radius: 8px;
    padding: 7px 10px; selection-background-color: {c['SELECTION']}; selection-color: {c['TEXT']};
}}
QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus, QTextEdit:focus {{
    border: 1px solid {c['ACCENT']};
}}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {c['SURFACE']}; border: 1px solid {c['BORDER']}; border-radius: 8px; padding: 4px;
    selection-background-color: {c['POPUP_SELECT']}; selection-color: {c['TEXT']}; outline: none;
}}
QComboBox QAbstractItemView::item {{ padding: 5px 8px; border-radius: 6px; color: {c['TEXT']}; }}
QComboBox QAbstractItemView::item:hover, QComboBox QAbstractItemView::item:selected {{
    background: {c['POPUP_SELECT']}; color: {c['TEXT']};
}}
QComboBox#StatusBox {{ padding: 3px 8px; font-size: 12px; border-radius: 6px; }}
QMenu {{
    background: {c['SURFACE']}; border: 1px solid {c['BORDER']}; border-radius: 8px; padding: 4px;
}}
QMenu::item {{ padding: 6px 14px; border-radius: 6px; }}
QMenu::item:selected {{ background: {c['POPUP_SELECT']}; color: {c['TEXT']}; }}
QRadioButton, QCheckBox {{ spacing: 8px; }}
QRadioButton::indicator {{
    width: 12px; height: 12px; border-radius: 8px; border: 2px solid {c['RADIO']}; background: {c['SURFACE']};
}}
QRadioButton::indicator:checked {{
    border: 2px solid {c['ACCENT']};
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
        stop:0 {c['ACCENT']}, stop:0.55 {c['ACCENT']}, stop:0.65 {c['SURFACE']});
}}

/* ---------- 进度条 ---------- */
QProgressBar {{
    background: {c['TRACK']}; border: none; border-radius: 3px; max-height: 6px;
}}
QProgressBar::chunk {{ background: {c['ACCENT']}; border-radius: 3px; }}

/* ---------- 滚动条 ---------- */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {c['SCROLL']}; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {c['SCROLL_HOVER']}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {c['SCROLL']}; border-radius: 4px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QMessageBox, QDialog {{ background: {c['BG']}; }}
"""
