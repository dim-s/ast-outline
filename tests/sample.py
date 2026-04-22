"""Generic sample Python file used for smoke tests."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


MAX_RETRIES: int = 3


class Storage(Protocol):
    """Abstract storage protocol."""

    def read(self, key: str) -> bytes | None: ...
    def write(self, key: str, value: bytes) -> None: ...


@dataclass
class User:
    """Domain model for a user."""

    id: int
    name: str
    email: str

    @property
    def display_name(self) -> str:
        """Human-friendly label."""
        return f"{self.name} <{self.email}>"


class UserService:
    """Business logic for user CRUD + auth."""

    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    def get(self, user_id: int) -> User | None:
        """Look up a user by id."""
        raw = self._storage.read(f"user:{user_id}")
        if raw is None:
            return None
        return _decode_user(raw)

    def save(self, user: User) -> None:
        """Persist a user."""
        self._storage.write(f"user:{user.id}", _encode_user(user))

    def _log(self, msg: str) -> None:
        print(msg)


def _encode_user(user: User) -> bytes:
    return f"{user.id}|{user.name}|{user.email}".encode()


def _decode_user(raw: bytes) -> User:
    uid, name, email = raw.decode().split("|", 2)
    return User(int(uid), name, email)
