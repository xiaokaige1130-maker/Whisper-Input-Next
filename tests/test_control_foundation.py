from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from pynput.keyboard import Key

from src.control.config_store import EnvStore
from src.glossary import GlossaryProcessor, GlossaryStore
from src.history.store import HistoryStore
from src.keyboard.listener import KeyboardManager
from src.llm.translate import TranslateProcessor
from src.persona import PersonaProcessor, PersonaStore


class EnvStoreTests(unittest.TestCase):
    def test_update_preserves_comments_and_unrelated_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / ".env"
            path.write_text(
                "# Voice settings\n"
                "TRANSCRIPTION_SERVICE=aliyun\n"
                "UNRELATED=value\n",
                encoding="utf-8",
            )

            store = EnvStore(path)
            store.update(
                {
                    "TRANSCRIPTION_SERVICE": "doubao",
                    "TRANSLATION_TARGET_LANGUAGE": "ja",
                }
            )

            content = path.read_text(encoding="utf-8")
            self.assertIn("# Voice settings", content)
            self.assertIn("TRANSCRIPTION_SERVICE=doubao", content)
            self.assertIn("UNRELATED=value", content)
            self.assertIn("TRANSLATION_TARGET_LANGUAGE=ja", content)


class HistoryStoreTests(unittest.TestCase):
    def test_records_success_failure_and_today_stats(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = HistoryStore(Path(temp_dir) / "history.db")
            success_id = store.add_success(
                text="Hello",
                service="aliyun+aliyun-mt",
                model="qwen3-asr-flash -> qwen-mt-flash",
                mode="translations",
                duration_seconds=3.2,
                latency_seconds=0.8,
            )
            store.add_failure(
                error="timeout",
                service="aliyun",
                model="qwen3-asr-flash",
                latency_seconds=2.0,
            )

            records = store.recent()
            stats = store.stats_today()

            self.assertEqual(len(records), 2)
            self.assertEqual(records[1].id, success_id)
            self.assertEqual(stats["total"], 2)
            self.assertEqual(stats["success"], 1)
            self.assertEqual(stats["success_rate"], 50.0)
            self.assertAlmostEqual(stats["avg_latency"], 0.8)
            self.assertAlmostEqual(stats["duration"], 3.2)


class GlossaryTests(unittest.TestCase):
    def test_default_terms_correct_spoken_technical_words(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = GlossaryStore(Path(temp_dir) / "glossary.db")
            processor = GlossaryProcessor(store)

            corrected = processor.apply(
                "S S H Linux。，S S H香港杠V P S。"
            )

            self.assertEqual(
                corrected,
                "SSH Linux。，SSH香港-VPS。",
            )
            self.assertEqual(store.enabled_count(), 3)

    def test_custom_terms_can_be_updated_disabled_and_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = GlossaryStore(Path(temp_dir) / "glossary.db")
            processor = GlossaryProcessor(store)

            entry_id = store.save("小凯歌", "小凯哥")
            self.assertEqual(processor.apply("你好，小凯歌。"), "你好，小凯哥。")

            store.save("小凯歌", "小凯哥语音输入法", entry_id=entry_id)
            self.assertEqual(
                processor.apply("打开小凯歌。"),
                "打开小凯哥语音输入法。",
            )

            store.set_enabled(entry_id, False)
            self.assertEqual(processor.apply("小凯歌"), "小凯歌")

            store.delete(entry_id)
            self.assertFalse(
                any(entry.id == entry_id for entry in store.entries())
            )


class TranslateProcessorTests(unittest.TestCase):
    def test_dashscope_translation_uses_requested_target_language(self) -> None:
        client = Mock()
        client.chat.completions.create.return_value = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="こんにちは")
                )
            ]
        )

        with patch.dict(
            os.environ,
            {
                "TRANSLATION_SERVICE": "aliyun",
                "TRANSLATION_TARGET_LANGUAGE": "ja",
                "DASHSCOPE_TRANSLATION_MODEL": "qwen-mt-flash",
            },
            clear=False,
        ):
            processor = TranslateProcessor(client=client)
            result = processor.translate("你好")

        self.assertEqual(result, "こんにちは")
        call = client.chat.completions.create.call_args.kwargs
        self.assertEqual(call["model"], "qwen-mt-flash")
        self.assertEqual(
            call["extra_body"]["translation_options"],
            {"source_lang": "auto", "target_lang": "Japanese"},
        )

    def test_streaming_translation_updates_preview(self) -> None:
        client = Mock()
        client.chat.completions.create.return_value = [
            SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        delta=SimpleNamespace(content="Hello")
                    )
                ]
            ),
            SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        delta=SimpleNamespace(content=" world")
                    )
                ]
            ),
        ]
        updates: list[str] = []

        with patch.dict(
            os.environ,
            {
                "TRANSLATION_SERVICE": "aliyun",
                "TRANSLATION_TARGET_LANGUAGE": "en",
            },
            clear=False,
        ):
            processor = TranslateProcessor(client=client)
            result = processor.translate("你好世界", on_update=updates.append)

        self.assertEqual(result, "Hello world")
        self.assertEqual(updates, ["Hello", "Hello world"])


