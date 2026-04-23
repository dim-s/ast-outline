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

# Non-code (narrative) document kinds — currently used by the markdown adapter
KIND_HEADING = "heading"
KIND_CODE_BLOCK = "code_block"

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
    # Count of tree-sitter ERROR + MISSING nodes encountered during parse.
    # Non-zero means the IR for some region of the file may be incomplete;
    # renderers surface this as a warning line so the consuming agent
    # knows the outline isn't authoritative for that file.
    error_count: int = 0


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
    # Markdown-only: cap heading depth in TOC digest (1=H1 only, 3=H1..H3, …).
    # Code blocks are shown only when include_fields is True.
    max_heading_depth: int = 3


# --- Match types ----------------------------------------------------------


@dataclass
class SymbolMatch:
    qualified_name: str
    kind: str
    start_line: int
    end_line: int
    source: str
    # Signatures of the enclosing ancestor declarations, outer → inner
    # (e.g. ["namespace Foo.Bar", "public class Player : MonoBehaviour"] for
    # a method on `Player`). Rendered by `show` as a breadcrumb so the agent
    # knows what the extracted body is nested inside. Empty for top-level
    # symbols. Attributes/annotations are already stripped from each signature
    # (adapters store the bare signature in Declaration.signature).
    ancestor_signatures: list[str] = field(default_factory=list)


@dataclass
class ImplMatch:
    path: str
    start_line: int
    end_line: int
    kind: str
    name: str
    bases: list[str]
    # Transitive chain from the queried target down to this match's
    # immediate parent. Empty for direct matches. For a 2-level chain
    # `Animal → Dog → Puppy`, Puppy's via is `["Dog"]`. For
    # `Animal → Dog → Quadruped → Pomeranian`, Pomeranian's via is
    # `["Dog", "Quadruped"]`. Only the first discovered path is kept
    # when a class inherits the target through multiple branches.
    via: list[str] = field(default_factory=list)


# --- Renderers ------------------------------------------------------------


def render_outline(result: ParseResult, opts: OutlineOptions) -> str:
    lines: list[str] = [_format_file_header(f"# {result.path}", result)]
    warn = _format_error_warning(result)
    if warn:
        lines.append(warn)
    for decl in result.declarations:
        _render_decl(decl, opts, indent=0, out=lines)
    return "\n".join(lines)


# --- Header helpers (shared between outline + digest) --------------------


def _format_file_header(prefix: str, result: ParseResult) -> str:
    """Build the `# path (N lines, ...)` header for one file.

    `prefix` is the leading marker + path (e.g. `"# /abs/path.py"` for
    outline or `"  name.py"` for digest). Appended in parentheses:
    line count, and non-zero category counters appropriate for the
    language family — types/methods/fields for code, headings/code
    blocks for markdown. Zero-valued categories are skipped so a
    trivial file still reads `(42 lines)` not `(42 lines, 0 types, 0 methods)`.
    """
    counts = _collect_counts(result.declarations)
    parts = [f"{result.line_count} lines"]
    if result.language == "markdown":
        order = [("headings", "headings"), ("code_blocks", "code blocks")]
    else:
        order = [("types", "types"), ("methods", "methods"), ("fields", "fields")]
    for key, label in order:
        n = counts.get(key, 0)
        if n > 0:
            parts.append(f"{n} {label}")
    return f"{prefix} ({', '.join(parts)})"


def _format_error_warning(result: ParseResult) -> Optional[str]:
    """Second header line warning about parse errors — only when
    `error_count > 0`. Agents should treat the file's outline as partial.
    """
    if result.error_count <= 0:
        return None
    plural = "s" if result.error_count != 1 else ""
    return (
        f"# WARNING: {result.error_count} parse error{plural} — "
        f"output may be incomplete"
    )


_TYPE_COUNT_KINDS = TYPE_KINDS
_METHOD_COUNT_KINDS = CALLABLE_KINDS
_FIELD_COUNT_KINDS = {KIND_FIELD, KIND_PROPERTY, KIND_EVENT, KIND_INDEXER}


def _collect_counts(decls: list[Declaration]) -> dict[str, int]:
    """Walk the declaration tree once, counting by category. Namespaces
    are transparent containers — not counted, but their children are.
    Enum members aren't counted (they're not "fields" semantically).
    """
    out = {
        "types": 0,
        "methods": 0,
        "fields": 0,
        "headings": 0,
        "code_blocks": 0,
    }
    stack: list[Declaration] = list(decls)
    while stack:
        d = stack.pop()
        k = d.kind
        if k in _TYPE_COUNT_KINDS:
            out["types"] += 1
        elif k in _METHOD_COUNT_KINDS:
            out["methods"] += 1
        elif k in _FIELD_COUNT_KINDS:
            out["fields"] += 1
        elif k == KIND_HEADING:
            out["headings"] += 1
        elif k == KIND_CODE_BLOCK:
            out["code_blocks"] += 1
        # namespace / enum_member / delegate → not counted at top level
        stack.extend(d.children)
    return out


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
    lines = [_format_file_header(f"  {result.path.name}", result)]
    warn = _format_error_warning(result)
    if warn:
        # Indent under the file line so the warning lives with its file.
        lines.append("  " + warn)

    # Markdown files digest as a hierarchical TOC, not a type/member list.
    if result.language == "markdown":
        toc = _digest_markdown(result.declarations, opts, indent=4, depth=1)
        if not toc:
            lines[-1] += "  # empty"
            return lines
        lines.extend(toc)
        return lines

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


