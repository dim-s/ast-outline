"""Language-agnostic intermediate representation + renderers.

Adapters parse source files into `ParseResult` containing a tree of
`Declaration` nodes. This module renders that IR to human-readable
outputs (outline, digest) and runs search operations (find_symbol,
find_implementations).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# Canonical kinds used across languages. Adapters map their native node
# types onto these. Consumers (renderers/search) reason about these.
KIND_NAMESPACE = "namespace"
KIND_CLASS = "class"
KIND_STRUCT = "struct"
KIND_INTERFACE = "interface"
KIND_RECORD = "record"
KIND_ENUM = "enum"
KIND_ENUM_MEMBER = "enum_member"

KIND_METHOD = "method"
KIND_FUNCTION = "function"
KIND_CTOR = "ctor"
KIND_DTOR = "dtor"
KIND_PROPERTY = "property"
KIND_INDEXER = "indexer"
KIND_FIELD = "field"
KIND_EVENT = "event"
KIND_DELEGATE = "delegate"
KIND_OPERATOR = "operator"

TYPE_KINDS = {KIND_CLASS, KIND_STRUCT, KIND_INTERFACE, KIND_RECORD, KIND_ENUM}
CALLABLE_KINDS = {KIND_METHOD, KIND_FUNCTION, KIND_CTOR, KIND_DTOR, KIND_OPERATOR}


@dataclass
class Declaration:
    kind: str               # canonical kind (see constants above)
    name: str               # identifier (not qualified)
    signature: str          # rendered signature line (no body)
    bases: list[str] = field(default_factory=list)      # for types
    attrs: list[str] = field(default_factory=list)      # decorators/attributes (inlined-ready)
    docs: list[str] = field(default_factory=list)       # doc-comment lines as-is (/// or """)
    docs_inside: bool = False  # True → emit docs AFTER signature with +1 indent (Python docstrings)
    visibility: str = ""    # "public"/"protected"/"private"/"internal"/"" (unknown)
    start_line: int = 0     # 1-based, inclusive
    end_line: int = 0       # 1-based, inclusive
    start_byte: int = 0     # for `show` — source slice
    end_byte: int = 0
    doc_start_byte: int = 0 # if there's leading doc, slice starts here
    children: list["Declaration"] = field(default_factory=list)

    # Convenience: rendered line suffix for line-range display
    def lines_suffix(self) -> str:
        if not self.start_line:
            return ""
        if self.start_line == self.end_line:
            return f"  L{self.start_line}"
        return f"  L{self.start_line}-{self.end_line}"


@dataclass
class ParseResult:
    path: Path
    language: str           # "csharp" / "python" / etc.
    source: bytes
    line_count: int
    declarations: list[Declaration]  # top-level (namespaces or types)


# --- Options --------------------------------------------------------------


@dataclass
class OutlineOptions:
    include_private: bool = True
    include_fields: bool = True
    include_xml_doc: bool = True
    include_attributes: bool = True
    include_line_numbers: bool = True
    max_doc_lines: int = 6


@dataclass
class DigestOptions:
    include_private: bool = False
    include_fields: bool = False
    max_members_per_type: int = 50


# --- Match types ----------------------------------------------------------


@dataclass
class SymbolMatch:
    qualified_name: str
    kind: str
    start_line: int
    end_line: int
    source: str


@dataclass
class ImplMatch:
    path: str
    start_line: int
    end_line: int
    kind: str
    name: str
    bases: list[str]


# --- Renderers ------------------------------------------------------------


def render_outline(result: ParseResult, opts: OutlineOptions) -> str:
    lines: list[str] = [f"# {result.path} ({result.line_count} lines)"]
    for decl in result.declarations:
        _render_decl(decl, opts, indent=0, out=lines)
    return "\n".join(lines)


