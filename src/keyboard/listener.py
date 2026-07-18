from pynput.keyboard import Controller, Key, Listener
import pyperclip
from ..utils.logger import logger
import threading
import time
from .inputState import InputState
from .paste_strategy import detect_active_window, resolve_paste_hotkey
import os


class KeyboardManager:
    KEY_ALIASES = {
        "ctrl": Key.ctrl,
        "control": Key.ctrl,
        "ctrl_l": Key.ctrl_l,
        "control_l": Key.ctrl_l,
        "ctrl_r": Key.ctrl_r,
        "control_r": Key.ctrl_r,
        "cmd": Key.cmd,
        "command": Key.cmd,
        "cmd_l": getattr(Key, "cmd_l", Key.cmd),
        "command_l": getattr(Key, "cmd_l", Key.cmd),
        "left_command": getattr(Key, "cmd_l", Key.cmd),
        "cmd_r": Key.cmd_r,
        "command_r": Key.cmd_r,
        "right_command": Key.cmd_r,
        "win": Key.cmd,
        "windows": Key.cmd,
        "super": Key.cmd,
        "alt": Key.alt,
        "option": Key.alt,
        "alt_l": getattr(Key, "alt_l", Key.alt),
        "option_l": getattr(Key, "alt_l", Key.alt),
        "left_option": getattr(Key, "alt_l", Key.alt),
        "alt_r": Key.alt_r,
        "option_r": Key.alt_r,
        "right_option": Key.alt_r,
        "alt_gr": Key.alt_gr,
    }
    KEY_DISPLAY_NAMES = {
        "ctrl": "Ctrl",
        "control": "Ctrl",
        "ctrl_l": "Left Ctrl",
        "control_l": "Left Ctrl",
        "ctrl_r": "Right Ctrl",
        "control_r": "Right Ctrl",
        "cmd": "Cmd",
        "command": "Cmd",
        "cmd_l": "Left Command",
        "command_l": "Left Command",
        "left_command": "Left Command",
        "cmd_r": "Right Command",
        "command_r": "Right Command",
        "right_command": "Right Command",
        "win": "Win",
        "windows": "Win",
        "super": "Win",
        "alt": "Alt",
        "option": "Option",
        "alt_l": "Left Alt",
        "option_l": "Left Option",
        "left_option": "Left Option",
        "alt_r": "Right Alt",
        "option_r": "Right Option",
        "right_option": "Right Option",
        "alt_gr": "AltGr",
    }
    SIDE_SPECIFIC_ALIASES = {
        "ctrl_l": Key.ctrl_l,
        "control_l": Key.ctrl_l,
        "ctrl_r": Key.ctrl_r,
        "control_r": Key.ctrl_r,
        "cmd_l": getattr(Key, "cmd_l", Key.cmd),
        "command_l": getattr(Key, "cmd_l", Key.cmd),
        "left_command": getattr(Key, "cmd_l", Key.cmd),
        "cmd_r": Key.cmd_r,
        "command_r": Key.cmd_r,
        "right_command": Key.cmd_r,
        "alt_l": getattr(Key, "alt_l", Key.alt),
        "option_l": getattr(Key, "alt_l", Key.alt),
        "left_option": getattr(Key, "alt_l", Key.alt),
        "alt_r": Key.alt_r,
        "option_r": Key.alt_r,
        "right_option": Key.alt_r,
        "shift_l": getattr(Key, "shift_l", Key.shift),
        "shift_r": Key.shift_r,
    }

    def __init__(
        self,
        on_record_start,
        on_record_stop,
        on_translate_start,
        on_translate_stop,
        on_kimi_start,
        on_kimi_stop,
        on_reset_state,
        on_state_change=None,
        on_smart_start=None,
        on_smart_stop=None,
        on_agent_start=None,
        on_agent_stop=None,
    ):
        self.keyboard = Controller()
        self.ctrl_pressed = False  # 快捷键修饰键状态
        self.f_pressed = False  # F键状态
        self.i_pressed = False  # I键状态
        self.single_hotkey_pressed = False
        self.single_translation_hotkey_pressed = False
        self.terminal_mode_key_pressed = False
        self.terminal_mode_active = False
        self.agent_mode_key_pressed = False
        self.agent_mode_active = False
        self.single_smart_hotkey_pressed = False
        self.temp_text_length = 0  # 用于跟踪临时文本的长度
        self.processing_text = None  # 用于跟踪正在处理的文本
        self.error_message = None  # 用于跟踪错误信息
        self.warning_message = None  # 用于跟踪警告信息
        self.is_recording = False  # toggle模式的录音状态
        self.last_key_time = 0  # 防止重复触发
        self.KEY_DEBOUNCE_TIME = 0.3  # 按键防抖时间（秒）
        
        
        # 回调函数
        self.on_record_start = on_record_start
        self.on_record_stop = on_record_stop
        self.on_translate_start = on_translate_start
        self.on_translate_stop = on_translate_stop
        self.on_kimi_start = on_kimi_start
        self.on_kimi_stop = on_kimi_stop
        self.on_reset_state = on_reset_state
        self.on_state_change = on_state_change
        self.on_smart_start = on_smart_start or on_record_start
        self.on_smart_stop = on_smart_stop or on_record_stop
        self.on_agent_start = on_agent_start or on_record_start
        self.on_agent_stop = on_agent_stop or on_record_stop
        self._direct_agent_recording = False

        
        # 状态管理
        self._state = InputState.IDLE
        self._state_messages = {
            InputState.IDLE: "",
            InputState.RECORDING: "0",
            InputState.RECORDING_TERMINAL: "0",
            InputState.RECORDING_AGENT: "0",
            InputState.RECORDING_SMART: "0",
            InputState.RECORDING_TRANSLATE: "0",
            InputState.RECORDING_KIMI: "0",
            InputState.PROCESSING: "1",
            InputState.PROCESSING_AGENT: "1",
            InputState.PROCESSING_SMART: "1",
            InputState.PROCESSING_KIMI: "1",
            InputState.TRANSLATING: "1",
            InputState.ERROR: lambda msg: f"{msg}",  # 错误消息使用函数动态生成
            InputState.WARNING: lambda msg: f"! {msg}"  # 警告消息使用感叹号
        }

        self.state_symbol_enabled = True

        # 获取系统平台
        self.system_platform = os.getenv("SYSTEM_PLATFORM", "").lower()
        if self.system_platform in ("win", "windows", "linux"):
            self.system_modifier = Key.ctrl
            logger.info("配置到Windows/Linux平台")
        else:
            self.system_modifier = Key.cmd
            logger.info("配置到Mac平台")
        

        # 获取转录按钮和快捷键修饰键
        (
            self.transcriptions_button,
            transcriptions_display,
            self.transcriptions_button_token,
        ) = self._resolve_button(
            "TRANSCRIPTIONS_BUTTON",
            "f",
        )
        (
            self.translations_button,
            modifier_display,
            self.translations_button_token,
        ) = self._resolve_button(
            "TRANSLATIONS_BUTTON",
            "win",
        )
        transcription_hotkey = os.getenv("TRANSCRIPTION_HOTKEY", "").strip().lower()
        self.single_transcription_hotkey = None
        self.single_transcription_hotkey_display = ""
        self.single_transcription_hotkey_token = ""
        self.single_transcription_hotkey_mode = os.getenv("TRANSCRIPTION_HOTKEY_MODE", "toggle").strip().lower()
        if transcription_hotkey:
            (
                self.single_transcription_hotkey,
                self.single_transcription_hotkey_display,
                self.single_transcription_hotkey_token,
            ) = self._resolve_button("TRANSCRIPTION_HOTKEY", transcription_hotkey)
            if self.single_transcription_hotkey_mode not in {"toggle", "hold"}:
                logger.error(f"无效的 TRANSCRIPTION_HOTKEY_MODE={self.single_transcription_hotkey_mode}，回退到 toggle")
                self.single_transcription_hotkey_mode = "toggle"

        translation_hotkey = os.getenv("TRANSLATION_HOTKEY", "cmd_r").strip().lower()
        self.single_translation_hotkey = None
        self.single_translation_hotkey_display = ""
        self.single_translation_hotkey_token = ""
        self.single_translation_hotkey_mode = os.getenv(
            "TRANSLATION_HOTKEY_MODE",
            "hold",
        ).strip().lower()
        if translation_hotkey:
            (
                self.single_translation_hotkey,
                self.single_translation_hotkey_display,
                self.single_translation_hotkey_token,
            ) = self._resolve_button("TRANSLATION_HOTKEY", translation_hotkey)
            if self.single_translation_hotkey_mode not in {"toggle", "hold"}:
                logger.error(
                    "无效的 TRANSLATION_HOTKEY_MODE=%s，回退到 hold",
                    self.single_translation_hotkey_mode,
                )
                self.single_translation_hotkey_mode = "hold"

        if (
            self.single_translation_hotkey is not None
            and self.single_translation_hotkey == self.single_transcription_hotkey
        ):
            logger.error("翻译快捷键与转写快捷键冲突，已禁用翻译快捷键")
            self.single_translation_hotkey = None

        self.dual_input_mode_enabled = (
            os.getenv("DUAL_INPUT_MODE_ENABLED", "false").strip().lower()
            in {"1", "true", "yes", "on"}
        )
        self.custom_hotkeys = {
            "fast": self._resolve_hotkey(
                "FAST_INPUT_HOTKEY",
                "alt_r",
            ),
            "smart": self._resolve_hotkey(
                "SMART_INPUT_HOTKEY",
                "cmd_r",
            ),
            "translation": self._resolve_hotkey(
                "SMART_TRANSLATION_HOTKEY",
                "cmd_r+e",
            ),
            "agent": self._resolve_hotkey(
                "KNOWLEDGE_AGENT_HOTKEY",
                "alt_r+a",
            ),
        }
        try:
            chord_delay_ms = int(os.getenv("HOTKEY_CHORD_DELAY_MS", "180"))
        except ValueError:
            chord_delay_ms = 180
        self.hotkey_chord_delay = max(50, min(chord_delay_ms, 500)) / 1000
        self._custom_lock = threading.RLock()
        self._custom_pressed_tokens: set[str] = set()
        self._custom_pending_timers: dict[str, threading.Timer] = {}
        self._custom_active_action: str | None = None
        self.terminal_mode_enabled = (
            os.getenv("TERMINAL_MODE_ENABLED", "false").strip().lower()
            in {"1", "true", "yes", "on"}
        )
        self.terminal_mode_key = None
        self.terminal_mode_key_display = ""
        self.terminal_mode_key_token = ""
        if self.terminal_mode_enabled:
            (
                self.terminal_mode_key,
                self.terminal_mode_key_display,
                self.terminal_mode_key_token,
            ) = self._resolve_button("TERMINAL_MODE_KEY", "m")
            if self.terminal_mode_key in {
                self.single_transcription_hotkey,
                self.single_translation_hotkey,
            }:
                logger.error("终端模式键与录音快捷键冲突，已禁用终端模式")
                self.terminal_mode_enabled = False
                self.terminal_mode_key = None

        self.agent_mode_enabled = (
            os.getenv("KNOWLEDGE_AGENT_ENABLED", "false").strip().lower()
            in {"1", "true", "yes", "on"}
        )
        self.agent_mode_key = None
        self.agent_mode_key_display = ""
        self.agent_mode_key_token = ""
        if self.agent_mode_enabled:
            (
                self.agent_mode_key,
                self.agent_mode_key_display,
                self.agent_mode_key_token,
            ) = self._resolve_button("KNOWLEDGE_AGENT_MODE_KEY", "a")
            if self.agent_mode_key in {
                self.single_transcription_hotkey,
                self.single_translation_hotkey,
                self.terminal_mode_key,
            }:
                logger.error("Agent 模式键与其他快捷键冲突，已禁用 Agent")
                self.agent_mode_enabled = False
                self.agent_mode_key = None

        if self.dual_input_mode_enabled:
            logger.info(
                "智能快捷键已启用：极速 %s，智能 %s，翻译 %s，Agent %s",
                self._display_hotkey(self.custom_hotkeys["fast"]),
                self._display_hotkey(self.custom_hotkeys["smart"]),
                self._display_hotkey(self.custom_hotkeys["translation"]),
                self._display_hotkey(self.custom_hotkeys["agent"]),
            )
        elif self.single_transcription_hotkey is not None:
            if self.single_transcription_hotkey_mode == "hold":
                logger.info(f"按住 {self.single_transcription_hotkey_display} 键：开始录音，松开停止并转写")
            else:
                logger.info(f"按 {self.single_transcription_hotkey_display} 键：切换录音状态（转录模式）")
        else:
            logger.info(f"按 {modifier_display}+{transcriptions_display} 键：切换录音状态（转录模式）")
        if not self.dual_input_mode_enabled and self.single_translation_hotkey is not None:
            mode_name = "翻译"
            action = (
                f"按住说话，松开{mode_name}"
                if self.single_translation_hotkey_mode == "hold"
                else f"按一次开始，再按一次结束并{mode_name}"
            )
            logger.info(
                "%s快捷键 %s：%s",
                "智能" if self.dual_input_mode_enabled else "翻译",
                self.single_translation_hotkey_display,
                action,
            )
        if self.terminal_mode_enabled:
            logger.info(
                "终端模式已启用：录音期间按 %s 切换本次输入",
                self.terminal_mode_key_display,
            )
        if self.agent_mode_enabled:
            logger.info(
                "知识库 Agent 已启用：普通录音期间按 %s 切换本次输入",
                self.agent_mode_key_display,
            )
        logger.info(f"按 {modifier_display}+I 键：切换录音状态（本地 Whisper 模式）")
        logger.info(f"两种模式都是按一下开始，再按一下结束")

    def _resolve_button(self, env_name, default_value):
        """Resolve a keyboard setting into a pynput Key or single character."""
        button_name = (os.getenv(env_name, default_value) or default_value).strip().lower()
        resolved = self._parse_button(button_name)

        if resolved is None:
            logger.error(f"无效的快捷键配置 {env_name}={button_name}，回退到 {default_value}")
            button_name = default_value
            resolved = self._parse_button(button_name)

        logger.info(f"配置到快捷键 {env_name}：{button_name}")
        return resolved, self._display_button_name(button_name), button_name

    def _resolve_hotkey(self, env_name: str, default_value: str) -> tuple[str, ...]:
        configured = os.getenv(env_name, default_value).strip().lower()
        tokens = self._parse_hotkey(configured)
        if not tokens:
            logger.error(
                "无效的组合快捷键 %s=%s，回退到 %s",
                env_name,
                configured,
                default_value,
            )
            tokens = self._parse_hotkey(default_value)
        logger.info("配置到组合快捷键 %s：%s", env_name, "+".join(tokens))
        return tokens

    @classmethod
    def _parse_hotkey(cls, value: str) -> tuple[str, ...]:
        tokens = tuple(
            token.strip().lower()
            for token in (value or "").split("+")
            if token.strip()
        )
        if not tokens or len(set(tokens)) != len(tokens):
            return ()
        if any(cls._parse_button(token) is None for token in tokens):
            return ()
        return tokens

    @classmethod
    def _display_hotkey(cls, tokens: tuple[str, ...]) -> str:
        return "+".join(cls._display_button_name(token) for token in tokens)

    @classmethod
    def _hotkey_tokens_for_key(
        cls,
        key,
        bindings: dict[str, tuple[str, ...]],
    ) -> set[str]:
        tokens = {
            token
            for binding in bindings.values()
            for token in binding
            if cls._key_matches_token(key, token)
        }
        return tokens

    @classmethod
    def _parse_button(cls, button_name):
        if len(button_name) == 1:
            return button_name

        if button_name in cls.KEY_ALIASES:
            return cls.KEY_ALIASES[button_name]

        try:
            return Key[button_name]
        except KeyError:
            return None

    @classmethod
    def _display_button_name(cls, button_name):
        if button_name in cls.KEY_DISPLAY_NAMES:
            return cls.KEY_DISPLAY_NAMES[button_name]
        if len(button_name) == 1:
            return button_name.upper()
        return button_name

    @staticmethod
    def _key_matches(key, configured_key):
        if isinstance(configured_key, str):
            return (
                hasattr(key, "char")
                and key.char
                and key.char.lower() == configured_key.lower()
            )

        if key == configured_key:
            return True

        aliases = []
        if configured_key == Key.ctrl:
            aliases = [getattr(Key, "ctrl_l", None), getattr(Key, "ctrl_r", None)]
        elif configured_key == Key.cmd:
            aliases = [getattr(Key, "cmd_l", None), getattr(Key, "cmd_r", None)]
        elif configured_key == Key.shift:
            aliases = [getattr(Key, "shift_l", None), getattr(Key, "shift_r", None)]
        elif configured_key == Key.alt:
            aliases = [getattr(Key, "alt_l", None), getattr(Key, "alt_r", None)]

        return any(alias is not None and key == alias for alias in aliases)

    @classmethod
    def _key_matches_token(
        cls,
        key,
        token: str,
        configured_key=None,
    ) -> bool:
        normalized = (token or "").strip().lower()
        if normalized in cls.SIDE_SPECIFIC_ALIASES:
            return key == cls.SIDE_SPECIFIC_ALIASES[normalized]
        resolved = (
            configured_key
            if configured_key is not None
            else cls._parse_button(normalized)
        )
        return resolved is not None and cls._key_matches(key, resolved)
    
    @property
    def state(self):
        """获取当前状态"""
        return self._state

    @property
    def direct_agent_recording(self) -> bool:
        return self._direct_agent_recording
    
    @state.setter
    def state(self, new_state):
        """设置新状态并更新UI"""
        if new_state != self._state:
            self._state = new_state
            
            # 获取状态消息
            message = self._state_messages[new_state]
            
            # 根据状态转换类型显示不同消息
            if new_state == InputState.RECORDING:
                # 录音状态
                self.terminal_mode_active = False
                self.terminal_mode_key_pressed = False
                self.agent_mode_active = False
                self.agent_mode_key_pressed = False
                self.temp_text_length = 0
                if self.state_symbol_enabled:
                    self.type_temp_text(message)
                self.on_record_start()

            elif new_state == InputState.RECORDING_TERMINAL:
                # 录音已经开始，只切换本次任务的处理模式。
                self.processing_text = "terminal"

            elif new_state == InputState.RECORDING_AGENT:
                if self._direct_agent_recording:
                    self.temp_text_length = 0
                    if self.state_symbol_enabled:
                        self.type_temp_text(message)
                    self.on_agent_start()
                else:
                    # 普通录音已经开始，只切换本次任务的处理模式。
                    self.processing_text = "agent"

            elif new_state == InputState.RECORDING_SMART:
                self.temp_text_length = 0
                if self.state_symbol_enabled:
                    self.type_temp_text(message)
                self.on_smart_start()
                
            elif new_state == InputState.RECORDING_TRANSLATE:
                # 翻译,录音状态
                self.temp_text_length = 0
                if self.state_symbol_enabled:
                    self.type_temp_text(message)
                self.on_translate_start()
                
            elif new_state == InputState.RECORDING_KIMI:
                # 本地 Whisper 录音状态
                self.temp_text_length = 0
                if self.state_symbol_enabled:
                    self.type_temp_text(message)
                self.on_kimi_start()

            elif new_state == InputState.PROCESSING:
                self._delete_previous_text()
                if self.state_symbol_enabled:
                    self.type_temp_text(message)
                self.processing_text = message
                self.on_record_stop()

            elif new_state == InputState.PROCESSING_AGENT:
                self._delete_previous_text()
                if self.state_symbol_enabled:
                    self.type_temp_text(message)
                self.processing_text = message
                self.on_agent_stop()

            elif new_state == InputState.PROCESSING_SMART:
                self._delete_previous_text()
                if self.state_symbol_enabled:
                    self.type_temp_text(message)
                self.processing_text = message
                self.on_smart_stop()
                
            elif new_state == InputState.PROCESSING_KIMI:
                # 本地 Whisper 处理状态
                self._delete_previous_text()
                if self.state_symbol_enabled:
                    self.type_temp_text(message)
                self.processing_text = message
                self.on_kimi_stop()

            elif new_state == InputState.TRANSLATING:
                # 翻译状态
                self._delete_previous_text()                 
                if self.state_symbol_enabled:
                    self.type_temp_text(message)
                self.processing_text = message
                self.on_translate_stop()
            
            elif new_state == InputState.WARNING:
                # 警告状态
                message = message(self.warning_message)
                self._delete_previous_text()
                if self.state_symbol_enabled:
                    self.type_temp_text(message)
                self.warning_message = None
                self._schedule_message_clear()     
            
            elif new_state == InputState.ERROR:
                # 错误状态
                message = message(self.error_message)
                self._delete_previous_text()
                if self.state_symbol_enabled:
                    self.type_temp_text(message)
                self.error_message = None
                self._schedule_message_clear()  
        
            elif new_state == InputState.IDLE:
                # 空闲状态，清除所有临时文本
                self.processing_text = None
                self._direct_agent_recording = False
            
            else:
                # 其他状态
                if self.state_symbol_enabled:
                    self.type_temp_text(message)

            if self.on_state_change:
                try:
                    self.on_state_change(new_state)
                except Exception as exc:  # noqa: BLE001
                    logger.debug(f"状态回调异常: {exc}")

    def set_state_symbol_enabled(self, enabled: bool):
        """开启或关闭在输入框内展示状态符号"""
        self.state_symbol_enabled = enabled
    
    def _schedule_message_clear(self):
        """计划清除消息"""
        def clear_message():
            time.sleep(2)  # 警告消息显示2秒
            self.state = InputState.IDLE
        
        import threading
        threading.Thread(target=clear_message, daemon=True).start()
    
    def show_warning(self, warning_message):
        """显示警告消息"""
        self.warning_message = warning_message
        self.state = InputState.WARNING
    
    def show_error(self, error_message):
        """显示错误消息"""
        self.error_message = error_message
        self.state = InputState.ERROR
    
    def _paste_text_from_clipboard(self, text: str) -> None:
        pyperclip.copy(text)
        try:
            delay_ms = int(os.getenv("PASTE_DELAY_MS", "80"))
        except ValueError:
            delay_ms = 80
        time.sleep(max(0, min(delay_ms, 1000)) / 1000)

        context = detect_active_window()
        configured_mode = os.getenv("PASTE_HOTKEY", "auto")
        hotkey = resolve_paste_hotkey(
            configured_mode,
            self.system_platform,
            context=context,
            extra_hints=os.getenv("PASTE_TERMINAL_HINTS", ""),
        )
        logger.debug(
            "粘贴策略: mode=%s resolved=%s class=%s process=%s",
            configured_mode,
            hotkey,
            context.window_class or "-",
            context.process_name or "-",
        )

        normalized = hotkey.lower()
        key_map = {
            "ctrl": Key.ctrl,
            "control": Key.ctrl,
            "cmd": Key.cmd,
            "command": Key.cmd,
            "shift": Key.shift,
            "alt": Key.alt,
            "option": Key.alt,
        }
        final_key_map = {
            "insert": Key.insert,
            "enter": Key.enter,
            "return": Key.enter,
        }
        parts = [part for part in normalized.split("+") if part]
        modifiers = [key_map[part] for part in parts[:-1] if part in key_map]
        final_name = parts[-1] if parts else "v"
        final_key = final_key_map.get(final_name, final_name)

        try:
            for modifier in modifiers:
                self.keyboard.press(modifier)
            self.keyboard.press(final_key)
            self.keyboard.release(final_key)
            for modifier in reversed(modifiers):
                self.keyboard.release(modifier)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"无法发送粘贴快捷键 {hotkey}: {exc}") from exc

    def type_text(self, text, error_message=None):
        """将文字输入到当前光标位置
        
        Args:
            text: 要输入的文本或包含文本和错误信息的元组
            error_message: 错误信息
        """
        # 如果text是元组，说明是从process_audio返回的结果
        if isinstance(text, tuple):
            text, error_message = text
            
        if error_message:
            self.show_error(error_message)
            return
            
        if not text:
            # 如果没有文本且不是错误，可能是录音时长不足
            if self.state in (InputState.PROCESSING, InputState.TRANSLATING):
                self.show_warning("录音时长过短，请至少录制1秒")
            return
            
        try:
            logger.info("正在输入转录文本...")
            self._delete_previous_text()
            self._paste_text_from_clipboard(text)
            
            # 等待一小段时间确保文本已输入
            time.sleep(0.5)
            
            logger.info("文本输入完成")

            # 清理处理状态（流式识别中不重置，保持录音状态）
            if self.state != InputState.DOUBAO_STREAMING:
                self.state = InputState.IDLE
        except Exception as e:
            logger.error(f"文本输入失败: {e}")
            self.show_error(f"❌ 文本输入失败: {e}")

    def copy_selected_text(self) -> str:
        """复制当前应用中的选中文字并返回剪贴板内容。"""
        previous = pyperclip.paste()
        pyperclip.copy("")
        modifier = Key.cmd if self.system_platform == "mac" else Key.ctrl
        self.keyboard.press(modifier)
        self.keyboard.press("c")
        self.keyboard.release("c")
        self.keyboard.release(modifier)
        time.sleep(0.12)
        selected = pyperclip.paste()
        if not selected:
            pyperclip.copy(previous)
        return selected

    def undo_and_type_text(self, text: str) -> None:
        """撤销目标应用上一次输入，再粘贴指定文字。"""
        modifier = Key.cmd if self.system_platform == "mac" else Key.ctrl
        self.keyboard.press(modifier)
        self.keyboard.press("z")
        self.keyboard.release("z")
        self.keyboard.release(modifier)
        time.sleep(0.12)
        self._paste_text_from_clipboard(text)
    
    def _delete_previous_text(self):
        """删除之前输入的临时文本"""
        if self.temp_text_length > 0:
            # 添加0.2秒延迟，让删除操作更自然
            import time
            time.sleep(0.2)
            
            for _ in range(self.temp_text_length):
                self.keyboard.press(Key.backspace)
                self.keyboard.release(Key.backspace)

        self.temp_text_length = 0
    
    def type_temp_text(self, text):
        """输入临时状态文本"""
        if not text or not self.state_symbol_enabled:
            return
            
        # 判断是否为状态符号（现在使用数字）
        is_status_symbol = text in ['0', '1']
        
        if is_status_symbol:
            # 状态符号直接输入，不使用剪贴板
            try:
                self.keyboard.type(text)
            except Exception as e:
                # 如果直接输入失败，记录错误但不中断程序
                logger.warning(f"直接输入状态符号失败: {e}, 文本: {text}")
        else:
            # 其他文本（如错误消息、警告等）通过剪贴板输入
            self._paste_text_from_clipboard(text)
        
        # 更新临时文本长度
        self.temp_text_length = len(text)
    
    def toggle_recording(self):
        """切换录音状态"""
        current_time = time.time()

        # 防抖处理
        if current_time - self.last_key_time < self.KEY_DEBOUNCE_TIME:
            return

        self.last_key_time = current_time
        
        if not self.is_recording:
            # 开始录音
            if self.state.can_start_recording:
                self.is_recording = True
                self.state = InputState.RECORDING
                logger.info("🎤 开始录音（转录模式）")
        else:
            # 停止录音
            self.is_recording = False
            self.state = InputState.PROCESSING
            logger.info("⏹️ 停止录音（转录模式）")
    
    def toggle_kimi_recording(self):
        """切换本地 Whisper 录音状态"""
        current_time = time.time()

        # 防抖处理
        if current_time - self.last_key_time < self.KEY_DEBOUNCE_TIME:
            return

        self.last_key_time = current_time
        
        if not self.is_recording:
            # 开始录音
            if self.state.can_start_recording:
                self.is_recording = True
                self.state = InputState.RECORDING_KIMI
                logger.info("🎤 开始录音（本地 Whisper 模式）")
        else:
            # 停止录音
            self.is_recording = False
            self.state = InputState.PROCESSING_KIMI
            logger.info("⏹️ 停止录音（本地 Whisper 模式）")

    def toggle_translation_recording(self):
        """切换录音和翻译状态。"""
        current_time = time.time()
        if current_time - self.last_key_time < self.KEY_DEBOUNCE_TIME:
            return
        self.last_key_time = current_time

        if not self.is_recording:
            if self.state.can_start_recording:
                self.is_recording = True
                self.state = InputState.RECORDING_TRANSLATE
                logger.info("🎤 开始录音（翻译模式）")
        else:
            self.is_recording = False
            self.state = InputState.TRANSLATING
            logger.info("⏹️ 停止录音并开始翻译")

    def start_hold_translation(self):
        """按住翻译键开始录音。"""
        if self.single_translation_hotkey_pressed:
            return
        self.single_translation_hotkey_pressed = True
        current_time = time.time()
        if current_time - self.last_key_time < self.KEY_DEBOUNCE_TIME:
            return
        self.last_key_time = current_time
        if not self.is_recording and self.state.can_start_recording:
            self.is_recording = True
            self.state = InputState.RECORDING_TRANSLATE
            logger.info("🎤 开始录音（按住翻译模式）")

    def stop_hold_translation(self):
        """松开翻译键后停止录音并翻译。"""
        if not self.single_translation_hotkey_pressed:
            return
        self.single_translation_hotkey_pressed = False
        if self.is_recording:
            self.is_recording = False
            self.state = InputState.TRANSLATING
            logger.info("⏹️ 停止录音并开始翻译（按住模式）")

    def toggle_smart_recording(self):
        """切换智能纠错录音状态。"""
        current_time = time.time()
        if current_time - self.last_key_time < self.KEY_DEBOUNCE_TIME:
            return
        self.last_key_time = current_time
        if not self.is_recording:
            if self.state.can_start_recording:
                self.is_recording = True
                self.state = InputState.RECORDING_SMART
                logger.info("🎤 开始录音（智能纠错模式）")
        else:
            self.is_recording = False
            self.state = InputState.PROCESSING_SMART
            logger.info("⏹️ 停止录音（智能纠错模式）")

    def start_hold_smart(self):
        """按住智能键开始录音。"""
        if self.single_smart_hotkey_pressed:
            return
        self.single_smart_hotkey_pressed = True
        current_time = time.time()
        if current_time - self.last_key_time < self.KEY_DEBOUNCE_TIME:
            return
        self.last_key_time = current_time
        if not self.is_recording and self.state.can_start_recording:
            self.is_recording = True
            self.state = InputState.RECORDING_SMART
            logger.info("🎤 开始录音（按住智能模式）")

    def stop_hold_smart(self):
        """松开智能键后停止录音并纠错。"""
        if not self.single_smart_hotkey_pressed:
            return
        self.single_smart_hotkey_pressed = False
        if self.is_recording:
            self.is_recording = False
            self.state = InputState.PROCESSING_SMART
            logger.info("⏹️ 停止录音并智能纠错（按住模式）")

    def start_hold_recording(self):
        """按住式热键：按下开始录音。"""
        if self.single_hotkey_pressed:
            return

        self.single_hotkey_pressed = True
        current_time = time.time()
        if current_time - self.last_key_time < self.KEY_DEBOUNCE_TIME:
            return

        self.last_key_time = current_time
        if not self.is_recording and self.state.can_start_recording:
            self.is_recording = True
            self.state = InputState.RECORDING
            logger.info("🎤 开始录音（按住说话模式）")

    def stop_hold_recording(self):
        """按住式热键：松开停止录音并转写。"""
        if not self.single_hotkey_pressed:
            return

        self.single_hotkey_pressed = False
        if self.is_recording:
            self.is_recording = False
            self.state = InputState.PROCESSING
            logger.info("⏹️ 停止录音（按住说话模式）")

    def _custom_binding_has_prefix(self, action: str) -> bool:
        binding = self.custom_hotkeys[action]
        return any(
            len(other_binding) > len(binding)
            and set(binding).issubset(other_binding)
            for other_binding in self.custom_hotkeys.values()
        )

    def _cancel_custom_timers(self) -> None:
        for timer in self._custom_pending_timers.values():
            timer.cancel()
        self._custom_pending_timers.clear()

    def _schedule_custom_action(self, action: str) -> None:
        old_timer = self._custom_pending_timers.pop(action, None)
        if old_timer is not None:
            old_timer.cancel()

        def activate() -> None:
            with self._custom_lock:
                self._custom_pending_timers.pop(action, None)
                binding = self.custom_hotkeys[action]
                if (
                    self._custom_active_action is not None
                    or not set(binding).issubset(self._custom_pressed_tokens)
                ):
                    return
                self._start_custom_action(action)

        timer = threading.Timer(self.hotkey_chord_delay, activate)
        timer.daemon = True
        self._custom_pending_timers[action] = timer
        timer.start()

    def _start_custom_action(self, action: str) -> bool:
        if self._custom_active_action is not None or not self.state.can_start_recording:
            return False
        if action == "agent" and not self.agent_mode_enabled:
            logger.info("Agent 快捷键已触发，但 Agent 总开关未开启")
            return False

        state_map = {
            "fast": InputState.RECORDING,
            "smart": InputState.RECORDING_SMART,
            "translation": InputState.RECORDING_TRANSLATE,
            "agent": InputState.RECORDING_AGENT,
        }
        self._custom_active_action = action
        self.is_recording = True
        self._direct_agent_recording = action == "agent"
        self.state = state_map[action]
        logger.info("智能快捷键开始录音：%s", action)
        return True

    def _stop_custom_action(self, action: str) -> None:
        if self._custom_active_action != action:
            return
        state_map = {
            "fast": InputState.PROCESSING,
            "smart": InputState.PROCESSING_SMART,
            "translation": InputState.TRANSLATING,
            "agent": InputState.PROCESSING_AGENT,
        }
        self._custom_active_action = None
        self.is_recording = False
        self.state = state_map[action]
        if action != "agent":
            self._direct_agent_recording = False
        logger.info("智能快捷键停止录音：%s", action)

    def _handle_custom_press(self, key) -> bool:
        tokens = self._hotkey_tokens_for_key(key, self.custom_hotkeys)
        if not tokens:
            return False
        with self._custom_lock:
            new_tokens = tokens - self._custom_pressed_tokens
            self._custom_pressed_tokens.update(tokens)
            if not new_tokens:
                return True
            if self._custom_active_action is not None:
                return True

            chord_actions = [
                action
                for action, binding in self.custom_hotkeys.items()
                if len(binding) > 1
                and set(binding).issubset(self._custom_pressed_tokens)
            ]
            if chord_actions:
                chord_actions.sort(
                    key=lambda action: len(self.custom_hotkeys[action]),
                    reverse=True,
                )
                self._cancel_custom_timers()
                self._start_custom_action(chord_actions[0])
                return True

            for action, binding in self.custom_hotkeys.items():
                if len(binding) != 1 or binding[0] not in new_tokens:
                    continue
                if self._custom_binding_has_prefix(action):
                    self._schedule_custom_action(action)
                else:
                    self._start_custom_action(action)
                break
        return True

    def _handle_custom_release(self, key) -> bool:
        tokens = self._hotkey_tokens_for_key(key, self.custom_hotkeys)
        if not tokens:
            return False
        with self._custom_lock:
            active_action = self._custom_active_action
            if (
                active_action is not None
                and set(tokens).intersection(self.custom_hotkeys[active_action])
            ):
                self._stop_custom_action(active_action)
            self._custom_pressed_tokens.difference_update(tokens)
            for action, timer in list(self._custom_pending_timers.items()):
                if set(tokens).intersection(self.custom_hotkeys[action]):
                    timer.cancel()
                    self._custom_pending_timers.pop(action, None)
        return True

    def activate_terminal_mode(self) -> bool:
        """将当前普通听写切换为终端模式。"""
        if (
            not self.terminal_mode_enabled
            or self.terminal_mode_key is None
            or not self.is_recording
            or self.state
            not in {InputState.RECORDING, InputState.RECORDING_TERMINAL}
        ):
            return False
        if self.terminal_mode_active:
            return True

        self.terminal_mode_active = True
        self.state = InputState.RECORDING_TERMINAL
        logger.info("⌨️ 本次录音已切换为终端模式")
        return True

    def consume_terminal_mode(self) -> bool:
        """读取并清除本次录音的终端模式标记。"""
        active = self.terminal_mode_active
        self.terminal_mode_active = False
        self.terminal_mode_key_pressed = False
        return active

    def activate_agent_mode(self) -> bool:
        """将当前普通听写切换为知识库 Agent 指令。"""
        if (
            not self.agent_mode_enabled
            or self.agent_mode_key is None
            or not self.is_recording
            or self.state not in {InputState.RECORDING, InputState.RECORDING_AGENT}
        ):
            return False
        if self.agent_mode_active:
            return True
        self.agent_mode_active = True
        self.terminal_mode_active = False
        self.state = InputState.RECORDING_AGENT
        logger.info("本次录音已切换为知识库 Agent 模式")
        return True

    def consume_agent_mode(self) -> bool:
        """读取并清除本次录音的 Agent 模式标记。"""
        active = self.agent_mode_active
        self.agent_mode_active = False
        self.agent_mode_key_pressed = False
        return active

    def on_press(self, key):
        """按键按下时的回调"""
        try:
            if self.dual_input_mode_enabled and self._handle_custom_press(key):
                return

            if (
                self.agent_mode_enabled
                and not self.dual_input_mode_enabled
                and self.agent_mode_key is not None
                and self._key_matches_token(
                    key,
                    getattr(self, "agent_mode_key_token", ""),
                    self.agent_mode_key,
                )
                and self.is_recording
                and self.state in {InputState.RECORDING, InputState.RECORDING_AGENT}
            ):
                if not self.agent_mode_key_pressed:
                    self.agent_mode_key_pressed = True
                    self.activate_agent_mode()
                return

            if (
                self.terminal_mode_enabled
                and self.terminal_mode_key is not None
                and self._key_matches_token(
                    key,
                    getattr(self, "terminal_mode_key_token", ""),
                    self.terminal_mode_key,
                )
                and self.is_recording
                and self.state
                in {InputState.RECORDING, InputState.RECORDING_TERMINAL}
            ):
                if not self.terminal_mode_key_pressed:
                    self.terminal_mode_key_pressed = True
                    self.activate_terminal_mode()
                return

            if (
                self.single_translation_hotkey is not None
                and self._key_matches_token(
                    key,
                    getattr(self, "single_translation_hotkey_token", ""),
                    self.single_translation_hotkey,
                )
            ):
                if self.single_translation_hotkey_mode == "hold":
                    self.start_hold_translation()
                else:
                    self.toggle_translation_recording()
                return

            if (
                self.single_transcription_hotkey is not None
                and self._key_matches_token(
                    key,
                    getattr(self, "single_transcription_hotkey_token", ""),
                    self.single_transcription_hotkey,
                )
            ):
                if self.single_transcription_hotkey_mode == "hold":
                    self.start_hold_recording()
                else:
                    self.toggle_recording()
                return

            # 检查转录按钮（字符键或特殊键）
            is_transcription_key = self._key_matches_token(
                key,
                getattr(self, "transcriptions_button_token", ""),
                self.transcriptions_button,
            )
                
            # 检查快捷键修饰键（如 Win/Ctrl/Cmd）
            is_translation_key = self._key_matches_token(
                key,
                getattr(self, "translations_button_token", ""),
                self.translations_button,
            )
            
            # 检查I键（用于本地 Whisper 模式）
            if hasattr(key, 'char') and key.char == 'i':
                self.i_pressed = True
                # 检查是否同时按下了修饰键+i（本地 Whisper 模式）
                if self.ctrl_pressed and self.i_pressed:
                    self.toggle_kimi_recording()
            elif is_transcription_key:  # F键
                self.f_pressed = True
                # 检查是否同时按下了修饰键+f
                if self.ctrl_pressed and self.f_pressed:
                    self.toggle_recording()
            elif is_translation_key:  # 快捷键修饰键
                self.ctrl_pressed = True
                # 检查是否同时按下了修饰键+f（默认转录模式）
                if self.ctrl_pressed and self.f_pressed:
                    self.toggle_recording()
                # 检查是否同时按下了修饰键+i（本地 Whisper 模式）
                elif self.ctrl_pressed and self.i_pressed:
                    self.toggle_kimi_recording()
        except AttributeError:
            pass

    def on_release(self, key):
        """按键释放时的回调"""
        try:
            if self.dual_input_mode_enabled and self._handle_custom_release(key):
                return

            if (
                self.agent_mode_enabled
                and not self.dual_input_mode_enabled
                and self.agent_mode_key is not None
                and self._key_matches_token(
                    key,
                    getattr(self, "agent_mode_key_token", ""),
                    self.agent_mode_key,
                )
            ):
                self.agent_mode_key_pressed = False
                return

            if (
                self.terminal_mode_enabled
                and self.terminal_mode_key is not None
                and self._key_matches_token(
                    key,
                    getattr(self, "terminal_mode_key_token", ""),
                    self.terminal_mode_key,
                )
            ):
                self.terminal_mode_key_pressed = False
                return

            if (
                self.single_translation_hotkey is not None
                and self._key_matches_token(
                    key,
                    getattr(self, "single_translation_hotkey_token", ""),
                    self.single_translation_hotkey,
                )
            ):
                if self.single_translation_hotkey_mode == "hold":
                    self.stop_hold_translation()
                return

            if (
                self.single_transcription_hotkey is not None
                and self._key_matches_token(
                    key,
                    getattr(self, "single_transcription_hotkey_token", ""),
                    self.single_transcription_hotkey,
                )
            ):
                if self.single_transcription_hotkey_mode == "hold":
                    self.stop_hold_recording()
                return

            # 检查转录按钮（字符键或特殊键）
            is_transcription_key = self._key_matches_token(
                key,
                getattr(self, "transcriptions_button_token", ""),
                self.transcriptions_button,
            )
                
            # 检查快捷键修饰键（如 Win/Ctrl/Cmd）
            is_translation_key = self._key_matches_token(
                key,
                getattr(self, "translations_button_token", ""),
                self.translations_button,
            )
                
            # 检查I键释放
            if hasattr(key, 'char') and key.char == 'i':
                self.i_pressed = False
            elif is_transcription_key:  # F键释放
                self.f_pressed = False
            elif is_translation_key:  # 快捷键修饰键释放
                self.ctrl_pressed = False

        except AttributeError:
            pass
    
    def start_listening(self):
        """开始监听键盘事件"""
        with Listener(on_press=self.on_press, on_release=self.on_release) as listener:
            listener.join()

    def reset_state(self):
        """重置所有状态和临时文本"""
        # 清除临时文本
        self._delete_previous_text()
        
        # 重置状态标志
        self.ctrl_pressed = False
        self.f_pressed = False
        self.i_pressed = False
        self.single_hotkey_pressed = False
        self.single_translation_hotkey_pressed = False
        self.single_smart_hotkey_pressed = False
        self.terminal_mode_key_pressed = False
        self.terminal_mode_active = False
        self.agent_mode_key_pressed = False
        self.agent_mode_active = False
        with self._custom_lock:
            self._cancel_custom_timers()
            self._custom_pressed_tokens.clear()
            self._custom_active_action = None
        self._direct_agent_recording = False
        self.is_recording = False
        self.last_key_time = time.time()
        self.processing_text = None
        self.error_message = None
        self.warning_message = None
        
        # 设置为空闲状态
        self.state = InputState.IDLE

def check_accessibility_permissions():
    """检查是否有辅助功能权限并提供指导"""
    logger.warning("\n=== macOS 辅助功能权限检查 ===")
    logger.warning("此应用需要辅助功能权限才能监听键盘事件。")
    logger.warning("\n请按照以下步骤授予权限：")
    logger.warning("1. 打开 系统偏好设置")
    logger.warning("2. 点击 隐私与安全性")
    logger.warning("3. 点击左侧的 辅助功能")
    logger.warning("4. 点击右下角的锁图标并输入密码")
    logger.warning("5. 在右侧列表中找到 Terminal（或者您使用的终端应用）并勾选")
    logger.warning("\n授权后，请重新运行此程序。")
    logger.warning("===============================\n") 