def _digest_markdown(
    decls: list[Declaration],
    opts: DigestOptions,
    indent: int,
    depth: int,
) -> list[str]:
    """Render markdown declarations as a hierarchical TOC.

    Respects `opts.max_heading_depth`. Code blocks are shown only when
    `opts.include_fields` is True (they're treated as noise in a TOC by
    default).
    """
    out: list[str] = []
    if depth > opts.max_heading_depth:
        return out
    pad = " " * indent
    for d in decls:
        if d.kind == KIND_HEADING:
            out.append(pad + d.signature + d.lines_suffix())
            out.extend(_digest_markdown(d.children, opts, indent + 2, depth + 1))
        elif d.kind == KIND_CODE_BLOCK and opts.include_fields:
            out.append(pad + d.signature + d.lines_suffix())
    return out


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
    _search_walk(result.declarations, result.source, [], [], parts, matches)
    return matches


def _search_walk(
    decls: list[Declaration],
    src: bytes,
    trail: list[str],
    ancestors: list[Declaration],
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
                    ancestor_signatures=[a.signature for a in ancestors if a.signature],
                )
            )
        if d.children:
            _search_walk(d.children, src, new_trail, ancestors + [d], parts, out)


def _trail_matches(trail: list[str], parts: list[str]) -> bool:
    if len(parts) > len(trail):
        return False
    return trail[-len(parts):] == parts


def find_implementations(
    results: list[ParseResult],
    type_name: str,
    *,
    transitive: bool = True,
) -> list[ImplMatch]:
    """Find all types in the batch that inherit / implement `type_name`.

    Matching is suffix-based on the last (generic-stripped) segment, so
    `Animal` matches `com.example.Animal` and `Animal<T>`.

    `transitive=True` (default) returns direct matches **and** anything
    that reaches the target through an intermediate type — e.g.
    `Puppy → Dog → Animal` includes Puppy with `via=["Dog"]`. Set
    `transitive=False` for direct-only matches.

    Enums are skipped — they can implement interfaces in Java/C# but
    "what extends this enum" is vanishingly rare as a query and polluting
    results with enum matches is usually noise.

    Cycle-safe: a class is visited at most once even if the graph has
    cycles (A extends B, B extends A) or diamond inheritance; the first
    discovered path wins.
    """
    target = _normalize_type_name(type_name)

    # Flatten every candidate type declaration from all files into one
    # list; we'll iterate it multiple times for the BFS.
    all_types: list[tuple[Path, Declaration]] = []
    for r in results:
        _collect_candidate_types(r.declarations, r.path, all_types)

    # Level 0 — direct matches: bases[] contains the target.
    direct: list[ImplMatch] = []
    for path, d in all_types:
        if target in (_normalize_type_name(b) for b in d.bases):
            direct.append(_impl_match(path, d, via=[]))

    if not transitive:
        return direct

    # Level 1+ — BFS outward. `frontier` is the set of "new parents" whose
    # own subclasses should be picked up as transitive matches.
    out: list[ImplMatch] = list(direct)
    seen: set[tuple[str, int]] = {(m.path, m.start_line) for m in direct}
    frontier: list[ImplMatch] = list(direct)
    while frontier:
        next_frontier: list[ImplMatch] = []
        for parent in frontier:
            parent_name = _normalize_type_name(parent.name)
            for path, d in all_types:
                key = (str(path), d.start_line)
                if key in seen:
                    continue
                if parent_name in (_normalize_type_name(b) for b in d.bases):
                    chain = parent.via + [parent.name]
                    m = _impl_match(path, d, via=chain)
                    seen.add(key)
                    out.append(m)
                    next_frontier.append(m)
        frontier = next_frontier
    return out


def _collect_candidate_types(
    decls: list[Declaration],
    path: Path,
    out: list[tuple[Path, Declaration]],
) -> None:
    """Flatten every non-enum TYPE_KIND declaration in the tree into
    `out` paired with its source path. Recurses into nested types."""
    for d in decls:
        if d.kind in TYPE_KINDS and d.kind != KIND_ENUM:
            out.append((path, d))
        if d.children:
            _collect_candidate_types(d.children, path, out)


def _impl_match(path: Path, d: Declaration, *, via: list[str]) -> ImplMatch:
    return ImplMatch(
        path=str(path),
        start_line=d.start_line,
        end_line=d.end_line,
        kind=d.kind,
        name=d.name,
        bases=d.bases,
        via=via,
    )


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
