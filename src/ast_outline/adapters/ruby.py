"""Ruby adapter — parses .rb / .rake / .gemspec / .ru / Rakefile / Gemfile
files via tree-sitter-ruby into Declaration IR.

Design notes (how Ruby concepts map to the IR):

- ``module`` definition           → KIND_NAMESPACE. ``module Foo::Bar``
                                    (already qualified at the source
                                    via ``scope_resolution``) keeps the
                                    qualified form verbatim. Old-style
                                    nested ``module A; module B; class C
                                    …; end; end; end`` where each level
                                    holds exactly one named child
                                    (excluding comments) is collapsed
                                    into a single ``module A::B`` node
                                    so the outline reads the same shape
                                    regardless of source style.
- ``class`` definition            → KIND_CLASS with optional superclass
                                    in ``bases[0]``. ``include M`` /
                                    ``extend M`` / ``prepend M`` calls
                                    inside the class body append
                                    source-true entries to ``bases``
                                    (``"include Comparable"``,
                                    ``"extend Searchable"``,
                                    ``"prepend Mixin"``) so the digest
                                    surfaces mixins on the class header
                                    line without inventing a new IR
                                    field. Reading order matches Ruby's
                                    method-resolution-order intuition:
                                    superclass first, then mixins.
- ``method``                      → KIND_METHOD inside class / module,
                                    KIND_FUNCTION at top level. Special
                                    cases:
                                    * ``initialize`` inside a class →
                                      KIND_CTOR.
                                    * Operator names (``def +``,
                                      ``def <=>``, ``def []``,
                                      ``def []=``, ``def ==``,
                                      ``def -@``) → KIND_OPERATOR. The
                                      grammar uses an explicit
                                      ``operator`` node for the name.
- ``singleton_method``            → ``def self.foo``. Same kind as a
                                    regular method but carries a
                                    ``[static]`` marker in attrs (the
                                    same form Python's ``@staticmethod``
                                    uses), so the digest renders
                                    ``static foo()`` in the member list.
- ``singleton_class``             → ``class << self`` block. Its body
                                    contents are unwrapped flat into
                                    the parent class with the
                                    ``[static]`` marker applied to each
                                    method or attr_accessor inside.
                                    The wrapper itself does not produce
                                    a separate declaration.
- ``attr_accessor :a, :b`` / ``attr_reader`` / ``attr_writer``
                                  → one KIND_FIELD per symbol with a
                                    bracketed marker
                                    (``[accessor]`` / ``[reader]`` /
                                    ``[writer]``) in attrs. Splitting
                                    multi-symbol calls into separate
                                    fields keeps each name grep-able
                                    in the digest, matching how
                                    developers reason about attrs
                                    ("does User have a ``name``
                                    attribute?").
- Rails associations              → ``has_many`` / ``has_one`` /
                                    ``belongs_to`` /
                                    ``has_and_belongs_to_many`` calls
                                    inside a class body produce one
                                    KIND_FIELD per symbol with a
                                    ``[has_many]`` / ``[has_one]`` /
                                    ``[belongs_to]`` / ``[habtm]``
                                    marker. These are recognised by
                                    default — Rails-style associations
                                    are real structural relationships
                                    (the analogue of Unreal Engine's
                                    UPROPERTY in our C++ adapter), and
                                    surfacing them in digest is the
                                    primary value an LLM gets from
                                    reading a model file. Other Rails
                                    DSL macros (``validates``,
                                    ``before_action``, ``scope``) are
                                    intentionally NOT recognised — that
                                    direction leads to an ad-hoc
                                    Rails-knowledge codebase. The line
                                    is drawn at relations because they
                                    name model-to-model edges.
- ``alias_method`` / ``alias``    → emitted as KIND_FIELD with an
                                    ``[alias]`` marker so the new name
                                    surfaces in the outline. The
                                    underlying target is preserved in
                                    the signature (``foo → bar``).
- Visibility                      → tracked as a state machine across
                                    the class body. A bare ``private``
                                    / ``protected`` / ``public`` call
                                    flips the default for all
                                    subsequent declarations.
                                    ``private :foo, :bar`` (with args)
                                    point-targets the named methods
                                    retroactively. The default at the
                                    start of every class body is
                                    public (Ruby's class default).
- Constants                       → ``MAX = 100`` (capitalised LHS)
                                    inside a class or at the top level
                                    surfaces as KIND_FIELD. Lowercase
                                    locals are not declarations — they
                                    parse as plain assignments and are
                                    skipped.
- ``require`` / ``require_relative`` / ``load`` / ``autoload``
                                  → ``imports`` entries, source-true.
                                    Conditional imports (inside
                                    ``if`` / ``begin`` / method body)
                                    are counted into
                                    ``conditional_imports_count`` —
                                    Ruby's ``require`` is dynamic so
                                    this matters more than in,
                                    say, Java.
- Comments preceding a decl       → absorbed into ``docs`` in source
                                    order. Standard convention is
                                    ``# rdoc`` style, one comment per
                                    line; consecutive ``#`` lines
                                    chain together as one doc block.
- Top-level method                → KIND_FUNCTION (defined on
                                    ``Object`` semantically; for
                                    outline purposes a free function).

Out of scope:

- ``define_method`` / ``method_missing`` and other meta-programming —
  these declare methods at runtime and tree-sitter can't see what they
  produce. The outline reflects what the source statically declares.
- Block-style DSL like RSpec ``describe ... do`` — these parse as
  ``call`` nodes with ``do_block`` arguments. They're skipped (no
  decl emitted). An RSpec spec file digests as "no declarations",
  which is honest: there are no Ruby methods at the top of the file.
  Future revisions could surface ``describe`` blocks as headings if
  there's demand.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from tree_sitter import Language, Node, Parser
import tree_sitter_ruby as tsrb

from .base import count_parse_errors
from ..core import (
    KIND_CLASS,
    KIND_CTOR,
    KIND_FIELD,
    KIND_FUNCTION,
    KIND_METHOD,
    KIND_NAMESPACE,
    KIND_OPERATOR,
    Declaration,
    ParseResult,
)


_LANGUAGE = Language(tsrb.language())
_PARSER = Parser(_LANGUAGE)


# Visibility flip names — methods (called like keywords).
_VISIBILITY_NAMES = frozenset({"private", "protected", "public"})

# Mixin names — when called inside a class body they add to the class's
# inheritance hierarchy (method-resolution order). We include each call
# verbatim in the class's `bases` list so the digest header surfaces
# them next to the superclass.
_MIXIN_NAMES = frozenset({"include", "extend", "prepend"})

# attr_* macros → KIND_FIELD with a bracketed marker.
_ATTR_MACROS: dict[str, str] = {
    "attr_accessor": "[accessor]",
    "attr_reader": "[reader]",
    "attr_writer": "[writer]",
}

# Rails-style association macros. Default-on, mirroring how UE
# UPROPERTY is recognised by the C++ adapter — these name real
# model-to-model edges that dominate the value of digesting a Rails
# model file. The list is restricted to the canonical four:
#   has_many / has_one / belongs_to / has_and_belongs_to_many
# Other Rails DSL (`validates`, `scope`, `before_action`, …) is
# intentionally NOT here — they describe behaviour, not structure,
# and adding them would push the adapter into Rails-knowledge territory
# we don't want to maintain.
_RAILS_ASSOCIATIONS: dict[str, str] = {
    "has_many": "[has_many]",
    "has_one": "[has_one]",
    "belongs_to": "[belongs_to]",
    "has_and_belongs_to_many": "[habtm]",
}


class RubyAdapter:
    language_name = "ruby"
    extensions = {".rb", ".rake", ".gemspec", ".ru"}
    # Convention-named extensionless files. Matched by exact basename
    # at adapter selection. Restricted to the universally-known names
    # — adding more would shift the adapter into "guess what's Ruby"
    # territory. ``Gemfile.lock`` is intentionally absent: it's not
    # Ruby source, just a serialisation format.
    basenames = {"Rakefile", "Gemfile"}

    def parse(self, path: Path) -> ParseResult:
        src = path.read_bytes()
        tree = _PARSER.parse(src)
        decls: list[Declaration] = []
        _walk_top(tree.root_node, src, decls)
        imports: list[str] = []
        _collect_imports(tree.root_node, src, imports)
        conditional_count = _count_conditional_imports(tree.root_node, src)
        return ParseResult(
            path=path,
            language=self.language_name,
            source=src,
            line_count=src.count(b"\n") + 1,
            declarations=decls,
            error_count=count_parse_errors(tree.root_node),
            imports=imports,
            conditional_imports_count=conditional_count,
        )


# --- Top-level walk -------------------------------------------------------


def _walk_top(root: Node, src: bytes, out: list[Declaration]) -> None:
    """Walk the program node, accumulating preceding ``#`` comments as
    docs for the next class/module/method declaration."""
    pending_docs: list[str] = []
    for child in root.named_children:
        t = child.type
        if t == "comment":
            pending_docs.append(_text(child, src).strip())
            continue
        decl = _node_to_decl(
            child,
            src,
            scope="top",
            current_visibility="",
            singleton=False,
        )
        if decl is not None:
            decl.docs = pending_docs + decl.docs
            decl.doc_start_byte = _doc_start_byte(decl, pending_docs, child, src)
            out.append(decl)
            pending_docs = []
        else:
            # Not a declaration we surface — drop pending docs (they
            # were attached to a non-decl call like RSpec ``describe``).
            pending_docs = []


def _doc_start_byte(
    decl: Declaration, pending: list[str], node: Node, src: bytes
) -> int:
    """Compute the byte where the leading doc block starts.

    With absorbed `# ...` comments, we want the source slice for `show`
    to include them. Walk backwards from `node.start_byte` over `pending`
    lines, skipping whitespace/newlines.
    """
    if not pending:
        return decl.doc_start_byte
    pos = node.start_byte
    for _ in pending:
        # Skip blank lines and trailing whitespace before the line.
        while pos > 0 and src[pos - 1 : pos] in (b"\n", b" ", b"\t", b"\r"):
            pos -= 1
        # Now `pos` is at the end of a comment line. Walk back to its
        # start (the previous newline, or 0).
        line_start = src.rfind(b"\n", 0, pos)
        line_start = 0 if line_start < 0 else line_start + 1
        pos = line_start
    return pos


# --- Declaration dispatch -------------------------------------------------


def _node_to_decl(
    node: Node,
    src: bytes,
    *,
    scope: str,           # "top" | "module" | "class"
    current_visibility: str,
    singleton: bool,      # True inside `class << self` body
) -> Optional[Declaration]:
    t = node.type

    if t == "module":
        return _module_to_decl(node, src)

    if t == "class":
        return _class_to_decl(node, src)

    if t == "method":
        return _method_to_decl(
            node, src,
            scope=scope,
            visibility=current_visibility,
            static=singleton,
        )

    if t == "singleton_method":
        return _method_to_decl(
            node, src,
            scope=scope,
            visibility=current_visibility,
            static=True,
        )

    if t == "assignment":
        return _assignment_to_decl(node, src, visibility=current_visibility)

    if t == "alias":
        return _alias_to_decl(node, src, visibility=current_visibility)

    return None


# --- module ---------------------------------------------------------------


def _module_to_decl(node: Node, src: bytes) -> Declaration:
    """Convert a ``module`` node to a KIND_NAMESPACE Declaration.

    Handles two qualified-name shapes:
    * ``module Foo::Bar::Baz`` — name is taken from ``scope_resolution``
      verbatim.
    * ``module A; module B; …; end; end`` — collapsed into ``A::B`` when
      every wrapping module's body has exactly one named child
      (excluding comments) which is itself a module. The HIGH-fix from
      the C++ adapter applies: count NAMED children, skipping comments,
      so a stray RDoc comment doesn't disable collapse.
    """
    name = _module_or_class_name(node, src)
    body = _body_statement(node)

    # Try collapse: A → A::B::C if each level holds exactly one named
    # child (excluding comments) which is itself a module.
    head_path = [name]
    cur_body = body
    inner_node: Optional[Node] = node
    while cur_body is not None:
        named = [
            c for c in cur_body.named_children if c.type != "comment"
        ]
        if len(named) != 1:
            break
        only = named[0]
        if only.type != "module":
            break
        inner_node = only
        head_path.append(_module_or_class_name(only, src))
        cur_body = _body_statement(only)
    qualified = "::".join(head_path)

    children = (
        _walk_module_body(cur_body, src) if cur_body is not None else []
    )

    return Declaration(
        kind=KIND_NAMESPACE,
        name=qualified,
        signature=f"module {qualified}",
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        start_byte=node.start_byte,
        end_byte=node.end_byte,
        doc_start_byte=node.start_byte,
        children=children,
    )


def _module_or_class_name(node: Node, src: bytes) -> str:
    """Extract the name field of a ``module`` / ``class`` node.

    The name child is either a ``constant`` (``Foo``) or a
    ``scope_resolution`` (``Foo::Bar::Baz``). We look for whichever
    appears first as a named child — both grammars place it
    immediately after the keyword.
    """
    for c in node.named_children:
        if c.type in ("constant", "scope_resolution"):
            return _text(c, src)
    return "?"


def _body_statement(node: Node) -> Optional[Node]:
    """Return the ``body_statement`` child of a class/module/method,
    or None if absent (empty body)."""
    for c in node.named_children:
        if c.type == "body_statement":
            return c
    return None


def _walk_module_body(body: Node, src: bytes) -> list[Declaration]:
    """Walk a module body. Modules don't enforce visibility, so we treat
    members as scope=module with empty visibility tracking."""
    out: list[Declaration] = []
    pending_docs: list[str] = []
    for child in body.named_children:
        t = child.type
        if t == "comment":
            pending_docs.append(_text(child, src).strip())
            continue
        decl = _node_to_decl(
            child, src, scope="module",
            current_visibility="", singleton=False,
        )
        if decl is not None:
            decl.docs = pending_docs + decl.docs
            decl.doc_start_byte = _doc_start_byte(decl, pending_docs, child, src)
            out.append(decl)
            pending_docs = []
        else:
            pending_docs = []
    return out


# --- class ----------------------------------------------------------------


def _class_to_decl(node: Node, src: bytes) -> Declaration:
    name = _module_or_class_name(node, src)
    superclass: Optional[str] = None

    # Superclass — `class Foo < Bar` puts a `superclass` named child on
    # the class node. Ruby allows at most one; we take the first.
    for c in node.named_children:
        if c.type == "superclass":
            for sc in c.named_children:
                superclass = _text(sc, src)
                break
            break

    body = _body_statement(node)
    children, mixin_bases = (
        _walk_class_body(body, src) if body is not None else ([], [])
    )

    # Signature stays close to source-true Ruby: `class Foo < Bar` with
    # at most one superclass after the `<`. Mixins (`include`, `extend`,
    # `prepend`) are NOT spliced in here — they're separate Ruby
    # statements in the source and putting them after the `<` would
    # produce non-Ruby syntax in the outline header. They surface in
    # the digest's `: bases` clause instead, where the `:` separator
    # is our canonical "any kind of MRO entry" marker.
    sig = f"class {name}"
    if superclass:
        sig += f" < {superclass}"

    # `bases` carries the full MRO contribution for digest rendering:
    # superclass first (when present), then mixin entries in source
    # order. Each mixin entry is stored as source-true text
    # (`"include Comparable"`, `"extend Searchable"`) so the digest
    # reproduces the Ruby keyword.
    bases: list[str] = []
    if superclass:
        bases.append(superclass)
    bases.extend(mixin_bases)

    return Declaration(
        kind=KIND_CLASS,
        name=name,
        signature=sig,
        bases=bases,
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        start_byte=node.start_byte,
        end_byte=node.end_byte,
        doc_start_byte=node.start_byte,
        children=children,
    )


def _walk_class_body(
    body: Node, src: bytes
) -> tuple[list[Declaration], list[str]]:
    """Walk a class body with visibility state-machine + mixin pickup.

    Returns (children declarations, mixin entries). The mixin entries
    are bubbled up to the parent's ``bases`` list as source-true text
    (``"include Foo"``, ``"extend Bar"``, ``"prepend Baz"``).

    Two visibility modes apply:
    * **Bare** ``private`` / ``public`` / ``protected`` flips the
      current visibility for all subsequent declarations.
    * **Targeted** ``private :foo, :bar`` (with symbol args)
      retroactively sets visibility on the named methods.
    """
    out: list[Declaration] = []
    mixin_bases: list[str] = []
    current_visibility = ""  # public default
    pending_docs: list[str] = []
    # Deferred targeted visibility flips: list of (visibility, names).
    deferred_visibility: list[tuple[str, set[str]]] = []

    for child in body.named_children:
        t = child.type
        if t == "comment":
            pending_docs.append(_text(child, src).strip())
            continue

        # Singleton class: `class << self ... end` — unwrap its body
        # flat into the parent class with [static] marker on each.
        if t == "singleton_class":
            inner_body = _body_statement(child)
            if inner_body is not None:
                inner_decls, _ = _walk_singleton_body(inner_body, src)
                for d in inner_decls:
                    d.visibility = current_visibility
                out.extend(inner_decls)
            pending_docs = []
            continue

        # Plain identifier as a body statement — bare `private` /
        # `public` / `protected` inside a class flips current state.
        if t == "identifier":
            name = _text(child, src)
            if name in _VISIBILITY_NAMES:
                current_visibility = "" if name == "public" else name
            pending_docs = []
            continue

        # `call` covers many cases: visibility/mixin/attr/Rails/private(:x).
        if t == "call":
            handled = _handle_class_call(
                child, src, current_visibility,
                out, mixin_bases, deferred_visibility, pending_docs,
            )
            if isinstance(handled, tuple) and handled[0] == "visibility_flip":
                # Bare `private()` / `public()` / `protected()` with
                # explicit empty parens — rare, but valid Ruby. The
                # handler returns the new visibility string so we can
                # update state from this scope.
                current_visibility = handled[1]
                pending_docs = []
                continue
            if handled is not None:
                pending_docs = []
                continue
            # Unhandled call (RSpec describe, custom DSL, etc.) — not
            # a structural decl. Drop docs.
            pending_docs = []
            continue

        decl = _node_to_decl(
            child, src,
            scope="class",
            current_visibility=current_visibility,
            singleton=False,
        )
        if decl is not None:
            decl.docs = pending_docs + decl.docs
            decl.doc_start_byte = _doc_start_byte(decl, pending_docs, child, src)
            out.append(decl)
            pending_docs = []
        else:
            pending_docs = []

    # Apply deferred targeted-visibility flips (`private :foo, :bar`).
    if deferred_visibility:
        for vis, names in deferred_visibility:
            for d in out:
                if d.name in names:
                    d.visibility = vis

    return out, mixin_bases


def _walk_singleton_body(
    body: Node, src: bytes
) -> tuple[list[Declaration], list[str]]:
    """Walk a `class << self` body. Methods/attrs become flat children
    of the enclosing class with the [static] marker. We also support
    `attr_accessor :counter` inside the singleton — same split-per-symbol
    logic, but each field gets `[static]` too."""
    out: list[Declaration] = []
    pending_docs: list[str] = []
    for child in body.named_children:
        t = child.type
        if t == "comment":
            pending_docs.append(_text(child, src).strip())
            continue

        if t == "method":
            decl = _method_to_decl(
                child, src, scope="class",
                visibility="", static=True,
            )
            if decl is not None:
                decl.docs = pending_docs + decl.docs
                decl.doc_start_byte = _doc_start_byte(decl, pending_docs, child, src)
                out.append(decl)
            pending_docs = []
            continue

        if t == "call":
            ident = _call_identifier_name(child, src)
            if ident in _ATTR_MACROS:
                marker = _ATTR_MACROS[ident]
                names = _symbol_args(child, src)
                for n in names:
                    out.append(_make_attr_field(
                        child, n, marker, "", static=True,
                    ))
                pending_docs = []
                continue

        pending_docs = []

    return out, []


def _handle_class_call(
    node: Node,
    src: bytes,
    current_visibility: str,
    out: list[Declaration],
    mixin_bases: list[str],
    deferred_visibility: list[tuple[str, set[str]]],
    pending_docs: list[str],
):
    """Handle a ``call`` node inside a class body.

    Returns:
    * ``("visibility_flip", new_visibility)`` — bare
      ``private()`` / ``public()`` / ``protected()`` with explicit
      parens. The caller updates its ``current_visibility`` from the
      tuple's second element.
    * ``"visibility_target"`` — targeted form (``private :foo``)
      recorded into ``deferred_visibility`` for retroactive apply.
    * ``"mixin"`` — ``include`` / ``extend`` / ``prepend`` pushed onto
      ``mixin_bases``.
    * ``"attr"`` — ``attr_accessor`` / ``attr_reader`` / ``attr_writer``
      (or ``alias_method``) expanded into ``KIND_FIELD`` decls in
      ``out``.
    * ``"rails"`` — ``has_many`` / ``has_one`` / ``belongs_to`` /
      ``has_and_belongs_to_many`` expanded into ``KIND_FIELD`` decls.
    * ``None`` — any other call (RSpec ``describe``, custom DSL
      macros, …); the caller treats those as non-decl noise.

    Note on bare ``private`` parsing: a bare ``private`` (no parens,
    no args) parses as an ``identifier`` node, not ``call`` — that
    case is handled by the walker's ``identifier`` branch directly.
    The ``("visibility_flip", …)`` tuple covers only the much rarer
    ``private()`` / ``public()`` form, where the empty arg list still
    produces a ``call`` node.
    """
    ident = _call_identifier_name(node, src)
    if ident is None:
        return None

    # Targeted or bare-with-parens visibility: `private :foo` /
    # `private()` / `public`-as-call (rare).
    if ident in _VISIBILITY_NAMES:
        names = _symbol_args(node, src)
        if names:
            vis = "" if ident == "public" else ident
            deferred_visibility.append((vis, set(names)))
            return "visibility_target"
        # No symbol args — `private()` form. Tell the caller to flip
        # `current_visibility` for subsequent decls.
        new_vis = "" if ident == "public" else ident
        return ("visibility_flip", new_vis)

    if ident in _MIXIN_NAMES:
        # `include Foo, Bar` → multiple mixins. Each name becomes a
        # source-true `include Foo` entry on the parent class's bases.
        targets = _constant_args(node, src)
        for target in targets:
            mixin_bases.append(f"{ident} {target}")
        return "mixin"

    if ident in _ATTR_MACROS:
        marker = _ATTR_MACROS[ident]
        names = _symbol_args(node, src)
        for n in names:
            field = _make_attr_field(
                node, n, marker, current_visibility, static=False,
            )
            field.docs = list(pending_docs)
            out.append(field)
        return "attr"

    if ident in _RAILS_ASSOCIATIONS:
        marker = _RAILS_ASSOCIATIONS[ident]
        names = _symbol_args(node, src)
        for n in names:
            field = _make_attr_field(
                node, n, marker, current_visibility, static=False,
            )
            field.docs = list(pending_docs)
            out.append(field)
        return "rails"

    if ident == "alias_method":
        # `alias_method :new_name, :old_name`
        names = _symbol_args(node, src)
        if len(names) >= 2:
            new, old = names[0], names[1]
            field = Declaration(
                kind=KIND_FIELD,
                name=new,
                signature=f"{new} → {old}",
                attrs=["[alias]"],
                visibility=current_visibility,
                docs=list(pending_docs),
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                start_byte=node.start_byte,
                end_byte=node.end_byte,
            )
            out.append(field)
            return "attr"

    if ident == "private_class_method":
        # `private_class_method :foo` — make a previously-defined
        # class method (def self.foo) private. Apply retroactively
        # via the deferred mechanism.
        names = _symbol_args(node, src)
        if names:
            deferred_visibility.append(("private", set(names)))
            return "visibility_target"

    return None


def _make_attr_field(
    node: Node, name: str, marker: str, visibility: str, *, static: bool
) -> Declaration:
    # `[static]` first so the order matches a reader's left-to-right
    # parse: scope-modifier, then kind-of-thing. Mirrors how Python
    # writes `@staticmethod\n@property` — outermost decorator first.
    attrs: list[str] = []
    if static:
        attrs.append("[static]")
    attrs.append(marker)
    return Declaration(
        kind=KIND_FIELD,
        name=name,
        signature=name,
        attrs=attrs,
        visibility=visibility,
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        start_byte=node.start_byte,
        end_byte=node.end_byte,
    )


def _call_identifier_name(node: Node, src: bytes) -> Optional[str]:
    """Return the name of a `call` node's primary identifier — the
    method being called. Only handles the bare-identifier shape
    (``foo(...)``); receiver-dot calls (``Other.foo(...)``) return
    None because those aren't decl-shaped DSL calls in practice."""
    for c in node.named_children:
        if c.type == "identifier":
            return _text(c, src)
        # Receiver before the dot — abort (this is `Foo.bar(...)`,
        # not a top-level DSL call).
        if c.type in ("constant", "scope_resolution", "self"):
            return None
    return None


