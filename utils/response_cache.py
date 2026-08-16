"""
Simple response cache for repeated questions (saves ProxyAPI calls).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional

from config import DATA_DIR


class ResponseCache:
    """JSON file cache keyed by normalized query + mode."""

    def __init__(self, cache_path: Optional[Path] = None) -> None:
        DATA_DIR.mkdir(exist_ok=True)
        self.cache_path = Path(cache_path or DATA_DIR / "response_cache.json")
        self._data: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if not self.cache_path.exists():
            self._data = {}
            return
        try:
            raw = json.loads(self.cache_path.read_text(encoding="utf-8"))
            self._data = raw if isinstance(raw, dict) else {}
        except (json.JSONDecodeError, OSError):
            self._data = {}

    def _save(self) -> None:
        self.cache_path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _key(query: str, mode: str) -> str:
        normalized = " ".join((query or "").strip().lower().split())
        payload = f"{mode}|{normalized}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(self, query: str, mode: str) -> Optional[str]:
        return self._data.get(self._key(query, mode))

    def set(self, query: str, mode: str, answer: str) -> None:
        if not answer:
            return
        self._data[self._key(query, mode)] = answer
        self._save()

    def clear(self) -> None:
        self._data = {}
        self._save()

    def size(self) -> int:
        return len(self._data)


response_cache = ResponseCache()