def _render_decl(decl: Declaration, opts: OutlineOptions, indent: int, out: list[str]) -> None:
    if decl.kind == KIND_FIELD and not opts.include_fields:
        return
    if decl.visibility == "private" and not opts.include_private:
        return

    prefix = "    " * indent

    # Docs BEFORE signature (C# /// XML-doc style)
    if opts.include_xml_doc and decl.docs and not decl.docs_inside:
        for d in _clip_docs(decl.docs, opts.max_doc_lines):
            out.append(prefix + d)

    # Attributes inlined
    attrs_prefix = ""
    if opts.include_attributes and decl.attrs:
        attrs_prefix = " ".join(decl.attrs) + " "

    suffix = decl.lines_suffix() if opts.include_line_numbers else ""

    # Namespace gets special rendering
    if decl.kind == KIND_NAMESPACE:
        out.append(prefix + f"namespace {decl.name}")
    else:
        out.append(prefix + attrs_prefix + decl.signature + suffix)

    # Docs AFTER signature (Python docstring style — they're inside the body)
    if opts.include_xml_doc and decl.docs and decl.docs_inside:
        inner_prefix = "    " * (indent + 1)
        for d in _clip_docs(decl.docs, opts.max_doc_lines):
            out.append(inner_prefix + d)

    # Recurse into children
    for child in decl.children:
        _render_decl(child, opts, indent + 1, out)

    # Blank line after top-level types and namespaces for readability
    if indent == 0 or decl.kind in TYPE_KINDS or decl.kind == KIND_NAMESPACE:
        out.append("")


def _clip_docs(docs: list[str], limit: int) -> list[str]:
    if len(docs) <= limit:
        return docs
    return docs[:limit] + ["..."]


# --- Digest ---------------------------------------------------------------


def render_digest(results: list[ParseResult], opts: DigestOptions, root: Optional[Path] = None) -> str:
    """Compact per-directory public-API map across a batch of parsed files."""
    if not results:
        return "# no files\n"
    # Common root for relative paths
    if root is None:
        try:
            import os
            root = Path(os.path.commonpath([str(r.path) for r in results]))
        except ValueError:
            root = results[0].path.parent

    grouped: dict[Path, list[ParseResult]] = {}
    for r in results:
        grouped.setdefault(r.path.parent, []).append(r)

    lines: list[str] = []
    for directory in sorted(grouped.keys(), key=str):
        try:
            rel = str(directory.relative_to(root))
        except ValueError:
            rel = str(directory)
        lines.append(f"{rel}/")
        for r in grouped[directory]:
            lines.extend(_digest_one(r, opts))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _digest_one(result: ParseResult, opts: DigestOptions) -> list[str]:
    lines = [f"  {result.path.name} ({result.line_count} lines)"]
    types = _flatten_types(result.declarations)
    free_functions = _flatten_free_functions(result.declarations, opts)

    if not types and not free_functions:
        lines[-1] += "  # no declarations"
        return lines

    for t in types:
        header = f"    {t.kind} {t.name}"
        if t.bases:
            header += " : " + ", ".join(t.bases)
        header += t.lines_suffix()
        lines.append(header)
        members = _digest_members(t, opts)
        if members:
            shown = members[: opts.max_members_per_type]
            tokens = []
            for m in shown:
                if m.kind in (KIND_METHOD, KIND_FUNCTION, KIND_CTOR, KIND_DTOR):
                    tokens.append(f"+{m.name}")
                else:
                    tokens.append(f"+{m.name} [{m.kind}]")
            lines.extend(_wrap_tokens(tokens, width=100, indent="      "))
            if len(members) > len(shown):
                lines.append(f"      ... +{len(members) - len(shown)} more")

    # Module-level functions / fields (common in Python)
    if free_functions:
        shown = free_functions[: opts.max_members_per_type]
        tokens = []
        for f in shown:
            if f.kind in (KIND_FUNCTION, KIND_METHOD):
                tokens.append(f"+{f.name}")
            else:
                tokens.append(f"+{f.name} [{f.kind}]")
        lines.extend(_wrap_tokens(tokens, width=100, indent="    "))
    return lines


def _flatten_free_functions(decls: list[Declaration], opts: DigestOptions) -> list[Declaration]:
    """Module-level callables/fields that aren't inside a type. Dives through namespaces."""
    out: list[Declaration] = []
    for d in decls:
        if d.kind == KIND_NAMESPACE:
            out.extend(_flatten_free_functions(d.children, opts))
        elif d.kind in TYPE_KINDS:
            continue
        else:
            if d.kind == KIND_FIELD and not opts.include_fields:
                continue
            if d.visibility == "private" and not opts.include_private:
                continue
            out.append(d)
    return out


