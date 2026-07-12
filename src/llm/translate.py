"""Text translation providers used after speech recognition."""

from __future__ import annotations

import os
from typing import Callable, Optional

from openai import OpenAI

from ..utils.logger import logger


TARGET_LANGUAGES = {
    "en": "English",
    "ja": "Japanese",
    "ru": "Russian",
    "ko": "Korean",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "pt": "Portuguese",
    "it": "Italian",
    "ar": "Arabic",
    "zh": "Chinese",
}

TARGET_LANGUAGE_LABELS = {
    "en": "英语",
    "ja": "日语",
    "ru": "俄语",
    "ko": "韩语",
    "fr": "法语",
    "de": "德语",
    "es": "西班牙语",
    "pt": "葡萄牙语",
    "it": "意大利语",
    "ar": "阿拉伯语",
    "zh": "中文",
}


class TranslateProcessor:
    def __init__(self, client: Optional[OpenAI] = None) -> None:
        self.provider = os.getenv("TRANSLATION_SERVICE", "aliyun").strip().lower()
        self.target_language = os.getenv(
            "TRANSLATION_TARGET_LANGUAGE",
            "en",
        ).strip().lower()
        self.model = os.getenv(
            "DASHSCOPE_TRANSLATION_MODEL",
            "qwen-mt-flash",
        ).strip()
        self._client = client

    @property
    def target_label(self) -> str:
        return TARGET_LANGUAGE_LABELS.get(
            self.target_language,
            self.target_language,
        )

    def is_available(self) -> bool:
        if self.provider in {"aliyun", "dashscope", "bailian"}:
            return bool(
                os.getenv("DASHSCOPE_API_KEY")
                or os.getenv("BAILIAN_API_KEY")
            )
        return False

    def translate(
        self,
        text: str,
        target_language: str | None = None,
        *,
        on_update: Callable[[str], None] | None = None,
    ) -> str:
        if not text:
            return text

        target_code = (target_language or self.target_language).strip().lower()
        target_name = TARGET_LANGUAGES.get(target_code)
        if target_name is None:
            raise ValueError(f"不支持的翻译目标语言: {target_code}")

        if self.provider not in {"aliyun", "dashscope", "bailian"}:
            raise ValueError(f"不支持的翻译服务: {self.provider}")

        client = self._get_dashscope_client()
        logger.info(
            "正在使用 %s 将文字翻译为 %s...",
            self.model,
            TARGET_LANGUAGE_LABELS.get(target_code, target_name),
        )

        if on_update is None:
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": text}],
                extra_body={
                    "translation_options": {
                        "source_lang": "auto",
                        "target_lang": target_name,
                    }
                },
            )
            translated = (response.choices[0].message.content or "").strip()
        else:
            translated_parts: list[str] = []
            stream = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": text}],
                extra_body={
                    "translation_options": {
                        "source_lang": "auto",
                        "target_lang": target_name,
                    }
                },
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if not delta:
                    continue
                translated_parts.append(delta)
                on_update("".join(translated_parts))
            translated = "".join(translated_parts).strip()

        if not translated:
            raise RuntimeError("翻译服务返回了空结果")
        logger.info("翻译完成: %s", translated)
        return translated

    def _get_dashscope_client(self) -> OpenAI:
        if self._client is not None:
            return self._client

        api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("BAILIAN_API_KEY")
        if not api_key:
            raise ValueError("未设置 DASHSCOPE_API_KEY 或 BAILIAN_API_KEY")
        self._client = OpenAI(
            api_key=api_key,
            base_url=os.getenv(
                "DASHSCOPE_BASE_URL",
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
            ),
        )
        return self._client
