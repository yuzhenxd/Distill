"""MeetingFlow AI - PyInstaller 打包入口。

exe 启动后等价于在本目录执行 `streamlit run app.py`，并自动打开浏览器。
"""
from __future__ import annotations

import os
import sys
import threading
import webbrowser

# 确保 PyInstaller 把运行时依赖一并打进来（app.py 是以数据文件形式携带的，
# 静态分析不到它的 import，这里显式引用一次）
import dotenv  # noqa: F401
import openai  # noqa: F401
import pydantic  # noqa: F401

import streamlit.web.cli as stcli

URL = "http://localhost:8501"


def resource_path(name: str) -> str:
    """返回打包后资源文件的真实路径（PyInstaller 解压目录或源码目录）。"""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def open_browser_later() -> None:
    """服务器就绪后打开浏览器（headless 模式下 streamlit 不会自己开）。"""
    import time
    import urllib.request

    for _ in range(60):
        time.sleep(1)
        try:
            urllib.request.urlopen(URL, timeout=2)
            webbrowser.open(URL)
            return
        except Exception:
            continue


def main() -> int:
    app_file = resource_path("app.py")
    sys.argv = [
        "streamlit",
        "run",
        app_file,
        # 冻结环境里必须关掉 streamlit 的开发模式检测，否则启动报错
        "--global.developmentMode=false",
        "--browser.gatherUsageStats=false",
        # headless 跳过 streamlit 首次运行的交互式邮箱提示（否则卡在等待输入）
        "--server.headless=true",
        "--server.port=8501",
    ]
    print(f"MeetingFlow AI 正在启动，稍候浏览器将自动打开 {URL} ...")
    print("关闭本窗口即可退出程序。")
    threading.Thread(target=open_browser_later, daemon=True).start()
    return stcli.main()


if __name__ == "__main__":
    sys.exit(main())
