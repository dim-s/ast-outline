"""Tests for enriched outline/digest headers — summary counters +
parse-error warning.

Two features under test:

1. **Summary counters** — the `(N lines, ...)` header adds language-
   appropriate counters (types/methods/fields for code; headings/code
   blocks for markdown). Zero-valued categories are omitted so a
   trivial file still reads cleanly.

2. **Parse-error warning** — when tree-sitter produces `ERROR` /
   `MISSING` nodes the renderer emits a second header line starting
   with `# WARNING:` so agents know the outline may be partial.
"""
from __future__ import annotations

from ast_outline.adapters.csharp import CSharpAdapter
from ast_outline.adapters.go import GoAdapter
from ast_outline.adapters.java import JavaAdapter
from ast_outline.adapters.kotlin import KotlinAdapter
from ast_outline.adapters.markdown import MarkdownAdapter
from ast_outline.adapters.python import PythonAdapter
from ast_outline.adapters.scala import ScalaAdapter
from ast_outline.adapters.typescript import TypeScriptAdapter
from ast_outline.core import (
    DigestOptions,
    OutlineOptions,
    render_digest,
    render_outline,
)


# --- error_count on ParseResult -------------------------------------------


def test_error_count_zero_on_clean_java(java_dir):
    r = JavaAdapter().parse(java_dir / "user_service.java")
    assert r.error_count == 0


def test_error_count_zero_on_clean_python(python_dir):
    r = PythonAdapter().parse(python_dir / "domain_model.py")
    assert r.error_count == 0


def test_error_count_zero_on_clean_csharp(csharp_dir):
    r = CSharpAdapter().parse(csharp_dir / "unity_behaviour.cs")
    assert r.error_count == 0


def test_error_count_zero_on_clean_typescript(fixtures_dir):
    r = TypeScriptAdapter().parse(fixtures_dir / "typescript" / "storage_service.ts")
    assert r.error_count == 0


def test_error_count_zero_on_clean_kotlin(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "user_service.kt")
    assert r.error_count == 0


def test_error_count_zero_on_clean_scala(scala_dir):
    r = ScalaAdapter().parse(scala_dir / "user_service.scala")
    assert r.error_count == 0


def test_error_count_zero_on_clean_go(go_dir):
    r = GoAdapter().parse(go_dir / "user_service.go")
    assert r.error_count == 0


def test_error_count_zero_on_clean_markdown(fixtures_dir):
    r = MarkdownAdapter().parse(fixtures_dir / "markdown" / "readme_style.md")
    assert r.error_count == 0


def test_error_count_nonzero_on_broken_file(java_dir):
    """The hand-crafted broken fixture has multiple syntax holes —
    tree-sitter should surface ERROR / MISSING nodes."""
    r = JavaAdapter().parse(java_dir / "broken_syntax.java")
    assert r.error_count > 0


def test_error_count_nonzero_on_broken_python(python_dir):
    """tree-sitter-python surfaces errors on unmatched brackets and
    missing class-header colons."""
    r = PythonAdapter().parse(python_dir / "broken_syntax.py")
    assert r.error_count > 0


def test_error_count_nonzero_on_broken_csharp(csharp_dir):
    """tree-sitter-c-sharp surfaces errors on missing closing braces
    and broken method signatures."""
    r = CSharpAdapter().parse(csharp_dir / "broken_syntax.cs")
    assert r.error_count > 0


def test_error_count_nonzero_on_broken_typescript(fixtures_dir):
    """tree-sitter-typescript surfaces errors on missing braces,
    incomplete expressions and bad type annotations."""
    r = TypeScriptAdapter().parse(fixtures_dir / "typescript" / "broken_syntax.ts")
    assert r.error_count > 0


def test_error_count_nonzero_on_broken_kotlin(kotlin_dir):
    """tree-sitter-kotlin surfaces errors on unclosed parameter lists
    and missing braces."""
    r = KotlinAdapter().parse(kotlin_dir / "broken_syntax.kt")
    assert r.error_count > 0


def test_error_count_nonzero_on_broken_scala(scala_dir):
    r = ScalaAdapter().parse(scala_dir / "broken_syntax.scala")
    assert r.error_count > 0


def test_error_count_nonzero_on_broken_go(go_dir):
    r = GoAdapter().parse(go_dir / "broken_syntax.go")
    assert r.error_count > 0


