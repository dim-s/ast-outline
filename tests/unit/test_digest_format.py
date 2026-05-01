"""Tests for the digest output format conventions documented in the
legend line: callable `()` marker, `[N overloads]` collapse, native-kind
keyword for types, and comma-space token separator.

These are LLM-facing format guarantees — a regression here is a silent
contract change with downstream agent prompts, so each rule has its own
test that names what it's protecting and why."""
from __future__ import annotations

from ast_outline.adapters.csharp import CSharpAdapter
from ast_outline.adapters.java import JavaAdapter
from ast_outline.adapters.kotlin import KotlinAdapter
from ast_outline.adapters.python import PythonAdapter
from ast_outline.adapters.rust import RustAdapter
from ast_outline.adapters.scala import ScalaAdapter
from ast_outline.core import (
    CALLABLE_KINDS,
    Declaration,
    DigestOptions,
    KIND_CLASS,
    KIND_FIELD,
    KIND_INTERFACE,
    KIND_METHOD,
    _collapse_overloads,
    _is_deprecated,
    _member_token,
    render_digest,
)


# --- Legend --------------------------------------------------------------


def test_digest_starts_with_legend_line(csharp_dir):
    """A self-describing legend is the first line of every digest so the
    format is parseable cold by an LLM that hasn't loaded
    `ast-outline prompt`."""
    r = CSharpAdapter().parse(csharp_dir / "unity_behaviour.cs")
    out = render_digest([r], DigestOptions())
    first = out.splitlines()[0]
    assert first.startswith("# legend:")


def test_legend_documents_each_non_obvious_token(csharp_dir):
    """Legend must mention every non-English token shape so an LLM
    reading cold can decode the body. Plain-English labels (`[tiny]` /
    `[broken]`) deliberately stay out of the legend to keep it compact."""
    r = CSharpAdapter().parse(csharp_dir / "unity_behaviour.cs")
    legend = render_digest([r], DigestOptions()).splitlines()[0]
    assert "name()" in legend
    assert "[kind]" in legend
    assert "overloads" in legend
    assert "[deprecated]" in legend
    assert "L<a>-<b>" in legend


def test_legend_is_a_single_line(csharp_dir):
    """Legend must fit on one line — multi-line legends get truncated by
    naive consumers and read awkwardly when piped into prompts."""
    r = CSharpAdapter().parse(csharp_dir / "unity_behaviour.cs")
    out = render_digest([r], DigestOptions())
    legend = out.splitlines()[0]
    # No internal newlines, fits comfortably in a 200-col terminal.
    assert "\n" not in legend
    assert len(legend) < 200


# --- Callable marker -----------------------------------------------------


def test_callables_render_with_paren_suffix(csharp_dir):
    """`name()` is the LLM-native marker for "this is a function" — every
    callable kind (method, function, ctor, dtor, operator) must carry it
    so the agent can distinguish callables from properties/fields without
    consulting the legend."""
    r = CSharpAdapter().parse(csharp_dir / "unity_behaviour.cs")
    out = render_digest([r], DigestOptions())
    assert "TakeDamage()" in out          # method
    assert "HeroController()" in out      # constructor


def test_non_callables_keep_kind_tag(csharp_dir):
    """Properties / events / fields render as `name [kind]` so the
    non-callable nature is explicit — avoids any "is this a method or a
    property" ambiguity."""
    r = CSharpAdapter().parse(csharp_dir / "unity_behaviour.cs")
    out = render_digest([r], DigestOptions())
    assert "CurrentHealth [property]" in out
    assert "OnHealthChanged [event]" in out


def test_callables_do_not_carry_plus_prefix(csharp_dir):
    """No `+` prefix on member tokens — earlier revisions used `+name`
    but the marker collides with diff syntax and adds no signal beyond
    `()` / `[kind]`. This test guards against re-introduction."""
    r = CSharpAdapter().parse(csharp_dir / "unity_behaviour.cs")
    out = render_digest([r], DigestOptions())
    body = "\n".join(out.splitlines()[1:])
    assert "+TakeDamage" not in body
    assert "+CurrentHealth" not in body
    assert "+HeroController" not in body