def _argument_list(node: Node) -> Optional[Node]:
    for c in node.named_children:
        if c.type == "argument_list":
            return c
    return None


def _symbol_args(node: Node, src: bytes) -> list[str]:
    """Extract `:foo`-style symbol args from a `call`'s argument list.

    Only ``simple_symbol`` and string-literal arg shapes are surfaced
    — ``has_many :posts, dependent: :destroy`` produces ``["posts"]``
    (the `dependent: :destroy` keyword is dropped, as is anything that
    isn't a positional symbol or string).
    """
    args = _argument_list(node)
    if args is None:
        return []
    out: list[str] = []
    for c in args.named_children:
        if c.type == "simple_symbol":
            text = _text(c, src)
            # Strip leading `:` from `:foo`
            if text.startswith(":"):
                text = text[1:]
            out.append(text)
        elif c.type == "string":
            # `attr_reader "name"` — same effect as `:name`
            out.append(_string_literal(c, src))
    return out


def _string_literal(node: Node, src: bytes) -> str:
    """Extract the inner text of a `string` node."""
    for c in node.named_children:
        if c.type == "string_content":
            return _text(c, src)
    return ""


def _constant_args(node: Node, src: bytes) -> list[str]:
    """Extract `Foo` / `Foo::Bar` constants from a call's argument list.
    Used for mixin args (``include Comparable, Enumerable``)."""
    args = _argument_list(node)
    if args is None:
        return []
    out: list[str] = []
    for c in args.named_children:
        if c.type in ("constant", "scope_resolution"):
            out.append(_text(c, src))
    return out


