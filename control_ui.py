from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import sounddevice as sd
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QBrush, QColor, QFont, QIcon
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.control import EnvStore, ServiceManager
from src.glossary import GlossaryEntry, GlossaryProcessor, GlossaryStore
from src.history import HistoryStore, TranscriptionRecord
from src.llm.translate import TARGET_LANGUAGE_LABELS
from src.persona import PersonaEntry, PersonaProcessor, PersonaStore


ROOT = Path(__file__).resolve().parent
APP_NAME = "小凯哥语音输入法"

SERVICE_LABELS = {
    "aliyun": "阿里云 Qwen ASR",
    "dashscope": "阿里云 Qwen ASR",
    "bailian": "阿里云 Qwen ASR",
    "openai": "OpenAI GPT-4o",
    "doubao": "豆包流式识别",
    "groq": "Groq Whisper",
    "siliconflow": "SiliconFlow SenseVoice",
    "local": "本地 Whisper",
    "aliyun-mt": "阿里云 Qwen-MT",
    "persona-agnes": "Agnes 人设改写",
    "persona-qwen": "Qwen 人设改写",
    "persona-ark": "火山方舟人设改写",
}

BATCH_SERVICES = [
    ("阿里云 Qwen ASR", "aliyun"),
    ("OpenAI GPT-4o Transcribe", "openai"),
    ("Groq Whisper", "groq"),
    ("SiliconFlow SenseVoice", "siliconflow"),
]

DEFAULT_SERVICES = [
    ("阿里云 Qwen ASR", "aliyun"),
    ("OpenAI GPT-4o Transcribe", "openai"),
    ("Groq Whisper", "groq"),
    ("SiliconFlow SenseVoice", "siliconflow"),
]

PERSONA_PROVIDERS = [
    ("阿里云 Qwen Flash", "qwen"),
    ("火山方舟 Doubao Seed", "ark"),
]

PERSONA_FALLBACK_PROVIDERS = [
    ("不自动切换", ""),
    ("阿里云 Qwen Flash", "qwen"),
    ("火山方舟 Doubao Seed", "ark"),
]

QWEN_REWRITE_MODELS = [
    ("Qwen Flash（最低成本）", "qwen-flash"),
    ("Qwen 3.5 Flash（质量均衡）", "qwen3.5-flash"),
    ("Qwen 3.6 Flash（更高质量）", "qwen3.6-flash"),
]

ARK_REWRITE_MODELS = [
    ("Seed 2.0 Mini（速度优先）", "doubao-seed-2-0-mini-260428"),
    ("Seed 2.0 Lite（质量优先）", "doubao-seed-2-0-lite-260428"),
]

TRANSLATION_LANGUAGES = [
    ("英语", "en"),
    ("日语", "ja"),
    ("俄语", "ru"),
    ("韩语", "ko"),
    ("法语", "fr"),
    ("德语", "de"),
    ("西班牙语", "es"),
    ("葡萄牙语", "pt"),
    ("意大利语", "it"),
    ("阿拉伯语", "ar"),
    ("中文", "zh"),
]

HOTKEY_LABELS = {
    "alt_r": "右 Alt",
    "option_r": "右 Alt",
    "right_option": "右 Alt",
    "ctrl_r": "右 Ctrl",
    "control_r": "右 Ctrl",
    "shift_r": "右 Shift",
    "cmd_r": "右 Command",
    "command_r": "右 Command",
    "right_command": "右 Command",
}


def format_duration(seconds: float | None) -> str:
    if not seconds:
        return "-"
    if seconds < 60:
        return f"{seconds:.1f} 秒"
    minutes, remaining = divmod(int(seconds), 60)
    return f"{minutes} 分 {remaining} 秒"