def test_member_token_pure_unit():
    """`_member_token` is the canonical formatter — exercised directly
    so the rule is enforced without going through an adapter."""
    method = Declaration(kind=KIND_METHOD, name="Foo", signature="void Foo()")
    field = Declaration(kind=KIND_FIELD, name="bar", signature="int bar")
    assert _member_token(method, count=1) == "Foo()"
    assert _member_token(method, count=3) == "Foo() [3 overloads]"
    assert _member_token(field, count=1) == "bar [field]"


# --- Overload collapse ---------------------------------------------------


def test_overloaded_methods_collapse_to_single_token(csharp_dir):
    """Money has two `Equals` overloads — one accepting Money, one
    decimal. They should appear as a single token annotated
    `[2 overloads]`, not two indistinguishable `Equals()` lines."""
    r = CSharpAdapter().parse(csharp_dir / "nested_and_overloads.cs")
    out = render_digest([r], DigestOptions())
    assert "Equals() [2 overloads]" in out
    # Only one Equals occurrence — the collapse must not also keep the
    # individual entries.
    assert out.count("Equals()") == 1


def test_single_method_does_not_carry_overload_tag(csharp_dir):
    """A unique callable name carries no `[N overloads]` — the
    annotation fires only when N > 1, otherwise it would be noise on
    every line."""
    r = CSharpAdapter().parse(csharp_dir / "unity_behaviour.cs")
    out = render_digest([r], DigestOptions())
    assert "[1 overloads]" not in out
    assert "TakeDamage() [" not in out  # no annotation for unique names


def test_collapse_overloads_preserves_first_occurrence_order():
    """`_collapse_overloads` returns groups in first-seen order so the
    digest still points to the agent's likeliest entry-point."""
    a = Declaration(kind=KIND_METHOD, name="A", signature="A()", start_line=10)
    b1 = Declaration(kind=KIND_METHOD, name="B", signature="B()", start_line=20)
    b2 = Declaration(kind=KIND_METHOD, name="B", signature="B(int)", start_line=25)
    c = Declaration(kind=KIND_METHOD, name="C", signature="C()", start_line=30)
    out = _collapse_overloads([a, b1, b2, c])
    assert [(d.name, n) for d, n in out] == [("A", 1), ("B", 2), ("C", 1)]
    # Representative for B is the FIRST occurrence (line 20), not the last.
    b_rep = next(d for d, _ in out if d.name == "B")
    assert b_rep.start_line == 20


def test_collapse_does_not_merge_non_callables():
    """Same-name fields must NOT collapse — they're a real source-level
    distinction (rare but possible) and `[N overloads]` would be
    semantically wrong for a non-callable."""
    f1 = Declaration(kind=KIND_FIELD, name="x", signature="int x")
    f2 = Declaration(kind=KIND_FIELD, name="x", signature="int x")
    out = _collapse_overloads([f1, f2])
    assert len(out) == 2
    assert all(count == 1 for _, count in out)


def test_overload_collapse_covers_every_callable_kind():
    """The collapse rule must apply uniformly to every kind in
    CALLABLE_KINDS — method, function, ctor, dtor, operator. A
    regression where one kind silently isn't collapsed would leak
    duplicates."""
    decls = [
        Declaration(kind=k, name="dup", signature="dup()")
        for k in CALLABLE_KINDS
    ] + [
        Declaration(kind=k, name="dup", signature="dup(int)")
        for k in CALLABLE_KINDS
    ]
    out = _collapse_overloads(decls)
    # Name "dup" used across all kinds, all with the same name in the
    # same scope — they all collapse into a single entry.
    assert len(out) == 1
    _, count = out[0]
    assert count == len(CALLABLE_KINDS) * 2


# --- Native keyword ------------------------------------------------------