# --- methods --------------------------------------------------------------


# Operator names that map to KIND_OPERATOR. These appear as the text of
# the ``operator`` node child of ``method``. Listed exhaustively so the
# adapter doesn't accidentally classify a non-operator def-with-symbol
# (which the grammar wouldn't actually allow) as an operator.
_OPERATOR_NAMES = frozenset({
    # arithmetic
    "+", "-", "*", "/", "%", "**",
    # comparison / equality
    "==", "!=", "===", "<", ">", "<=", ">=", "<=>",
    # bitwise / logical
    "&", "|", "^", "~", "<<", ">>",
    # indexing
    "[]", "[]=",
    # unary forms (Ruby-specific spellings)
    "-@", "+@", "!", "!@",
    # case-equality is `===` (already above); pattern-match `===` is the same op
})


def _method_to_decl(
    node: Node,
    src: bytes,
    *,
    scope: str,
    visibility: str,
    static: bool,
) -> Declaration:
    """Build a Declaration for a `method` or `singleton_method` node.

    Kind is decided by:
    * Operator-named methods → KIND_OPERATOR.
    * Inside a class with name ``initialize`` → KIND_CTOR.
    * Inside a class otherwise → KIND_METHOD.
    * Top-level (``scope == "top"``) → KIND_FUNCTION.
    * Inside a module → KIND_METHOD (modules-as-namespace can hold
      module functions; for the IR they read like methods).

    `static=True` (set by the singleton_method branch and class-method
    walks) attaches a ``[static]`` marker to attrs, matching the way
    Python's @staticmethod is recorded.
    """
    name, is_operator = _method_name(node, src)
    sig = _method_signature(node, src, name)

    if is_operator:
        kind = KIND_OPERATOR
    elif scope == "class" and name == "initialize":
        kind = KIND_CTOR
    elif scope == "top":
        kind = KIND_FUNCTION
    else:
        kind = KIND_METHOD

    attrs: list[str] = []
    if static:
        attrs.append("[static]")

    return Declaration(
        kind=kind,
        name=name,
        signature=sig,
        attrs=attrs,
        visibility=visibility,
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        start_byte=node.start_byte,
        end_byte=node.end_byte,
        doc_start_byte=node.start_byte,
    )


