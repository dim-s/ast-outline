"""Multi-level inheritance fixture for `implements` transitive tests.

Covers: abstract base + multiple concrete subclasses + grandchild +
great-grandchild, a multiple-inheritance diamond, and a Protocol-style
interface chain.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol


class Animal(ABC):
    @abstractmethod
    def eat(self) -> None:
        ...


class Dog(Animal):
    def eat(self) -> None:
        pass


class Cat(Animal):
    def eat(self) -> None:
        pass


# Transitive through Dog.
class Puppy(Dog):
    def play(self) -> None:
        pass


# Two-level transitive: Animal ← Dog ← Puppy ← Pomeranian.
class Pomeranian(Puppy):
    def yap(self) -> None:
        pass


# Protocol chain — transitive via Readable.
class Readable(Protocol):
    def read(self) -> str: ...


class SizedReadable(Readable, Protocol):
    def size(self) -> int: ...


class FileReader(SizedReadable):
    def read(self) -> str:
        return ""

    def size(self) -> int:
        return 0