def test_rust_trait_renders_as_trait_not_interface(rust_dir):
    """Rust `trait` maps to KIND_INTERFACE in the IR (so `implements`
    queries find sub-traits uniformly with Java/C# interfaces), but the
    digest must print `trait` so the agent doesn't see a fictional
    `interface` keyword that grep against the source would not find."""
    r = RustAdapter().parse(rust_dir / "hierarchy.rs")
    out = render_digest([r], DigestOptions())
    assert "trait Animal" in out
    # And NOT the canonical-kind keyword.
    assert "interface Animal" not in out


def test_scala_trait_renders_as_trait(scala_dir):
    """Scala traits — same compromise as Rust: KIND_INTERFACE for
    search, `trait` for digest."""
    r = ScalaAdapter().parse(scala_dir / "hierarchy.scala")
    out = render_digest([r], DigestOptions())
    # Names are package-qualified in digest (`zoo.Movable`); just
    # confirm the source-true keyword precedes them.
    assert "trait zoo.Movable" in out
    assert "interface zoo.Movable" not in out


def test_scala_object_renders_as_object(scala_dir):
    """Scala singleton `object` is KIND_CLASS in the IR but the digest
    should reflect the actual keyword."""
    r = ScalaAdapter().parse(scala_dir / "companion_and_objects.scala")
    out = render_digest([r], DigestOptions())
    # At least one `object` declaration in this fixture must surface
    # with the native keyword.
    assert "object " in out
    # Find a known object name from the fixture and check its header
    # uses `object`, not `class`.
    lines = [line for line in out.splitlines() if "object " in line]
    assert any(line.lstrip().startswith("object ") for line in lines)


def test_java_annotation_type_renders_as_interface(java_dir):
    """Java `@interface` annotation types render as plain `interface`
    in digest. Java devs don't say "@interface" in conversation —
    the annotation nature is recoverable from `@Retention`/`@Target`
    attrs in outline. Treating annotation types as ordinary interfaces
    keeps the digest legend short and matches the language's
    everyday vocabulary."""
    r = JavaAdapter().parse(java_dir / "annotation_type.java")
    out = render_digest([r], DigestOptions())
    assert "interface com.example.demo.ann.Tagged" in out
    # Specifically NOT the `@interface` literal from source.
    assert "@interface " not in out


def test_kotlin_data_class_renders_as_data_class(kotlin_dir):
    """`data class` maps to KIND_RECORD; digest must restore the source
    keyword so `data class Point` reads truthfully."""
    r = KotlinAdapter().parse(kotlin_dir / "data_and_sealed.kt")
    out = render_digest([r], DigestOptions())
    assert "data class com.example.demo.model.Point" in out
    # Should NOT use the canonical `record` keyword.
    assert "record com.example.demo.model.Point" not in out


def test_kotlin_object_renders_as_object(kotlin_dir):
    """Kotlin `object` (singleton) → KIND_CLASS in IR, `object` in
    digest."""
    r = KotlinAdapter().parse(kotlin_dir / "companion_and_objects.kt")
    out = render_digest([r], DigestOptions())
    assert "object app.Logger" in out


def test_kotlin_annotation_class_renders_as_annotation_class(kotlin_dir):
    """`annotation class Foo` maps to KIND_INTERFACE for query parity,
    but digest carries the source-true `annotation class` keyword."""
    r = KotlinAdapter().parse(kotlin_dir / "annotations_generics.kt")
    out = render_digest([r], DigestOptions())
    assert "annotation class gen.Marker" in out


def test_native_kind_falls_back_to_canonical_kind(python_dir):
    """When an adapter doesn't set `native_kind`, the canonical `kind`
    is used. Python only has `class` (no divergence), so the digest
    must use the canonical keyword unchanged."""
    r = PythonAdapter().parse(python_dir / "domain_model.py")
    out = render_digest([r], DigestOptions())
    # Type lines start with `class ` (canonical kind, no native override).
    assert "class " in out


def test_native_kind_default_is_empty_string():
    """Declaration default for `native_kind` is the empty string —
    sentinel used by the renderer to decide fallback. A regression to
    None or a non-empty default would change behavior silently."""
    d = Declaration(kind=KIND_CLASS, name="X", signature="class X")
    assert d.native_kind == ""


