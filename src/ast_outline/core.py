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

# Data/config document kinds — used by the YAML adapter. One canonical
# kind covers every YAML construct (mapping key, sequence item, scalar
# leaf): the renderer differentiates by whether the node has children
# and what shape the signature has, not by sub-kinds. This keeps the
# IR uniform — same way `KIND_HEADING` covers every markdown heading
# regardless of level.
KIND_YAML_KEY = "yaml_key"
KIND_YAML_DOC = "yaml_doc"

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
    # Native source-language keyword for the declaration's kind, when it
    # diverges from the canonical `kind`. Empty string → digest falls
    # back to `kind`. Used by `render_digest` to print the source-true
    # keyword (e.g. Rust `trait` / Java `@interface` / Scala `trait`)
    # while the IR keeps a unified canonical kind for search.
    native_kind: str = ""
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
    """Build the `# path (N lines, ~N tokens, ...)` header for one file.

    `prefix` is the leading marker + path (e.g. `"# /abs/path.py"` for
    outline or `"  name.py"` for digest). Appended in parentheses:
    line count, an approximate token count (so the agent can size up
    the file before deciding between Read / outline / show), and any
    non-zero category counters appropriate for the language family —
    types/methods/fields for code, headings/code blocks for markdown.
    Zero-valued categories are skipped so a trivial file reads
    `(42 lines, ~310 tokens)` not `(42 lines, ~310 tokens, 0 types, 0 methods)`.

    Token estimate is ``len(source_bytes) // 4`` — a coarse BPE-style
    approximation, deliberately not exact (no tiktoken dep). The ``~``
    prefix and the rule-of-thumb in the digest legend make it explicit
    this is an order-of-magnitude figure.
    """
    counts = _collect_counts(result.declarations)
    parts = [
        f"{result.line_count} lines",
        f"~{_estimate_tokens(result.source):,} tokens",
    ]
    if result.language == "markdown":
        order = [("headings", "headings"), ("code_blocks", "code blocks")]
    elif result.language == "yaml":
        # YAML files report their document count when multi-doc — for
        # k8s manifests this is the primary "what's in here" signal.
        # Single-doc files skip the counter (`1 doc` would be noise).
        n_docs = sum(1 for d in result.declarations if d.kind == KIND_YAML_DOC)
        if n_docs > 1:
            parts.append(f"{n_docs} docs")
        order = []
    else:
        order = [("types", "types"), ("methods", "methods"), ("fields", "fields")]
    for key, label in order:
        n = counts.get(key, 0)
        if n > 0:
            parts.append(f"{n} {label}")

    # Format-detect annotation — appended after the closing paren with
    # an em-dash so the eye visually separates the "what is this file"
    # signal from the size/counter parens. Only fires for single-doc
    # YAML where a clear format is detectable; multi-doc shows per-doc
    # annotations in each `--- doc N of M` separator line instead.
    suffix = ""
    if result.language == "yaml":
        suffix = _yaml_format_suffix(result.declarations)
    return f"{prefix} ({', '.join(parts)}){suffix}"


def _yaml_format_suffix(decls: list[Declaration]) -> str:
    """Generate the `— OpenAPI 3.0.0, 23 paths` style annotation. Empty
    string when no specific format is detected, or when the file is
    multi-document (per-doc annotations live in the separator lines)."""
    n_docs = sum(1 for d in decls if d.kind == KIND_YAML_DOC)
    if n_docs > 1:
        return ""
    # Single-doc — detect on the top-level decls directly
    from .adapters.yaml import _format_for_doc
    hint = _format_for_doc(decls)
    if hint:
        return f" — {hint}"
    return ""


def _estimate_tokens(source: bytes) -> int:
    """Approximate the BPE token count of `source`.

    Counts **characters**, not bytes — for Cyrillic / CJK content one
    byte ≠ one char in UTF-8, and a byte-based estimate would inflate
    the count by 30-50% for those files. ``chars // 4`` matches Claude
    and GPT BPE tokenizers within ±15-20% on real code/YAML/markdown,
    which is more than enough for the size-hint heuristic.
    """
    return len(source.decode("utf-8", errors="replace")) // 4


# --- Size label ----------------------------------------------------------
#
# Categorical descriptors of file size, displayed next to each filename
# in `digest`. Deliberately **descriptive**, not prescriptive — the
# label tells the agent how big the file is, the agent picks Read /
# outline / show based on the task at hand. A directive-style label
# (`[Read]` / `[outline]`) would override the agent's judgment in cases
# where the file IS small but the agent still wants the structural
# overview, or vice versa. Information beats instruction.
#
# The thresholds are the only "magic numbers" in the project, calibrated
# against typical code/config sizes where outline-vs-Read trade-offs
# meaningfully shift.