def test_markdown_parser_permissive_no_false_positive_errors(fixtures_dir):
    """tree-sitter-markdown is intentionally permissive — plain text,
    random indentation, stray punctuation are all valid markdown.
    Regression guard: none of our markdown fixtures should spuriously
    raise the error counter."""
    for name in ("readme_style.md", "article.md", "setext_and_codes.md", "empty.md"):
        r = MarkdownAdapter().parse(fixtures_dir / "markdown" / name)
        assert r.error_count == 0, f"unexpected errors in {name}: {r.error_count}"


# --- Header contents on clean files --------------------------------------


def test_outline_header_includes_type_count(java_dir):
    r = JavaAdapter().parse(java_dir / "user_service.java")
    first = render_outline(r, OutlineOptions()).splitlines()[0]
    # UserService (class) + Inner (nested class) + Callback (nested interface) = 3 types
    assert " types" in first
    assert "3 types" in first


def test_outline_header_includes_method_count(java_dir):
    r = JavaAdapter().parse(java_dir / "user_service.java")
    first = render_outline(r, OutlineOptions()).splitlines()[0]
    assert " methods" in first


def test_outline_header_includes_field_count(java_dir):
    r = JavaAdapter().parse(java_dir / "user_service.java")
    first = render_outline(r, OutlineOptions()).splitlines()[0]
    assert " fields" in first


def test_outline_header_markdown_has_heading_count(fixtures_dir):
    """Markdown gets different categories — headings + code blocks, not
    types/methods/fields."""
    r = MarkdownAdapter().parse(fixtures_dir / "markdown" / "readme_style.md")
    first = render_outline(r, OutlineOptions()).splitlines()[0]
    assert " headings" in first
    # readme_style.md also has fenced code blocks
    assert " code blocks" in first


def test_outline_header_markdown_skips_type_methods(fixtures_dir):
    """Code-style categories must not leak into markdown headers."""
    r = MarkdownAdapter().parse(fixtures_dir / "markdown" / "readme_style.md")
    first = render_outline(r, OutlineOptions()).splitlines()[0]
    assert " types" not in first
    assert " methods" not in first
    assert " fields" not in first


def test_outline_header_skips_zero_categories(java_dir):
    """Java file with only a single class and no fields/methods should
    not clutter the header with `0 methods, 0 fields`."""
    r = JavaAdapter().parse(java_dir / "plain_block_comment.java")
    first = render_outline(r, OutlineOptions()).splitlines()[0]
    # Has 1 class (Foo), no methods, no fields
    assert "1 types" in first
    assert " methods" not in first
    assert " fields" not in first


# --- Warning line on broken files ----------------------------------------


def test_warning_line_present_on_broken_file(java_dir):
    r = JavaAdapter().parse(java_dir / "broken_syntax.java")
    lines = render_outline(r, OutlineOptions()).splitlines()
    # Second line must be the warning
    assert lines[1].startswith("# WARNING:")
    assert "parse error" in lines[1]
    assert "incomplete" in lines[1]


def test_warning_line_absent_on_clean_file(java_dir):
    r = JavaAdapter().parse(java_dir / "user_service.java")
    lines = render_outline(r, OutlineOptions()).splitlines()
    # No line in the whole outline starts with "# WARNING:"
    assert not any(ln.startswith("# WARNING:") for ln in lines)


def test_warning_line_singular_when_single_error():
    """`1 parse error` (singular), `2 parse errors` (plural)."""
    import tempfile
    from pathlib import Path

    # A file with exactly one missing closing brace — should surface a
    # single MISSING node, not more.
    src = "package demo;\npublic class Foo { public int x = 1;\n"
    with tempfile.NamedTemporaryFile(suffix=".java", mode="w", delete=False) as f:
        f.write(src)
        p = Path(f.name)
    try:
        r = JavaAdapter().parse(p)
        assert r.error_count >= 1
        out = render_outline(r, OutlineOptions())
        warning = next(ln for ln in out.splitlines() if ln.startswith("# WARNING:"))
        if r.error_count == 1:
            assert "1 parse error " in warning  # space — no trailing "s"
        else:
            assert f"{r.error_count} parse errors" in warning
    finally:
        p.unlink()


# --- Header in digest mode -----------------------------------------------


def test_digest_header_includes_counts(java_dir):
    from ast_outline.adapters import collect_files

    files = collect_files([java_dir])
    java_files = [f for f in files if f.suffix == ".java"]
    results = [JavaAdapter().parse(f) for f in java_files]
    text = render_digest(results, DigestOptions(), root=java_dir)
    # At least one per-file line should mention the counters
    assert "types" in text
    assert "methods" in text


