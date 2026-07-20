from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtGui import QFocusEvent, QKeyEvent
from PyQt5.QtWidgets import QApplication, QHeaderView, QSpinBox

from control_ui import ControlUI, HotkeyCaptureEdit


class ControlUISmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_window_builds_all_pages_and_loads_translation_settings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "logs").mkdir()
            (root / ".env").write_text(
                "TRANSCRIPTION_SERVICE=aliyun\n"
                "BATCH_TRANSCRIPTION_SERVICE=aliyun\n"
                "TRANSLATION_TARGET_LANGUAGE=ru\n"
                "TRANSLATION_HOTKEY=ctrl_r\n"
                "DASHSCOPE_TRANSLATION_MODEL=qwen-mt-plus\n"
                "FAST_INPUT_HOTKEY=alt_r\n"
                "SMART_INPUT_HOTKEY=cmd_r\n"
                "SMART_TRANSLATION_HOTKEY=cmd_r+e\n"
                "KNOWLEDGE_AGENT_HOTKEY=alt_r+a\n"
                "PASTE_HOTKEY=auto\n"
                "TERMINAL_MODE_ENABLED=true\n"
                "TERMINAL_MODE_KEY=>\n"
                "CHINESE_CONVERSION=s2t\n"
                "PERSONA_REWRITE_PROVIDER=agnes\n"
                "AGNES_MODEL=agnes-2.0-flash\n",
                encoding="utf-8",
            )

            window = ControlUI(root)
            self.assertEqual(window.windowTitle(), "小凯哥语音输入法")
            self.assertEqual(window.stack.count(), 11)
            self.assertEqual(window.nav.count(), 11)
            self.assertEqual(window.nav.item(3).text(), "快捷键")
            self.assertEqual(window.nav.item(4).text(), "翻译")
            self.assertEqual(window.nav.item(5).text(), "粘贴与文本")
            self.assertEqual(window.nav.item(7).text(), "个人资料库")
            self.assertEqual(window.nav.item(8).text(), "智能与 Agent")
            self.assertEqual(window.nav.item(9).text(), "人设与改写")
            self.assertEqual(window.nav.item(10).text(), "诊断")
            self.assertEqual(window.translation_language_combo.currentData(), "ru")
            self.assertEqual(window.translation_model_input.text(), "qwen-mt-plus")
            self.assertEqual(window.translation_hotkey_input.hotkey(), "ctrl_r")
            self.assertEqual(window.translation_hotkey_input.text(), "右 Ctrl")
            self.assertEqual(window.paste_combo.currentData(), "auto")
            self.assertTrue(window.terminal_mode_enabled_check.isChecked())
            self.assertEqual(window.terminal_mode_key_combo.currentText(), ">")
            self.assertEqual(window.chinese_conversion_combo.currentData(), "s2t")
            self.assertEqual(window.history_retention_combo.currentData(), 1)
            self.assertFalse(window.history_table.wordWrap())
            for column in range(1, window.history_table.columnCount()):
                self.assertNotEqual(
                    window.history_table.horizontalHeader().sectionResizeMode(column),
                    QHeaderView.ResizeToContents,
                )
            self.assertEqual(
                window.paste_delay_spin.buttonSymbols(),
                QSpinBox.NoButtons,
            )
            self.assertLessEqual(window.paste_combo.maximumWidth(), 340)
            self.assertIn("右 Ctrl", window.translation_value.text())
            self.assertIn("俄语", window.translation_value.text())
            self.assertEqual(window.persona_provider_combo.currentData(), "qwen")
            self.assertEqual(window.persona_provider_combo.findData("agnes"), -1)
            self.assertGreaterEqual(window.persona_provider_combo.findData("ark"), 0)
            self.assertGreaterEqual(
                window.ark_model_combo.findData(
                    "doubao-seed-2-0-mini-260428"
                ),
                0,
            )
            self.assertEqual(window.default_service_combo.findData("doubao"), -1)
            self.assertGreaterEqual(window.glossary_table.rowCount(), 3)
            self.assertFalse(window.ai_correction_enabled_check.isChecked())
            self.assertEqual(
                window.ai_correction_level_combo.currentData(),
                "light",
            )
            self.assertEqual(
                window.ai_correction_model_combo.currentData(),
                "qwen3.5-flash",
            )
            self.assertFalse(window.dual_input_mode_check.isChecked())
            self.assertEqual(window.fast_input_hotkey_input.hotkey(), "alt_r")
            self.assertEqual(window.fast_input_hotkey_input.text(), "右 Alt")
            self.assertEqual(window.smart_input_hotkey_input.hotkey(), "cmd_r")
            self.assertEqual(
                window.smart_translation_hotkey_input.hotkey(),
                "cmd_r+e",
            )
            self.assertEqual(window.agent_hotkey_input.hotkey(), "alt_r+a")
            # Linux hotkey defaults must stay (different from macOS).
            self.assertEqual(
                window.smart_input_hotkey_input.hotkey(),
                "cmd_r",
            )
            self.assertEqual(window.theme_combo.currentData(), "classic")
            self.assertEqual(window._ui_theme, "classic")
            self.assertIn("#101411", window.styleSheet())
            theme_index = window.theme_combo.findData("dark")
            self.assertGreaterEqual(theme_index, 0)
            window.theme_combo.setCurrentIndex(theme_index)
            window._save_ui_theme()
            self.assertEqual(window._ui_theme, "dark")
            self.assertIn("#1c1c1e", window.styleSheet())
            saved_env = (root / ".env").read_text(encoding="utf-8")
            self.assertIn("UI_THEME=dark", saved_env)
            # Restore classic for remaining assertions.
            classic_index = window.theme_combo.findData("classic")
            window.theme_combo.setCurrentIndex(classic_index)
            window._save_ui_theme()
            self.assertLessEqual(window.minimumWidth(), 1000)
            self.assertLessEqual(window.width(), 1100)
            self.assertEqual(
                window.translation_shortcut_summary.text(),
                "右 Ctrl · 按住说话",
            )
            self.assertEqual(
                window.agent_shortcut_summary.text(),
                "智能快捷键未开启",
            )
            self.assertEqual(
                window.hotkey_conflict_label.property("state"),
                "good",
            )
            self.assertEqual(
                window.smart_correction_level_combo.currentData(),
                "medium",
            )
            self.assertEqual(window.hotkey_chord_delay_spin.value(), 180)
            self.assertFalse(window.correction_undo_check.isChecked())
            self.assertFalse(window.voice_edit_commands_check.isChecked())
            self.assertFalse(window.app_profile_check.isChecked())
            self.assertFalse(window.selected_text_ai_check.isChecked())
            self.assertFalse(window.glossary_learning_check.isChecked())
            self.assertFalse(window.knowledge_agent_enabled_check.isChecked())
            self.assertEqual(
                window.agent_automation_combo.currentData(),
                "semi",
            )
            self.assertEqual(window.agent_history_days_spin.value(), 7)
            self.assertLessEqual(
                window.smart_correction_level_combo.maximumWidth(),
                220,
            )
            self.assertGreaterEqual(
                window.stack.widget(3).widget().minimumHeight(),
                800,
            )
            self.assertGreaterEqual(
                window.stack.widget(8).widget().minimumHeight(),
                700,
            )
            self.assertIn(
                "我的表达风格",
                window.memory_style_input.toPlainText(),
            )
            self.assertIn("稍后回复", window.memory_replies_input.toPlainText())
            self.assertTrue(window.memory_enabled_check.isChecked())
            self.assertEqual(window.memory_max_chars_spin.value(), 3200)
            self.assertIn("SSH", window.glossary_preview.text())
            self.assertIn("VPS", window.glossary_preview.text())

            window.fast_input_hotkey_input.set_hotkey("ctrl_l+space")
            window.smart_input_hotkey_input.set_hotkey("shift_r")
            window.smart_translation_hotkey_input.set_hotkey("shift_r+e")
            window.agent_hotkey_input.set_hotkey("ctrl_l+a")
            self.assertTrue(window.refresh_hotkey_conflicts())
            window._restart_after_save = Mock()
            window.save_behavior_settings()
            saved = window.env_store.read()
            self.assertEqual(saved["FAST_INPUT_HOTKEY"], "ctrl_l+space")
            self.assertEqual(saved["SMART_INPUT_HOTKEY"], "shift_r")
            self.assertEqual(
                saved["SMART_TRANSLATION_HOTKEY"],
                "shift_r+e",
            )
            self.assertEqual(saved["KNOWLEDGE_AGENT_HOTKEY"], "ctrl_l+a")
            window._restart_after_save.assert_called_once()

            window.agent_hotkey_input.set_hotkey("shift_r")
            self.assertFalse(window.refresh_hotkey_conflicts())
            self.assertEqual(
                window.hotkey_conflict_label.property("state"),
                "bad",
            )
            self.assertIn("智能纠错、Agent 指令", window.hotkey_conflict_label.text())

            window.fast_input_hotkey_input.set_hotkey("alt")
            window.smart_input_hotkey_input.set_hotkey("alt_l")
            self.assertFalse(window.refresh_hotkey_conflicts())
            self.assertIn("极速输入、智能纠错", window.hotkey_conflict_label.text())

            window.glossary_source_input.setText("小凯歌")
            window.glossary_replacement_input.setText("小凯哥")
            window.save_glossary_entry()
            self.assertEqual(
                window.glossary_processor.apply("打开小凯歌"),
                "打开小凯哥",
            )
            window.close()


class HotkeyCaptureEditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    @staticmethod
    def _key_event(
        event_type: QEvent.Type,
        key: int,
        modifiers: Qt.KeyboardModifiers = Qt.NoModifier,
        text: str = "",
    ) -> QKeyEvent:
        return QKeyEvent(event_type, key, modifiers, text)

    def test_captures_and_orders_modifier_chord(self) -> None:
        field = HotkeyCaptureEdit()
        field.set_hotkey("alt_r")
        finished = Mock()
        field.captureFinished.connect(finished)

        field.focusInEvent(QFocusEvent(QEvent.FocusIn))
        field.keyPressEvent(
            self._key_event(
                QEvent.KeyPress,
                Qt.Key_Control,
                Qt.ControlModifier,
            )
        )
        field.keyPressEvent(
            self._key_event(
                QEvent.KeyPress,
                Qt.Key_E,
                Qt.ControlModifier,
                "e",
            )
        )
        field.keyReleaseEvent(
            self._key_event(
                QEvent.KeyRelease,
                Qt.Key_E,
                Qt.ControlModifier,
                "e",
            )
        )
        field.keyReleaseEvent(
            self._key_event(
                QEvent.KeyRelease,
                Qt.Key_Control,
                Qt.NoModifier,
            )
        )

        self.assertEqual(field.hotkey(), "ctrl+e")
        self.assertEqual(field.text(), "Ctrl+E")
        finished.assert_called_once()

    def test_escape_restores_and_delete_clears(self) -> None:
        field = HotkeyCaptureEdit()
        field.set_hotkey("cmd_r+e")

        field.focusInEvent(QFocusEvent(QEvent.FocusIn))
        field.keyPressEvent(
            self._key_event(QEvent.KeyPress, Qt.Key_Escape)
        )
        self.assertEqual(field.hotkey(), "cmd_r+e")

        field.focusInEvent(QFocusEvent(QEvent.FocusIn))
        field.keyPressEvent(
            self._key_event(QEvent.KeyPress, Qt.Key_Delete)
        )
        self.assertEqual(field.hotkey(), "")
        self.assertEqual(field.text(), "")


if __name__ == "__main__":
    unittest.main()
