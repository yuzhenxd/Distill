# MeetingFlow AI

把冗长的会议录音转写文本一键提炼为**会议摘要 + 关键决策 + 可视化任务看板**，并导出标准 JSON 对接飞书 / Trello。

## 项目结构

```text
meetingflow_ai/
├── app.py              # Streamlit 前端：输入、看板、导出
├── agent.py            # LLM 调用（DeepSeek / Ollama 双引擎）、异常处理、音频转写
├── schemas.py          # Pydantic 数据模型与字段校验
├── requirements.txt    # 依赖清单
├── .env.example        # 环境变量示例
└── README.md
```

## 方式一：直接下载 Windows EXE（免装 Python）

到 [Releases](https://github.com/yuzhenxd/MeetingFlow-AI/releases) 下载最新的 `MeetingFlowAI-windows.zip`，解压后双击 `MeetingFlowAI/MeetingFlowAI.exe`，浏览器会自动打开 `http://localhost:8501`。DeepSeek API Key 在左侧边栏填写即可。

EXE 由 GitHub Actions 在 Windows 机器上用 PyInstaller 自动构建（见 `.github/workflows/build-exe.yml`），每次推送 `v*` 标签自动发布。

## 方式二：源码运行（Windows）

在 PowerShell 或 CMD 中执行（需 Python 3.10+，[python.org](https://www.python.org/downloads/) 安装时勾选 *Add Python to PATH*）：

```powershell
cd meetingflow_ai

# 1. 创建并激活虚拟环境
python -m venv .venv
.venv\Scripts\activate
# 若 PowerShell 提示禁止运行脚本，先执行：
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 API Key（二选一）
copy .env.example .env     # 然后用记事本编辑 .env 填入真实 Key
# 或临时设置环境变量：
# PowerShell: $env:DEEPSEEK_API_KEY="sk-xxxx"
# CMD:        set DEEPSEEK_API_KEY=sk-xxxx

# 4. 启动
streamlit run app.py
```

浏览器会自动打开 `http://localhost:8501`。

macOS / Linux 的差别只有激活命令：`source .venv/bin/activate`。

## 课堂演示（10 秒链路）

1. 侧边栏确认引擎为 **DeepSeek 云端 API** 且已填 Key；
2. 点击侧边栏 **「🎬 加载模拟会议纪要」**；
3. 点击主区域 **「🚀 开始智能提炼」**；
4. 展示摘要、决策、任务看板（拖动状态下拉框演示 To Do → Done）、JSON 下载。

## 推理引擎切换

| 引擎 | base_url | model | 说明 |
| --- | --- | --- | --- |
| DeepSeek 云端 | `https://api.deepseek.com` | `deepseek-chat` | 高精度，强制 JSON Mode |
| 本地 Ollama | `http://localhost:11434/v1` | `llama3` | 敏感数据不出内网 |

本地模式需先安装 [Ollama for Windows](https://ollama.com/download/windows) 并执行 `ollama pull llama3`，两套引擎共用同一份 `openai` SDK 调用代码。

## 可选：真实音频转写

```powershell
pip install faster-whisper
```

未安装时上传 `.mp3/.wav` 会自动降级为模拟转写文本，不影响演示链路。

## 已处理的异常

- 401 API Key 无效、402 余额不足、429 限流（自动退避重试）、5xx 服务端错误
- 网络超时 / 连接失败自动重试 3 次；Ollama 未启动时给出明确提示
- 模型输出非法 JSON 时三级兜底解析（直接解析 → 剥离 ```json 围栏 → 截取首个 `{...}`），再经 Pydantic 字段校验与同义值归一（如 `high`/`高` → `High`）
- Windows 记事本 `.txt` 常见的 UTF-8 BOM / GBK / UTF-16 编码自动识别
