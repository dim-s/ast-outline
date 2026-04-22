"""Python adapter — parses .py files via tree-sitter-python into Declaration IR.

Design notes (how Python concepts map to the IR):
- `class_definition`          → KIND_CLASS
- `function_definition`       → KIND_METHOD (when inside a class) or KIND_FUNCTION (top-level)
- `decorated_definition`      → wraps the above, attrs collected from decorators
- `@property` decorator       → KIND_PROPERTY (nicer digest output)
- `__init__`                  → KIND_CTOR
- Docstring (first string expr in body) → docs[]
- Module-level assignments with type hints → KIND_FIELD
- Class-body assignments → KIND_FIELD
- Visibility heuristic: name starts with `_` and not `__dunder__` → private
- Inheritance: `class Foo(Bar, Baz):` — parenthesized args
- No namespaces in Python (module = file)
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from tree_sitter import Language, Node, Parser
import tree_sitter_python as tspy

from ..core import (
    KIND_CLASS,
    KIND_CTOR,
    KIND_FIELD,
    KIND_FUNCTION,
    KIND_METHOD,
    KIND_PROPERTY,
    Declaration,
    ParseResult,
)


_LANGUAGE = Language(tspy.language())
_PARSER = Parser(_LANGUAGE)


class PythonAdapter:
    language_name = "python"
    extensions = {".py", ".pyi"}

    def parse(self, path: Path) -> ParseResult:
        src = path.read_bytes()
        tree = _PARSER.parse(src)
        decls: list[Declaration] = []
        _walk_module(tree.root_node, src, decls)
        return ParseResult(
            path=path,
            language=self.language_name,
            source=src,
            line_count=src.count(b"\n") + 1,
            declarations=decls,
        )


# --- Walk -----------------------------------------------------------------


def _walk_module(root: Node, src: bytes, out: list[Declaration]) -> None:
    for child in root.named_children:
        decl = _node_to_decl(child, src, inside_class=False)
        if decl is not None:
            out.append(decl)


def _walk_class_body(block: Node, src: bytes) -> list[Declaration]:
    children: list[Declaration] = []
    for c in block.named_children:
        decl = _node_to_decl(c, src, inside_class=True)
        if decl is not None:
            children.append(decl)
    return children


def _node_to_decl(node: Node, src: bytes, *, inside_class: bool) -> Optional[Declaration]:
    # Decorators wrap the actual definition
    if node.type == "decorated_definition":
        decorators = [_collapse_ws(_text(c, src)) for c in node.children if c.type == "decorator"]
        definition = node.child_by_field_name("definition")
        if definition is None:
            return None
        decl = _node_to_decl(definition, src, inside_class=inside_class)
        if decl is None:
            return None
        # Record byte range INCLUDING decorators (so `show` prints them too)
        decl.attrs = decorators + decl.attrs
        decl.start_line = node.start_point[0] + 1
        decl.start_byte = node.start_byte
        decl.doc_start_byte = min(decl.doc_start_byte or node.start_byte, node.start_byte)
        # @property transforms a method into a "property" for nicer digests
        if inside_class and decl.kind == KIND_METHOD and any(
            d == "@property" or d.startswith("@property ") or d.startswith("@property\n")
            for d in decorators
        ):
            decl.kind = KIND_PROPERTY
        return decl

    if node.type == "class_definition":
        return _class_to_decl(node, src)

    if node.type == "function_definition":
        return _function_to_decl(node, src, inside_class=inside_class)

    if node.type == "expression_statement":
        # Could be a docstring — handled by the parent. Skip here.
        return None

    if node.type == "assignment":
        # Module or class-body field declaration
        return _assignment_to_decl(node, src)

    return None


def _class_to_decl(node: Node, src: bytes) -> Declaration:
    name = _field_text(node, "name", src) or "?"
    bases = _class_bases(node, src)
    body = node.child_by_field_name("body")
    docs = _docstring(body, src) if body is not None else []
    children = _walk_class_body(body, src) if body is not None else []

    sig = f"class {name}"
    if bases:
        sig += "(" + ", ".join(bases) + ")"

    return Declaration(
        kind=KIND_CLASS,
        name=name,
        signature=sig,
        bases=bases,
        attrs=[],
        docs=docs,
        docs_inside=True,
        visibility=_visibility_for_name(name),
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        start_byte=node.start_byte,
        end_byte=node.end_byte,
        doc_start_byte=node.start_byte,
        children=children,
    )


def _function_to_decl(node: Node, src: bytes, *, inside_class: bool) -> Declaration:
    name = _field_text(node, "name", src) or "?"
    body = node.child_by_field_name("body")
    docs = _docstring(body, src) if body is not None else []
    sig = _function_signature(node, src)

    if inside_class and name == "__init__":
        kind = KIND_CTOR
    elif inside_class:
        kind = KIND_METHOD
    else:
        kind = KIND_FUNCTION

    return Declaration(
        kind=kind,
        name=name,
        signature=sig,
        docs=docs,
        docs_inside=True,
        visibility=_visibility_for_name(name),
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        start_byte=node.start_byte,
        end_byte=node.end_byte,
        doc_start_byte=node.start_byte,
    )


def _assignment_to_decl(node: Node, src: bytes) -> Optional[Declaration]:
    """Treat typed / value-initialized module- or class-level assignments as fields.

    Only names we care about: simple `name = value` or `name: Type = value`.
    Skip anything complex (tuples, attribute targets).
    """
    left = node.child_by_field_name("left")
    if left is None or left.type != "identifier":
        return None
    name = _text(left, src)

    type_node = node.child_by_field_name("type")
    type_str = _text(type_node, src).lstrip(": ").strip() if type_node is not None else None

    # Rendered signature: `name: Type` or `name = value`
    if type_str:
        sig = f"{name}: {type_str}"
    else:
        sig = name
    return Declaration(
        kind=KIND_FIELD,
        name=name,
        signature=sig,
        visibility=_visibility_for_name(name),
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        start_byte=node.start_byte,
        end_byte=node.end_byte,
    )


# --- Helpers --------------------------------------------------------------


def _function_signature(node: Node, src: bytes) -> str:
    """`def foo(a, b: int) -> X` — everything up to (but not including) the body block."""
    body = node.child_by_field_name("body")
    end = body.start_byte if body is not None else node.end_byte
    text = src[node.start_byte : end].decode("utf8", errors="replace")
    text = _collapse_ws(text).rstrip(" :")
    return text


def _class_bases(node: Node, src: bytes) -> list[str]:
    """For `class Foo(Bar, Baz, metaclass=X):` return ['Bar', 'Baz'] — skip kwargs."""
    sup = node.child_by_field_name("superclasses")
    if sup is None:
        return []
    out: list[str] = []
    for c in sup.named_children:
        if c.type == "keyword_argument":
            continue  # skip metaclass=... etc
        t = _collapse_ws(_text(c, src))
        if t:
            out.append(t)
    return out


def _docstring(block: Optional[Node], src: bytes) -> list[str]:
    """Return the docstring (if any) of a class/function body, as a list of lines.

    Docstring = first statement in block is an expression_statement wrapping a string.
    """
    if block is None:
        return []
    for c in block.named_children:
        if c.type == "expression_statement":
            inner = c.named_children[0] if c.named_children else None
            if inner is not None and inner.type in ("string", "concatenated_string"):
                text = _text(inner, src)
                # Split on newlines and keep triple-quoted form as-is
                return text.splitlines()
        break  # only check the very first statement
    return []


def _visibility_for_name(name: str) -> str:
    if name.startswith("__") and name.endswith("__"):
        return ""  # dunder — conventionally public API (magic methods)
    if name.startswith("_"):
        return "private"
    return ""


def _collapse_ws(text: str) -> str:
    return " ".join(text.split())


def _text(node: Node, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf8", errors="replace")


def _field_text(node: Node, field_name: str, src: bytes) -> Optional[str]:
    c = node.child_by_field_name(field_name)
    return _text(c, src) if c is not None else None