_SIZE_LABEL_MEDIUM_FLOOR = 500    # below this — outline shrinks little vs full read
_SIZE_LABEL_LARGE_FLOOR = 5000    # above this — outline alone may be long; show helps


def _size_label(token_count: int) -> str:
    """One of three descriptive size labels.

    - ``[tiny]`` — under ~500 tokens. Outline returns roughly the same
      content as Read, with light structural overlay.
    - ``[medium]`` — 500-5000 tokens. Outline meaningfully compresses
      (5-10× typical) while staying compact enough to consume whole.
    - ``[large]`` — 5000+ tokens. Outline output itself can run long;
      ``show`` for specific sections is the surgical follow-up.

    The agent reads the label, weighs its task, and decides. We don't
    tell it what to do.
    """
    if token_count < _SIZE_LABEL_MEDIUM_FLOOR:
        return "[tiny]"
    if token_count < _SIZE_LABEL_LARGE_FLOOR:
        return "[medium]"
    return "[large]"


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
    suffix = decl.lines_suffix() if opts.include_line_numbers else ""

    # YAML multi-document separator. The doc itself is a logical group
    # but visually it's a flat horizontal slice — its children render
    # at the SAME indent level as the separator line, not indented one
    # level deeper. This keeps the YAML body looking like the actual
    # YAML it represents, instead of double-indenting everything inside
    # a multi-doc file.
    if decl.kind == KIND_YAML_DOC:
        out.append(prefix + decl.signature + suffix)
        for child in decl.children:
            _render_decl(child, opts, indent, out)
        out.append("")  # blank line between docs for visual separation
        return

    # Docs BEFORE signature (C# /// XML-doc style)
    if opts.include_xml_doc and decl.docs and not decl.docs_inside:
        for d in _clip_docs(decl.docs, opts.max_doc_lines):
            out.append(prefix + d)

    # Attributes inlined
    attrs_prefix = ""
    if opts.include_attributes and decl.attrs:
        attrs_prefix = " ".join(decl.attrs) + " "

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

    # Blank line after top-level types and namespaces for readability.
    # YAML keys are intentionally excluded — top-level YAML keys
    # (`apiVersion`, `kind`, `metadata`, `spec`) sit on adjacent lines
    # in the source file, and inserting blanks between them would make
    # the outline look unlike the YAML it represents.
    if decl.kind == KIND_YAML_KEY:
        return
    if indent == 0 or decl.kind in TYPE_KINDS or decl.kind == KIND_NAMESPACE:
        out.append("")


def _clip_docs(docs: list[str], limit: int) -> list[str]:
    if len(docs) <= limit:
        return docs
    return docs[:limit] + ["..."]


# --- Digest ---------------------------------------------------------------


# One-liner legend prepended to every digest. Keep this single line —
# scannable, fits in a terminal, and survives copy-paste into LLM prompts
# without wrapping. Only documents tokens that aren't plain English; size
# labels (`[tiny]`/`[medium]`/`[large]`) and `[broken]` are
# self-explanatory and stay out of the legend to keep it short.
_DIGEST_LEGEND = (
    "# legend: name()=callable, name [kind]=non-callable, "
    "[N overloads]=N callables share name, L<a>-<b>=line range, "
    ": Base, …=inheritance"
)


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

    # One-line legend at the top so the digest is self-describing for an
    # LLM reading it cold (without `ast-outline prompt` loaded). The
    # tokens cover everything that isn't plain English already
    # (`[tiny]` / `[medium]` / `[large]` / `[broken]` are
    # self-explanatory and don't need a legend entry).
    lines: list[str] = [_DIGEST_LEGEND]
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
    # Inject the descriptive size label between the filename and the
    # parenthesised counters: `  name.py [medium] (95 lines, ...)`.
    # The bracket lands right after the filename so the agent reads
    # the size class first, then the precise counters second.
    #
    # If the parse hit ERROR/MISSING nodes, append a `[broken]` marker —
    # plain English, instantly recognisable, no legend lookup needed.
    # Agent scanning digest sees `name.py [tiny] [broken]` and knows
    # the file's syntax is malformed somewhere, so the outline below
    # may be incomplete. The full `# WARNING:` line still appears
    # beneath the filename for those who want the count of errors.
    label = _size_label(_estimate_tokens(result.source))
    integrity = " [broken]" if result.error_count > 0 else ""
    prefix = f"  {result.path.name} {label}{integrity}"
    lines = [_format_file_header(prefix, result)]
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

    # YAML files digest as either:
    # - top-level keys (single-doc files: `+apiVersion +kind +metadata +spec`)
    # - per-doc separator lines (multi-doc: each `--- doc N of M — ...`)
    # No `[yaml_key]` / `[yaml_doc]` annotations — the tag would be
    # uniform-and-noisy for every entry.
    if result.language == "yaml":
        body = _digest_yaml(result.declarations, opts)
        if not body:
            lines[-1] += "  # empty"
            return lines
        lines.extend(body)
        return lines

    types = _flatten_types(result.declarations)
    free_functions = _flatten_free_functions(result.declarations, opts)

    if not types and not free_functions:
        lines[-1] += "  # no declarations"
        return lines

    # Visual grouping rule: insert a blank line AFTER a type whose body
    # rendered at least one member row. Empty types (no body lines)
    # stack tightly so digest stays compact for declaration-heavy files.
    # The blank serves as a paragraph break between a "type + its
    # members" block and whatever comes next, mirroring how prose uses
    # blank lines to separate paragraphs. The trailing blank after the
    # last type is removed by `render_digest`'s final `rstrip`.
    for t in types:
        # Use the source-language native keyword when the adapter set
        # one (e.g. Rust `trait` for KIND_INTERFACE), otherwise fall
        # back to the canonical kind. This lets digest read truthfully
        # against the source while the IR keeps a unified kind for
        # search.
        keyword = t.native_kind or t.kind
        header = f"    {keyword} {t.name}"
        if t.bases:
            header += " : " + ", ".join(t.bases)
        header += t.lines_suffix()
        lines.append(header)
        members = _digest_members(t, opts)
        if members:
            collapsed = _collapse_overloads(members)
            shown = collapsed[: opts.max_members_per_type]
            tokens = [_member_token(m, count) for m, count in shown]
            lines.extend(_wrap_tokens(tokens, width=100, indent="      "))
            if len(collapsed) > len(shown):
                lines.append(f"      ... ({len(collapsed) - len(shown)} more)")
            lines.append("")  # paragraph break — types with bodies own their block

    # Module-level functions / fields (common in Python)
    if free_functions:
        collapsed = _collapse_overloads(free_functions)
        shown = collapsed[: opts.max_members_per_type]
        tokens = [_member_token(f, count) for f, count in shown]
        lines.extend(_wrap_tokens(tokens, width=100, indent="    "))
    return lines


