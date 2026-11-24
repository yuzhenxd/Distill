from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget,
)

from .styles import PRIORITY_COLORS

MAX_CONTENT_WIDTH = 920


def label(text: str, name: str = "", wrap: bool = False, selectable: bool = False) -> QLabel:
    w = QLabel(text)
    if name:
        w.setObjectName(name)
    w.setWordWrap(wrap)
    if selectable:
        w.setTextInteractionFlags(Qt.TextSelectableByMouse)
    return w


def card() -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("Card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(22, 18, 22, 20)
    layout.setSpacing(10)
    return frame, layout


def clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            # 先隐藏再延迟删除：deleteLater 生效前旧控件仍是可见子控件，会叠在新内容下面
            item.widget().hide()
            item.widget().deleteLater()
        elif item.layout():
            clear_layout(item.layout())


def badge(text: str, fg: str, bg: str) -> QLabel:
    w = QLabel(text)
    w.setStyleSheet(
        f"color: {fg}; background: {bg}; border-radius: 9px; padding: 2px 8px; font-size: 12px;"
    )
    return w


def priority_badge(priority: str) -> QLabel:
    fg, bg = PRIORITY_COLORS.get(priority, PRIORITY_COLORS["中"])
    return badge(f"{priority}优先级", fg, bg)


class Page(QScrollArea):
    """可滚动页面：内容区水平居中、最大宽度 920px、四周留白充足。"""

    def __init__(self, scroll: bool = True, max_width: int = MAX_CONTENT_WIDTH):
        super().__init__()
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        if not scroll:
            self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer = QWidget()
        outer.setObjectName("Page")
        row = QHBoxLayout(outer)
        row.setContentsMargins(40, 36, 40, 40)
        self.content = QWidget()
        self.content.setObjectName("Page")
        self.content.setMaximumWidth(max_width)
        self.body = QVBoxLayout(self.content)
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(16)
        row.addStretch(1)
        row.addWidget(self.content, 100)
        row.addStretch(1)
        self.setWidget(outer)

    def header(self, title: str, subtitle: str = "") -> None:
        self.body.addWidget(label(title, "H2"))
        if subtitle:
            self.body.addWidget(label(subtitle, "Muted", wrap=True))
        self.body.addSpacing(6)


class EmptyState(QWidget):
    def __init__(self, icon: str, title: str, hint: str):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 80, 0, 80)
        layout.setSpacing(8)
        for text, name, size in ((icon, "", 40), (title, "H3", 0), (hint, "Muted", 0)):
            w = label(text, name, wrap=True)
            w.setAlignment(Qt.AlignCenter)
            if size:
                w.setStyleSheet(f"font-size: {size}px;")
            layout.addWidget(w)
