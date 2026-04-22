"""Language adapters — parse source into Declaration IR.

Each adapter knows: a set of file extensions it handles, and how to convert
tree-sitter AST nodes for its language into the `core.Declaration` tree.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .base import LanguageAdapter
from .csharp import CSharpAdapter
from .markdown import MarkdownAdapter
from .python import PythonAdapter
from .typescript import TypeScriptAdapter


ADAPTERS: list[LanguageAdapter] = [
    CSharpAdapter(),
    PythonAdapter(),
    TypeScriptAdapter(),
    MarkdownAdapter(),
]


def get_adapter_for(path: Path) -> Optional[LanguageAdapter]:
    ext = path.suffix.lower()
    for a in ADAPTERS:
        if ext in a.extensions:
            return a
    return None


def supported_extensions() -> set[str]:
    out: set[str] = set()
    for a in ADAPTERS:
        out.update(a.extensions)
    return out


def collect_files(paths: list[Path], glob: Optional[str] = None) -> list[Path]:
    """Gather all source files under `paths` that any adapter handles.

    If `glob` is given, only match that pattern (used for --glob override).
    Otherwise every supported extension is included.
    """
    out: list[Path] = []
    exts = supported_extensions()
    for p in paths:
        if p.is_file():
            out.append(p)
        elif p.is_dir():
            if glob:
                out.extend(sorted(p.rglob(glob)))
            else:
                for f in sorted(p.rglob("*")):
                    if f.is_file() and f.suffix.lower() in exts:
                        out.append(f)
    return out
