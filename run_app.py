"""MeetingFlow AI - PyInstaller 打包入口。

exe 启动后等价于在本目录执行 `streamlit run app.py`，并自动打开浏览器。
"""
from __future__ import annotations

import os
import sys

# 确保 PyInstaller 把运行时依赖一并打进来（app.py 是以数据文件形式携带的，
# 静态分析不到它的 import，这里显式引用一次）
import dotenv  # noqa: F401
import openai  # noqa: F401
import pydantic  # noqa: F401

import streamlit.web.cli as stcli


def resource_path(name: str) -> str:
    """返回打包后资源文件的真实路径（PyInstaller 解压目录或源码目录）。"""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def main() -> int:
    app_file = resource_path("app.py")
    sys.argv = [
        "streamlit",
        "run",
        app_file,
        # 冻结环境里必须关掉 streamlit 的开发模式检测，否则启动报错
        "--global.developmentMode=false",
        "--browser.gatherUsageStats=false",
        "--server.port=8501",
    ]
    print("MeetingFlow AI 正在启动，浏览器将自动打开 http://localhost:8501 ...")
    print("关闭本窗口即可退出程序。")
    return stcli.main()


if __name__ == "__main__":
    sys.exit(main())