def _method_name(node: Node, src: bytes) -> tuple[str, bool]:
    """Return (name, is_operator) for a method / singleton_method node.

    The name is the first child of type ``identifier`` /
    ``constant`` / ``operator`` after the ``def`` keyword (and after
    ``self.`` for ``singleton_method``). For ``operator`` children we
    take the bare operator text (``+``, ``<=>``, …) and flag the
    method as an operator.
    """
    for c in node.named_children:
        if c.type == "identifier":
            return _text(c, src), False
        if c.type == "constant":
            return _text(c, src), False
        if c.type == "operator":
            text = _text(c, src).strip()
            return text, text in _OPERATOR_NAMES or _looks_like_operator(text)
    return "?", False


def _looks_like_operator(text: str) -> bool:
    """Fallback for operator detection — matches when the name has no
    alphabetic characters at all (every char is symbolic). Catches any
    operator the grammar exposes that isn't in our explicit allow-list,
    without wrongly tagging an alphabetic identifier as an operator."""
    return bool(text) and all(not c.isalpha() for c in text)


def _method_signature(node: Node, src: bytes, name: str) -> str:
    """Render `def name(args)` — everything from `def` up to (but not
    including) the body. Single-line signatures stay single-line; multi-
    line param lists get whitespace-collapsed.

    For `singleton_method` (``def self.foo``) the signature includes
    the ``self.`` prefix verbatim, so the LLM sees the source-true
    shape.
    """
    # Find the body to know where to stop slicing.
    body = _body_statement(node)
    # Some empty methods have no body_statement child — slice up to the
    # `end` keyword instead.
    end_byte = body.start_byte if body is not None else _slice_to_end_keyword(node, src)
    text = src[node.start_byte:end_byte].decode("utf8", errors="replace")
    return _collapse_ws(text).rstrip()


