from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PyQt5.QtWidgets import QApplication

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
                "PERSONA_REWRITE_PROVIDER=agnes\n"
                "AGNES_MODEL=agnes-2.0-flash\n",
                encoding="utf-8",
            )

            window = ControlUI(root)
            self.assertEqual(window.windowTitle(), "小凯哥语音输入法")
            self.assertEqual(window.stack.count(), 7)
            self.assertEqual(window.nav.count(), 7)
            self.assertEqual(window.translation_language_combo.currentData(), "ru")
            self.assertEqual(window.translation_hotkey_input.text(), "ctrl_r")
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
