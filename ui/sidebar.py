from PySide6.QtCore import QPropertyAnimation, QEasingCurve, Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QListWidget, QListWidgetItem, QMenu,
    QPushButton, QVBoxLayout,
)

from .widgets import label

SIDEBAR_WIDTH = 240

NAV_ITEMS = [
    ("🎙️", "新建会议解析"),
    ("📋", "智能任务看板"),
    ("📤", "导出与同步"),
    ("⚙️", "模型与 API 设置"),
]


class Sidebar(QFrame):
    page_selected = Signal(int)
    meeting_selected = Signal(str)
    meeting_delete_requested = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("Sidebar")
        self.setFixedWidth(SIDEBAR_WIDTH)
        self._anim = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 18, 12, 14)
        layout.setSpacing(4)

        top = QHBoxLayout()
        top.setContentsMargins(8, 0, 0, 0)
        logo = label("✳ MeetingFlow AI", "Logo")
        logo.setStyleSheet("font-size: 17px; font-weight: 600;")
        top.addWidget(logo)
        top.addStretch()
        self.collapse_btn = QPushButton("«")
        self.collapse_btn.setObjectName("IconButton")
        self.collapse_btn.setToolTip("收起侧边栏（Ctrl+B）")
        self.collapse_btn.setFixedSize(28, 28)
        top.addWidget(self.collapse_btn)
        layout.addLayout(top)
        layout.addSpacing(18)

        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        for i, (icon, text) in enumerate(NAV_ITEMS):
            btn = QPushButton(f"{icon}  {text}")
            btn.setObjectName("NavButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            self.group.addButton(btn, i)
            layout.addWidget(btn)
        self.group.idClicked.connect(self.page_selected.emit)

        layout.addSpacing(18)
        layout.addWidget(label("历史会议", "SideSection"))
        self.history = QListWidget()
        self.history.setObjectName("History")
        self.history.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.history.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.history.setContextMenuPolicy(Qt.CustomContextMenu)
        self.history.itemClicked.connect(lambda it: self.meeting_selected.emit(it.data(Qt.UserRole)))
        self.history.customContextMenuRequested.connect(self._history_menu)
        layout.addWidget(self.history, 1)
        self.empty_hint = label("还没有会议记录", "Small")
        self.empty_hint.setContentsMargins(10, 0, 0, 0)
        layout.addWidget(self.empty_hint)

    def set_page(self, index: int) -> None:
        self.group.button(index).setChecked(True)

    def set_history(self, meetings: list[dict], current_id: str | None) -> None:
        self.history.clear()
        for m in meetings:
            item = QListWidgetItem(f"{m['title']}")
            item.setToolTip(f"{m['title']}\n{m['created_at']}")
            item.setData(Qt.UserRole, m["id"])
            self.history.addItem(item)
            if m["id"] == current_id:
                item.setSelected(True)
        self.empty_hint.setVisible(not meetings)

    def _history_menu(self, pos) -> None:
        item = self.history.itemAt(pos)
        if item is None:
            return
        menu = QMenu(self)
        delete = menu.addAction("删除此会议")
        if menu.exec(self.history.mapToGlobal(pos)) is delete:
            self.meeting_delete_requested.emit(item.data(Qt.UserRole))

    def animate_visible(self, visible: bool) -> None:
        if visible:
            self.show()
        start, end = (0, SIDEBAR_WIDTH) if visible else (SIDEBAR_WIDTH, 0)
        self.setMinimumWidth(0)
        anim = QPropertyAnimation(self, b"maximumWidth", self)
        anim.setDuration(180)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.setStartValue(start)
        anim.setEndValue(end)
        if not visible:
            anim.finished.connect(self.hide)
        else:
            anim.finished.connect(lambda: self.setFixedWidth(SIDEBAR_WIDTH))
        anim.start()
        self._anim = anim