def _slice_to_end_keyword(node: Node, src: bytes) -> int:
    """Find the byte offset of the trailing `end` keyword in a method
    node, used as a signature slice cutoff for empty-body methods."""
    for c in node.children:
        if c.type == "end":
            return c.start_byte
    return node.end_byte


# --- assignments → fields -------------------------------------------------


def _assignment_to_decl(
    node: Node, src: bytes, *, visibility: str
) -> Optional[Declaration]:
    """Surface only constant assignments (``MAX = 100``) as KIND_FIELD.

    Lowercase locals and instance/class variable assignments
    (``@foo = …``, ``@@bar = …``) are not "declarations" in the
    structural sense — they're imperative state. We skip them.
    """
    left: Optional[Node] = None
    for c in node.named_children:
        left = c
        break
    if left is None or left.type != "constant":
        return None
    name = _text(left, src)
    return Declaration(
        kind=KIND_FIELD,
        name=name,
        signature=name,
        visibility=visibility,
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        start_byte=node.start_byte,
        end_byte=node.end_byte,
    )


def _alias_to_decl(
    node: Node, src: bytes, *, visibility: str
) -> Optional[Declaration]:
    """Convert ``alias new_name old_name`` into a KIND_FIELD with
    ``[alias]`` marker. Symbol vs identifier args are both accepted.

    `alias_method :a, :b` (the method-form) is handled in
    `_handle_class_call` instead — keyword `alias` gets its own AST
    node here, but `alias_method` is a regular `call`.
    """
    parts: list[str] = []
    for c in node.named_children:
        if c.type == "identifier":
            parts.append(_text(c, src))
        elif c.type == "simple_symbol":
            text = _text(c, src)
            if text.startswith(":"):
                text = text[1:]
            parts.append(text)
    if len(parts) < 2:
        return None
    new, old = parts[0], parts[1]
    return Declaration(
        kind=KIND_FIELD,
        name=new,
        signature=f"{new} → {old}",
        attrs=["[alias]"],
        visibility=visibility,
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        start_byte=node.start_byte,
        end_byte=node.end_byte,
    )


