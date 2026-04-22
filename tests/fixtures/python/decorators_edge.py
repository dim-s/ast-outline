"""Edge cases for decorators. Used to check that:
  - decorator line is the declaration's start (so `show` includes it)
  - stacked decorators are all captured as attrs
  - @property → KIND_PROPERTY, @staticmethod/@classmethod keep KIND_METHOD
"""
from __future__ import annotations

import functools


def tracing(fn):
    @functools.wraps(fn)
    def inner(*args, **kwargs):
        return fn(*args, **kwargs)
    return inner


class Widget:
    """Toy widget with many decorator shapes."""

    @property
    def name(self) -> str:
        """Widget display name."""
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    @staticmethod
    def factory() -> "Widget":
        return Widget()

    @classmethod
    def from_dict(cls, data: dict) -> "Widget":
        obj = cls()
        obj._name = data.get("name", "")
        return obj

    @tracing
    @functools.lru_cache(maxsize=128)
    def compute(self, x: int) -> int:
        """Compute with two stacked decorators."""
        return x * x
