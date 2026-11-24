import os
import sys
from pathlib import Path

APP_NAME = "MeetingFlowAI"


def data_dir() -> Path:
    """用户数据目录：打包成 exe/app 后程序目录可能只读，所以数据放在系统标准位置。"""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    path = base / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path
