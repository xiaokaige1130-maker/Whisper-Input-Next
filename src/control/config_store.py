"""Small, comment-preserving .env configuration store."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Mapping


_ENV_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class EnvStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def read(self) -> dict[str, str]:
        values: dict[str, str] = {}
        if not self.path.exists():
            return values

        for line in self.path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            values[key.strip()] = value.strip()
        return values

    def update(self, updates: Mapping[str, object]) -> None:
        normalized = self._normalize(updates)
        existing = (
            self.path.read_text(encoding="utf-8").splitlines()
            if self.path.exists()
            else []
        )
        seen: set[str] = set()
        output: list[str] = []

        for line in existing:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                output.append(line)
                continue

            key = stripped.split("=", 1)[0].strip()
            if key in normalized:
                output.append(f"{key}={normalized[key]}")
                seen.add(key)
            else:
                output.append(line)

        missing = [key for key in normalized if key not in seen]
        if missing and output and output[-1].strip():
            output.append("")
        output.extend(f"{key}={normalized[key]}" for key in missing)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_name(f".{self.path.name}.tmp")
        temp_path.write_text("\n".join(output) + "\n", encoding="utf-8")
        if self.path.exists():
            os.chmod(temp_path, self.path.stat().st_mode)
        os.replace(temp_path, self.path)

    @staticmethod
    def get_bool(values: Mapping[str, str], key: str, default: bool = False) -> bool:
        fallback = "true" if default else "false"
        return values.get(key, fallback).strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def get_int(
        values: Mapping[str, str],
        key: str,
        default: int,
        *,
        minimum: int | None = None,
        maximum: int | None = None,
    ) -> int:
        try:
            value = int(values.get(key, str(default)))
        except (TypeError, ValueError):
            value = default
        if minimum is not None:
            value = max(minimum, value)
        if maximum is not None:
            value = min(maximum, value)
        return value

    @staticmethod
    def _normalize(updates: Mapping[str, object]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for key, value in updates.items():
            if not _ENV_KEY.match(key):
                raise ValueError(f"Invalid environment key: {key}")
            text = str(value).replace("\n", " ").replace("\r", " ").strip()
            normalized[key] = text
        return normalized