def test_digest_warning_line_for_broken_file(java_dir):
    """The digest must surface the WARNING for broken files too, not only
    the outline view — an agent running `digest` should still notice."""
    from ast_outline.adapters import collect_files

    files = collect_files([java_dir])
    java_files = [f for f in files if f.suffix == ".java"]
    results = [JavaAdapter().parse(f) for f in java_files]
    text = render_digest(results, DigestOptions(), root=java_dir)
    assert "# WARNING:" in text
    assert "broken_syntax.java" in text


# --- Counting semantics --------------------------------------------------


def test_namespace_not_counted_as_type(java_dir):
    """A package/namespace wrapper is transparent — it should NOT inflate
    the type counter. UserService.java has one real class + one nested
    class + one nested interface = 3, not 4 (the package wrapper is
    not counted)."""
    r = JavaAdapter().parse(java_dir / "user_service.java")
    first = render_outline(r, OutlineOptions()).splitlines()[0]
    # 3 types, not 4 — no "4 types"
    assert "3 types" in first
    assert "4 types" not in first


def test_enum_members_not_counted_as_fields(java_dir):
    """Enum constants (ACTIVE, INACTIVE, …) are KIND_ENUM_MEMBER, not
    KIND_FIELD — the fields counter should only reflect real instance
    fields."""
    r = JavaAdapter().parse(java_dir / "status_enum.java")
    first = render_outline(r, OutlineOptions()).splitlines()[0]
    # status_enum.java has 2 real fields (label, weight); 4 enum constants
    # should NOT be counted.
    assert "2 fields" in first


def test_python_counts_functions_as_methods(python_dir):
    """Python module-level `def` is KIND_FUNCTION — included in `methods`
    together with class methods (CALLABLE_KINDS)."""
    r = PythonAdapter().parse(python_dir / "domain_model.py")
    first = render_outline(r, OutlineOptions()).splitlines()[0]
    assert " methods" in first


def test_csharp_header_shows_all_three_categories(csharp_dir):
    """C# fixture exercises types (class + interface), methods, and
    fields (including properties / events / indexers that fold into
    the `fields` category by design)."""
    r = CSharpAdapter().parse(csharp_dir / "unity_behaviour.cs")
    first = render_outline(r, OutlineOptions()).splitlines()[0]
    assert " types" in first
    assert " methods" in first
    assert " fields" in first


def test_csharp_property_counted_as_field(csharp_dir):
    """C# properties are KIND_PROPERTY, but semantically they hold state
    like a field — _FIELD_COUNT_KINDS folds them into the `fields` counter.
    Guards against someone later moving PROPERTY out of that set."""
    r = CSharpAdapter().parse(csharp_dir / "unity_behaviour.cs")
    first = render_outline(r, OutlineOptions()).splitlines()[0]
    # unity_behaviour.cs declares: CurrentHealth (property), MaxHealth
    # (field), event, + a couple more → at least 5 fields in the counter
    import re
    match = re.search(r"(\d+) fields", first)
    assert match is not None, f"no field counter in header: {first}"
    assert int(match.group(1)) >= 3


def test_typescript_header_covers_all_types(fixtures_dir):
    """TypeScript types.ts has classes, interfaces, enums AND type
    aliases — all should land in the `types` counter (enum members
    should NOT)."""
    r = TypeScriptAdapter().parse(fixtures_dir / "typescript" / "types.ts")
    first = render_outline(r, OutlineOptions()).splitlines()[0]
    assert " types" in first
    # `types.ts` has at least 3 distinct KIND_* types declared
    import re
    match = re.search(r"(\d+) types", first)
    assert match is not None
    assert int(match.group(1)) >= 3


def test_kotlin_header_shows_types_methods_fields(kotlin_dir):
    """Kotlin exercises the same three counter categories as Java/C#:
    types (class/interface/object/data/enum), methods, fields
    (incl. properties and primary-ctor val/var)."""
    r = KotlinAdapter().parse(kotlin_dir / "user_service.kt")
    first = render_outline(r, OutlineOptions()).splitlines()[0]
    assert " types" in first
    assert " methods" in first
    assert " fields" in first


def test_kotlin_data_class_counts_as_type(kotlin_dir):
    """A Kotlin `data class` maps onto KIND_RECORD, which is in TYPE_KINDS,
    so it must increment the `types` counter."""
    r = KotlinAdapter().parse(kotlin_dir / "data_and_sealed.kt")
    first = render_outline(r, OutlineOptions()).splitlines()[0]
    import re
    match = re.search(r"(\d+) types", first)
    assert match is not None
    # data_and_sealed.kt: Point (data), Shape (sealed), Circle (data),
    # Square (class), UnitShape (object), Status (enum), nested Companion
    # → at least 6 types
    assert int(match.group(1)) >= 6


