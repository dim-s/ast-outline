"""Pytest shared fixtures. Only used by the test suite itself."""
from __future__ import annotations

from pathlib import Path

import pytest


FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture(scope="session")
def csharp_dir() -> Path:
    return FIXTURES_DIR / "csharp"


@pytest.fixture(scope="session")
def python_dir() -> Path:
    return FIXTURES_DIR / "python"


@pytest.fixture(scope="session")
def java_dir() -> Path:
    return FIXTURES_DIR / "java"


@pytest.fixture(scope="session")
def kotlin_dir() -> Path:
    return FIXTURES_DIR / "kotlin"


@pytest.fixture(scope="session")
def scala_dir() -> Path:
    return FIXTURES_DIR / "scala"


@pytest.fixture(scope="session")
def go_dir() -> Path:
    return FIXTURES_DIR / "go"


@pytest.fixture(scope="session")
def md_dir() -> Path:
    return FIXTURES_DIR / "markdown"
