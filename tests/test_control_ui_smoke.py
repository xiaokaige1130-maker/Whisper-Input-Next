from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PyQt5.QtWidgets import QApplication, QHeaderView, QSpinBox

from control_ui import ControlUI


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
            self.assertEqual(window.stack.count(), 9)
            self.assertEqual(window.nav.count(), 9)
            self.assertEqual(window.nav.item(3).text(), "快捷键与翻译")
            self.assertEqual(window.nav.item(4).text(), "粘贴与文本")
            self.assertEqual(window.nav.item(6).text(), "个人资料库")
            self.assertEqual(window.translation_language_combo.currentData(), "ru")
            self.assertEqual(window.translation_hotkey_input.text(), "ctrl_r")
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
            self.assertIn(
                "我的表达风格",
                window.memory_style_input.toPlainText(),
            )
            self.assertIn("稍后回复", window.memory_replies_input.toPlainText())
            self.assertTrue(window.memory_enabled_check.isChecked())
            self.assertEqual(window.memory_max_chars_spin.value(), 3200)
            self.assertIn("SSH", window.glossary_preview.text())
            self.assertIn("VPS", window.glossary_preview.text())

            window.glossary_source_input.setText("小凯歌")
            window.glossary_replacement_input.setText("小凯哥")
            window.save_glossary_entry()
            self.assertEqual(
                window.glossary_processor.apply("打开小凯歌"),
                "打开小凯哥",
            )
            window.close()


if __name__ == "__main__":
    unittest.main()