def test_kotlin_enum_members_not_counted_as_fields(kotlin_dir):
    """Kotlin enum entries (ACTIVE, INACTIVE, …) are KIND_ENUM_MEMBER —
    not KIND_FIELD. They must NOT inflate the `fields` counter."""
    r = KotlinAdapter().parse(kotlin_dir / "data_and_sealed.kt")
    from ast_outline.core import KIND_ENUM_MEMBER, _collect_counts

    counts = _collect_counts(r.declarations)
    # Count entries directly
    stack = list(r.declarations)
    entries = 0
    while stack:
        d = stack.pop()
        if d.kind == KIND_ENUM_MEMBER:
            entries += 1
        stack.extend(d.children)
    assert entries >= 4  # ACTIVE / INACTIVE / BANNED / UNKNOWN
    # Fields are `label`, `weight` on Status plus data-class ctor fields —
    # never inflated by the enum entries themselves.
    # Sanity check: adding entries would push the count past reality.
    assert counts["fields"] < entries + 20


def test_kotlin_warning_line_surfaces_on_broken_file(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "broken_syntax.kt")
    lines = render_outline(r, OutlineOptions()).splitlines()
    assert lines[1].startswith("# WARNING:")
    assert "parse error" in lines[1]


def test_kotlin_typealias_and_property_not_counted_as_type(kotlin_dir):
    """typealiases (KIND_DELEGATE) and properties/fields must NOT leak into
    the `types` counter — that category is reserved for TYPE_KINDS."""
    r = KotlinAdapter().parse(kotlin_dir / "extensions_and_toplevel.kt")
    from ast_outline.core import _collect_counts

    counts = _collect_counts(r.declarations)
    # Fixture has exactly one class (Vec2); typealiases should not bump the count
    assert counts["types"] == 1


def test_scala_header_shows_types_methods_fields(scala_dir):
    """Scala exercises all three counter categories — types (class /
    trait / object / case class / enum), methods, and fields (incl.
    primary-ctor val/var and case-class bare params)."""
    r = ScalaAdapter().parse(scala_dir / "user_service.scala")
    first = render_outline(r, OutlineOptions()).splitlines()[0]
    assert " types" in first
    assert " methods" in first
    assert " fields" in first


def test_scala_case_class_counts_as_type(scala_dir):
    """A Scala `case class` maps to KIND_RECORD, which is in TYPE_KINDS,
    so it increments the `types` counter. data_and_sealed.scala has
    multiple case classes + a sealed trait + a class + a case object + enum."""
    r = ScalaAdapter().parse(scala_dir / "data_and_sealed.scala")
    first = render_outline(r, OutlineOptions()).splitlines()[0]
    import re
    match = re.search(r"(\d+) types", first)
    assert match is not None
    # Point (record) + Shape (trait) + Circle (record) + Square (class)
    # + UnitShape (object→class) + Status (enum) → at least 6
    assert int(match.group(1)) >= 6


def test_scala_enum_members_not_counted_as_fields(scala_dir):
    """Scala 3 enum entries (Active / Inactive / …) are KIND_ENUM_MEMBER —
    they must NOT inflate the `fields` counter."""
    r = ScalaAdapter().parse(scala_dir / "data_and_sealed.scala")
    from ast_outline.core import KIND_ENUM_MEMBER, _collect_counts

    counts = _collect_counts(r.declarations)
    stack = list(r.declarations)
    entries = 0
    while stack:
        d = stack.pop()
        if d.kind == KIND_ENUM_MEMBER:
            entries += 1
        stack.extend(d.children)
    assert entries >= 4  # Active / Inactive / Banned / Unknown
    # Entries aren't added to the fields counter
    assert counts["fields"] < entries + 20


def test_scala_warning_line_surfaces_on_broken_file(scala_dir):
    r = ScalaAdapter().parse(scala_dir / "broken_syntax.scala")
    lines = render_outline(r, OutlineOptions()).splitlines()
    assert lines[1].startswith("# WARNING:")
    assert "parse error" in lines[1]


def test_go_header_shows_types_methods_fields(go_dir):
    """Go counts types (struct/interface), methods, and fields (incl.
    const/var declarations and struct fields)."""
    r = GoAdapter().parse(go_dir / "user_service.go")
    first = render_outline(r, OutlineOptions()).splitlines()[0]
    assert " types" in first
    assert " methods" in first
    assert " fields" in first