def format_time(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.strftime("%m-%d %H:%M")
    except (TypeError, ValueError):
        return value


def set_combo_data(combo: QComboBox, value: str) -> None:
    index = combo.findData(value)
    combo.setCurrentIndex(index if index >= 0 else 0)


def format_hotkey(value: str) -> str:
    normalized = (value or "").strip().lower()
    return HOTKEY_LABELS.get(normalized, value or "未配置")


def service_display(value: str) -> str:
    parts = [
        SERVICE_LABELS.get(part, part)
        for part in (value or "unknown").split("+")
    ]
    return " + ".join(parts)


def repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


class MetricCard(QFrame):
    def __init__(self, title: str, subtitle: str) -> None:
        super().__init__()
        self.setObjectName("metricCard")
        self.setMinimumHeight(108)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(5)

        title_label = QLabel(title)
        title_label.setObjectName("metricTitle")
        self.value_label = QLabel("0")
        self.value_label.setObjectName("metricValue")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("metricSubtitle")

        layout.addWidget(title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(subtitle_label)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)


class ControlUI(QMainWindow):
    PAGE_TITLES = [
        "概览",
        "历史记录",
        "识别引擎",
        "快捷键与文本",
        "词库与纠错",
        "人设与改写",
        "诊断",
    ]

    def __init__(self, root: Path = ROOT) -> None:
        super().__init__()
        self.root = Path(root)
        self.env_store = EnvStore(self.root / ".env")
        self.service = ServiceManager(self.root)
        self.history = HistoryStore(self.root / "data" / "history.db")
        self.glossary = GlossaryStore(self.root / "data" / "glossary.db")
        self.glossary_processor = GlossaryProcessor(self.glossary)
        self.personas = PersonaStore(self.root / "data" / "personas.db")
        self._history_rows: list[TranscriptionRecord] = []
        self._glossary_rows: list[GlossaryEntry] = []
        self._persona_rows: list[PersonaEntry] = []
        self._editing_glossary_id: int | None = None
        self._editing_persona_id: int | None = None
        self._glossary_updating = False
        self._persona_updating = False
        self._running = False

        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(1080, 720)
        self.resize(1240, 820)
        icon_path = self.root / "assets" / "icons" / "whisper-input.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._build_ui()
        self._apply_styles()
        self.load_settings()
        self.refresh_all()

        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.refresh_status)
        self.status_timer.start(2000)

        self.data_timer = QTimer(self)
        self.data_timer.timeout.connect(self.refresh_passive_data)
        self.data_timer.start(4000)

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("appRoot")
        self.setCentralWidget(central)

        shell = QHBoxLayout(central)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        sidebar = self._build_sidebar()
        shell.addWidget(sidebar)

        content = QFrame()
        content.setObjectName("contentPanel")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(30, 22, 30, 26)
        content_layout.setSpacing(18)

        topbar = QHBoxLayout()
        topbar.setSpacing(12)
        self.page_title = QLabel(self.PAGE_TITLES[0])
        self.page_title.setObjectName("pageTitle")
        topbar.addWidget(self.page_title)
        topbar.addStretch()

        self.status_chip = QFrame()
        self.status_chip.setObjectName("statusChip")
        self.status_chip.setProperty("state", "stopped")
        chip_layout = QHBoxLayout(self.status_chip)
        chip_layout.setContentsMargins(12, 6, 12, 6)
        chip_layout.setSpacing(7)
        self.status_dot = QLabel("●")
        self.status_dot.setObjectName("statusDot")
        self.top_status_label = QLabel("未运行")
        self.top_status_label.setObjectName("statusText")
        chip_layout.addWidget(self.status_dot)
        chip_layout.addWidget(self.top_status_label)
        topbar.addWidget(self.status_chip)

        quick_restart = QPushButton()
        quick_restart.setObjectName("iconButton")
        quick_restart.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        quick_restart.setToolTip("重启语音输入服务")
        quick_restart.setFixedSize(34, 34)
        quick_restart.clicked.connect(self.restart_service)
        topbar.addWidget(quick_restart)
        content_layout.addLayout(topbar)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_overview_page())
        self.stack.addWidget(self._build_history_page())
        self.stack.addWidget(self._build_engines_page())
        self.stack.addWidget(self._build_behavior_page())
        self.stack.addWidget(self._build_glossary_page())
        self.stack.addWidget(self._build_persona_page())
        self.stack.addWidget(self._build_diagnostics_page())
        content_layout.addWidget(self.stack, stretch=1)

        shell.addWidget(content, stretch=1)

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(224)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 24, 18, 20)
        layout.setSpacing(18)

        brand = QLabel(APP_NAME)
        brand.setObjectName("brandTitle")
        brand_subtitle = QLabel("AI 语音输入工作台")
        brand_subtitle.setObjectName("brandSubtitle")
        layout.addWidget(brand)
        layout.addWidget(brand_subtitle)

        self.nav = QListWidget()
        self.nav.setObjectName("navigation")
        self.nav.setFocusPolicy(Qt.NoFocus)
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        for title in self.PAGE_TITLES:
            item = QListWidgetItem(title)
            self.nav.addItem(item)
        self.nav.setCurrentRow(0)
        self.nav.currentRowChanged.connect(self.change_page)
        layout.addWidget(self.nav, stretch=1)

        version_label = QLabel("XIAOKAIGE VOICE V4")
        version_label.setObjectName("versionLabel")
        layout.addWidget(version_label)
        return sidebar

    def _build_overview_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        hero = QFrame()
        hero.setObjectName("heroPanel")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(24, 22, 24, 22)
        hero_layout.setSpacing(20)

        hero_copy = QVBoxLayout()
        hero_copy.setSpacing(5)
        eyebrow = QLabel("VOICE SERVICE")
        eyebrow.setObjectName("eyebrow")
        self.hero_title = QLabel("正在检查服务")
        self.hero_title.setObjectName("heroTitle")
        self.hero_detail = QLabel("正在读取当前识别引擎和快捷键配置。")
        self.hero_detail.setObjectName("heroDetail")
        self.hero_detail.setWordWrap(True)
        hero_copy.addWidget(eyebrow)
        hero_copy.addWidget(self.hero_title)
        hero_copy.addWidget(self.hero_detail)
        hero_layout.addLayout(hero_copy, stretch=1)

        self.service_button = self._button(
            "启动服务",
            QStyle.SP_MediaPlay,
            "primary",
        )
        self.service_button.clicked.connect(self.toggle_service)
        hero_layout.addWidget(self.service_button)

        restart_button = self._button(
            "重启",
            QStyle.SP_BrowserReload,
            "secondary",
        )
        restart_button.clicked.connect(self.restart_service)
        hero_layout.addWidget(restart_button)
        layout.addWidget(hero)

        metrics = QHBoxLayout()
        metrics.setSpacing(12)
        self.today_metric = MetricCard("今日转写", "成功与失败任务")
        self.success_metric = MetricCard("成功率", "今日识别稳定性")
        self.latency_metric = MetricCard("平均耗时", "从录音结束到文字返回")
        self.duration_metric = MetricCard("语音时长", "今日累计录音")
        for card in (
            self.today_metric,
            self.success_metric,
            self.latency_metric,
            self.duration_metric,
        ):
            metrics.addWidget(card)
        layout.addLayout(metrics)

        section_row = QHBoxLayout()
        section_title = QLabel("当前工作配置")
        section_title.setObjectName("sectionTitle")
        section_row.addWidget(section_title)
        section_row.addStretch()
        layout.addLayout(section_row)

        config_band = QFrame()
        config_band.setObjectName("configBand")
        config_layout = QHBoxLayout(config_band)
        config_layout.setContentsMargins(20, 15, 20, 15)
        config_layout.setSpacing(12)
        self.engine_value = self._config_value(config_layout, "识别引擎")
        self.hotkey_value = self._config_value(config_layout, "听写快捷键")
        self.microphone_value = self._config_value(config_layout, "麦克风")
        self.translation_value = self._config_value(config_layout, "翻译模式")
        self.persona_value = self._config_value(config_layout, "人设改写")
        self.archive_value = self._config_value(config_layout, "录音保存")
        layout.addWidget(config_band)

        recent_header = QHBoxLayout()
        recent_title = QLabel("最近转写")
        recent_title.setObjectName("sectionTitle")
        recent_header.addWidget(recent_title)
        recent_header.addStretch()
        view_all = QPushButton("查看全部")
        view_all.setProperty("role", "link")
        view_all.clicked.connect(lambda: self.nav.setCurrentRow(1))
        recent_header.addWidget(view_all)
        layout.addLayout(recent_header)

        self.recent_table = self._table(["时间", "内容", "引擎", "识别耗时"])
        self.recent_table.setMaximumHeight(220)
        header = self.recent_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        layout.addWidget(self.recent_table)
        return page

    def _build_history_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        self.history_search = QLineEdit()
        self.history_search.setPlaceholderText("搜索转写内容、引擎或模型")
        self.history_search.setClearButtonEnabled(True)
        self.history_search.textChanged.connect(self.refresh_history)
        toolbar.addWidget(self.history_search, stretch=1)

        refresh_button = self._button(
            "刷新",
            QStyle.SP_BrowserReload,
            "secondary",
        )
        refresh_button.clicked.connect(self.refresh_history)
        toolbar.addWidget(refresh_button)

        copy_button = self._button(
            "复制",
            QStyle.SP_FileDialogDetailedView,
            "secondary",
        )
        copy_button.clicked.connect(self.copy_selected_history)
        toolbar.addWidget(copy_button)

        delete_button = self._button(
            "删除",
            QStyle.SP_TrashIcon,
            "danger",
        )
        delete_button.clicked.connect(self.delete_selected_history)
        toolbar.addWidget(delete_button)
        layout.addLayout(toolbar)

        hint = QLabel("历史文字始终保存；只有开启录音归档后才会保留音频文件。")
        hint.setObjectName("pageHint")
        layout.addWidget(hint)

        self.history_table = self._table(
            ["ID", "时间", "转写内容", "服务", "模型", "录音", "识别", "状态"]
        )
        self.history_table.setColumnHidden(0, True)
        history_header = self.history_table.horizontalHeader()
        history_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        history_header.setSectionResizeMode(2, QHeaderView.Stretch)
        for column in range(3, 8):
            history_header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        self.history_table.doubleClicked.connect(self.copy_selected_history)
        layout.addWidget(self.history_table, stretch=1)
        return page

    def _build_engines_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        cloud_panel = self._section_panel(
            "云端识别",
            "选择默认识别方式，并集中管理各平台凭据。",
        )
        cloud_form = QFormLayout()
        cloud_form.setHorizontalSpacing(22)
        cloud_form.setVerticalSpacing(12)

        self.default_service_combo = QComboBox()
        for label, value in DEFAULT_SERVICES:
            self.default_service_combo.addItem(label, value)
        cloud_form.addRow("默认识别方式", self.default_service_combo)

        self.batch_service_combo = QComboBox()
        for label, value in BATCH_SERVICES:
            self.batch_service_combo.addItem(label, value)
        cloud_form.addRow("批量/翻译引擎", self.batch_service_combo)

        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("qwen3-asr-flash")
        cloud_form.addRow("阿里云模型", self.model_input)

        self.translation_model_input = QLineEdit()
        self.translation_model_input.setPlaceholderText("qwen-mt-flash")
        cloud_form.addRow("翻译模型", self.translation_model_input)

        self.dashscope_key_input = self._password_input("DashScope API Key")
        cloud_form.addRow("DashScope Key", self.dashscope_key_input)

        self.openai_key_input = self._password_input("OpenAI API Key")
        cloud_form.addRow("OpenAI Key", self.openai_key_input)

        cloud_panel.layout().addLayout(cloud_form)
        layout.addWidget(cloud_panel)

        local_panel = self._section_panel(
            "本地 Whisper",
            "离线语音识别备用方案。需要安装 whisper.cpp，不联网，也不参与翻译。",
        )
        local_form = QFormLayout()
        local_form.setHorizontalSpacing(22)
        local_form.setVerticalSpacing(12)
        self.whisper_cli_input = QLineEdit()
        self.whisper_model_input = QLineEdit()
        local_form.addRow("whisper-cli 程序", self.whisper_cli_input)
        local_form.addRow("本地模型文件", self.whisper_model_input)
        local_panel.layout().addLayout(local_form)
        layout.addWidget(local_panel)

        actions = QHBoxLayout()
        actions.addStretch()
        save_button = self._button(
            "保存并重启",
            QStyle.SP_DialogSaveButton,
            "primary",
        )
        save_button.clicked.connect(self.save_engine_settings)
        actions.addWidget(save_button)
        layout.addLayout(actions)
        layout.addStretch()
        return page

    def _build_behavior_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        hotkey_panel = self._section_panel(
            "输入方式",
            "控制录音触发方式、文字粘贴和失败重试。",
        )
        form = QFormLayout()
        form.setHorizontalSpacing(22)
        form.setVerticalSpacing(12)

        self.hotkey_input = QLineEdit()
        self.hotkey_input.setPlaceholderText("alt_r")
        form.addRow("触发按键", self.hotkey_input)

        self.hotkey_mode_combo = QComboBox()
        self.hotkey_mode_combo.addItem("按住说话，松开转写", "hold")
        self.hotkey_mode_combo.addItem("按一次开始，再按一次结束", "toggle")
        form.addRow("触发模式", self.hotkey_mode_combo)

        self.paste_combo = QComboBox()
        self.paste_combo.addItem("Ctrl+V", "ctrl+v")
        self.paste_combo.addItem("Ctrl+Shift+V", "ctrl+shift+v")
        form.addRow("粘贴快捷键", self.paste_combo)

        self.archive_combo = QComboBox()
        self.archive_combo.addItem("不保存录音，仅保存文字历史", "off")
        self.archive_combo.addItem("保存全部录音和文字", "all")
        form.addRow("录音归档", self.archive_combo)

        self.retry_spin = QSpinBox()
        self.retry_spin.setRange(0, 10)
        self.retry_spin.setSuffix(" 次")
        form.addRow("失败自动重试", self.retry_spin)

        self.translation_language_combo = QComboBox()
        for label, value in TRANSLATION_LANGUAGES:
            self.translation_language_combo.addItem(label, value)
        form.addRow("翻译目标语言", self.translation_language_combo)

        self.translation_hotkey_input = QLineEdit()
        self.translation_hotkey_input.setPlaceholderText("cmd_r")
        form.addRow("翻译快捷键", self.translation_hotkey_input)

        self.translation_hotkey_mode_combo = QComboBox()
        self.translation_hotkey_mode_combo.addItem("按住说话，松开翻译", "hold")
        self.translation_hotkey_mode_combo.addItem(
            "按一次开始，再按一次结束并翻译",
            "toggle",
        )
        form.addRow("翻译触发模式", self.translation_hotkey_mode_combo)
        hotkey_panel.layout().addLayout(form)
        layout.addWidget(hotkey_panel)

        text_panel = self._section_panel(
            "文字处理",
            "识别完成后进行轻量处理，不额外调用模型。",
        )
        options_layout = QHBoxLayout()
        options_layout.setSpacing(18)
        self.clean_fillers_check = QCheckBox("清理口头禅和短重复")
        self.simplified_check = QCheckBox("繁体转简体")
        self.add_symbol_check = QCheckBox("补充标点")
        self.optimize_check = QCheckBox("优化识别结果")
        options_layout.addWidget(self.clean_fillers_check)
        options_layout.addWidget(self.simplified_check)
        options_layout.addWidget(self.add_symbol_check)
        options_layout.addWidget(self.optimize_check)
        options_layout.addStretch()
        text_panel.layout().addLayout(options_layout)
        layout.addWidget(text_panel)

        actions = QHBoxLayout()
        actions.addStretch()
        save_button = self._button(
            "保存并重启",
            QStyle.SP_DialogSaveButton,
            "primary",
        )
        save_button.clicked.connect(self.save_behavior_settings)
        actions.addWidget(save_button)
        layout.addLayout(actions)
        layout.addStretch()
        return page

    def _build_glossary_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        editor_panel = self._section_panel(
            "常用词与自动纠错",
            "输入口述形式和期望输出。规则会应用到普通转写、翻译原文和流式识别结果。",
        )
        editor = QHBoxLayout()
        editor.setSpacing(10)
        self.glossary_source_input = QLineEdit()
        self.glossary_source_input.setPlaceholderText("口述形式，例如：S S H")
        editor.addWidget(self.glossary_source_input, stretch=1)

        arrow = QLabel("→")
        arrow.setObjectName("glossaryArrow")
        arrow.setAlignment(Qt.AlignCenter)
        editor.addWidget(arrow)

        self.glossary_replacement_input = QLineEdit()
        self.glossary_replacement_input.setPlaceholderText("输出形式，例如：SSH")
        editor.addWidget(self.glossary_replacement_input, stretch=1)

        self.glossary_save_button = self._button(
            "添加词条",
            QStyle.SP_DialogSaveButton,
            "primary",
        )
        self.glossary_save_button.clicked.connect(self.save_glossary_entry)
        editor.addWidget(self.glossary_save_button)

        clear_button = self._button(
            "清空",
            QStyle.SP_DialogResetButton,
            "secondary",
        )
        clear_button.clicked.connect(self.clear_glossary_editor)
        editor.addWidget(clear_button)
        editor_panel.layout().addLayout(editor)

        self.glossary_status_label = QLabel("替换结果可留空，用于删除不需要的口头内容。")
        self.glossary_status_label.setObjectName("glossaryStatus")
        editor_panel.layout().addWidget(self.glossary_status_label)
        layout.addWidget(editor_panel)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        self.glossary_search = QLineEdit()
        self.glossary_search.setPlaceholderText("搜索口述形式或输出结果")
        self.glossary_search.setClearButtonEnabled(True)
        self.glossary_search.textChanged.connect(self.refresh_glossary)
        toolbar.addWidget(self.glossary_search, stretch=1)

        edit_button = self._button(
            "编辑",
            QStyle.SP_FileDialogDetailedView,
            "secondary",
        )
        edit_button.clicked.connect(self.edit_selected_glossary)
        toolbar.addWidget(edit_button)

        delete_button = self._button(
            "删除",
            QStyle.SP_TrashIcon,
            "danger",
        )
        delete_button.clicked.connect(self.delete_selected_glossary)
        toolbar.addWidget(delete_button)
        layout.addLayout(toolbar)

        self.glossary_table = self._table(
            ["启用", "口述形式", "输出结果", "更新时间"]
        )
        self.glossary_table.itemChanged.connect(self.toggle_glossary_entry)
        self.glossary_table.itemDoubleClicked.connect(self.edit_selected_glossary)
        glossary_header = self.glossary_table.horizontalHeader()
        glossary_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        glossary_header.setSectionResizeMode(1, QHeaderView.Stretch)
        glossary_header.setSectionResizeMode(2, QHeaderView.Stretch)
        glossary_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        layout.addWidget(self.glossary_table, stretch=1)

        test_panel = self._section_panel(
            "即时测试",
            "在这里检查词库效果，不会写入历史记录。",
        )
        test_row = QHBoxLayout()
        test_row.setSpacing(10)
        self.glossary_test_input = QLineEdit(
            "S S H Linux，S S H香港杠V P S。"
        )
        test_row.addWidget(self.glossary_test_input, stretch=1)
        test_button = self._button(
            "测试纠错",
            QStyle.SP_MediaPlay,
            "secondary",
        )
        test_button.clicked.connect(self.test_glossary)
        test_row.addWidget(test_button)
        test_panel.layout().addLayout(test_row)

        self.glossary_preview = QLabel()
        self.glossary_preview.setObjectName("glossaryPreview")
        self.glossary_preview.setWordWrap(True)
        test_panel.layout().addWidget(self.glossary_preview)
        layout.addWidget(test_panel)
        return page

    def _build_persona_page(self) -> QWidget:
        page = QScrollArea()
        page.setObjectName("personaScroll")
        page.setWidgetResizable(True)
        page.setFrameShape(QFrame.NoFrame)
        page.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        content.setObjectName("personaContent")
        content.setMinimumHeight(980)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        provider_panel = self._section_panel(
            "实时人设改写",
            "普通听写完成后按选定人设改写。翻译模式保持独立，不经过人设处理。",
        )
        provider_form = QFormLayout()
        provider_form.setHorizontalSpacing(22)
        provider_form.setVerticalSpacing(9)

        self.persona_enabled_check = QCheckBox("开启后，普通听写自动应用当前人设")
        provider_form.addRow("功能状态", self.persona_enabled_check)

        self.active_persona_combo = QComboBox()
        provider_form.addRow("当前人设", self.active_persona_combo)

        self.persona_provider_combo = QComboBox()
        for label, value in PERSONA_PROVIDERS:
            self.persona_provider_combo.addItem(label, value)
        provider_form.addRow("首选模型", self.persona_provider_combo)

        self.persona_fallback_combo = QComboBox()
        for label, value in PERSONA_FALLBACK_PROVIDERS:
            self.persona_fallback_combo.addItem(label, value)
        provider_form.addRow("失败备用", self.persona_fallback_combo)

        self.qwen_model_combo = QComboBox()
        for label, value in QWEN_REWRITE_MODELS:
            self.qwen_model_combo.addItem(label, value)
        provider_form.addRow("Qwen 模型", self.qwen_model_combo)

        self.ark_model_combo = QComboBox()
        for label, value in ARK_REWRITE_MODELS:
            self.ark_model_combo.addItem(label, value)
        provider_form.addRow("火山方舟模型", self.ark_model_combo)

        self.ark_key_input = self._password_input("火山方舟 Ark API Key")
        provider_form.addRow("火山 Ark Key", self.ark_key_input)

        self.persona_max_tokens_spin = QSpinBox()
        self.persona_max_tokens_spin.setRange(64, 4096)
        self.persona_max_tokens_spin.setSingleStep(64)
        self.persona_max_tokens_spin.setSuffix(" Token")
        provider_form.addRow("最大输出", self.persona_max_tokens_spin)
        provider_panel.layout().addLayout(provider_form)

        provider_actions = QHBoxLayout()
        provider_actions.addStretch()
        test_model_button = self._button(
            "测试当前模型",
            QStyle.SP_MediaPlay,
            "secondary",
        )
        test_model_button.clicked.connect(self.test_persona)
        provider_actions.addWidget(test_model_button)
        save_settings_button = self._button(
            "保存并重启",
            QStyle.SP_DialogSaveButton,
            "primary",
        )
        save_settings_button.clicked.connect(self.save_persona_settings)
        provider_actions.addWidget(save_settings_button)
        provider_panel.layout().addLayout(provider_actions)
        layout.addWidget(provider_panel)

        personas_panel = self._section_panel(
            "人设词库",
            "可直接使用内置人设，也可以添加自己的改写指令。",
        )
        persona_editor = QHBoxLayout()
        persona_editor.setSpacing(10)
        self.persona_name_input = QLineEdit()
        self.persona_name_input.setPlaceholderText("人设名称")
        self.persona_name_input.setMaximumWidth(190)
        persona_editor.addWidget(self.persona_name_input)

        self.persona_instruction_input = QPlainTextEdit()
        self.persona_instruction_input.setObjectName("compactTextEdit")
        self.persona_instruction_input.setPlaceholderText(
            "描述要如何改写，例如：整理为简洁、专业的项目进度汇报。"
        )
        self.persona_instruction_input.setMaximumHeight(74)
        persona_editor.addWidget(self.persona_instruction_input, stretch=1)

        persona_editor_actions = QVBoxLayout()
        self.persona_save_button = self._button(
            "添加人设",
            QStyle.SP_DialogSaveButton,
            "primary",
        )
        self.persona_save_button.clicked.connect(self.save_persona_entry)
        persona_editor_actions.addWidget(self.persona_save_button)
        clear_persona_button = self._button(
            "清空",
            QStyle.SP_DialogResetButton,
            "secondary",
        )
        clear_persona_button.clicked.connect(self.clear_persona_editor)
        persona_editor_actions.addWidget(clear_persona_button)
        persona_editor.addLayout(persona_editor_actions)
        personas_panel.layout().addLayout(persona_editor)

        persona_toolbar = QHBoxLayout()
        persona_toolbar.addStretch()
        edit_persona_button = self._button(
            "编辑",
            QStyle.SP_FileDialogDetailedView,
            "secondary",
        )
        edit_persona_button.clicked.connect(self.edit_selected_persona)
        persona_toolbar.addWidget(edit_persona_button)
        delete_persona_button = self._button(
            "删除",
            QStyle.SP_TrashIcon,
            "danger",
        )
        delete_persona_button.clicked.connect(self.delete_selected_persona)
        persona_toolbar.addWidget(delete_persona_button)
        personas_panel.layout().addLayout(persona_toolbar)

        self.persona_table = self._table(["启用", "名称", "类型", "改写指令"])
        self.persona_table.setMaximumHeight(180)
        self.persona_table.itemChanged.connect(self.toggle_persona_entry)
        self.persona_table.itemDoubleClicked.connect(self.edit_selected_persona)
        persona_header = self.persona_table.horizontalHeader()
        persona_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        persona_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        persona_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        persona_header.setSectionResizeMode(3, QHeaderView.Stretch)
        personas_panel.layout().addWidget(self.persona_table)
        layout.addWidget(personas_panel, stretch=1)

        test_panel = self._section_panel(
            "即时测试",
            "测试文本不会写入转写历史。",
        )
        test_row = QHBoxLayout()
        test_row.setSpacing(10)
        self.persona_test_input = QLineEdit(
            "今天天气很好，我准备出去走走。"
        )
        test_row.addWidget(self.persona_test_input, stretch=1)
        test_button = self._button(
            "执行改写",
            QStyle.SP_MediaPlay,
            "secondary",
        )
        test_button.clicked.connect(self.test_persona)
        test_row.addWidget(test_button)
        test_panel.layout().addLayout(test_row)

        self.persona_test_output = QLabel("选择人设和模型后，可在这里查看结果。")
        self.persona_test_output.setObjectName("personaPreview")
        self.persona_test_output.setWordWrap(True)
        self.persona_test_output.setTextInteractionFlags(Qt.TextSelectableByMouse)
        test_panel.layout().addWidget(self.persona_test_output)
        layout.addWidget(test_panel)
        layout.addStretch()
        page.setWidget(content)
        return page

    def _build_diagnostics_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        toolbar = QHBoxLayout()
        refresh_button = self._button(
            "重新检查",
            QStyle.SP_BrowserReload,
            "secondary",
        )
        refresh_button.clicked.connect(self.refresh_diagnostics)
        toolbar.addWidget(refresh_button)

        test_button = self._button(
            "测试 ASR",
            QStyle.SP_MediaPlay,
            "secondary",
        )
        test_button.clicked.connect(self.test_asr)
        toolbar.addWidget(test_button)

        cleanup_button = self._button(
            "清理录音缓存",
            QStyle.SP_TrashIcon,
            "danger",
        )
        cleanup_button.clicked.connect(self.cleanup_archive)
        toolbar.addWidget(cleanup_button)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        checks = QHBoxLayout()
        checks.setSpacing(10)
        self.service_check = self._diagnostic_card("后台服务")
        self.mic_check = self._diagnostic_card("麦克风")
        self.engine_check = self._diagnostic_card("识别配置")
        self.local_check = self._diagnostic_card("本地 Whisper")
        for card in (
            self.service_check[0],
            self.mic_check[0],
            self.engine_check[0],
            self.local_check[0],
        ):
            checks.addWidget(card)
        layout.addLayout(checks)

        log_header = QHBoxLayout()
        log_title = QLabel("运行日志")
        log_title.setObjectName("sectionTitle")
        self.log_path_label = QLabel("暂无日志")
        self.log_path_label.setObjectName("logPath")
        log_header.addWidget(log_title)
        log_header.addStretch()
        log_header.addWidget(self.log_path_label)
        layout.addLayout(log_header)

        self.log_view = QPlainTextEdit()
        self.log_view.setObjectName("logView")
        self.log_view.setReadOnly(True)
        self.log_view.setLineWrapMode(QPlainTextEdit.NoWrap)
        layout.addWidget(self.log_view, stretch=1)
        return page

    def _section_panel(self, title: str, detail: str) -> QFrame:
        panel = QFrame()
        panel.setObjectName("sectionPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(22, 18, 22, 20)
        panel_layout.setSpacing(12)
        title_label = QLabel(title)
        title_label.setObjectName("panelTitle")
        detail_label = QLabel(detail)
        detail_label.setObjectName("panelDetail")
        detail_label.setWordWrap(True)
        panel_layout.addWidget(title_label)
        panel_layout.addWidget(detail_label)
        return panel

    def _diagnostic_card(self, title: str) -> tuple[QFrame, QLabel]:
        card = QFrame()
        card.setObjectName("diagnosticCard")
        card.setProperty("status", "neutral")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 13, 16, 13)
        layout.setSpacing(5)
        title_label = QLabel(title)
        title_label.setObjectName("diagnosticTitle")
        value_label = QLabel("检查中")
        value_label.setObjectName("diagnosticValue")
        value_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        return card, value_label

    def _config_value(self, layout: QHBoxLayout, title: str) -> QLabel:
        block = QVBoxLayout()
        block.setSpacing(3)
        title_label = QLabel(title)
        title_label.setObjectName("configTitle")
        value_label = QLabel("-")
        value_label.setObjectName("configValue")
        value_label.setWordWrap(True)
        block.addWidget(title_label)
        block.addWidget(value_label)
        layout.addLayout(block, stretch=1)
        return value_label

    def _button(
        self,
        text: str,
        icon: QStyle.StandardPixmap,
        role: str,
    ) -> QPushButton:
        button = QPushButton(text)
        button.setProperty("role", role)
        button.setIcon(self.style().standardIcon(icon))
        button.setCursor(Qt.PointingHandCursor)
        return button

    @staticmethod
    def _password_input(placeholder: str) -> QLineEdit:
        field = QLineEdit()
        field.setEchoMode(QLineEdit.Password)
        field.setPlaceholderText(placeholder)
        return field

    @staticmethod
    def _table(headers: list[str]) -> QTableWidget:
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setObjectName("dataTable")
        table.setAlternatingRowColors(False)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setShowGrid(False)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(42)
        return table

    def _apply_styles(self) -> None:
        self.setFont(QFont("Ubuntu Sans", 10))
        self.setStyleSheet(
            """
            * {
                font-family: "Ubuntu Sans", "Noto Sans CJK SC";
                font-size: 14px;
                color: #172019;
            }
            QMainWindow, QWidget#appRoot, QFrame#contentPanel {
                background: #f3f5f2;
            }
            QFrame#sidebar {
                background: #101411;
                border: none;
            }
            QLabel#brandTitle {
                color: #f5f7f4;
                font-size: 22px;
                font-weight: 700;
            }
            QLabel#brandSubtitle {
                color: #8f9b92;
                font-size: 12px;
            }
            QLabel#versionLabel {
                color: #657169;
                font-size: 10px;
                font-weight: 700;
            }
            QListWidget#navigation {
                background: transparent;
                border: none;
                outline: none;
            }
            QListWidget#navigation::item {
                color: #aeb8b1;
                min-height: 42px;
                padding: 0 14px;
                margin: 3px 0;
                border-radius: 6px;
            }
            QListWidget#navigation::item:hover {
                background: #1a201c;
                color: #ffffff;
            }
            QListWidget#navigation::item:selected {
                background: #21392b;
                color: #f6fff9;
                font-weight: 700;
            }
            QLabel#pageTitle {
                font-size: 24px;
                font-weight: 700;
                color: #172019;
            }
            QFrame#statusChip {
                border-radius: 8px;
                border: 1px solid #d6ddd7;
                background: #ffffff;
            }
            QFrame#statusChip[state="running"] {
                background: #eaf7ef;
                border-color: #b8dfc7;
            }
            QLabel#statusDot {
                color: #a5aca7;
                font-size: 12px;
            }
            QFrame#statusChip[state="running"] QLabel#statusDot {
                color: #238553;
            }
            QLabel#statusText {
                color: #48534b;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton#iconButton {
                background: #ffffff;
                border: 1px solid #d9dfda;
                border-radius: 6px;
                padding: 0;
            }
            QPushButton#iconButton:hover {
                background: #e9ede9;
            }
            QFrame#heroPanel {
                background: #ffffff;
                border: 1px solid #dce2dd;
                border-radius: 8px;
            }
            QLabel#eyebrow {
                color: #238553;
                font-size: 10px;
                font-weight: 700;
            }
            QLabel#heroTitle {
                color: #162019;
                font-size: 22px;
                font-weight: 700;
            }
            QLabel#heroDetail, QLabel#pageHint, QLabel#panelDetail {
                color: #6b766e;
                font-size: 12px;
            }
            QFrame#metricCard, QFrame#diagnosticCard {
                background: #ffffff;
                border: 1px solid #dce2dd;
                border-radius: 8px;
            }
            QLabel#metricTitle, QLabel#diagnosticTitle, QLabel#configTitle {
                color: #737e76;
                font-size: 11px;
                font-weight: 600;
            }
            QLabel#metricValue {
                color: #142019;
                font-size: 25px;
                font-weight: 700;
            }
            QLabel#metricSubtitle {
                color: #8a948d;
                font-size: 10px;
            }
            QLabel#sectionTitle, QLabel#panelTitle {
                color: #1c251e;
                font-size: 15px;
                font-weight: 700;
            }
            QFrame#configBand {
                background: #e8ece8;
                border: 1px solid #d7ddd8;
                border-radius: 8px;
            }
            QLabel#configValue {
                color: #202a22;
                font-size: 13px;
                font-weight: 700;
            }
            QFrame#sectionPanel {
                background: #ffffff;
                border: 1px solid #dce2dd;
                border-radius: 8px;
            }
            QLabel#diagnosticValue {
                color: #4e5a51;
                font-size: 13px;
                font-weight: 700;
            }
            QFrame#diagnosticCard[status="good"] {
                background: #ecf8f0;
                border-color: #b8dfc7;
            }
            QFrame#diagnosticCard[status="bad"] {
                background: #fff0ee;
                border-color: #ecc5c1;
            }
            QFrame#diagnosticCard[status="warning"] {
                background: #fff7e8;
                border-color: #ebd2a6;
            }
            QPushButton {
                min-height: 36px;
                padding: 0 14px;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton[role="primary"] {
                color: #ffffff;
                background: #227d4f;
                border: 1px solid #227d4f;
            }
            QPushButton[role="primary"]:hover {
                background: #196840;
            }
            QPushButton[role="secondary"] {
                color: #263129;
                background: #ffffff;
                border: 1px solid #ccd4ce;
            }
            QPushButton[role="secondary"]:hover {
                background: #edf0ed;
            }
            QPushButton[role="danger"] {
                color: #9b3733;
                background: #fff7f6;
                border: 1px solid #e7c7c4;
            }
            QPushButton[role="danger"]:hover {
                background: #fde9e7;
            }
            QPushButton[role="link"] {
                color: #227d4f;
                background: transparent;
                border: none;
                padding: 0 4px;
            }
            QLineEdit, QComboBox, QSpinBox {
                min-height: 36px;
                background: #fbfcfb;
                border: 1px solid #cfd7d1;
                border-radius: 6px;
                padding: 0 10px;
                selection-background-color: #2e8a59;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
                border: 1px solid #2b8b58;
                background: #ffffff;
            }
            QComboBox::drop-down {
                border: none;
                width: 26px;
            }
            QCheckBox {
                spacing: 8px;
                color: #354038;
            }
            QTableWidget#dataTable {
                background: #ffffff;
                alternate-background-color: #ffffff;
                border: 1px solid #dce2dd;
                border-radius: 8px;
                outline: none;
                selection-background-color: #e5f3ea;
                selection-color: #152019;
            }
            QTableWidget#dataTable::item {
                border-bottom: 1px solid #edf0ed;
                padding: 0 8px;
            }
            QHeaderView::section {
                min-height: 34px;
                color: #667169;
                background: #eef1ee;
                border: none;
                border-bottom: 1px solid #d9dfda;
                padding: 0 8px;
                font-size: 11px;
                font-weight: 700;
            }
            QLabel#logPath {
                color: #7c867f;
                font-size: 11px;
            }
            QLabel#glossaryArrow {
                color: #238553;
                font-size: 20px;
                font-weight: 700;
                min-width: 24px;
            }
            QLabel#glossaryStatus {
                color: #728078;
                font-size: 11px;
            }
            QLabel#glossaryPreview {
                color: #1d5e3b;
                background: #edf7f0;
                border: 1px solid #cce3d4;
                border-radius: 6px;
                padding: 10px 12px;
                font-size: 13px;
                font-weight: 600;
            }
            QLabel#personaPreview {
                color: #23476b;
                background: #eef5fb;
                border: 1px solid #c7d9e8;
                border-radius: 6px;
                padding: 10px 12px;
                font-size: 13px;
                font-weight: 600;
                min-height: 36px;
            }
            QPlainTextEdit#compactTextEdit {
                color: #172019;
                background: #fbfcfb;
                border: 1px solid #cfd7d1;
                border-radius: 6px;
                padding: 7px 9px;
                selection-background-color: #2e8a59;
            }
            QPlainTextEdit#compactTextEdit:focus {
                border: 1px solid #2b8b58;
                background: #ffffff;
            }
            QPlainTextEdit#logView {
                color: #dce8df;
                background: #151a16;
                border: 1px solid #2b332d;
                border-radius: 8px;
                padding: 12px;
                font-family: "Ubuntu Mono";
                font-size: 12px;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 10px;
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background: #bec7c0;
                border-radius: 4px;
                min-height: 28px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            """
        )

    def change_page(self, index: int) -> None:
        if index < 0:
            return
        self.stack.setCurrentIndex(index)
        self.page_title.setText(self.PAGE_TITLES[index])
        if index == 1:
            self.refresh_history()
        elif index == 4:
            self.refresh_glossary()
        elif index == 5:
            self.refresh_personas()
        elif index == 6:
            self.refresh_diagnostics()

    def refresh_all(self) -> None:
        self.refresh_status()
        self.refresh_metrics()
        self.refresh_history()
        self.refresh_glossary()
        self.refresh_personas()
        self.refresh_diagnostics()
        self.refresh_logs()

    def refresh_passive_data(self) -> None:
        self.refresh_metrics()
        self.refresh_history()
        self.refresh_logs()

    def refresh_status(self) -> None:
        self._running = self.service.is_running()
        env = self.env_store.read()
        service_name = env.get("TRANSCRIPTION_SERVICE", "unknown").lower()
        service_label = SERVICE_LABELS.get(service_name, service_name or "未配置")
        hotkey = env.get("TRANSCRIPTION_HOTKEY", "alt_r")
        hotkey_label = format_hotkey(hotkey)
        mode = env.get("TRANSCRIPTION_HOTKEY_MODE", "hold")
        mode_label = "按住说话" if mode == "hold" else "按键切换"
        translation_hotkey = env.get("TRANSLATION_HOTKEY", "cmd_r")
        translation_hotkey_label = format_hotkey(translation_hotkey)
        translation_mode = env.get("TRANSLATION_HOTKEY_MODE", "hold")
        translation_mode_label = (
            "按住翻译" if translation_mode == "hold" else "按键切换"
        )
        target_language = env.get("TRANSLATION_TARGET_LANGUAGE", "en")
        target_label = TARGET_LANGUAGE_LABELS.get(target_language, target_language)
        persona_enabled = self.env_store.get_bool(
            env,
            "PERSONA_REWRITE_ENABLED",
            False,
        )
        persona_id = self.env_store.get_int(
            env,
            "PERSONA_ACTIVE_ID",
            0,
            minimum=0,
        )
        persona = self.personas.get(persona_id)
        persona_name = persona.name if persona is not None else "未选择"
        persona_provider = env.get("PERSONA_REWRITE_PROVIDER", "qwen")
        persona_provider_label = {
            "qwen": "Qwen",
            "ark": "火山",
            "agnes": "Agnes",
        }.get(persona_provider, persona_provider)

        self.status_chip.setProperty(
            "state",
            "running" if self._running else "stopped",
        )
        repolish(self.status_chip)
        self.top_status_label.setText("运行中" if self._running else "未运行")
        self.hero_title.setText(
            "语音输入已就绪" if self._running else "语音输入服务未启动"
        )
        self.hero_detail.setText(
            (
                f"{service_label} · 听写 {hotkey_label} · "
                f"翻译 {translation_hotkey_label} → {target_label} · "
                f"人设 {'开启' if persona_enabled else '关闭'}"
            )
            if self._running
            else "启动后台服务后，快捷键才会开始监听麦克风。"
        )
        self.service_button.setText("停止服务" if self._running else "启动服务")
        self.service_button.setIcon(
            self.style().standardIcon(
                QStyle.SP_MediaStop if self._running else QStyle.SP_MediaPlay
            )
        )
        self.service_button.setProperty(
            "role",
            "danger" if self._running else "primary",
        )
        repolish(self.service_button)

        self.engine_value.setText(service_label)
        self.hotkey_value.setText(f"{hotkey_label} · {mode_label}")
        self.microphone_value.setText(self.current_microphone())
        self.archive_value.setText(
            "保留录音" if env.get("AUDIO_ARCHIVE_MODE", "off") == "all" else "仅文字"
        )
        self.translation_value.setText(
            f"{translation_hotkey_label} · {translation_mode_label} → {target_label}"
        )
        self.persona_value.setText(
            (
                f"{persona_name} · {persona_provider_label}"
            )
            if persona_enabled
            else "关闭"
        )

    def refresh_metrics(self) -> None:
        stats = self.history.stats_today()
        self.today_metric.set_value(str(stats["total"]))
        self.success_metric.set_value(f"{stats['success_rate']:.0f}%")
        self.latency_metric.set_value(
            f"{stats['avg_latency']:.1f} 秒" if stats["avg_latency"] else "-"
        )
        self.duration_metric.set_value(format_duration(float(stats["duration"])))

    def refresh_history(self) -> None:
        query = self.history_search.text() if hasattr(self, "history_search") else ""
        records = self.history.recent(250, query)
        self._history_rows = records

        self.history_table.setSortingEnabled(False)
        self.history_table.setRowCount(len(records))
        for row, record in enumerate(records):
            values = [
                str(record.id),
                format_time(record.created_at),
                record.text or record.error or "识别失败",
                service_display(record.service),
                record.model,
                format_duration(record.duration_seconds),
                format_duration(record.latency_seconds),
                "成功" if record.status == "success" else "失败",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in {5, 6, 7}:
                    item.setTextAlignment(Qt.AlignCenter)
                if record.status != "success" and column in {2, 7}:
                    item.setForeground(QBrush(QColor("#b43b38")))
                self.history_table.setItem(row, column, item)

        recent = self.history.recent(5)
        self.recent_table.setRowCount(len(recent))
        for row, record in enumerate(recent):
            values = [
                format_time(record.created_at),
                record.text or record.error or "识别失败",
                service_display(record.service),
                format_duration(record.latency_seconds),
            ]
            for column, value in enumerate(values):
                self.recent_table.setItem(row, column, QTableWidgetItem(value))

    def refresh_glossary(self) -> None:
        query = self.glossary_search.text() if hasattr(self, "glossary_search") else ""
        entries = self.glossary.entries(query)
        self._glossary_rows = entries

        self._glossary_updating = True
        self.glossary_table.blockSignals(True)
        self.glossary_table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            status_item = QTableWidgetItem("启用" if entry.enabled else "停用")
            status_item.setFlags(
                Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable
            )
            status_item.setCheckState(Qt.Checked if entry.enabled else Qt.Unchecked)
            status_item.setTextAlignment(Qt.AlignCenter)
            self.glossary_table.setItem(row, 0, status_item)
            self.glossary_table.setItem(row, 1, QTableWidgetItem(entry.source))
            self.glossary_table.setItem(
                row,
                2,
                QTableWidgetItem(entry.replacement or "（删除匹配内容）"),
            )
            updated_item = QTableWidgetItem(format_time(entry.updated_at))
            updated_item.setTextAlignment(Qt.AlignCenter)
            self.glossary_table.setItem(row, 3, updated_item)
        self.glossary_table.blockSignals(False)
        self._glossary_updating = False
        self.test_glossary()

    def refresh_personas(self, selected_id: int | None = None) -> None:
        if not hasattr(self, "persona_table"):
            return
        if selected_id is None:
            selected_id = self.active_persona_combo.currentData()
        entries = self.personas.entries()
        self._persona_rows = entries

        self.active_persona_combo.blockSignals(True)
        self.active_persona_combo.clear()
        for entry in entries:
            if entry.enabled:
                self.active_persona_combo.addItem(entry.name, entry.id)
        active_index = self.active_persona_combo.findData(selected_id)
        self.active_persona_combo.setCurrentIndex(
            active_index if active_index >= 0 else 0
        )
        self.active_persona_combo.blockSignals(False)

        self._persona_updating = True
        self.persona_table.blockSignals(True)
        self.persona_table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            status_item = QTableWidgetItem("启用" if entry.enabled else "停用")
            status_item.setFlags(
                Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable
            )
            status_item.setCheckState(Qt.Checked if entry.enabled else Qt.Unchecked)
            status_item.setTextAlignment(Qt.AlignCenter)
            self.persona_table.setItem(row, 0, status_item)
            self.persona_table.setItem(row, 1, QTableWidgetItem(entry.name))
            type_item = QTableWidgetItem("内置" if entry.builtin else "自定义")
            type_item.setTextAlignment(Qt.AlignCenter)
            self.persona_table.setItem(row, 2, type_item)
            self.persona_table.setItem(
                row,
                3,
                QTableWidgetItem(entry.instruction),
            )
        self.persona_table.blockSignals(False)
        self._persona_updating = False

    def refresh_diagnostics(self) -> None:
        env = self.env_store.read()
        service_name = env.get("TRANSCRIPTION_SERVICE", "").lower()

        self._set_diagnostic(
            self.service_check,
            "运行中" if self.service.is_running() else "未启动",
            "good" if self.service.is_running() else "bad",
        )

        microphone = self.current_microphone()
        self._set_diagnostic(
            self.mic_check,
            microphone,
            "good" if microphone != "不可用" else "bad",
        )

        key_map = {
            "aliyun": "DASHSCOPE_API_KEY",
            "dashscope": "DASHSCOPE_API_KEY",
            "bailian": "DASHSCOPE_API_KEY",
            "openai": "OFFICIAL_OPENAI_API_KEY",
            "doubao": "DOUBAO_ACCESS_KEY",
            "groq": "GROQ_API_KEY",
            "siliconflow": "SILICONFLOW_API_KEY",
        }
        key_name = key_map.get(service_name)
        configured = bool(env.get(key_name, "")) if key_name else False
        self._set_diagnostic(
            self.engine_check,
            f"{SERVICE_LABELS.get(service_name, service_name or '未配置')} · "
            f"{'凭据已配置' if configured else '缺少凭据'}",
            "good" if configured else "warning",
        )

        cli_path = Path(env.get("WHISPER_CLI_PATH", ""))
        model_path = self._resolve_whisper_model(env)
        local_ready = cli_path.is_file() and model_path is not None and model_path.is_file()
        self._set_diagnostic(
            self.local_check,
            "可用" if local_ready else "未配置",
            "good" if local_ready else "warning",
        )
        self.refresh_logs()

    def _set_diagnostic(
        self,
        diagnostic: tuple[QFrame, QLabel],
        text: str,
        status: str,
    ) -> None:
        card, label = diagnostic
        label.setText(text)
        card.setProperty("status", status)
        repolish(card)

    def refresh_logs(self) -> None:
        log_path, lines = self.service.latest_log_lines()
        self.log_path_label.setText(log_path.name if log_path else "暂无日志")
        self.log_view.setPlainText("\n".join(lines) if lines else "暂无运行日志")
        scroll_bar = self.log_view.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum())

    def load_settings(self) -> None:
        env = self.env_store.read()
        set_combo_data(
            self.default_service_combo,
            env.get("TRANSCRIPTION_SERVICE", "aliyun"),
        )
        set_combo_data(
            self.batch_service_combo,
            env.get("BATCH_TRANSCRIPTION_SERVICE", "aliyun"),
        )
        self.model_input.setText(env.get("DASHSCOPE_ASR_MODEL", "qwen3-asr-flash"))
        self.translation_model_input.setText(
            env.get("DASHSCOPE_TRANSLATION_MODEL", "qwen-mt-flash")
        )
        self.dashscope_key_input.setText(env.get("DASHSCOPE_API_KEY", ""))
        self.openai_key_input.setText(
            env.get("OFFICIAL_OPENAI_API_KEY", env.get("OPENAI_API_KEY", ""))
        )
        self.whisper_cli_input.setText(env.get("WHISPER_CLI_PATH", ""))
        self.whisper_model_input.setText(
            env.get("WHISPER_MODEL_PATH", "models/ggml-large-v3.bin")
        )

        self.hotkey_input.setText(env.get("TRANSCRIPTION_HOTKEY", "alt_r"))
        set_combo_data(
            self.hotkey_mode_combo,
            env.get("TRANSCRIPTION_HOTKEY_MODE", "hold"),
        )
        set_combo_data(self.paste_combo, env.get("PASTE_HOTKEY", "ctrl+v"))
        set_combo_data(self.archive_combo, env.get("AUDIO_ARCHIVE_MODE", "off"))
        self.retry_spin.setValue(
            self.env_store.get_int(
                env,
                "AUTO_RETRY_LIMIT",
                5,
                minimum=0,
                maximum=10,
            )
        )
        set_combo_data(
            self.translation_language_combo,
            env.get("TRANSLATION_TARGET_LANGUAGE", "en"),
        )
        self.translation_hotkey_input.setText(
            env.get("TRANSLATION_HOTKEY", "cmd_r")
        )
        set_combo_data(
            self.translation_hotkey_mode_combo,
            env.get("TRANSLATION_HOTKEY_MODE", "hold"),
        )
        self.clean_fillers_check.setChecked(
            self.env_store.get_bool(env, "CLEAN_ASR_FILLERS", False)
        )
        self.simplified_check.setChecked(
            self.env_store.get_bool(env, "CONVERT_TO_SIMPLIFIED", False)
        )
        self.add_symbol_check.setChecked(
            self.env_store.get_bool(env, "ADD_SYMBOL", False)
        )
        self.optimize_check.setChecked(
            self.env_store.get_bool(env, "OPTIMIZE_RESULT", False)
        )
        self.persona_enabled_check.setChecked(
            self.env_store.get_bool(env, "PERSONA_REWRITE_ENABLED", False)
        )
        set_combo_data(
            self.persona_provider_combo,
            env.get("PERSONA_REWRITE_PROVIDER", "qwen"),
        )
        set_combo_data(
            self.persona_fallback_combo,
            env.get("PERSONA_FALLBACK_PROVIDER", "ark"),
        )
        set_combo_data(
            self.qwen_model_combo,
            env.get("QWEN_REWRITE_MODEL", "qwen-flash"),
        )
        set_combo_data(
            self.ark_model_combo,
            env.get(
                "ARK_REWRITE_MODEL",
                "doubao-seed-2-0-mini-260428",
            ),
        )
        self.ark_key_input.setText(
            env.get("ARK_API_KEY", env.get("VOLCENGINE_ARK_API_KEY", ""))
        )
        self.persona_max_tokens_spin.setValue(
            self.env_store.get_int(
                env,
                "PERSONA_MAX_TOKENS",
                800,
                minimum=64,
                maximum=4096,
            )
        )
        self.refresh_personas(
            selected_id=self.env_store.get_int(
                env,
                "PERSONA_ACTIVE_ID",
                0,
                minimum=0,
            )
        )

    def save_engine_settings(self) -> None:
        default_service = self.default_service_combo.currentData()
        batch_service = self.batch_service_combo.currentData()
        if default_service in {value for _, value in BATCH_SERVICES}:
            batch_service = default_service

        self.env_store.update(
            {
                "TRANSCRIPTION_SERVICE": default_service,
                "BATCH_TRANSCRIPTION_SERVICE": batch_service,
                "DASHSCOPE_ASR_MODEL": self.model_input.text().strip()
                or "qwen3-asr-flash",
                "DASHSCOPE_TRANSLATION_MODEL": self.translation_model_input.text().strip()
                or "qwen-mt-flash",
                "DASHSCOPE_API_KEY": self.dashscope_key_input.text().strip(),
                "OFFICIAL_OPENAI_API_KEY": self.openai_key_input.text().strip(),
                "WHISPER_CLI_PATH": self.whisper_cli_input.text().strip(),
                "WHISPER_MODEL_PATH": self.whisper_model_input.text().strip()
                or "models/ggml-large-v3.bin",
            }
        )
        self._restart_after_save("识别引擎配置已保存。")

    def save_behavior_settings(self) -> None:
        self.env_store.update(
            {
                "TRANSCRIPTION_HOTKEY": self.hotkey_input.text().strip() or "alt_r",
                "TRANSCRIPTION_HOTKEY_MODE": self.hotkey_mode_combo.currentData(),
                "PASTE_HOTKEY": self.paste_combo.currentData(),
                "AUDIO_ARCHIVE_MODE": self.archive_combo.currentData(),
                "AUTO_RETRY_LIMIT": self.retry_spin.value(),
                "TRANSLATION_SERVICE": "aliyun",
                "TRANSLATION_TARGET_LANGUAGE": self.translation_language_combo.currentData(),
                "TRANSLATION_HOTKEY": self.translation_hotkey_input.text().strip()
                or "cmd_r",
                "TRANSLATION_HOTKEY_MODE": self.translation_hotkey_mode_combo.currentData(),
                "CLEAN_ASR_FILLERS": str(self.clean_fillers_check.isChecked()).lower(),
                "CONVERT_TO_SIMPLIFIED": str(self.simplified_check.isChecked()).lower(),
                "ADD_SYMBOL": str(self.add_symbol_check.isChecked()).lower(),
                "OPTIMIZE_RESULT": str(self.optimize_check.isChecked()).lower(),
            }
        )
        self._restart_after_save("输入和文字设置已保存。")

    def save_persona_settings(self) -> None:
        active_id = self.active_persona_combo.currentData()
        if active_id is None:
            QMessageBox.warning(self, "无法保存", "请至少启用一个人设。")
            return
        self.env_store.update(
            {
                "PERSONA_REWRITE_ENABLED": str(
                    self.persona_enabled_check.isChecked()
                ).lower(),
                "PERSONA_ACTIVE_ID": active_id,
                "PERSONA_REWRITE_PROVIDER": self.persona_provider_combo.currentData(),
                "PERSONA_FALLBACK_PROVIDER": self.persona_fallback_combo.currentData(),
                "QWEN_REWRITE_MODEL": self.qwen_model_combo.currentData(),
                "ARK_API_KEY": self.ark_key_input.text().strip(),
                "ARK_BASE_URL": "https://ark.cn-beijing.volces.com/api/v3",
                "ARK_REWRITE_MODEL": self.ark_model_combo.currentData(),
                "PERSONA_MAX_TOKENS": self.persona_max_tokens_spin.value(),
                "PERSONA_TEMPERATURE": "0.35",
                "QWEN_TIMEOUT_SECONDS": "30",
                "ARK_TIMEOUT_SECONDS": "20",
            }
        )
        self._restart_after_save("人设与改写配置已保存。")

    def _restart_after_save(self, message: str) -> None:
        if self.service.is_running():
            success, detail = self.service.restart()
            if not success:
                QMessageBox.critical(self, "重启失败", detail)
                return
            message = f"{message}\n服务已自动重启。"
        self.load_settings()
        self.refresh_all()
        QMessageBox.information(self, "配置已保存", message)

    def toggle_service(self) -> None:
        success, message = (
            self.service.stop() if self._running else self.service.start()
        )
        self.refresh_all()
        if not success:
            QMessageBox.critical(self, "操作失败", message)

    def restart_service(self) -> None:
        success, message = self.service.restart()
        self.refresh_all()
        if not success:
            QMessageBox.critical(self, "重启失败", message)

    def test_asr(self) -> None:
        env = self.env_store.read()
        platform = env.get("BATCH_TRANSCRIPTION_SERVICE", "aliyun")
        script = f"""
import os
from dotenv import load_dotenv
load_dotenv('.env')
os.environ['SERVICE_PLATFORM'] = {platform!r}
from src.transcription.whisper import WhisperProcessor
p = WhisperProcessor()
with open('assets/audio/test_audio.wav', 'rb') as f:
    text, error = p.process_audio(f)
print(error or text)
"""
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            result = self.service.run(
                [".venv/bin/python", "-c", script],
                timeout=90,
            )
        except Exception as exc:
            QMessageBox.critical(self, "ASR 测试失败", str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()

        output = ((result.stdout or "") + (result.stderr or "")).strip()
        if result.returncode == 0:
            QMessageBox.information(self, "ASR 测试结果", output or "测试完成")
        else:
            QMessageBox.critical(self, "ASR 测试失败", output or "未知错误")

    def cleanup_archive(self) -> None:
        answer = QMessageBox.question(
            self,
            "清理录音缓存",
            "这会删除已归档的音频文件和旧版转写缓存，但不会删除文字历史。继续吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        audio_dir = self.root / "audio_archive" / "audio"
        removed = 0
        if audio_dir.exists():
            for path in audio_dir.glob("*.wav"):
                path.unlink(missing_ok=True)
                removed += 1
        (self.root / "audio_archive" / "cache.json").unlink(missing_ok=True)
        QMessageBox.information(self, "已清理", f"已删除 {removed} 个录音文件。")

    def save_glossary_entry(self) -> None:
        source = self.glossary_source_input.text()
        replacement = self.glossary_replacement_input.text()
        enabled = True
        if self._editing_glossary_id is not None:
            current = next(
                (
                    entry
                    for entry in self._glossary_rows
                    if entry.id == self._editing_glossary_id
                ),
                None,
            )
            enabled = current.enabled if current is not None else True

        try:
            entry_id = self.glossary.save(
                source,
                replacement,
                entry_id=self._editing_glossary_id,
                enabled=enabled,
            )
        except Exception as exc:
            QMessageBox.critical(self, "词条保存失败", str(exc))
            return

        action = "更新" if self._editing_glossary_id is not None else "添加"
        self.clear_glossary_editor()
        self.glossary_status_label.setText(
            f"已{action}词条 #{entry_id}，下一次语音输入立即生效。"
        )
        self.refresh_glossary()

    def clear_glossary_editor(self, *_args: object) -> None:
        self._editing_glossary_id = None
        self.glossary_source_input.clear()
        self.glossary_replacement_input.clear()
        self.glossary_save_button.setText("添加词条")
        self.glossary_status_label.setText(
            "替换结果可留空，用于删除不需要的口头内容。"
        )
        self.glossary_source_input.setFocus()

    def edit_selected_glossary(self, *_args: object) -> None:
        row = self.glossary_table.currentRow()
        if row < 0 or row >= len(self._glossary_rows):
            return
        entry = self._glossary_rows[row]
        self._editing_glossary_id = entry.id
        self.glossary_source_input.setText(entry.source)
        self.glossary_replacement_input.setText(entry.replacement)
        self.glossary_save_button.setText("更新词条")
        self.glossary_status_label.setText(f"正在编辑词条 #{entry.id}")
        self.glossary_source_input.setFocus()
        self.glossary_source_input.selectAll()

    def delete_selected_glossary(self) -> None:
        row = self.glossary_table.currentRow()
        if row < 0 or row >= len(self._glossary_rows):
            return
        entry = self._glossary_rows[row]
        answer = QMessageBox.question(
            self,
            "删除词条",
            f"确定删除“{entry.source} → {entry.replacement}”吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.glossary.delete(entry.id)
        if self._editing_glossary_id == entry.id:
            self.clear_glossary_editor()
        self.glossary_status_label.setText(f"已删除词条 #{entry.id}")
        self.refresh_glossary()

    def toggle_glossary_entry(self, item: QTableWidgetItem) -> None:
        if self._glossary_updating or item.column() != 0:
            return
        row = item.row()
        if row < 0 or row >= len(self._glossary_rows):
            return
        entry = self._glossary_rows[row]
        enabled = item.checkState() == Qt.Checked
        self.glossary.set_enabled(entry.id, enabled)
        self.glossary_status_label.setText(
            f"已{'启用' if enabled else '停用'}“{entry.source}”。"
        )
        self.refresh_glossary()

    def test_glossary(self) -> None:
        text = self.glossary_test_input.text().strip()
        if not text:
            self.glossary_preview.setText("请输入测试文本。")
            return
        corrected = self.glossary_processor.apply(text)
        self.glossary_preview.setText(f"纠错结果：{corrected}")

    def save_persona_entry(self) -> None:
        name = self.persona_name_input.text()
        instruction = self.persona_instruction_input.toPlainText()
        enabled = True
        if self._editing_persona_id is not None:
            current = self.personas.get(self._editing_persona_id)
            enabled = current.enabled if current is not None else True
        try:
            persona_id = self.personas.save(
                name,
                instruction,
                persona_id=self._editing_persona_id,
                enabled=enabled,
            )
        except Exception as exc:
            QMessageBox.critical(self, "人设保存失败", str(exc))
            return

        self.clear_persona_editor()
        self.refresh_personas(selected_id=persona_id)
        self.persona_test_output.setText(
            f"人设“{name.strip()}”已保存，下一次改写立即生效。"
        )

    def clear_persona_editor(self, *_args: object) -> None:
        self._editing_persona_id = None
        self.persona_name_input.clear()
        self.persona_instruction_input.clear()
        self.persona_save_button.setText("添加人设")
        self.persona_name_input.setFocus()

    def edit_selected_persona(self, *_args: object) -> None:
        row = self.persona_table.currentRow()
        if row < 0 or row >= len(self._persona_rows):
            return
        persona = self._persona_rows[row]
        self._editing_persona_id = persona.id
        self.persona_name_input.setText(persona.name)
        self.persona_instruction_input.setPlainText(persona.instruction)
        self.persona_save_button.setText("更新人设")
        self.persona_name_input.setFocus()
        self.persona_name_input.selectAll()

    def delete_selected_persona(self) -> None:
        row = self.persona_table.currentRow()
        if row < 0 or row >= len(self._persona_rows):
            return
        persona = self._persona_rows[row]
        if persona.builtin:
            QMessageBox.information(
                self,
                "内置人设",
                "内置人设不能删除，可以编辑或停用。",
            )
            return
        answer = QMessageBox.question(
            self,
            "删除人设",
            f"确定删除“{persona.name}”吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            self.personas.delete(persona.id)
        except Exception as exc:
            QMessageBox.critical(self, "删除失败", str(exc))
            return
        if self._editing_persona_id == persona.id:
            self.clear_persona_editor()
        self.refresh_personas()

    def toggle_persona_entry(self, item: QTableWidgetItem) -> None:
        if self._persona_updating or item.column() != 0:
            return
        row = item.row()
        if row < 0 or row >= len(self._persona_rows):
            return
        persona = self._persona_rows[row]
        enabled = item.checkState() == Qt.Checked
        self.personas.set_enabled(persona.id, enabled)
        self.refresh_personas()

    def test_persona(self) -> None:
        text = self.persona_test_input.text().strip()
        persona_id = self.active_persona_combo.currentData()
        provider = self.persona_provider_combo.currentData()
        if not text:
            self.persona_test_output.setText("请输入测试文本。")
            return
        if persona_id is None:
            self.persona_test_output.setText("请至少启用一个人设。")
            return

        settings = self.env_store.read()
        settings.update(
            {
                "PERSONA_REWRITE_PROVIDER": provider,
                "PERSONA_FALLBACK_PROVIDER": self.persona_fallback_combo.currentData(),
                "QWEN_REWRITE_MODEL": self.qwen_model_combo.currentData(),
                "ARK_API_KEY": self.ark_key_input.text().strip(),
                "ARK_REWRITE_MODEL": self.ark_model_combo.currentData(),
                "PERSONA_MAX_TOKENS": str(self.persona_max_tokens_spin.value()),
            }
        )
        dashscope_key = self.dashscope_key_input.text().strip()
        if dashscope_key:
            settings["DASHSCOPE_API_KEY"] = dashscope_key

        processor = PersonaProcessor(store=self.personas, settings=settings)
        self.persona_test_output.setText("正在调用当前模型...")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            result = processor.rewrite(
                text,
                persona_id=int(persona_id),
                provider=str(provider),
                on_update=self._update_persona_test_output,
            )
        except Exception as exc:
            self.persona_test_output.setText(f"测试失败：{exc}")
        else:
            self.persona_test_output.setText(result)
        finally:
            QApplication.restoreOverrideCursor()

    def _update_persona_test_output(self, text: str) -> None:
        self.persona_test_output.setText(text)
        QApplication.processEvents()

    def copy_selected_history(self, *_args: object) -> None:
        row = self.history_table.currentRow()
        if row < 0 or row >= len(self._history_rows):
            return
        record = self._history_rows[row]
        text = record.text or record.error or ""
        QApplication.clipboard().setText(text)

    def delete_selected_history(self) -> None:
        row = self.history_table.currentRow()
        if row < 0 or row >= len(self._history_rows):
            return
        record = self._history_rows[row]
        answer = QMessageBox.question(
            self,
            "删除历史",
            "确定删除这条转写记录吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.history.delete(record.id)
        self.refresh_history()
        self.refresh_metrics()

    @staticmethod
    def current_microphone() -> str:
        try:
            device = sd.query_devices(kind="input")
            return str(device.get("name", "系统默认麦克风"))
        except Exception:
            return "不可用"

    @staticmethod
    def _resolve_whisper_model(env: dict[str, str]) -> Path | None:
        cli_value = env.get("WHISPER_CLI_PATH", "")
        model_value = env.get("WHISPER_MODEL_PATH", "")
        if not cli_value or not model_value:
            return None
        model_path = Path(model_value).expanduser()
        if model_path.is_absolute():
            return model_path
        cli_path = Path(cli_value).expanduser()
        try:
            whisper_root = cli_path.parents[2]
        except IndexError:
            return None
        return whisper_root / model_path


if __name__ == "__main__":
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
    app = QApplication([])
    app.setApplicationName(APP_NAME)
    window = ControlUI()
    window.show()
    app.exec_()
