from dataclasses import replace

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QFormLayout, QHBoxLayout, QLineEdit, QPushButton, QRadioButton,
    QVBoxLayout, QWidget,
)

from core.config import Settings
from .widgets import Page, card, label

WHISPER_SIZES = ["tiny", "base", "small", "medium", "large-v3"]
LANGUAGES = [("中文", "zh"), ("英文", "en"), ("自动检测", "")]


def _form() -> QFormLayout:
    f = QFormLayout()
    f.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    f.setHorizontalSpacing(18)
    f.setVerticalSpacing(12)
    return f


def _secret(text: str, placeholder: str) -> QLineEdit:
    e = QLineEdit(text)
    e.setEchoMode(QLineEdit.Password)
    e.setPlaceholderText(placeholder)
    return e


class SettingsPage(QWidget):
    save_requested = Signal(object)          # Settings
    test_requested = Signal(object)          # Settings
    ollama_models_requested = Signal(str)    # base_url

    def __init__(self, settings: Settings):
        super().__init__()
        self.setObjectName("Workspace")
        self.settings = settings
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        page = Page()
        outer.addWidget(page)
        body = page.body
        page.header("模型与 API 设置", "配置保存在本机用户目录，不会上传到任何地方。")

        # ---- 大模型引擎 ----
        frame, lay = card()
        lay.addWidget(label("大模型引擎", "H3"))
        radios = QHBoxLayout()
        self.engine = QButtonGroup(self)
        self.r_deepseek = QRadioButton("DeepSeek 云端 API")
        self.r_ollama = QRadioButton("本地 Ollama（数据不出本机）")
        self.engine.addButton(self.r_deepseek)
        self.engine.addButton(self.r_ollama)
        radios.addWidget(self.r_deepseek)
        radios.addSpacing(16)
        radios.addWidget(self.r_ollama)
        radios.addStretch()
        lay.addLayout(radios)

        self.deepseek_box = QWidget()
        f = _form()
        f.setContentsMargins(0, 8, 0, 0)
        self.ds_key = _secret(settings.deepseek_api_key, "sk-…")
        self.ds_url = QLineEdit(settings.deepseek_base_url)
        self.ds_model = QComboBox()
        self.ds_model.setEditable(True)
        self.ds_model.addItems(["deepseek-chat", "deepseek-reasoner"])
        self.ds_model.setCurrentText(settings.deepseek_model)
        f.addRow("API Key", self.ds_key)
        f.addRow("Base URL", self.ds_url)
        f.addRow("模型", self.ds_model)
        self.deepseek_box.setLayout(f)
        lay.addWidget(self.deepseek_box)

        self.ollama_box = QWidget()
        f = _form()
        f.setContentsMargins(0, 8, 0, 0)
        self.ol_url = QLineEdit(settings.ollama_base_url)
        model_row = QHBoxLayout()
        self.ol_model = QComboBox()
        self.ol_model.setEditable(True)
        self.ol_model.addItem(settings.ollama_model)
        self.ol_model.setCurrentText(settings.ollama_model)
        self.ol_refresh = QPushButton("刷新本地模型")
        self.ol_refresh.clicked.connect(lambda: self.ollama_models_requested.emit(self.ol_url.text().strip()))
        model_row.addWidget(self.ol_model, 1)
        model_row.addWidget(self.ol_refresh)
        f.addRow("服务地址", self.ol_url)
        f.addRow("模型", model_row)
        f.addRow("", label("需先安装 Ollama 并执行 ollama pull qwen2.5:7b（或其他模型）。", "Small", wrap=True))
        self.ollama_box.setLayout(f)
        lay.addWidget(self.ollama_box)

        test_row = QHBoxLayout()
        self.test_btn = QPushButton("测试连接")
        self.test_btn.clicked.connect(lambda: self.test_requested.emit(self.collect()))
        self.test_result = label("", "Small", wrap=True)
        test_row.addWidget(self.test_btn)
        test_row.addWidget(self.test_result, 1)
        lay.addLayout(test_row)
        body.addWidget(frame)

        self.r_deepseek.toggled.connect(self._sync_engine)
        (self.r_ollama if settings.provider == "ollama" else self.r_deepseek).setChecked(True)
        self._sync_engine()

        # ---- 语音转写 ----
        frame, lay = card()
        lay.addWidget(label("语音转写（Whisper）", "H3"))
        radios = QHBoxLayout()
        self.whisper = QButtonGroup(self)
        self.w_local = QRadioButton("本地 faster-whisper")
        self.w_api = QRadioButton("云端 Whisper API")
        self.whisper.addButton(self.w_local)
        self.whisper.addButton(self.w_api)
        radios.addWidget(self.w_local)
        radios.addSpacing(16)
        radios.addWidget(self.w_api)
        radios.addStretch()
        lay.addLayout(radios)

        self.local_box = QWidget()
        f = _form()
        f.setContentsMargins(0, 8, 0, 0)
        self.w_size = QComboBox()
        self.w_size.addItems(WHISPER_SIZES)
        self.w_size.setCurrentText(settings.whisper_model_size)
        f.addRow("模型大小", self.w_size)
        f.addRow("", label(self._whisper_status(), "Small", wrap=True))
        self.local_box.setLayout(f)
        lay.addWidget(self.local_box)

        self.api_box = QWidget()
        f = _form()
        f.setContentsMargins(0, 8, 0, 0)
        self.w_key = _secret(settings.whisper_api_key, "兼容 OpenAI 音频接口的 API Key")
        self.w_url = QLineEdit(settings.whisper_base_url)
        self.w_model = QLineEdit(settings.whisper_api_model)
        f.addRow("API Key", self.w_key)
        f.addRow("Base URL", self.w_url)
        f.addRow("模型", self.w_model)
        self.api_box.setLayout(f)
        lay.addWidget(self.api_box)

        f = _form()
        self.lang = QComboBox()
        for name, code in LANGUAGES:
            self.lang.addItem(name, code)
        self.lang.setCurrentIndex(max(0, self.lang.findData(settings.language)))
        f.addRow("会议语言", self.lang)
        lay.addLayout(f)

        self.w_local.toggled.connect(self._sync_whisper)
        (self.w_api if settings.whisper_mode == "api" else self.w_local).setChecked(True)
        self._sync_whisper()
        body.addWidget(frame)

        save_row = QHBoxLayout()
        save_row.addStretch()
        save = QPushButton("保存设置")
        save.setObjectName("Primary")
        save.clicked.connect(lambda: self.save_requested.emit(self.collect()))
        save_row.addWidget(save)
        body.addLayout(save_row)
        body.addStretch()

    @staticmethod
    def _whisper_status() -> str:
        try:
            import faster_whisper  # noqa: F401
        except ImportError:
            return "⚠ 未安装 faster-whisper。执行 pip install faster-whisper 后重启应用，或改用云端 API。"
        return "✓ 已检测到 faster-whisper。首次使用会自动下载所选模型。"

    def _sync_engine(self) -> None:
        self.deepseek_box.setVisible(self.r_deepseek.isChecked())
        self.ollama_box.setVisible(self.r_ollama.isChecked())
        self.test_result.setText("")

    def _sync_whisper(self) -> None:
        self.local_box.setVisible(self.w_local.isChecked())
        self.api_box.setVisible(self.w_api.isChecked())

    def collect(self) -> Settings:
        return replace(
            self.settings,
            provider="ollama" if self.r_ollama.isChecked() else "deepseek",
            deepseek_api_key=self.ds_key.text().strip(),
            deepseek_base_url=self.ds_url.text().strip() or "https://api.deepseek.com",
            deepseek_model=self.ds_model.currentText().strip() or "deepseek-chat",
            ollama_base_url=self.ol_url.text().strip() or "http://localhost:11434/v1",
            ollama_model=self.ol_model.currentText().strip(),
            whisper_mode="api" if self.w_api.isChecked() else "local",
            whisper_model_size=self.w_size.currentText(),
            whisper_api_key=self.w_key.text().strip(),
            whisper_base_url=self.w_url.text().strip() or "https://api.openai.com/v1",
            whisper_api_model=self.w_model.text().strip() or "whisper-1",
            language=self.lang.currentData(),
        )

    # ---- 主窗口回调 ----
    def set_test_busy(self) -> None:
        self.test_btn.setEnabled(False)
        self.test_result.setStyleSheet("")
        self.test_result.setText("正在测试…")

    def set_test_result(self, ok: bool, message: str) -> None:
        self.test_btn.setEnabled(True)
        self.test_result.setStyleSheet(f"color: {'#4D7A55' if ok else '#B4442A'};")
        self.test_result.setText(("✓ " if ok else "✕ ") + message)

    def set_ollama_models(self, models: list[str]) -> None:
        current = self.ol_model.currentText()
        self.ol_model.clear()
        self.ol_model.addItems(models)
        self.ol_model.setCurrentText(current if current in models or not models else models[0])
