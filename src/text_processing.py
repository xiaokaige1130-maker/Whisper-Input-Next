from __future__ import annotations

import os
import re

from opencc import OpenCC


class TextPostProcessor:
    def __init__(
        self,
        *,
        chinese_conversion: str = "none",
        clean_fillers: bool = True,
        normalize_text: bool = True,
        smart_sentence_ending: bool = False,
    ) -> None:
        conversion = chinese_conversion.strip().lower()
        self.chinese_conversion = (
            conversion if conversion in {"none", "t2s", "s2t"} else "none"
        )
        self.clean_fillers = clean_fillers
        self.normalize_text = normalize_text
        self.smart_sentence_ending = smart_sentence_ending
        self._converter = (
            OpenCC(self.chinese_conversion)
            if self.chinese_conversion != "none"
            else None
        )

    @classmethod
    def from_environment(cls) -> "TextPostProcessor":
        conversion = os.getenv("CHINESE_CONVERSION", "").strip().lower()
        if not conversion:
            conversion = (
                "t2s"
                if os.getenv("CONVERT_TO_SIMPLIFIED", "false").lower() == "true"
                else "none"
            )
        return cls(
            chinese_conversion=conversion,
            clean_fillers=os.getenv(
                "CLEAN_ASR_FILLERS",
                "true",
            ).lower()
            == "true",
            normalize_text=os.getenv(
                "NORMALIZE_TRANSCRIPT_TEXT",
                "true",
            ).lower()
            == "true",
            smart_sentence_ending=os.getenv(
                "SMART_SENTENCE_ENDING",
                "false",
            ).lower()
            == "true",
        )

    def process(self, text: str) -> str:
        if not text:
            return text

        processed = text.strip()
        if self._converter is not None:
            processed = self._converter.convert(processed)
        if self.clean_fillers:
            processed = self._clean_asr_fillers(processed)
        if self.normalize_text:
            processed = self._normalize_text(processed)
        if self.smart_sentence_ending:
            processed = self._add_sentence_ending(processed)
        return processed.strip()

    @staticmethod
    def _clean_asr_fillers(text: str) -> str:
        cleaned = text.strip()
        filler_patterns = [
            r"(?:(?<=^)|(?<=[\s，,。.!！？?；;：:、]))"
            r"(?:嗯+|呃+|额+|啊+|呐+|唔+|em+|emm+|呃嗯+)"
            r"[\s，,。.!！？?；;：:、]*",
            r"[\s，,。.!！？?；;：:、]*"
            r"(?:嗯+|呃+|额+|啊+|呐+|唔+|em+|emm+|呃嗯+)"
            r"(?=$|[\s，,。.!！？?；;：:、])",
            r"(?:(?<=^)|(?<=[\s，,。.!！？?；;：:、]))"
            r"(?:这个|那个|就是|然后呢|然后|怎么说呢|怎么讲呢|"
            r"你知道吧|对吧|是吧)[\s，,。.!！？?；;：:、]*",
        ]
        for pattern in filler_patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

        repeat_words = [
            "我",
            "你",
            "他",
            "她",
            "它",
            "这",
            "那",
            "是",
            "有",
            "要",
            "会",
            "就",
            "这个",
            "那个",
            "然后",
            "但是",
            "如果",
            "因为",
            "所以",
        ]
        for word in repeat_words:
            cleaned = re.sub(f"(?:{re.escape(word)}){{2,}}", word, cleaned)
        return cleaned

    @staticmethod
    def _normalize_text(text: str) -> str:
        normalized = re.sub(r"[\t\r\f\v ]+", " ", text)
        normalized = re.sub(
            r"(?<=[\u3400-\u9fff]) +(?=[\u3400-\u9fff])",
            "",
            normalized,
        )
        normalized = re.sub(r"\s*([，。！？；：、])\s*", r"\1", normalized)
        normalized = re.sub(r"[，,、]{2,}", "，", normalized)
        normalized = re.sub(r"([。！？；：])\1+", r"\1", normalized)
        normalized = re.sub(r"[，,、]+([。！？；：])", r"\1", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized.strip(" ，,、")

    @staticmethod
    def _add_sentence_ending(text: str) -> str:
        if not text or re.search(r"[。！？!?…；;：:]$", text):
            return text
        if re.search(r"[\u3400-\u9fff]", text):
            return f"{text}。"
        return text
