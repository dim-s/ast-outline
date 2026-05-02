"""TypeScript / JavaScript adapter (handles .ts, .tsx, .js, .jsx, .mjs, .cjs).

Design notes (how JS/TS concepts map to the IR):
- `class_declaration` / `abstract_class_declaration`  → KIND_CLASS
- `interface_declaration`                             → KIND_INTERFACE
- `enum_declaration`                                  → KIND_ENUM
- `type_alias_declaration` (`type Foo = ...`)         → KIND_FIELD
- `function_declaration`                              → KIND_FUNCTION (top-level)
- `method_definition`                                 → KIND_METHOD, or KIND_CTOR for `constructor`
- `lexical_declaration` (`const`/`let`) with arrow /
  function expression on the right                    → KIND_FUNCTION
- `lexical_declaration` with any other RHS            → KIND_FIELD
- `public_field_definition` (class body)              → KIND_FIELD
- `property_signature` (interface body)               → KIND_FIELD
- `method_signature` (interface body)                 → KIND_METHOD
- `enum_assignment` / `property_identifier` (in enum) → KIND_ENUM_MEMBER
- `export_statement`                                  → transparent wrapper;
  unwrap the inner declaration and widen its byte range to include `export`

Visibility:
- `accessibility_modifier` values: public / protected / private
- `#name` → private (TS 4.3+ true-private)
- Top-level types: "public" (TS has no `internal`)
- Class members without a modifier → "public" (unlike C#)

Docs: preceding `comment` siblings (JSDoc `/** ... */` or `//` lines) are
captured as docs and rendered before the signature (docs_inside=False),
matching TypeScript/JS convention.

Grammars:
- `.tsx` / `.jsx` use the TSX grammar (JSX-aware).
- `.ts` / `.js` / `.mjs` / `.cjs` use the TypeScript grammar (accepts plain
  JS as a subset; may reject angle-bracket type assertions mixed with JSX,
  but those shouldn't appear in non-.tsx files).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import tree_sitter_typescript as tsts
from tree_sitter import Language, Node, Parser

from .base import count_parse_errors
from ..core import (
    KIND_CLASS,
    KIND_CTOR,
    KIND_ENUM,
    KIND_ENUM_MEMBER,
    KIND_FIELD,
    KIND_FUNCTION,
    KIND_INTERFACE,
    KIND_METHOD,
    Declaration,
    ParseResult,
)


_LANG_TS = Language(tsts.language_typescript())
_LANG_TSX = Language(tsts.language_tsx())
_PARSER_TS = Parser(_LANG_TS)
_PARSER_TSX = Parser(_LANG_TSX)

_TSX_EXTS = {".tsx", ".jsx"}


class TypeScriptAdapter:
    language_name = "typescript"
    extensions = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}

    def parse(self, path: Path) -> ParseResult:
        src = path.read_bytes()
        parser = _PARSER_TSX if path.suffix.lower() in _TSX_EXTS else _PARSER_TS
        tree = parser.parse(src)
        decls: list[Declaration] = []
        _walk_module(tree.root_node, src, decls)
        imports: list[str] = []
        _collect_imports(tree.root_node, src, imports)
        return ParseResult(
            path=path,
            language=self.language_name,
            source=src,
            line_count=src.count(b"\n") + 1,
            declarations=decls,
            error_count=count_parse_errors(tree.root_node),
            imports=imports,
        )


# --- Imports --------------------------------------------------------------
#
# TS/JS `import` statements are top-level only (ESM rule). We collect the
# source text of every `import_statement` at module-scope verbatim,
# collapse internal whitespace (multi-line `import { X,\n Y } from ...`
# → one line), and strip the trailing semicolon. Source-true output is
# what any LLM agent already knows how to read; no synthetic format.
#
# Out of scope for `--imports`:
# - `require(...)` calls in .js/.cjs (a runtime function, not an import
#   statement; pattern-matching the LHS = .name and RHS = call form is
#   fragile and noisy)
# - `import('...')` dynamic expressions (runtime, not declarative)
# - `export ... from '...'` re-exports (separate concern, would need a
#   sibling --exports flag)


def _collect_imports(root: Node, src: bytes, out: list[str]) -> None:
    for child in root.named_children:
        if child.type == "import_statement":
            text = _collapse_ws(_text(child, src)).rstrip(";").strip()
            if text:
                out.append(text)


# --- Walk -----------------------------------------------------------------


def _walk_module(root: Node, src: bytes, out: list[Declaration]) -> None:
    for child in root.named_children:
        decl = _node_to_decl(child, src, inside_class=False, inside_interface=False)
        if decl is not None:
            out.append(decl)


def _node_to_decl(
    node: Node,
    src: bytes,
    *,
    inside_class: bool,
    inside_interface: bool,
) -> Optional[Declaration]:
    kind = node.type

    # `export ...` / `export default ...` — unwrap, then widen byte range
    # to include the `export` keyword so `show` prints it too.
    if kind in ("export_statement",):
        # TS puts class-level decorators as siblings of `class_declaration`
        # inside `export_statement`, not as children of the class itself.
        # Collect them here so we can hand them to the inner decl.
        export_decorators = [
            _collapse_ws(_text(c, src)) for c in node.named_children if c.type == "decorator"
        ]
        for inner in node.named_children:
            if inner.type in _HANDLED_TOP_LEVEL:
                decl = _node_to_decl(
                    inner,
                    src,
                    inside_class=inside_class,
                    inside_interface=inside_interface,
                )
                if decl is not None:
                    decl.start_byte = node.start_byte
                    decl.start_line = node.start_point[0] + 1
                    decl.doc_start_byte = _leading_doc_start_byte(node, src) or node.start_byte
                    decl.docs = _collect_docs(node, src)
                    if export_decorators:
                        decl.attrs = export_decorators + decl.attrs
                    # Recompute the signature from the widened range so the
                    # `export` / `export default` prefix shows up.
                    decl.signature = _signature_from_range(node, src, inner)
                    return decl
        return None

    if kind == "class_declaration" or kind == "abstract_class_declaration":
        return _class_to_decl(node, src)
    if kind == "interface_declaration":
        return _interface_to_decl(node, src)
    if kind == "enum_declaration":
        return _enum_to_decl(node, src)
    if kind == "type_alias_declaration":
        return _type_alias_to_decl(node, src)
    if kind == "function_declaration":
        return _function_to_decl(node, src, inside_class=False)

    # `const foo = ...` / `let foo = ...` — one or more variable_declarators.
    # If the RHS is an arrow / function expression, treat as KIND_FUNCTION;
    # otherwise, KIND_FIELD.
    if kind in ("lexical_declaration", "variable_declaration"):
        return _lexical_to_decl(node, src)

    # Inside a class body
    if kind == "method_definition":
        return _method_to_decl(node, src)
    if kind == "public_field_definition":
        return _class_field_to_decl(node, src)

    # Inside an interface body
    if kind == "property_signature":
        return _property_signature_to_decl(node, src)
    if kind in ("method_signature", "construct_signature", "call_signature"):
        return _method_signature_to_decl(node, src)
    if kind == "index_signature":
        return None  # skip — rarely useful in an outline

    # Enum members
    if kind in ("property_identifier", "enum_assignment"):
        return _enum_member_to_decl(node, src)

    return None


# Top-level nodes we unwrap from `export_statement`
_HANDLED_TOP_LEVEL = {
    "class_declaration",
    "abstract_class_declaration",
    "interface_declaration",
    "enum_declaration",
    "type_alias_declaration",
    "function_declaration",
    "lexical_declaration",
    "variable_declaration",
}


# --- Type / class / interface / enum --------------------------------------


def _class_to_decl(node: Node, src: bytes) -> Declaration:
    name = _field_text(node, "name", src) or "?"
    bases = _class_bases(node, src)
    attrs = _decorators(node, src)
    docs = _collect_docs(node, src)
    visibility = "public"

    signature = _class_signature(node, src)

    body = node.child_by_field_name("body")
    children: list[Declaration] = []
    if body is not None:
        for c in body.named_children:
            d = _node_to_decl(c, src, inside_class=True, inside_interface=False)
            if d is not None:
                children.append(d)

    return Declaration(
        kind=KIND_CLASS,
        name=name,
        signature=signature,
        bases=bases,
        attrs=attrs,
        docs=docs,
        visibility=visibility,
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        start_byte=node.start_byte,
        end_byte=node.end_byte,
        doc_start_byte=_leading_doc_start_byte(node, src) or node.start_byte,
        children=children,
    )


def _interface_to_decl(node: Node, src: bytes) -> Declaration:
    name = _field_text(node, "name", src) or "?"
    bases = _interface_bases(node, src)
    docs = _collect_docs(node, src)
    body = node.child_by_field_name("body")
    children: list[Declaration] = []
    if body is not None:
        for c in body.named_children:
            d = _node_to_decl(c, src, inside_class=False, inside_interface=True)
            if d is not None:
                children.append(d)

    return Declaration(
        kind=KIND_INTERFACE,
        name=name,
        signature=_head_text(node, src, body),
        bases=bases,
        docs=docs,
        visibility="public",
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        start_byte=node.start_byte,
        end_byte=node.end_byte,
        doc_start_byte=_leading_doc_start_byte(node, src) or node.start_byte,
        children=children,
    )


def _enum_to_decl(node: Node, src: bytes) -> Declaration:
    name = _field_text(node, "name", src) or "?"
    docs = _collect_docs(node, src)
    body = node.child_by_field_name("body")
    children: list[Declaration] = []
    if body is not None:
        for c in body.named_children:
            d = _node_to_decl(c, src, inside_class=False, inside_interface=False)
            if d is not None:
                children.append(d)
    return Declaration(
        kind=KIND_ENUM,
        name=name,
        signature=_head_text(node, src, body),
        docs=docs,
        visibility="public",
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        start_byte=node.start_byte,
        end_byte=node.end_byte,
        doc_start_byte=_leading_doc_start_byte(node, src) or node.start_byte,
        children=children,
    )


def _enum_member_to_decl(node: Node, src: bytes) -> Optional[Declaration]:
    # enum_assignment wraps `Foo = 1`; property_identifier is the bare `Foo`
    if node.type == "enum_assignment":
        name_node = node.child_by_field_name("name") or (
            node.named_children[0] if node.named_children else None
        )
        name = _text(name_node, src) if name_node is not None else None
    else:  # property_identifier
        name = _text(node, src)
    if not name:
        return None
    return Declaration(
        kind=KIND_ENUM_MEMBER,
        name=name,
        signature=_collapse_ws(_text(node, src)),
        visibility="public",
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        start_byte=node.start_byte,
        end_byte=node.end_byte,
    )


def _type_alias_to_decl(node: Node, src: bytes) -> Declaration:
    name = _field_text(node, "name", src) or "?"
    sig = _collapse_ws(_text(node, src)).rstrip(";")
    return Declaration(
        kind=KIND_FIELD,  # no dedicated kind for type aliases; field is close enough
        name=name,
        signature=sig,
        docs=_collect_docs(node, src),
        visibility="public",
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        start_byte=node.start_byte,
        end_byte=node.end_byte,
        doc_start_byte=_leading_doc_start_byte(node, src) or node.start_byte,
    )


# --- Functions ------------------------------------------------------------


def _function_to_decl(node: Node, src: bytes, *, inside_class: bool) -> Declaration:
    name = _field_text(node, "name", src) or "?"
    sig = _function_signature(node, src)
    docs = _collect_docs(node, src)

    return Declaration(
        kind=KIND_METHOD if inside_class else KIND_FUNCTION,
        name=name,
        signature=sig,
        docs=docs,
        visibility=_visibility_for_name(name),
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        start_byte=node.start_byte,
        end_byte=node.end_byte,
        doc_start_byte=_leading_doc_start_byte(node, src) or node.start_byte,
    )


def _method_to_decl(node: Node, src: bytes) -> Optional[Declaration]:
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return None
    name = _text(name_node, src)
    kind = KIND_CTOR if name == "constructor" else KIND_METHOD
    sig = _function_signature(node, src)
    docs = _collect_docs(node, src)
    # TS class members default to `public` when no modifier is given
    # (opposite of C#).
    visibility = (
        _visibility_from_modifiers(node, src)
        or _visibility_for_name(name)
        or "public"
    )
    attrs = _decorators(node, src)
    return Declaration(
        kind=kind,
        name=name,
        signature=sig,
        attrs=attrs,
        docs=docs,
        visibility=visibility,
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        start_byte=node.start_byte,
        end_byte=node.end_byte,
        doc_start_byte=_leading_doc_start_byte(node, src) or node.start_byte,
    )


def _method_signature_to_decl(node: Node, src: bytes) -> Optional[Declaration]:
    """Interface method signature (no body)."""
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return None
    name = _text(name_node, src)
    sig = _collapse_ws(_text(node, src)).rstrip(";")
    return Declaration(
        kind=KIND_METHOD,
        name=name,
        signature=sig,
        docs=_collect_docs(node, src),
        visibility="public",
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        start_byte=node.start_byte,
        end_byte=node.end_byte,
        doc_start_byte=_leading_doc_start_byte(node, src) or node.start_byte,
    )


# --- Fields / properties --------------------------------------------------


def _class_field_to_decl(node: Node, src: bytes) -> Optional[Declaration]:
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return None
    name = _text(name_node, src)
    sig = _field_signature_text(node, src)
    visibility = (
        _visibility_from_modifiers(node, src)
        or _visibility_for_name(name)
        or "public"
    )
    return Declaration(
        kind=KIND_FIELD,
        name=name,
        signature=sig,
        docs=_collect_docs(node, src),
        attrs=_decorators(node, src),
        visibility=visibility,
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        start_byte=node.start_byte,
        end_byte=node.end_byte,
        doc_start_byte=_leading_doc_start_byte(node, src) or node.start_byte,
    )


def _property_signature_to_decl(node: Node, src: bytes) -> Optional[Declaration]:
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return None
    name = _text(name_node, src)
    sig = _collapse_ws(_text(node, src)).rstrip(";,")
    return Declaration(
        kind=KIND_FIELD,
        name=name,
        signature=sig,
        docs=_collect_docs(node, src),
        visibility="public",
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        start_byte=node.start_byte,
        end_byte=node.end_byte,
    )


# --- Lexical declarations -------------------------------------------------


def _lexical_to_decl(node: Node, src: bytes) -> Optional[Declaration]:
    """`const foo = ...` / `let foo = ...`.

    If the RHS is an arrow / function expression → KIND_FUNCTION.
    Otherwise → KIND_FIELD. Only the first variable_declarator is
    promoted to a declaration (the common case); multi-declarator
    assignments like `const a = 1, b = 2` still pick up `a`.
    """
    declarators = [c for c in node.named_children if c.type == "variable_declarator"]
    if not declarators:
        return None
    d = declarators[0]
    name_node = d.child_by_field_name("name")
    if name_node is None or name_node.type != "identifier":
        return None
    name = _text(name_node, src)
    value = d.child_by_field_name("value")
    docs = _collect_docs(node, src)

    if value is not None and value.type in ("arrow_function", "function_expression", "function"):
        sig = _arrow_signature(node, d, value, src)
        return Declaration(
            kind=KIND_FUNCTION,
            name=name,
            signature=sig,
            docs=docs,
            visibility=_visibility_for_name(name),
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            start_byte=node.start_byte,
            end_byte=node.end_byte,
            doc_start_byte=_leading_doc_start_byte(node, src) or node.start_byte,
        )

    # Plain field
    sig = _collapse_ws(_text(node, src)).rstrip(";")
    if len(sig) > 140:
        sig = sig[:137] + "..."
    return Declaration(
        kind=KIND_FIELD,
        name=name,
        signature=sig,
        docs=docs,
        visibility=_visibility_for_name(name),
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        start_byte=node.start_byte,
        end_byte=node.end_byte,
        doc_start_byte=_leading_doc_start_byte(node, src) or node.start_byte,
    )


# --- Signature extraction -------------------------------------------------


def _function_signature(node: Node, src: bytes) -> str:
    """Text up to (but not including) the function body block."""
    body = node.child_by_field_name("body")
    end = body.start_byte if body is not None else node.end_byte
    text = src[node.start_byte:end].decode("utf8", errors="replace")
    text = _strip_leading_decorators(text)
    return _collapse_ws(text).rstrip(" {;").rstrip()


def _arrow_signature(lex_node: Node, declarator: Node, value: Node, src: bytes) -> str:
    """Signature for `const foo = (x): T => { ... }`.

    We emit the prefix (`const foo = ...`) up to the arrow body, so the
    signature reads naturally and the reader sees the name + parameters.
    """
    # Body of the arrow expression — slice everything before it.
    body = value.child_by_field_name("body")
    end = body.start_byte if body is not None else value.end_byte
    text = src[lex_node.start_byte:end].decode("utf8", errors="replace")
    text = _collapse_ws(text).rstrip(" {").rstrip()
    return text


def _field_signature_text(node: Node, src: bytes) -> str:
    """Class field signature — include type annotation, drop `= defaultValue`."""
    text = _text(node, src)
    # Cut at ` = ` to drop default-value assignment
    eq = text.find(" = ")
    if eq > 0:
        text = text[:eq]
    return _collapse_ws(text).rstrip(";")


def _class_signature(node: Node, src: bytes) -> str:
    body = node.child_by_field_name("body")
    end = body.start_byte if body is not None else node.end_byte
    text = src[node.start_byte:end].decode("utf8", errors="replace")
    text = _strip_leading_decorators(text)
    return _collapse_ws(text).rstrip(" {").rstrip()


def _head_text(node: Node, src: bytes, body: Optional[Node]) -> str:
    end = body.start_byte if body is not None else node.end_byte
    text = src[node.start_byte:end].decode("utf8", errors="replace")
    return _collapse_ws(text).rstrip(" {").rstrip()


def _strip_leading_decorators(text: str) -> str:
    s = text.lstrip()
    while s.startswith("@"):
        # Drop to end of this decorator line or until the next non-whitespace
        # line that doesn't start with @ — but the signature slice only has
        # one decorator line at most since decorators end in newlines.
        nl = s.find("\n")
        if nl == -1:
            break
        s = s[nl + 1:].lstrip()
    return s


# --- Bases / heritage ----------------------------------------------------


def _class_bases(node: Node, src: bytes) -> list[str]:
    """Collect both `extends X` and `implements Y, Z` into a flat bases list."""
    out: list[str] = []
    for child in node.children:
        if child.type == "class_heritage":
            for h in child.named_children:
                # extends_clause / implements_clause
                for inner in h.named_children:
                    t = _collapse_ws(_text(inner, src)).rstrip(",")
                    if t:
                        out.append(t)
    return out


def _interface_bases(node: Node, src: bytes) -> list[str]:
    out: list[str] = []
    for child in node.children:
        if child.type == "extends_type_clause":
            for inner in child.named_children:
                t = _collapse_ws(_text(inner, src)).rstrip(",")
                if t:
                    out.append(t)
    return out


# --- Modifiers / decorators / docs ---------------------------------------


def _decorators(node: Node, src: bytes) -> list[str]:
    """Collect decorator children of `node` AND decorator siblings that
    immediately precede it (tree-sitter-typescript places class-body
    decorators as siblings of the method, not children)."""
    out: list[str] = [
        _collapse_ws(_text(c, src)) for c in node.children if c.type == "decorator"
    ]
    preceding: list[str] = []
    sib = node.prev_sibling
    while sib is not None and sib.type == "decorator":
        preceding.append(_collapse_ws(_text(sib, src)))
        sib = sib.prev_sibling
    preceding.reverse()
    return preceding + out


def _signature_from_range(outer: Node, src: bytes, inner: Node) -> str:
    """Signature text when `inner` is a declaration nested inside `outer`
    (typically `export_statement` wrapping a class/function). Captures the
    full prefix (`export`, `export default`) up to the body of `inner`.
    """
    body = inner.child_by_field_name("body")
    end = body.start_byte if body is not None else inner.end_byte
    text = src[outer.start_byte:end].decode("utf8", errors="replace")
    text = _strip_leading_decorators(text)
    return _collapse_ws(text).rstrip(" {;").rstrip()


def _visibility_from_modifiers(node: Node, src: bytes) -> Optional[str]:
    """Look for an accessibility_modifier child (public/protected/private)."""
    for c in node.children:
        if c.type == "accessibility_modifier":
            t = _text(c, src).strip()
            if t in ("public", "protected", "private"):
                return t
    # TS 4.3+ private: `#name` prefix on the name itself
    name_node = node.child_by_field_name("name")
    if name_node is not None and name_node.type in ("private_property_identifier",):
        return "private"
    return None


def _visibility_for_name(name: str) -> str:
    # JS convention: a leading underscore signals "intended private".
    # Dunder names are library/framework-specific and aren't universally
    # public, so we don't treat them specially here.
    if name.startswith("_"):
        return "private"
    return ""


def _collect_docs(node: Node, src: bytes) -> list[str]:
    """Collect contiguous preceding comment siblings as docs."""
    docs: list[str] = []
    sib = node.prev_sibling
    while sib is not None and sib.type == "comment":
        docs.append(_text(sib, src))
        sib = sib.prev_sibling
    docs.reverse()
    return docs


def _leading_doc_start_byte(node: Node, src: bytes) -> Optional[int]:
    first: Optional[Node] = None
    sib = node.prev_sibling
    while sib is not None and sib.type == "comment":
        first = sib
        sib = sib.prev_sibling
    return first.start_byte if first is not None else None


# --- Misc helpers --------------------------------------------------------


def _collapse_ws(text: str) -> str:
    return " ".join(text.split())


def _text(node: Node, src: bytes) -> str:
    return src[node.start_byte:node.end_byte].decode("utf8", errors="replace")


def _field_text(node: Node, field_name: str, src: bytes) -> Optional[str]:
    c = node.child_by_field_name(field_name)
    return _text(c, src) if c is not None else None