# --- imports --------------------------------------------------------------


_RUBY_IMPORT_NAMES = frozenset({
    "require", "require_relative", "load", "autoload",
})

# Top-level statement nodes we descend into looking for additional
# imports — Ruby's analogue of Python's `if TYPE_CHECKING:` is `if`/
# `unless`/`begin`/`rescue` blocks at file scope, sometimes used to
# guard `require` against missing gems. Keeping these visible matches
# what an agent would expect from a static dependency read.
_RUBY_IMPORT_DESCEND = frozenset({
    # Conditional / exception-handling shells. Their bodies aren't
    # `body_statement` blocks — tree-sitter-ruby uses dedicated `then`
    # / `else` / `elsif` / `rescue` / `ensure` clause nodes whose
    # children are statements directly.
    "if", "unless",
    "then", "else", "elsif",
    "begin", "rescue", "ensure",
    "if_modifier", "unless_modifier",
    "body_statement",
})

# Scopes that promote a require to "conditional" (counted, not listed).
# Note: `do_block` is here, NOT in `_RUBY_IMPORT_DESCEND` — a require
# inside `Foo.each { require "x" }` is genuinely lazy (only fires when
# the block runs), not a static top-level dependency. Listing it as
# static would mislead the agent into thinking the require always
# executes on file load.
_RUBY_SCOPED = frozenset({
    "method", "singleton_method", "block", "do_block", "lambda",
})