def _collapse_overloads(decls: list[Declaration]) -> list[tuple[Declaration, int]]:
    """Group consecutive same-name callables under a single representative.

    Returns a list of `(decl, count)` pairs in original order, where
    `count` is the number of callables sharing the name (1 = no
    overloads). Non-callables always pass through with `count=1` and
    are NOT merged even if names happen to repeat — same name across
    different non-callable kinds (e.g. a property and a field) is rare
    and would be a meaningful source-level distinction worth preserving.

    The first occurrence "wins" — its source position represents the
    group, so the digest still points to one concrete declaration the
    agent can `show`. Order across groups is the order in which the
    first occurrence appeared.
    """
    out: list[tuple[Declaration, int]] = []
    index_by_name: dict[str, int] = {}
    for d in decls:
        if d.kind in CALLABLE_KINDS and d.name in index_by_name:
            i = index_by_name[d.name]
            rep, count = out[i]
            out[i] = (rep, count + 1)
            continue
        if d.kind in CALLABLE_KINDS:
            index_by_name[d.name] = len(out)
        out.append((d, 1))
    return out


def _member_token(d: Declaration, count: int) -> str:
    """Render a single digest token for a member or free declaration.

    - Callable kinds get a `()` suffix — universally understood as
      "this is a function" in programming-doc convention, no legend
      needed for an LLM reading cold.
    - When `count > 1` the token carries an `[N overloads]` annotation
      so the agent knows the name resolves to multiple callables.
    - Non-callable kinds keep their `[kind]` tag so the type stays
      inferable without any other signal.

    No leading `+` marker — earlier digest revisions used `+name` as a
    member tag, but that visually collides with diff syntax and adds no
    semantic information beyond what `()` / `[kind]` already convey.
    """
    if d.kind in CALLABLE_KINDS:
        if count > 1:
            return f"{d.name}() [{count} overloads]"
        return f"{d.name}()"
    return f"{d.name} [{d.kind}]"