# --- Separator -----------------------------------------------------------


def test_digest_uses_comma_separator_between_member_tokens(csharp_dir):
    """Member tokens are joined with `, ` (comma-space) — universal
    list-separator convention, parsed cleanly by every BPE tokenizer.
    Earlier revisions used double-space, which was a weaker LLM signal."""
    r = CSharpAdapter().parse(csharp_dir / "unity_behaviour.cs")
    out = render_digest([r], DigestOptions())
    body = "\n".join(out.splitlines()[1:])
    # Comma-space appears in the member wrap-line (HeroController has
    # multiple members on a single line).
    assert ", " in body
    # Specifically: a wrap-line with at least two tokens must join them
    # with ", " — never with double-space.
    member_lines = [
        line for line in body.splitlines()
        if line.lstrip().startswith(
            ("CurrentHealth", "TakeDamage", "value", "priority")
        )
    ]
    assert member_lines, "fixture must produce a member wrap-line"
    for line in member_lines:
        stripped = line.lstrip()
        # No double-space between tokens — `, ` is the separator.
        assert "  " not in stripped, f"unexpected double-space in {line!r}"


# --- Visual grouping (blank-line rule) ----------------------------------


def test_blank_line_after_type_with_members(csharp_dir):
    """A type whose body emits at least one member row gets a trailing
    blank line — paragraph break that visually owns the "type + its
    members" block. Empty types (no body lines) stay tight so digest
    remains compact for declaration-heavy files."""
    r = CSharpAdapter().parse(csharp_dir / "hierarchy.cs")
    out = render_digest([r], DigestOptions())
    lines = out.splitlines()
    # Locate `class Demo.Hierarchy.Animal` (has a body member `Eat()`).
    animal_idx = next(i for i, line in enumerate(lines) if "class Demo.Hierarchy.Animal" in line)
    # Member line right after.
    assert "Eat()" in lines[animal_idx + 1]
    # Then a blank — the paragraph break.
    assert lines[animal_idx + 2] == ""


def test_no_blank_line_between_empty_types(csharp_dir):
    """Empty types (record / marker class with no body) stack tightly —
    introducing a blank between every empty declaration would defeat
    digest's compactness goal."""
    r = CSharpAdapter().parse(csharp_dir / "file_scoped_ns.cs")
    out = render_digest([r], DigestOptions())
    lines = out.splitlines()
    # `record UserDto` and `record Vec2` are both bodyless and adjacent
    # in the source.
    user_dto_idx = next(i for i, line in enumerate(lines) if "record Demo.Services.UserDto" in line)
    # Next non-blank line should be `record Vec2`, NOT a blank.
    assert "record Demo.Services.Vec2" in lines[user_dto_idx + 1]


# --- Type modifiers -----------------------------------------------------


def test_type_modifier_extracted_from_signature(csharp_dir):
    """`abstract class Foo` in source — the `abstract` modifier is in
    the signature line and should appear before the kind keyword in the
    digest header. Otherwise the agent can't tell instantiable types
    from abstract ones at a glance."""
    r = CSharpAdapter().parse(csharp_dir / "hierarchy.cs")
    out = render_digest([r], DigestOptions())
    assert "abstract class Demo.Hierarchy.Animal" in out


def test_static_class_modifier_surfaces(csharp_dir):
    """C# `static class` is a meaningful semantic — only static
    members allowed, can't be instantiated. Must show in digest."""
    r = CSharpAdapter().parse(csharp_dir / "file_scoped_ns.cs")
    out = render_digest([r], DigestOptions())
    assert "static class Demo.Services.UserExtensions" in out


def test_multiple_modifiers_stack(java_dir):
    """Java `static final` (or any combination) — both modifiers
    surface in source order before the kind keyword."""
    r = JavaAdapter().parse(java_dir / "user_service.java")
    out = render_digest([r], DigestOptions())
    # `static final class Inner` lives in the fixture.
    assert "static final class" in out