def _flatten_types(decls: list[Declaration], prefix: str = "") -> list[Declaration]:
    """Dive through namespaces to collect types with qualified names."""
    out: list[Declaration] = []
    for d in decls:
        if d.kind == KIND_NAMESPACE:
            out.extend(_flatten_types(d.children, prefix=(prefix + d.name + "." if prefix else d.name + ".")))
        elif d.kind in TYPE_KINDS:
            qualified = Declaration(
                kind=d.kind,
                name=(prefix + d.name) if prefix else d.name,
                signature=d.signature,
                bases=d.bases,
                attrs=d.attrs,
                docs=d.docs,
                visibility=d.visibility,
                start_line=d.start_line,
                end_line=d.end_line,
                start_byte=d.start_byte,
                end_byte=d.end_byte,
                doc_start_byte=d.doc_start_byte,
                children=d.children,
            )
            out.append(qualified)
            # Also flatten nested types (they appear as their own rows)
            out.extend(_flatten_types(d.children, prefix=qualified.name + "."))
    return out


def _digest_members(type_decl: Declaration, opts: DigestOptions) -> list[Declaration]:
    members: list[Declaration] = []
    for c in type_decl.children:
        if c.kind in TYPE_KINDS or c.kind == KIND_NAMESPACE:
            continue
        if c.kind == KIND_ENUM_MEMBER:
            continue
        if c.kind == KIND_FIELD and not opts.include_fields:
            continue
        if c.visibility == "private" and not opts.include_private:
            continue
        members.append(c)
    return members


def _wrap_tokens(tokens: list[str], width: int, indent: str) -> list[str]:
    if not tokens:
        return []
    out: list[str] = []
    cur = indent
    for tok in tokens:
        piece = ("  " if cur != indent else "") + tok
        if len(cur) + len(piece) > width and cur != indent:
            out.append(cur)
            cur = indent + tok
        else:
            cur += piece
    if cur != indent:
        out.append(cur)
    return out


# --- Search ---------------------------------------------------------------


def find_symbols(result: ParseResult, symbol: str) -> list[SymbolMatch]:
    """Find declarations matching a dotted symbol path.

    Matching is suffix-based — `TakeDamage` matches `Foo.Bar.TakeDamage`
    and `PlayerController.TakeDamage` also matches.
    """
    parts = symbol.split(".")
    matches: list[SymbolMatch] = []
    _search_walk(result.declarations, result.source, [], parts, matches)
    return matches


def _search_walk(
    decls: list[Declaration],
    src: bytes,
    trail: list[str],
    parts: list[str],
    out: list[SymbolMatch],
) -> None:
    for d in decls:
        new_trail = trail + [d.name] if d.name else trail
        if d.name and _trail_matches(new_trail, parts):
            # Include doc block in source slice if present
            start = d.doc_start_byte or d.start_byte
            end = d.end_byte
            out.append(
                SymbolMatch(
                    qualified_name=".".join(new_trail),
                    kind=d.kind,
                    start_line=d.start_line,
                    end_line=d.end_line,
                    source=src[start:end].decode("utf8", errors="replace"),
                )
            )
        if d.children:
            _search_walk(d.children, src, new_trail, parts, out)


def _trail_matches(trail: list[str], parts: list[str]) -> bool:
    if len(parts) > len(trail):
        return False
    return trail[-len(parts):] == parts


def find_implementations(results: list[ParseResult], type_name: str) -> list[ImplMatch]:
    """Find all types in the batch whose base list contains `type_name`
    (last segment, generic-stripped). Direct inheritance/implementation only.
    """
    target = _normalize_type_name(type_name)
    out: list[ImplMatch] = []
    for r in results:
        _impl_walk(r.declarations, r.path, target, out)
    return out


def _impl_walk(decls: list[Declaration], path: Path, target: str, out: list[ImplMatch]) -> None:
    for d in decls:
        if d.kind in TYPE_KINDS and d.kind != KIND_ENUM:
            normalized = [_normalize_type_name(b) for b in d.bases]
            if target in normalized:
                out.append(
                    ImplMatch(
                        path=str(path),
                        start_line=d.start_line,
                        end_line=d.end_line,
                        kind=d.kind,
                        name=d.name,
                        bases=d.bases,
                    )
                )
        if d.children:
            _impl_walk(d.children, path, target, out)


def _normalize_type_name(name: str) -> str:
    name = name.strip()
    gen = name.find("<")
    if gen > 0:
        name = name[:gen]
    gen = name.find("[")  # Python generics `List[X]`
    if gen > 0:
        name = name[:gen]
    if "." in name:
        name = name.split(".")[-1]
    return name