def _digest_yaml(decls: list[Declaration], opts: DigestOptions) -> list[str]:
    """Render YAML declarations for the digest body.

    Two shapes:
    - Multi-document files: emit each ``KIND_YAML_DOC`` separator line
      verbatim with its line range, so the agent sees `--- doc 1 of 3
      — ConfigMap prod/api-config  L1-8` for every doc in the file.
    - Single-document files: emit top-level keys as flat tokens
      (``+apiVersion  +kind  +metadata  +spec``). No ``[yaml_key]``
      annotation — every entry would carry it, pure noise.
    """
    if any(d.kind == KIND_YAML_DOC for d in decls):
        out: list[str] = []
        for d in decls:
            if d.kind == KIND_YAML_DOC:
                out.append("    " + d.signature + d.lines_suffix())
        return out
    tokens = [f"+{d.name}" for d in decls if d.kind == KIND_YAML_KEY]
    if not tokens:
        return []
    return _wrap_tokens(tokens, width=100, indent="    ")


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
                native_kind=d.native_kind,
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
    """Wrap a flat list of digest tokens into width-bounded lines.

    Uses `", "` (comma-space) as the inter-token separator — universally
    understood as a list separator across programming docs, English
    prose, and CSV. Stronger LLM signal than double-space: BPE
    tokenisers split commas into discrete tokens, and natural-language
    training data overwhelmingly uses commas to delimit list items, so
    attention reliably treats each piece as a separate element.

    Identifier tokens never contain commas (kind tags are single words
    like `property` / `field`), so the separator is unambiguous.
    """
    if not tokens:
        return []
    out: list[str] = []
    cur = indent
    for tok in tokens:
        piece = (", " if cur != indent else "") + tok
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

    Markdown headings get a relaxed contract: case-insensitive **substring**
    containment per dotted part. Heading text routinely carries decoration
    an LLM agent can't be expected to remember verbatim — number prefixes
    (``1.`` ``2.1``), trailing qualifiers (``(февраль 2026)``,
    ``(Уверенность: 70%)``), formatting marks. So ``"ТЕКУЩИЙ АНАЛИЗ"``
    matches ``"1. ТЕКУЩИЙ АНАЛИЗ (февраль 2026)"`` for headings, even
    though it wouldn't for a code symbol.
    """
    parts = _split_query(symbol)
    matches: list[SymbolMatch] = []
    _search_walk(result.declarations, result.source, [], [], parts, matches)
    return matches


import re as _re

# Regex tokenizer for dotted/bracketed queries.
# Matches either a `[…]` bracketed segment (sequence-index path
# component, used by YAML) or a stretch of chars that are neither
# a dot nor an opening bracket.
# Examples:
#   "Foo.Bar"               → ["Foo", "Bar"]
#   "containers[0].image"   → ["containers", "[0]", "image"]
#   "matrix[2][3]"          → ["matrix", "[2]", "[3]"]
#   "[0].image"             → ["[0]", "image"]
_QUERY_TOKEN_RE = _re.compile(r"\[[^\]]*\]|[^.\[]+")


def _split_query(symbol: str) -> list[str]:
    """Tokenise a dotted (and possibly bracketed) query into trail parts.

    Code symbols use plain dots: ``Foo.Bar.method`` → ``["Foo", "Bar", "method"]``.

    YAML / data-shaped queries can include JSONPath-style sequence
    indices: ``spec.containers[0].image`` →
    ``["spec", "containers", "[0]", "image"]``. The bracket part lands
    as its OWN trail entry (matching how the YAML adapter emits
    sequence items as ``Declaration(name="[0]")``), so suffix-matching
    works without special cases in the walker."""
    return _QUERY_TOKEN_RE.findall(symbol)


def _join_trail(trail: list[str]) -> str:
    """Build a ``qualified_name`` from a trail of declaration names.

    Bracketed parts (``[0]``, ``[12]``) attach to the previous part
    WITHOUT a dot separator, so a YAML sequence path renders as
    ``containers[0].image`` (JSONPath-natural) instead of
    ``containers.[0].image`` (clunky, would also need special parsing
    on the agent side)."""
    if not trail:
        return ""
    out = trail[0]
    for part in trail[1:]:
        if part.startswith("[") and part.endswith("]"):
            out += part
        else:
            out += "." + part
    return out


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
        # Markdown headings opt in to substring matching — see find_symbols
        # docstring. Other kinds keep strict suffix-equality semantics so
        # code-symbol lookups stay precise.
        substring = d.kind == KIND_HEADING
        if d.name and _trail_matches(new_trail, parts, substring=substring):
            # Include doc block in source slice if present
            start = d.doc_start_byte or d.start_byte
            end = d.end_byte
            out.append(
                SymbolMatch(
                    qualified_name=_join_trail(new_trail),
                    kind=d.kind,
                    start_line=d.start_line,
                    end_line=d.end_line,
                    source=src[start:end].decode("utf8", errors="replace"),
                    ancestor_signatures=[a.signature for a in ancestors if a.signature],
                )
            )
        if d.children:
            _search_walk(d.children, src, new_trail, ancestors + [d], parts, out)


def _trail_matches(trail: list[str], parts: list[str], *, substring: bool = False) -> bool:
    if len(parts) > len(trail):
        return False
    tail = trail[-len(parts):]
    if substring:
        # Case-insensitive containment per element. ``casefold`` (not
        # ``lower``) so non-ASCII titles match correctly — German ß,
        # Turkish dotted/dotless I, etc.
        return all(p.casefold() in t.casefold() for p, t in zip(parts, tail))
    return tail == parts


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
