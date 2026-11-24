import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow

# 打包后资源在 PyInstaller 的解压目录里，源码运行时在本文件旁边
ICON = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "assets" / "icon.png"


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Distill")
    app.setWindowIcon(QIcon(str(ICON)))
    app.setStyle("Fusion")
    window = MainWindow()  # 按设置里的配色方案应用调色板和样式表
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
