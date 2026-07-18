from __future__ import annotations

import re


class TerminalTextProcessor:
    SYMBOL_RULES = (
        ("双横杠", "--"),
        ("反斜杠", "\\"),
        ("左方括号", "["),
        ("右方括号", "]"),
        ("左花括号", "{"),
        ("右花括号", "}"),
        ("左括号", "("),
        ("右括号", ")"),
        ("双引号", '"'),
        ("单引号", "'"),
        ("管道符", "|"),
        ("与符号", "&"),
        ("大于号", ">"),
        ("小于号", "<"),
        ("下划线", "_"),
        ("美元符号", "$"),
        ("百分号", "%"),
        ("艾特符号", "@"),
        ("艾特", "@"),
        ("井号", "#"),
        ("星号", "*"),
        ("等号", "="),
        ("冒号", ":"),
        ("分号", ";"),
        ("逗号", ","),
        ("点号", "."),
        ("斜杠", "/"),
        ("横杠", "-"),
        ("空格", " "),
    )

    def process(self, text: str) -> str:
        if not text:
            return text

        processed = text.strip()
        for spoken, symbol in self.SYMBOL_RULES:
            processed = processed.replace(spoken, symbol)

        processed = processed.translate(
            str.maketrans(
                {
                    "（": "(",
                    "）": ")",
                    "【": "[",
                    "】": "]",
                    "：": ":",
                    "；": ";",
                }
            )
        )
        processed = re.sub(r"[。！？!?]+$", "", processed)
        processed = re.sub(r"[ \t]+", " ", processed)
        processed = re.sub(r" *\n *", "\n", processed)
        return processed.strip()