def test_visibility_keywords_excluded_from_modifiers(csharp_dir):
    """`public` / `private` / `protected` / `internal` are visibility,
    handled by the visibility filter — they must NOT appear as
    modifiers, otherwise every header line would carry redundant
    `public`."""
    r = CSharpAdapter().parse(csharp_dir / "hierarchy.cs")
    out = render_digest([r], DigestOptions())
    # No `public class` — even though the source says `public class Animal`,
    # the digest must drop visibility keywords.
    assert "public class" not in out
    assert "public abstract class" not in out


# --- Type attrs prefix --------------------------------------------------


def test_type_attrs_render_before_keyword(csharp_dir):
    """C# `[RequireComponent(...)]` attrs surface before the kind
    keyword, in the source-natural order: `[Attr] class Name`. Without
    them the agent reads framework-bound types as if they had no
    runtime contract."""
    r = CSharpAdapter().parse(csharp_dir / "unity_behaviour.cs")
    out = render_digest([r], DigestOptions())
    assert "[RequireComponent(typeof(Rigidbody2D))] class Demo.Combat.HeroController" in out


def test_python_decorator_renders_before_class(python_dir):
    """`@dataclass class Point` style — the decorator is part of the
    type's identity; without it `class Point` reads as a regular
    class, not a value record."""
    r = PythonAdapter().parse(python_dir / "domain_model.py")
    out = render_digest([r], DigestOptions())
    assert "@dataclass class User" in out


def test_rust_derive_attr_renders_before_struct(rust_dir):
    """Rust `#[derive(Debug, Clone)]` is the canonical "this struct
    auto-implements these traits" signal. Must surface in digest so
    the agent doesn't think it has to write an impl by hand."""
    r = RustAdapter().parse(rust_dir / "user_service.rs")
    out = render_digest([r], DigestOptions())
    assert "#[derive(Debug, Clone)] struct User" in out


def test_multiple_attrs_render_space_separated(rust_dir):
    """A struct with two attrs (`#[derive(Debug)]` + `#[repr(C)]`) shows
    both, joined by a single space — the source-natural form for
    inline attribute groups."""
    r = RustAdapter().parse(rust_dir / "comments_edge.rs")
    out = render_digest([r], DigestOptions())
    assert "#[derive(Debug)] #[repr(C)] struct InterleavedDocAttrs" in out


# --- Deprecated marker --------------------------------------------------


def test_deprecated_type_carries_tag(java_dir):
    """`@Deprecated` on a Java class surfaces as a compact
    `[deprecated]` tag after the type name. Without it, the agent will
    happily recommend retired APIs."""
    r = JavaAdapter().parse(java_dir / "user_service.java")
    out = render_digest([r], DigestOptions())
    # UserService is annotated `@Deprecated(since = "2.0", ...)`.
    assert "[deprecated]" in out
    # And specifically attaches to UserService, not some other type.
    user_service_lines = [
        line for line in out.splitlines()
        if "UserService" in line and "Inner" not in line and "Callback" not in line
    ]
    assert any("[deprecated]" in line for line in user_service_lines)


def test_kotlin_deprecated_type_carries_tag(kotlin_dir):
    """Kotlin `@Deprecated("use V2")` on a class surfaces as
    `[deprecated]` tag — same pattern as Java/Rust/C#."""
    r = KotlinAdapter().parse(kotlin_dir / "user_service.kt")
    out = render_digest([r], DigestOptions())
    user_service_lines = [
        line for line in out.splitlines()
        if "UserService" in line and "Inner" not in line and "Callback" not in line and "Companion" not in line
    ]
    assert any("[deprecated]" in line for line in user_service_lines)


