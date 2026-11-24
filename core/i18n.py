"""界面语言。源码里的界面文字一律用中文书写，英文界面时按原文查表替换。

带变量的文字写成 str.format 模板，例如 tr("找到 {n} 个本地模型", n=3)。
存进数据库的数据（任务状态、优先级、会议内容）不经过这里，只翻译显示出来的文字。
"""

UI_LANGUAGES = [("中文", "zh"), ("English", "en")]

_language = "zh"


def set_language(lang: str) -> None:
    global _language
    _language = lang if lang in ("zh", "en") else "zh"


def tr(text: str, **kwargs) -> str:
    if _language == "en":
        text = EN.get(text, text)
    return text.format(**kwargs) if kwargs else text


EN = {
    # ---- 侧边栏 ----
    "会议": "Meetings",
    "翻译": "Translate",
    "任务状态": "Tasks",
    "导出": "Export",
    "设置": "Settings",
    "收起侧边栏（Ctrl+B）": "Hide sidebar (Ctrl+B)",
    "展开侧边栏（Ctrl+B）": "Show sidebar (Ctrl+B)",
    "历史会议": "History",
    "还没有会议记录": "No meetings yet",
    "删除此会议": "Delete this meeting",

    # ---- 主窗口 ----
    "删除会议": "Delete meeting",
    "确定删除「{title}」及其所有任务吗？此操作无法撤销。":
        "Delete \"{title}\" and all its tasks? This cannot be undone.",
    "已删除会议": "Meeting deleted",
    "解析完成：识别到 {n} 个行动项": "Analysis complete: {n} action items found",
    "解析失败": "Analysis failed",
    "无法开始实时翻译": "Cannot start live translation",
    "无法开始录音": "Cannot start recording",
    "实时翻译记录 {time}": "Live translation {time}",
    "实时录音 · 译为 {target}": "Live recording · into {target}",
    "macOS 没有允许本程序使用麦克风，或麦克风被静音。\n\n"
    "请打开「系统设置 → 隐私与安全性 → 麦克风」，打开 Distill 的开关"
    "（从终端运行源码时打开「终端」或启动它的程序），然后重启本程序再录音。":
        "macOS has not allowed this app to use the microphone, or the microphone is muted.\n\n"
        "Open System Settings → Privacy & Security → Microphone and turn on Distill "
        "(when running from source, turn on Terminal or whichever app launched it), "
        "then restart this app and record again.",
    "Windows 没有允许桌面应用使用麦克风，或麦克风被静音。\n\n"
    "请打开「设置 → 隐私和安全性 → 麦克风」，打开「允许桌面应用访问麦克风」，"
    "并检查声音设置里的输入音量，然后再录音。":
        "Windows has not allowed desktop apps to use the microphone, or the microphone is muted.\n\n"
        "Open Settings → Privacy & security → Microphone, turn on \"Let desktop apps access your "
        "microphone\", check the input volume in Sound settings, then record again.",
    "请检查系统的麦克风权限和输入音量，然后再录音。":
        "Check the system's microphone permission and input volume, then record again.",
    "麦克风没有声音": "No sound from the microphone",
    "录音开始 2 秒内收到的全是静音，已停止录音。":
        "Only silence was received in the first 2 seconds, so recording was stopped.",
    "没有识别到语音内容，本次未保存记录。": "No speech was recognized, so nothing was saved.",
    "录音已保存到历史会议，正在生成会议纪要和行动项…":
        "Recording saved to History. Generating the minutes and action items…",
    "已保存到历史会议「{title}」，识别到 {n} 个行动项。":
        "Saved to History as \"{title}\", {n} action items found.",
    "原文与译文已保存到历史会议，但生成纪要失败：{message}":
        "The transcript and translation were saved to History, but generating the minutes failed: {message}",
    "前往设置": "Open Settings",
    "好的": "OK",
    "设置已保存": "Settings saved",
    "找到 {n} 个本地模型": "Found {n} local models",
    "Ollama 中还没有模型，请先执行 ollama pull": "Ollama has no models yet. Run ollama pull first.",
    "推送失败": "Push failed",
    "实时录音": "Live recording",
    "正在录音或生成纪要。已识别的内容都已保存，但尚未处理的片段和会议纪要会丢失，确定要退出吗？":
        "Recording or generating minutes. Everything recognized so far is saved, but unprocessed "
        "segments and the minutes will be lost. Quit anyway?",
    "正在解析": "Analyzing",
    "会议仍在解析中，确定要退出吗？": "The meeting is still being analyzed. Quit anyway?",
    "正在录音或处理中，请结束后再切换语言": "Busy recording or processing. Switch the language when it finishes.",

    # ---- 会议（上传与解析结果） ----
    "会议录音或文本 (*.mp3 *.wav *.m4a *.txt *.md)": "Meeting audio or text (*.mp3 *.wav *.m4a *.txt *.md)",
    "拖拽会议录音或文本到这里": "Drop a meeting recording or transcript here",
    "或点击选择文件 · 支持 .mp3 / .wav / .m4a / .txt / .md":
        "or click to choose a file · .mp3 / .wav / .m4a / .txt / .md",
    "选择会议文件": "Choose a meeting file",
    "不支持的文件格式：{name}": "Unsupported file type: {name}",
    "今天要整理哪场会议？": "Which meeting shall we go over today?",
    "上传录音或会议文本，Distill 会为你提炼摘要、关键决策，并把行动项排进任务看板。":
        "Upload a recording or transcript. Distill writes the summary and key decisions, "
        "and puts the action items on the task board.",
    "加载内置演示会议": "Load the demo meeting",
    "准备中…": "Preparing…",
    "＋ 新建解析": "＋ New analysis",
    "会议摘要": "Summary",
    "（模型未给出摘要）": "(The model gave no summary)",
    "关键决策": "Key decisions",
    "（无）": "(None)",
    "行动项 · {n}": "Action items · {n}",
    "在任务看板中管理 →": "Manage on the task board →",
    "会议中没有识别到明确的行动项。": "No clear action items were found in this meeting.",
    "原文与译文 · 译为 {target}": "Transcript and translation · into {target}",
    "导出与同步": "Export & sync",
    "待定": "TBD",
    "未定": "Not set",

    # ---- 翻译（实时翻译记录） ----
    "实时翻译记录": "Live Translation",
    "边说边转写、边翻译。记录会自动保存到历史会议，结束后自动生成会议纪要和行动项。":
        "Speech is transcribed and translated as you talk. The record is saved to History, "
        "and the minutes and action items are generated when you stop.",
    "麦克风": "Microphone",
    "重新检测麦克风": "Detect microphones again",
    "翻译为": "Translate into",
    "● 开始录音": "● Start recording",
    "■ 结束并保存": "■ Stop and save",
    "准备就绪": "Ready",
    "查看会议纪要 →": "View minutes →",
    "未检测到麦克风": "No microphone found",
    "还没有开始": "Not started yet",
    "点击「开始录音」，说话内容会逐段显示原文与译文。":
        "Click \"Start recording\". Each segment appears with its transcript and translation.",
    "● 录音中 {time}": "● Recording {time}",
    "录音已结束，正在处理剩余片段": "Recording stopped. Processing the remaining segments",
    " · {n} 段识别翻译中…": " · {n} segments being transcribed and translated…",

    # ---- 任务状态（看板） ----
    "待办 To Do": "To Do",
    "进行中 In Progress": "In Progress",
    "已完成 Done": "Done",
    "高": "High",
    "中": "Medium",
    "低": "Low",
    "{p}优先级": "{p} priority",
    "新增任务": "New task",
    "例如：整理 v1.2 需求文档": "e.g. Write up the v1.2 requirements",
    "暂不设定": "No deadline",
    "任务内容": "Task",
    "负责人": "Assignee",
    "截止时间": "Deadline",
    "优先级": "Priority",
    "状态": "Status",
    "添加": "Add",
    "取消": "Cancel",
    "任务内容不能为空": "The task cannot be empty",
    "删除任务": "Delete task",
    "原文：“{quote}”": "Source: \"{quote}\"",
    "还没有打开任何会议": "No meeting is open",
    "先在「会议」中解析一场会议，或从左侧历史记录中选择。":
        "Analyze a meeting under Meetings first, or pick one from History on the left.",
    "智能任务看板": "Task Board",
    "{title} · 共 {n} 项，已完成 {done} 项": "{title} · {n} tasks, {done} done",
    "＋ 新增任务": "＋ New task",
    "＋ 添加": "＋ Add",
    "确定删除任务「{title}」吗？": "Delete the task \"{title}\"?",

    # ---- 导出 ----
    "飞书消息": "Feishu message",
    "JSON 文件 (*.json)": "JSON file (*.json)",
    "Markdown 文件 (*.md)": "Markdown file (*.md)",
    "还没有可导出的会议": "No meeting to export",
    "解析一场会议后，可在这里导出 JSON / Markdown 或推送到飞书。":
        "Once a meeting is analyzed, export it here as JSON or Markdown, or push it to Feishu.",
    "导出与同步": "Export & Sync",
    "当前会议：{title}": "Current meeting: {title}",
    "复制到剪贴板": "Copy to clipboard",
    "保存为文件…": "Save as file…",
    "推送到飞书群": "Push to a Feishu group",
    "在飞书群设置 → 群机器人 → 添加「自定义机器人」，复制 Webhook 地址粘贴到下方。":
        "In the Feishu group, open Settings → Bots → add a Custom Bot, then paste its webhook URL below.",
    "推送": "Push",
    "推送中…": "Pushing…",
    "已复制到剪贴板": "Copied to clipboard",
    "导出 {name}": "Export {name}",
    "已保存：{path}": "Saved: {path}",
    "请填写以 https:// 开头的飞书 Webhook 地址": "Enter a Feishu webhook URL starting with https://",

    # ---- 设置 ----
    "配置保存在本机用户目录，不会上传到任何地方。":
        "Settings are stored in your user folder on this computer and are never uploaded.",
    "外观": "Appearance",
    "配色方案": "Color scheme",
    "日间": "Light",
    "夜间": "Dark",
    "界面语言": "Language",
    "模型与 API": "Models & API",
    "大模型引擎": "Language model",
    "DeepSeek 云端 API": "DeepSeek cloud API",
    "本地 Ollama（数据不出本机）": "Local Ollama (data stays on this computer)",
    "模型": "Model",
    "刷新本地模型": "Refresh local models",
    "服务地址": "Server URL",
    "需先安装 Ollama 并执行 ollama pull qwen2.5:7b（或其他模型）。":
        "Install Ollama first, then run ollama pull qwen2.5:7b (or another model).",
    "测试连接": "Test connection",
    "正在测试…": "Testing…",
    "语音转写": "Speech to text",
    "DeepSeek 语音识别": "DeepSeek speech recognition",
    "本地 faster-whisper": "Local faster-whisper",
    "云端 Whisper API": "Cloud Whisper API",
    "与大模型共用上方的 DeepSeek API Key 和 Base URL，无需另外配置；大模型选本地 Ollama 时也需要填写这把 Key。"
    "自动识别说话语言；长录音会自动切成 2 分钟以内的片段逐段上传。":
        "Uses the DeepSeek API Key and Base URL above, with nothing else to set up; the key is needed "
        "even when the language model is local Ollama. The spoken language is detected automatically, "
        "and long recordings are uploaded in pieces of under 2 minutes.",
    "模型大小": "Model size",
    "⚠ 未安装 faster-whisper。执行 pip install faster-whisper 后重启应用，或改用云端 API。":
        "⚠ faster-whisper is not installed. Run pip install faster-whisper and restart the app, "
        "or use a cloud API.",
    "✓ 已检测到 faster-whisper。首次使用会自动下载所选模型。":
        "✓ faster-whisper found. The selected model is downloaded on first use.",
    "兼容 OpenAI 音频接口的 API Key": "API Key for an OpenAI-compatible audio API",
    "会议语言": "Meeting language",
    "中文": "Chinese",
    "英文": "English",
    "自动检测": "Detect automatically",
    "保存设置": "Save settings",

    # ---- 后台处理的进度与错误 ----
    "正在读取会议文本…": "Reading the transcript…",
    "会议内容为空。": "The meeting is empty.",
    "正在调用大模型提取摘要、关键决策与行动项…":
        "Asking the language model for the summary, key decisions and action items…",
    "解析完成": "Analysis complete",
    "文件里没有音频轨道。": "The file has no audio track.",
    "无法解码音频文件：{error}": "Cannot decode the audio file: {error}",
    "无法加载录音组件：{error}": "Cannot load the recording component: {error}",
    "无法打开麦克风：{error}": "Cannot open the microphone: {error}",
    "翻译失败：{error}": "Translation failed: {error}",
    "尚未配置 DeepSeek API Key，请前往「设置」填写。": "No DeepSeek API Key yet. Enter one in Settings.",
    "API Key 无效或已过期，请在设置页检查。": "The API Key is invalid or expired. Check it in Settings.",
    "模型响应超时，请稍后重试。": "The model timed out. Try again later.",
    "本地 Ollama（请确认已运行 ollama serve）": "local Ollama (make sure ollama serve is running)",
    "DeepSeek 服务": "the DeepSeek service",
    "无法连接到{where}，请检查网络或服务地址。": "Cannot connect to {where}. Check the network or the server URL.",
    "模型「{model}」不存在，请在设置页确认模型名称。":
        "The model \"{model}\" does not exist. Check the model name in Settings.",
    "模型服务返回错误（HTTP {code}）：{message}": "The model service returned an error (HTTP {code}): {message}",
    "连接成功：{model}": "Connected: {model}",
    "无法连接本地 Ollama，请先运行 ollama serve。": "Cannot connect to local Ollama. Run ollama serve first.",
    "模型返回的内容不是合法 JSON，请重试或更换模型。":
        "The model did not return valid JSON. Try again or use another model.",
    "无法连接飞书：{error}": "Cannot connect to Feishu: {error}",
    "飞书返回错误（{code}）：{message}": "Feishu returned an error ({code}): {message}",
    "已推送到飞书群": "Pushed to the Feishu group",
    "无法识别文本文件编码，请另存为 UTF-8 后重试。":
        "Cannot tell the text file's encoding. Save it as UTF-8 and try again.",
    "语音识别使用 DeepSeek，但尚未填写 DeepSeek API Key，请前往「设置」。":
        "Speech recognition uses DeepSeek, but no DeepSeek API Key is set. Enter one in Settings.",
    "尚未填写 Whisper API Key，请前往「设置」配置。": "No Whisper API Key yet. Enter one in Settings.",
    "尚未填写 DeepSeek API Key，请前往「设置」。": "No DeepSeek API Key yet. Enter one in Settings.",
    "DeepSeek API Key 无效，请在设置页检查。": "The DeepSeek API Key is invalid. Check it in Settings.",
    "DeepSeek 语音识别返回错误（HTTP {code}）：{message}":
        "DeepSeek speech recognition returned an error (HTTP {code}): {message}",
    "DeepSeek 语音识别超时，请稍后重试。": "DeepSeek speech recognition timed out. Try again later.",
    "无法连接到 DeepSeek 语音识别服务，请检查网络。":
        "Cannot connect to DeepSeek speech recognition. Check the network.",
    "正在解码音频…": "Decoding audio…",
    "DeepSeek 正在转写第 {i} / {n} 段…": "DeepSeek is transcribing part {i} of {n}…",
    "没有从音频中识别到语音内容。": "No speech was recognized in the audio.",
    "转写完成": "Transcription complete",
    "未检测到本地转写引擎 faster-whisper。\n\n"
    "方案一：在「设置」中把转写方式切换为「DeepSeek 语音识别」；\n"
    "方案二：在终端执行 pip install faster-whisper，然后重启应用；\n"
    "方案三：直接上传会议文本（.txt / .md）。":
        "The local transcription engine faster-whisper was not found.\n\n"
        "Option 1: in Settings, switch speech to text to DeepSeek speech recognition;\n"
        "Option 2: run pip install faster-whisper in a terminal, then restart the app;\n"
        "Option 3: upload the meeting transcript (.txt / .md) instead.",
    "Whisper 模型加载失败：{error}": "Failed to load the Whisper model: {error}",
    "正在加载 Whisper 模型（{size}），首次使用需要下载模型文件…":
        "Loading the Whisper model ({size}). The first use downloads the model files…",
    "正在识别语音…": "Recognizing speech…",
    "正在转写音频… {pos} / {total}": "Transcribing audio… {pos} / {total}",
    "音频转写失败：{error}": "Audio transcription failed: {error}",
    "Whisper API Key 无效，请在设置页检查。": "The Whisper API Key is invalid. Check it in Settings.",
    "云端转写失败：{error}": "Cloud transcription failed: {error}",
    "正在上传音频到云端 Whisper 转写…": "Uploading audio to cloud Whisper…",
    "云端转写完成": "Cloud transcription complete",

    # ---- 存储位置 ----
    "数据存储": "Storage",
    "历史会议和任务保存在下面的文件夹里。更改后，现有记录会一并移过去。":
        "Meetings and tasks are saved in the folder below. If you change it, existing records move with it.",
    "更改…": "Change…",
    "选择存储文件夹": "Choose a storage folder",
    "选择存储位置": "Choose where to store",
    "欢迎使用 Distill！请先选择会议记录的存储位置。": "Welcome to Distill! First, choose where to store your meetings.",
    "找不到之前选择的存储文件夹：\n{path}\n\n请重新选择会议记录的存储位置。":
        "The storage folder you chose before can't be found:\n{path}\n\nChoose where to store your meetings again.",
    "默认位置：{path}\n之后可以在「设置 → 数据存储」中更改。":
        "Default: {path}\nYou can change this later in Settings → Storage.",
    "选择文件夹…": "Choose folder…",
    "使用默认位置": "Use default",
    "无法使用该文件夹": "Can't use this folder",
    "没有写入「{path}」的权限，请换一个文件夹。": "You don't have permission to write to \"{path}\". Choose another folder.",
    "正在录音或处理中，请结束后再更改存储位置": "Recording or processing. Change the storage location when it's done.",
    "更改存储位置失败": "Couldn't change storage location",
    "移动会议记录时出错：{error}": "Error moving meeting records: {error}",
    "该文件夹中已有会议记录，已改为使用这些记录": "That folder already has meeting records. Now using those.",
    "会议记录已移到：{path}": "Meeting records moved to: {path}",
}
