import os
import sys
from pathlib import Path

APP_NAME = "Distill"
OLD_APP_NAME = "MeetingFlowAI"  # 改名前的数据目录


def data_dir() -> Path:
    """用户数据目录：打包成 exe/app 后程序目录可能只读，所以数据放在系统标准位置。"""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    path = base / APP_NAME
    old = base / OLD_APP_NAME
    if not path.exists() and old.is_dir():
        old.rename(path)  # 沿用改名前的历史会议和设置
    path.mkdir(parents=True, exist_ok=True)
    return path