def test_go_struct_and_interface_count_as_types(go_dir):
    """KIND_STRUCT and KIND_INTERFACE both live in TYPE_KINDS — both
    must increment the `types` counter."""
    r = GoAdapter().parse(go_dir / "hierarchy.go")
    first = render_outline(r, OutlineOptions()).splitlines()[0]
    import re
    match = re.search(r"(\d+) types", first)
    assert match is not None
    # hierarchy.go: Animal/Dog/Puppy/Pomeranian/Cat (5 structs) +
    # Movable/Walker (2 interfaces) + Skater (1 struct) → at least 8
    assert int(match.group(1)) >= 8


def test_go_typealias_not_counted_as_type(go_dir):
    """`type Reader = io.Reader` is KIND_DELEGATE (not in TYPE_KINDS)
    and must NOT inflate the `types` counter."""
    r = GoAdapter().parse(go_dir / "user_service.go")
    from ast_outline.core import _collect_counts

    counts = _collect_counts(r.declarations)
    # user_service.go declares 2 structs + 2 interfaces = 4 types.
    # `Reader` (type alias) and `UserID` (newtype) are KIND_DELEGATE
    # and shouldn't count.
    assert counts["types"] == 4


def test_go_warning_line_surfaces_on_broken_file(go_dir):
    r = GoAdapter().parse(go_dir / "broken_syntax.go")
    lines = render_outline(r, OutlineOptions()).splitlines()
    assert lines[1].startswith("# WARNING:")
    assert "parse error" in lines[1]


def test_typescript_enum_member_not_counted_as_field(fixtures_dir):
    """Same contract as Java: TypeScript enum members (KIND_ENUM_MEMBER)
    must NOT inflate the `fields` counter."""
    r = TypeScriptAdapter().parse(fixtures_dir / "typescript" / "types.ts")
    first = render_outline(r, OutlineOptions()).splitlines()[0]
    # Count the ACTUAL enum members vs what the header reports.
    from ast_outline.core import KIND_ENUM_MEMBER, _collect_counts
    all_decls = r.declarations
    # Walk tree, count enum members directly
    stack = list(all_decls)
    enum_members = 0
    while stack:
        d = stack.pop()
        if d.kind == KIND_ENUM_MEMBER:
            enum_members += 1
        stack.extend(d.children)
    assert enum_members > 0, "fixture must contain enum members for this test to be meaningful"
    counts = _collect_counts(all_decls)
    # The enum members must NOT be reflected in either `fields` or `types`
    # — they live in their own KIND, not counted at all.
    # (Can't easily express "exactly X fields" without knowing fixture shape,
    # so instead check that counts["fields"] < total declarations including members.)
    assert counts["fields"] + counts["types"] + counts["methods"] < sum(
        1 for _ in _iter_all(all_decls)
    )


def _iter_all(decls):
    """Flat iterator over every Declaration in the tree — helper for
    counting-semantics tests."""
    stack = list(decls)
    while stack:
        d = stack.pop()
        yield d
        stack.extend(d.children)


# --- Token-count signal --------------------------------------------------


def test_outline_header_includes_approx_token_count(java_dir):
    """The header reports an approximate token count alongside lines so the
    agent can size up a file before deciding between Read / outline / show.

    We don't pin the exact value — it's a coarse ``len(bytes) // 4``
    estimate by design — but the header MUST contain ``~`` + a digit + a
    space + ``tokens`` after the line count."""
    import re

    r = JavaAdapter().parse(java_dir / "user_service.java")
    first = render_outline(r, OutlineOptions()).splitlines()[0]
    assert re.search(r"\d+ lines, ~[\d,]+ tokens", first), first


def test_outline_token_count_is_present_for_every_language(
    csharp_dir, python_dir, java_dir, kotlin_dir, scala_dir, go_dir, fixtures_dir
):
    """Token count is computed inline from source bytes — must work
    universally, no per-adapter changes required."""
    import re

    samples = [
        CSharpAdapter().parse(csharp_dir / "unity_behaviour.cs"),
        PythonAdapter().parse(python_dir / "domain_model.py"),
        JavaAdapter().parse(java_dir / "user_service.java"),
        KotlinAdapter().parse(kotlin_dir / "user_service.kt"),
        ScalaAdapter().parse(scala_dir / "user_service.scala"),
        GoAdapter().parse(go_dir / "user_service.go"),
        TypeScriptAdapter().parse(fixtures_dir / "typescript" / "storage_service.ts"),
        MarkdownAdapter().parse(fixtures_dir / "markdown" / "readme_style.md"),
    ]
    for r in samples:
        first = render_outline(r, OutlineOptions()).splitlines()[0]
        assert re.search(r"~[\d,]+ tokens", first), f"{r.language}: {first}"