def test_deprecation_attr_filtered_from_visible_attrs(java_dir):
    """When deprecation triggers the `[deprecated]` tag, the
    underlying `@Deprecated(...)` attr must NOT also be printed in
    the visible attrs prefix — same signal twice is noise. Other
    attrs (e.g. `@Service`) stay visible."""
    r = JavaAdapter().parse(java_dir / "user_service.java")
    out = render_digest([r], DigestOptions())
    # `@Service` should still appear (it's not a deprecation marker).
    assert "@Service" in out
    # `@Deprecated(...)` should NOT appear — replaced by the tag.
    assert "@Deprecated(" not in out


def test_is_deprecated_helper_recognises_each_pattern():
    """`_is_deprecated` accepts every common deprecation syntax across
    languages. Case-insensitive substring match keeps the rule simple
    and forgiving (`@deprecated`, `@Deprecated`, `[Obsolete]`,
    `[Obsolete("reason")]`, `#[deprecated]`, `#[deprecated(since=...)]`)."""
    cases = [
        "@Deprecated",
        '@Deprecated(since = "2.0")',
        "@deprecated",
        "[Obsolete]",
        '[Obsolete("Use NewMethod instead")]',
        "#[deprecated]",
        '#[deprecated(since = "1.2")]',
    ]
    for attr_text in cases:
        d = Declaration(
            kind=KIND_CLASS, name="X", signature="class X", attrs=[attr_text]
        )
        assert _is_deprecated(d), f"failed to detect deprecation in {attr_text!r}"


def test_is_deprecated_does_not_false_positive():
    """An attr that incidentally contains the word should NOT trigger
    the tag — but our cheap substring rule is permissive on purpose
    (a real attr literally named `Deprecated` IS a deprecation
    marker). We just check non-deprecation attrs stay clean."""
    d = Declaration(
        kind=KIND_CLASS, name="X", signature="class X",
        attrs=["@Component", "[Authorize]", "#[derive(Debug)]"],
    )
    assert not _is_deprecated(d)


def test_deprecated_member_carries_tag():
    """A deprecated METHOD must carry `[deprecated]` in its member
    token, separate from the overload count tag if present."""
    method = Declaration(
        kind=KIND_METHOD, name="OldFoo", signature="void OldFoo()",
        attrs=["@Deprecated"],
    )
    assert _member_token(method, count=1) == "OldFoo() [deprecated]"
    # With overloads — both tags surface independently.
    assert (
        _member_token(method, count=3) == "OldFoo() [3 overloads] [deprecated]"
    )


# --- Help drift guard ---------------------------------------------------


def test_help_digest_describes_actual_format():
    """`ast-outline help digest` documents the digest format. If the
    format changes but the help text is forgotten, agents copy-pasting
    from `--help` will hit a mismatch with real output. This guard
    fails when the help drifts from the rendered legend tokens.

    Mirrors `test_prompt_command.py`'s drift guard for AGENT_PROMPT —
    same pattern: assert the help body mentions the non-obvious format
    tokens by name."""
    from ast_outline.cli import GUIDE_DIGEST

    # Each token below is a stable contract surface — if the renderer
    # changes any of them, the help line that documents it must be
    # updated in the same commit.
    assert "name()" in GUIDE_DIGEST
    assert "[kind]" in GUIDE_DIGEST
    assert "[N overloads]" in GUIDE_DIGEST
    assert "[deprecated]" in GUIDE_DIGEST
    assert "abstract" in GUIDE_DIGEST  # modifier example
    assert "@dataclass" in GUIDE_DIGEST or "[Serializable]" in GUIDE_DIGEST
    assert ", " in GUIDE_DIGEST  # comma separator
    assert "blank line" in GUIDE_DIGEST  # paragraph-break rule


def test_truncation_marker_uses_parenthesised_count(csharp_dir):
    """Truncation marker is `... (N more)` — readable English. Earlier
    revisions used `... +N more` with a leading `+`, which collided
    with the (now-removed) `+` member prefix."""
    r = CSharpAdapter().parse(csharp_dir / "file_scoped_ns.cs")
    out = render_digest([r], DigestOptions(max_members_per_type=1))
    assert "(more)" in out or "more)" in out
    import re
    assert re.search(r"\.\.\.\s+\(\d+\s+more\)", out), out
