from dataclasses import replace

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QFormLayout, QHBoxLayout, QLineEdit, QPushButton, QRadioButton,
    QVBoxLayout, QWidget,
)

from core.config import Settings
from core.i18n import UI_LANGUAGES, tr
from .styles import THEME_NAMES
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
    theme_changed = Signal(str)              # light | dark，点选后立即生效并保存
    ui_language_changed = Signal(str)        # zh | en，点选后立即生效并保存

    def __init__(self, settings: Settings):
        super().__init__()
        self.setObjectName("Workspace")
        self.settings = settings
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        page = Page()
        outer.addWidget(page)
        body = page.body
        page.header(tr("设置"), tr("配置保存在本机用户目录，不会上传到任何地方。"))

        # ---- 外观 ----
        frame, lay = card()
        lay.addWidget(label(tr("外观"), "H3"))
        f = _form()
        radios = QHBoxLayout()
        self.theme = QButtonGroup(self)
        for name, key in THEME_NAMES:
            r = QRadioButton(tr(name))
            r.setChecked(key == settings.theme)
            r.toggled.connect(lambda on, k=key: on and self.theme_changed.emit(k))
            self.theme.addButton(r)
            radios.addWidget(r)
            radios.addSpacing(16)
        radios.addStretch()
        f.addRow(tr("配色方案"), radios)

        radios = QHBoxLayout()
        self.ui_language = QButtonGroup(self)
        self.ui_language_radios: dict[str, QRadioButton] = {}
        for name, code in UI_LANGUAGES:  # 语言名用各自的文字显示，不随界面语言翻译
            r = QRadioButton(name)
            r.setChecked(code == settings.ui_language)
            r.toggled.connect(lambda on, c=code: on and self.ui_language_changed.emit(c))
            self.ui_language.addButton(r)
            self.ui_language_radios[code] = r
            radios.addWidget(r)
            radios.addSpacing(16)
        radios.addStretch()
        f.addRow(tr("界面语言"), radios)
        lay.addLayout(f)
        body.addWidget(frame)

        body.addSpacing(6)
        body.addWidget(label(tr("模型与 API"), "H2"))

        # ---- 大模型引擎 ----
        frame, lay = card()
        lay.addWidget(label(tr("大模型引擎"), "H3"))
        radios = QHBoxLayout()
        self.engine = QButtonGroup(self)
        self.r_deepseek = QRadioButton(tr("DeepSeek 云端 API"))
        self.r_ollama = QRadioButton(tr("本地 Ollama（数据不出本机）"))
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
        f.addRow(tr("模型"), self.ds_model)
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
        self.ol_refresh = QPushButton(tr("刷新本地模型"))
        self.ol_refresh.clicked.connect(lambda: self.ollama_models_requested.emit(self.ol_url.text().strip()))
        model_row.addWidget(self.ol_model, 1)
        model_row.addWidget(self.ol_refresh)
        f.addRow(tr("服务地址"), self.ol_url)
        f.addRow(tr("模型"), model_row)
        f.addRow("", label(tr("需先安装 Ollama 并执行 ollama pull qwen2.5:7b（或其他模型）。"), "Small", wrap=True))
        self.ollama_box.setLayout(f)
        lay.addWidget(self.ollama_box)

        test_row = QHBoxLayout()
        self.test_btn = QPushButton(tr("测试连接"))
        self.test_btn.clicked.connect(lambda: self.test_requested.emit(self.collect()))
        self.test_result = label("", "Small", wrap=True)
        test_row.addWidget(self.test_btn)
        test_row.addWidget(self.test_result, 1)
        lay.addLayout(test_row)
        body.addWidget(frame)

        # ---- 语音转写 ----
        frame, lay = card()
        lay.addWidget(label(tr("语音转写"), "H3"))
        radios = QHBoxLayout()
        self.whisper = QButtonGroup(self)
        self.w_deepseek = QRadioButton(tr("DeepSeek 语音识别"))
        self.w_local = QRadioButton(tr("本地 faster-whisper"))
        self.w_api = QRadioButton(tr("云端 Whisper API"))
        for r in (self.w_deepseek, self.w_local, self.w_api):
            self.whisper.addButton(r)
            radios.addWidget(r)
            radios.addSpacing(16)
        radios.addStretch()
        lay.addLayout(radios)

        self.ds_asr_box = label(
            tr("与大模型共用上方的 DeepSeek API Key 和 Base URL，无需另外配置；大模型选本地 Ollama 时也需要填写这把 Key。"
               "自动识别说话语言；长录音会自动切成 2 分钟以内的片段逐段上传。"),
            "Small", wrap=True,
        )
        self.ds_asr_box.setContentsMargins(0, 8, 0, 0)
        lay.addWidget(self.ds_asr_box)

        self.local_box = QWidget()
        f = _form()
        f.setContentsMargins(0, 8, 0, 0)
        self.w_size = QComboBox()
        self.w_size.addItems(WHISPER_SIZES)
        self.w_size.setCurrentText(settings.whisper_model_size)
        f.addRow(tr("模型大小"), self.w_size)
        f.addRow("", label(self._whisper_status(), "Small", wrap=True))
        self.local_box.setLayout(f)
        lay.addWidget(self.local_box)

        self.api_box = QWidget()
        f = _form()
        f.setContentsMargins(0, 8, 0, 0)
        self.w_key = _secret(settings.whisper_api_key, tr("兼容 OpenAI 音频接口的 API Key"))
        self.w_url = QLineEdit(settings.whisper_base_url)
        self.w_model = QLineEdit(settings.whisper_api_model)
        f.addRow("API Key", self.w_key)
        f.addRow("Base URL", self.w_url)
        f.addRow(tr("模型"), self.w_model)
        self.api_box.setLayout(f)
        lay.addWidget(self.api_box)

        self.lang_box = QWidget()
        f = _form()
        f.setContentsMargins(0, 0, 0, 0)
        self.lang = QComboBox()
        for name, code in LANGUAGES:
            self.lang.addItem(tr(name), code)
        self.lang.setCurrentIndex(max(0, self.lang.findData(settings.language)))
        f.addRow(tr("会议语言"), self.lang)
        self.lang_box.setLayout(f)
        lay.addWidget(self.lang_box)

        body.addWidget(frame)

        # 两组单选都建好后再连接信号：DeepSeek Key 一栏的显隐同时取决于两组选择
        self.r_deepseek.toggled.connect(self._sync_engine)
        (self.r_ollama if settings.provider == "ollama" else self.r_deepseek).setChecked(True)
        self.whisper.buttonToggled.connect(self._sync_whisper)
        {"api": self.w_api, "local": self.w_local}.get(settings.whisper_mode, self.w_deepseek).setChecked(True)
        self._sync_engine()
        self._sync_whisper()

        save_row = QHBoxLayout()
        save_row.addStretch()
        save = QPushButton(tr("保存设置"))
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
            return tr("⚠ 未安装 faster-whisper。执行 pip install faster-whisper 后重启应用，或改用云端 API。")
        return tr("✓ 已检测到 faster-whisper。首次使用会自动下载所选模型。")

    def _sync_engine(self) -> None:
        # 大模型用 Ollama 但转写用 DeepSeek 时，仍需显示 DeepSeek Key 一栏
        self.deepseek_box.setVisible(self.r_deepseek.isChecked() or self.w_deepseek.isChecked())
        self.ollama_box.setVisible(self.r_ollama.isChecked())
        self.test_result.setText("")

    def _sync_whisper(self) -> None:
        self.deepseek_box.setVisible(self.r_deepseek.isChecked() or self.w_deepseek.isChecked())
        self.ds_asr_box.setVisible(self.w_deepseek.isChecked())
        self.local_box.setVisible(self.w_local.isChecked())
        self.api_box.setVisible(self.w_api.isChecked())
        self.lang_box.setVisible(not self.w_deepseek.isChecked())  # DeepSeek 不接受语言参数

    def _whisper_mode(self) -> str:
        if self.w_api.isChecked():
            return "api"
        return "local" if self.w_local.isChecked() else "deepseek"

    def collect(self) -> Settings:
        return replace(
            self.settings,
            provider="ollama" if self.r_ollama.isChecked() else "deepseek",
            deepseek_api_key=self.ds_key.text().strip(),
            deepseek_base_url=self.ds_url.text().strip() or "https://api.deepseek.com",
            deepseek_model=self.ds_model.currentText().strip() or "deepseek-chat",
            ollama_base_url=self.ol_url.text().strip() or "http://localhost:11434/v1",
            ollama_model=self.ol_model.currentText().strip(),
            whisper_mode=self._whisper_mode(),
            whisper_model_size=self.w_size.currentText(),
            whisper_api_key=self.w_key.text().strip(),
            whisper_base_url=self.w_url.text().strip() or "https://api.openai.com/v1",
            whisper_api_model=self.w_model.text().strip() or "whisper-1",
            language=self.lang.currentData(),
        )

    # ---- 主窗口回调 ----
    def set_test_busy(self) -> None:
        self.test_btn.setEnabled(False)
        self._set_result_style("Small")
        self.test_result.setText(tr("正在测试…"))

    def set_test_result(self, ok: bool, message: str) -> None:
        self.test_btn.setEnabled(True)
        self._set_result_style("Success" if ok else "Failure")
        self.test_result.setText(("✓ " if ok else "✕ ") + message)

    def _set_result_style(self, name: str) -> None:
        # 颜色由全局样式表按对象名决定，改名后需要重新应用样式
        self.test_result.setObjectName(name)
        self.test_result.style().unpolish(self.test_result)
        self.test_result.style().polish(self.test_result)

    def revert_ui_language(self, code: str) -> None:
        """切换被拒绝（正在录音或处理中）时把单选恢复成当前语言，不再触发信号。"""
        r = self.ui_language_radios[code]
        r.blockSignals(True)
        r.setChecked(True)
        r.blockSignals(False)

    def set_ollama_models(self, models: list[str]) -> None:
        current = self.ol_model.currentText()
        self.ol_model.clear()
        self.ol_model.addItems(models)
        self.ol_model.setCurrentText(current if current in models or not models else models[0])
