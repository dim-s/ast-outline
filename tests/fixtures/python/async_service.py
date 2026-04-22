"""Async-heavy fixture. Exercises async def, ABCs, classmethod/staticmethod,
generic typing, class with metaclass keyword argument."""
from __future__ import annotations

import abc
from typing import Generic, TypeVar


T = TypeVar("T")


class Handler(abc.ABC, metaclass=abc.ABCMeta):
    """Abstract async handler."""

    @abc.abstractmethod
    async def handle(self, event: object) -> None:
        """Process a single event."""
        ...

    @classmethod
    def default(cls) -> "Handler":
        raise NotImplementedError

    @staticmethod
    def describe() -> str:
        return "Handler"


class Queue(Generic[T]):
    """Generic FIFO queue."""

    def __init__(self) -> None:
        self._items: list[T] = []

    async def push(self, item: T) -> None:
        self._items.append(item)

    async def pop(self) -> T | None:
        if not self._items:
            return None
        return self._items.pop(0)

    def __len__(self) -> int:
        return len(self._items)


async def run_forever(handler: Handler, queue: Queue[object]) -> None:
    """Drive handler with events from queue until cancelled."""
    while True:
        event = await queue.pop()
        if event is None:
            break
        await handler.handle(event)
