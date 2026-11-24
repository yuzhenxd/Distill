# Distill

把会议录音或会议文本一键提炼为摘要、关键决策与任务看板的原生桌面应用（PySide6 / Qt6）。

- 大模型：DeepSeek 云端 API（JSON Mode），或本地 Ollama（数据不出本机）
- 语音转写：本地 faster-whisper（可选安装），或兼容 OpenAI 的 Whisper API
- 智能任务看板：To Do / In Progress / Done 三列，可改状态、新增、删除
- 导出：JSON、Markdown、飞书消息（可直接推送到飞书机器人 Webhook）
- 历史会议保存在本机 SQLite，首次启动时选择存放的文件夹，之后可在「设置 → 数据存储」中更改，现有记录会一并移过去
- 设置文件固定在 Windows 的 `%APPDATA%\Distill`、macOS 的 `~/Library/Application Support/Distill`，这也是会议记录的默认位置（旧版的 MeetingFlowAI 目录会在首次启动时自动迁移）

## 下载

在 [Releases](https://github.com/yuzhenxd/Distill/releases) 中下载以 `desktop-v` 开头的版本：

- **Windows**：`Distill-windows-x64.zip`，解压后双击 `Distill.exe`。首次运行若出现 SmartScreen 提示，点「更多信息 → 仍要运行」。
- **macOS（Apple 芯片）**：`Distill-macos-arm64.zip`，解压后在 `Distill.app` 上右键选「打开」。应用未签名，若提示「已损坏」，执行 `xattr -cr "/Applications/Distill.app"`。

打开后在「设置」里填写 DeepSeek API Key，或切换到本地 Ollama。

## 从源码运行

```bash
pip install -r requirements.txt
python main.py
```

已在 Python 3.12 上测试。如需离线转写录音，再执行 `pip install faster-whisper`。

## 自己打包

```bash
# macOS：生成 dist/Distill.app
pyinstaller --noconfirm --windowed --name "Distill" --icon assets/icon.icns --add-data "assets/icon.png:assets" main.py

# Windows：生成单文件 dist\Distill.exe
pyinstaller --noconfirm --onefile --windowed --name "Distill" --icon assets/icon.ico --add-data "assets/icon.png:assets" main.py
```

推送 `desktop-v*` 标签（如 `git tag desktop-v1.0.0 && git push origin desktop-v1.0.0`）会触发 GitHub Actions，在 Windows 和 macOS 上各打一份包并发布到 Release。