class PersonaStoreTests(unittest.TestCase):
    def test_seeds_builtin_personas_and_manages_custom_personas(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = PersonaStore(Path(temp_dir) / "personas.db")

            names = {persona.name for persona in store.entries()}
            self.assertIn("文言文", names)
            self.assertIn("网络热梗", names)
            self.assertIn("AI 提示词", names)

            persona_id = store.save("客服语气", "改写成耐心、简洁的客服答复。")
            self.assertEqual(store.get(persona_id).name, "客服语气")

            store.save(
                "客服语气",
                "改写成专业、耐心且简洁的客服答复。",
                persona_id=persona_id,
            )
            self.assertIn("专业", store.get(persona_id).instruction)

            store.delete(persona_id)
            self.assertIsNone(store.get(persona_id))


class PersonaProcessorTests(unittest.TestCase):
    def test_agnes_rewrite_disables_thinking(self) -> None:
        client = Mock()
        client.chat.completions.create.return_value = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="今日天朗，宜出游。")
                )
            ]
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = PersonaStore(Path(temp_dir) / "personas.db")
            persona = next(item for item in store.entries() if item.name == "文言文")
            with patch.dict(
                os.environ,
                {
                    "PERSONA_REWRITE_PROVIDER": "agnes",
                    "AGNES_API_KEY": "test-key",
                    "AGNES_MODEL": "agnes-2.0-flash",
                },
                clear=False,
            ):
                processor = PersonaProcessor(
                    store=store,
                    clients={"agnes": client},
                )
                result = processor.rewrite(
                    "今天天气很好，我准备出去走走。",
                    persona_id=persona.id,
                )

        self.assertEqual(result, "今日天朗，宜出游。")
        call = client.chat.completions.create.call_args.kwargs
        self.assertEqual(call["model"], "agnes-2.0-flash")
        self.assertFalse(
            call["extra_body"]["chat_template_kwargs"]["enable_thinking"]
        )

    def test_qwen_rewrite_uses_qwen_flash_without_thinking(self) -> None:
        client = Mock()
        client.chat.completions.create.return_value = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="把登录接口改成支持 OAuth 2.0。")
                )
            ]
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = PersonaStore(Path(temp_dir) / "personas.db")
            persona = next(
                item for item in store.entries() if item.name == "AI 提示词"
            )
            with patch.dict(
                os.environ,
                {
                    "PERSONA_REWRITE_PROVIDER": "qwen",
                    "DASHSCOPE_API_KEY": "test-key",
                    "QWEN_REWRITE_MODEL": "qwen-flash",
                },
                clear=False,
            ):
                processor = PersonaProcessor(
                    store=store,
                    clients={"qwen": client},
                )
                result = processor.rewrite(
                    "帮我改登录接口，支持 OAuth。",
                    persona_id=persona.id,
                )

        self.assertIn("OAuth", result)
        call = client.chat.completions.create.call_args.kwargs
        self.assertEqual(call["model"], "qwen-flash")
        self.assertFalse(call["extra_body"]["enable_thinking"])

    def test_ark_rewrite_uses_doubao_seed_without_thinking(self) -> None:
        client = Mock()
        client.chat.completions.create.return_value = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="今日天朗，宜出行。")
                )
            ]
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = PersonaStore(Path(temp_dir) / "personas.db")
            persona = next(item for item in store.entries() if item.name == "文言文")
            with patch.dict(
                os.environ,
                {
                    "PERSONA_REWRITE_PROVIDER": "ark",
                    "ARK_API_KEY": "test-key",
                    "ARK_REWRITE_MODEL": "doubao-seed-2-0-lite-260428",
                },
                clear=False,
            ):
                processor = PersonaProcessor(
                    store=store,
                    clients={"ark": client},
                )
                result = processor.rewrite(
                    "今天天气很好，我准备出去走走。",
                    persona_id=persona.id,
                )

        self.assertEqual(result, "今日天朗，宜出行。")
        call = client.chat.completions.create.call_args.kwargs
        self.assertEqual(
            call["model"],
            "doubao-seed-2-0-lite-260428",
        )
        self.assertEqual(
            call["extra_body"]["thinking"],
            {"type": "disabled"},
        )

    def test_rewrite_falls_back_to_selected_backup_provider(self) -> None:
        agnes_client = Mock()
        agnes_client.chat.completions.create.side_effect = RuntimeError("timeout")
        qwen_client = Mock()
        qwen_client.chat.completions.create.return_value = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="备用模型结果")
                )
            ]
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = PersonaStore(Path(temp_dir) / "personas.db")
            persona = store.entries()[0]
            with patch.dict(
                os.environ,
                {
                    "PERSONA_REWRITE_PROVIDER": "agnes",
                    "PERSONA_FALLBACK_PROVIDER": "qwen",
                    "AGNES_API_KEY": "agnes-key",
                    "DASHSCOPE_API_KEY": "qwen-key",
                },
                clear=False,
            ):
                processor = PersonaProcessor(
                    store=store,
                    clients={
                        "agnes": agnes_client,
                        "qwen": qwen_client,
                    },
                )
                result = processor.rewrite("测试", persona_id=persona.id)

        self.assertEqual(result, "备用模型结果")
        qwen_client.chat.completions.create.assert_called_once()


class KeyboardManagerTests(unittest.TestCase):
    def test_right_command_aliases_are_supported(self) -> None:
        self.assertEqual(KeyboardManager._parse_button("cmd_r"), Key.cmd_r)
        self.assertEqual(
            KeyboardManager._parse_button("right_command"),
            Key.cmd_r,
        )
        self.assertEqual(
            KeyboardManager._display_button_name("cmd_r"),
            "Right Command",
        )


if __name__ == "__main__":
    unittest.main()