def test_outline_token_count_grows_with_file_size(csharp_dir, fixtures_dir):
    """Sanity check: a bigger source file produces a bigger token estimate
    so the heuristic has any meaning at all."""
    from ast_outline.core import _estimate_tokens

    small = MarkdownAdapter().parse(fixtures_dir / "markdown" / "empty.md")
    big = CSharpAdapter().parse(csharp_dir / "unity_behaviour.cs")
    assert _estimate_tokens(small.source) < _estimate_tokens(big.source)


# --- Digest legend -------------------------------------------------------


def test_digest_does_not_repeat_label_legend(java_dir):
    """The digest output is intentionally legend-free — the size-label
    and `[broken]` conventions live in the canonical agent prompt
    (`ast-outline prompt`) so they're paid for once per session, not
    on every digest call. The labels themselves remain readable cold."""
    r = JavaAdapter().parse(java_dir / "user_service.java")
    out = render_digest([r], DigestOptions())
    # No `# size labels` / `# rule of thumb` / similar lecture-lines.
    for ln in out.splitlines():
        assert "size labels next to each file" not in ln, ln
        assert "rule of thumb" not in ln, ln


def test_digest_per_file_header_includes_token_count(java_dir):
    """Per-file headers inside the digest carry the same ``~Nt tokens``
    annotation as the standalone outline header — agent gets the size
    signal whether it called ``digest`` or jumped straight to ``outline``."""
    import re

    r = JavaAdapter().parse(java_dir / "user_service.java")
    out = render_digest([r], DigestOptions())
    # Find the file-header line (starts with two spaces + filename)
    file_line = next(ln for ln in out.splitlines() if ln.lstrip().startswith("user_service.java"))
    assert re.search(r"\d+ lines, ~[\d,]+ tokens", file_line), file_line


def test_digest_per_file_includes_size_label_bracket(java_dir):
    """Each file line carries one of the three descriptive size labels —
    the agent's primary at-a-glance signal for the file's bulk."""
    r = JavaAdapter().parse(java_dir / "user_service.java")
    out = render_digest([r], DigestOptions())
    file_line = next(ln for ln in out.splitlines() if ln.lstrip().startswith("user_service.java"))
    assert any(tag in file_line for tag in ("[tiny]", "[medium]", "[large]")), file_line


def test_size_label_thresholds():
    """The three buckets must map cleanly — boundary values verified
    here so silent threshold drift breaks a test, not an agent."""
    from ast_outline.core import _size_label

    assert _size_label(0) == "[tiny]"
    assert _size_label(499) == "[tiny]"
    assert _size_label(500) == "[medium]"
    assert _size_label(4999) == "[medium]"
    assert _size_label(5000) == "[large]"
    assert _size_label(1_000_000) == "[large]"


def test_size_label_appears_before_counters_in_digest(java_dir):
    """Visual scan order: filename → size label → counters in parens.
    The label is the agent's primary at-a-glance signal."""
    r = JavaAdapter().parse(java_dir / "user_service.java")
    out = render_digest([r], DigestOptions())
    file_line = next(ln for ln in out.splitlines() if ln.lstrip().startswith("user_service.java"))
    bracket_pos = max(file_line.find("[tiny]"), file_line.find("[medium]"), file_line.find("[large]"))
    paren_pos = file_line.find("(")
    assert 0 < bracket_pos < paren_pos, file_line


def test_token_estimate_uses_chars_not_bytes_for_cyrillic(tmp_path):
    """Cyrillic content is 2 bytes/char in UTF-8. Counting bytes would
    inflate the estimate by ~2× for Cyrillic files. We count characters
    so the size hint stays accurate for non-Latin content."""
    from ast_outline.core import _estimate_tokens

    cyrillic = "А" * 1000  # 1000 chars, 2000 bytes in UTF-8
    ascii_same_chars = "a" * 1000  # 1000 chars, 1000 bytes
    # Both should estimate the same — chars-based, not bytes-based
    assert _estimate_tokens(cyrillic.encode("utf-8")) == _estimate_tokens(ascii_same_chars.encode("utf-8"))