# Note on coverage: `require` calls inside a class or module body
# (rare but valid: `class Foo; require "bar"; end`) are neither listed
# statically nor counted as conditional. The gap is intentional — the
# class/module body isn't a runtime scope but isn't a file's top-level
# either, and counting it as either form would mislead the agent.
# Realistic Ruby code doesn't `require` from class bodies; the few
# legacy codebases that do can `--imports` the file directly.


def _collect_imports(root: Node, src: bytes, out: list[str]) -> None:
    for child in root.named_children:
        t = child.type
        if t == "call":
            ident = _call_identifier_name(child, src)
            if ident in _RUBY_IMPORT_NAMES:
                _emit_import(child, src, ident, out)
                continue
        if t in _RUBY_IMPORT_DESCEND:
            _collect_imports(child, src, out)


def _emit_import(node: Node, src: bytes, ident: str, out: list[str]) -> None:
    """Render a `require "x"` / `require_relative "x"` / `load "x"` /
    `autoload :Foo, "path"` call as source-true text."""
    args = _argument_list(node)
    if args is None:
        return
    if ident == "autoload":
        # `autoload :Foo, "path"` — keep both args verbatim.
        pieces: list[str] = []
        for c in args.named_children:
            pieces.append(_text(c, src))
        out.append(f"autoload {', '.join(pieces)}")
        return
    # require / require_relative / load — single string arg.
    for c in args.named_children:
        if c.type == "string":
            inner = _string_literal(c, src)
            out.append(f'{ident} "{inner}"')
            return
        # Variable / constant arg (`require gem`) — emit the raw text
        # so the agent at least sees the dynamic dependency exists.
        out.append(f"{ident} {_text(c, src)}")
        return


def _count_conditional_imports(root: Node, src: bytes) -> int:
    """Count `require` / `require_relative` / `load` / `autoload` calls
    that live inside a method / block / lambda scope.

    We do NOT count requires inside top-level `if` / `begin` / `rescue`
    — `_collect_imports` already lists those statically (they're a
    common pattern for "require X if X is available" guards), so
    counting them here would double-state a dependency already in the
    static imports list.
    """
    count = 0
    stack: list[tuple[Node, bool]] = [(root, False)]
    while stack:
        node, in_scope = stack.pop()
        t = node.type
        if t == "call" and in_scope:
            ident = _call_identifier_name(node, src)
            if ident in _RUBY_IMPORT_NAMES:
                count += 1
        new_scope = in_scope or t in _RUBY_SCOPED
        for c in node.children:
            stack.append((c, new_scope))
    return count


# --- helpers --------------------------------------------------------------


def _collapse_ws(text: str) -> str:
    return " ".join(text.split())


def _text(node: Node, src: bytes) -> str:
    return src[node.start_byte:node.end_byte].decode("utf8", errors="replace")
