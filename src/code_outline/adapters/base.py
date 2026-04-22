"""Adapter protocol."""
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ..core import ParseResult


class LanguageAdapter(Protocol):
    language_name: str
    extensions: set[str]

    def parse(self, path: Path) -> ParseResult: ...
