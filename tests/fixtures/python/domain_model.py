"""Domain model fixture. Exercises dataclass, Protocol, inheritance,
module-level typed fields, @property getter/setter, stacked decorators."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


DEFAULT_TIMEOUT: int = 30
_PRIVATE_CONSTANT = "hidden"


class Repository(Protocol):
    """Abstract repository contract."""

    def get(self, key: str) -> bytes | None: ...
    def put(self, key: str, value: bytes) -> None: ...


class BaseEntity:
    """Root of the entity hierarchy."""

    def __init__(self, id: int) -> None:
        self._id = id

    @property
    def id(self) -> int:
        """Read-only identity."""
        return self._id


@dataclass
class User(BaseEntity):
    """A user. Inherits identity from BaseEntity but is also a dataclass."""

    id: int
    name: str
    email: str

    @property
    def display_name(self) -> str:
        """Human-friendly label."""
        return f"{self.name} <{self.email}>"

    @display_name.setter
    def display_name(self, value: str) -> None:
        self.name, _, rest = value.partition(" <")
        self.email = rest.rstrip(">")


class UserService:
    """Business logic for users."""

    def __init__(self, repo: Repository) -> None:
        self._repo = repo

    def get(self, user_id: int) -> User | None:
        """Look up a user by id."""
        raw = self._repo.get(f"user:{user_id}")
        if raw is None:
            return None
        return _decode(raw)

    def save(self, user: User) -> None:
        self._repo.put(f"user:{user.id}", _encode(user))

    def _log(self, msg: str) -> None:
        """Private helper — visibility test."""
        print(msg)


def _encode(user: User) -> bytes:
    return f"{user.id}|{user.name}|{user.email}".encode()


def _decode(raw: bytes) -> User:
    uid, name, email = raw.decode().split("|", 2)
    return User(int(uid), name, email)


def public_helper(x: int) -> int:
    """Module-level public function."""
    return x * 2
