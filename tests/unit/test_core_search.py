"""Tests for find_symbols."""
from __future__ import annotations

import pytest

from ast_outline.adapters.csharp import CSharpAdapter
from ast_outline.adapters.go import GoAdapter
from ast_outline.adapters.java import JavaAdapter
from ast_outline.adapters.kotlin import KotlinAdapter
from ast_outline.adapters.markdown import MarkdownAdapter
from ast_outline.adapters.python import PythonAdapter
from ast_outline.adapters.rust import RustAdapter
from ast_outline.adapters.scala import ScalaAdapter
from ast_outline.adapters.typescript import TypeScriptAdapter
from ast_outline.core import find_symbols


# --- find_symbols --------------------------------------------------------


def test_find_symbols_short_name_matches(csharp_dir):
    r = CSharpAdapter().parse(csharp_dir / "unity_behaviour.cs")
    matches = find_symbols(r, "TakeDamage")
    # One in HeroController, one in the IDamageable interface
    assert len(matches) == 2
    names = [m.qualified_name for m in matches]
    assert any("HeroController.TakeDamage" in n for n in names)
    assert any("IDamageable.TakeDamage" in n for n in names)


def test_find_symbols_class_qualified_disambiguates(csharp_dir):
    r = CSharpAdapter().parse(csharp_dir / "unity_behaviour.cs")
    matches = find_symbols(r, "HeroController.TakeDamage")
    assert len(matches) == 1
    assert matches[0].qualified_name.endswith("HeroController.TakeDamage")


def test_find_symbols_single_segment_returns_all_same_name(csharp_dir):
    """Single-segment suffix match returns every declaration with that tail —
    in C# the class and its ctor share the name, so both are returned."""
    r = CSharpAdapter().parse(csharp_dir / "unity_behaviour.cs")
    matches = find_symbols(r, "HeroController")
    kinds = sorted(m.kind for m in matches)
    assert "class" in kinds
    assert "ctor" in kinds
    # The class match includes the XML doc; the ctor match is a single line.
    class_match = next(m for m in matches if m.kind == "class")
    assert "public class HeroController" in class_match.source


def test_find_symbols_no_match_returns_empty(csharp_dir):
    r = CSharpAdapter().parse(csharp_dir / "unity_behaviour.cs")
    assert find_symbols(r, "DoesNotExist") == []


def test_find_symbols_source_includes_leading_doc(csharp_dir):
    r = CSharpAdapter().parse(csharp_dir / "unity_behaviour.cs")
    [match] = find_symbols(r, "HeroController.TakeDamage")
    # The ///-comment ABOVE the signature should be included in the slice.
    assert "/// <summary>Apply damage" in match.source
    assert "public void TakeDamage" in match.source


def test_find_symbols_python_method(python_dir):
    r = PythonAdapter().parse(python_dir / "domain_model.py")
    matches = find_symbols(r, "UserService.get")
    assert len(matches) == 1
    assert "def get" in matches[0].source


def test_find_symbols_python_includes_decorators(python_dir):
    """decorated_definition byte range must start at the decorator line."""
    r = PythonAdapter().parse(python_dir / "decorators_edge.py")
    [match] = find_symbols(r, "Widget.compute")
    assert "@tracing" in match.source
    assert "@functools.lru_cache" in match.source
    assert "def compute" in match.source


# --- find_symbols: `show <Type>` returns the WHOLE body -----------------
#
# Regression guard: every code-language adapter must emit a top-level type
# Declaration whose `start_byte..end_byte` covers the full body, not just
# the signature line. If anyone refactors an adapter to bound a type at
# the end of its header, `show <ClassName>` would silently start returning
# truncated bodies — these tests catch that per language.
#
# Each case picks a target from a fixture file that holds MULTIPLE sibling
# types — also exercising the case the prompt advertises ("multiple types
# in one file"). The slice must contain three markers in order: the
# signature, an inner member, and the closing token.


_WHOLE_TYPE_CASES = [
    pytest.param(
        CSharpAdapter, "csharp/hierarchy.cs", "UserService", "class",
        "public class UserService : IReadService",
        "public void Run() {}",
        "public object Read() => null;",
        id="csharp",
    ),
    pytest.param(
        PythonAdapter, "python/hierarchy.py", "FileReader", "class",
        "class FileReader(SizedReadable):",
        "def read(self) -> str:",
        "return 0",
        id="python",
    ),
    pytest.param(
        TypeScriptAdapter, "typescript/hierarchy.ts", "UserService", "class",
        "export class UserService implements IReadService",
        "run() {}",
        "read() { return null; }",
        id="typescript",
    ),
    pytest.param(
        JavaAdapter, "java/hierarchy.java", "Pomeranian", "class",
        "public class Pomeranian extends Puppy",
        "public void yap() {}",
        "}",
        id="java",
    ),
    pytest.param(
        KotlinAdapter, "kotlin/hierarchy.kt", "Skater", "class",
        'class Skater : Animal("s"), Movable',
        "override fun move(distance: Int) = distance * 2",
        "}",
        id="kotlin",
    ),
    pytest.param(
        ScalaAdapter, "scala/hierarchy.scala", "Skater", "class",
        'class Skater extends Animal("s") with Movable',
        "override def move(distance: Int): Int = distance * 2",
        "}",
        id="scala",
    ),
    pytest.param(
        GoAdapter, "go/hierarchy.go", "Walker", "interface",
        "type Walker interface",
        # Tab-indented form — the doc comment also says "adds Walk()." so
        # the bare "Walk()" substring would match the comment before the
        # signature. The interface body uses leading tabs.
        "\tWalk()",
        "}",
        id="go",
    ),
    pytest.param(
        RustAdapter, "rust/hierarchy.rs", "PackAnimal", "interface",
        "pub trait PackAnimal: Quadruped",
        "fn pack_size(&self) -> u32;",
        "}",
        id="rust",
    ),
    pytest.param(
        MarkdownAdapter, "markdown/article.md", "The Argument", "heading",
        "## The Argument",
        "### Second Point",
        "Details of the third point.",
        id="markdown",
    ),
]


@pytest.mark.parametrize(
    "adapter_cls, fixture_subpath, target, expected_kind, "
    "sig_marker, mid_marker, end_marker",
    _WHOLE_TYPE_CASES,
)
def test_find_symbols_returns_whole_type_body(
    fixtures_dir,
    adapter_cls,
    fixture_subpath,
    target,
    expected_kind,
    sig_marker,
    mid_marker,
    end_marker,
):
    r = adapter_cls().parse(fixtures_dir / fixture_subpath)
    matches = [m for m in find_symbols(r, target) if m.kind == expected_kind]
    assert len(matches) == 1, (
        f"expected exactly one {expected_kind} match for {target!r} in "
        f"{fixture_subpath}, got {len(matches)}: "
        f"{[(m.qualified_name, m.kind) for m in matches]}"
    )
    [match] = matches
    src = match.source
    i_sig = src.find(sig_marker)
    i_mid = src.find(mid_marker)
    # rfind for the end marker — closing braces appear multiple times in
    # bodies (inner method braces, etc.); the relevant one is the LAST.
    i_end = src.rfind(end_marker)
    assert i_sig != -1, f"signature marker missing: {sig_marker!r}\n---\n{src}"
    assert i_mid != -1, f"body marker missing: {mid_marker!r}\n---\n{src}"
    assert i_end != -1, f"end marker missing: {end_marker!r}\n---\n{src}"
    assert i_sig < i_mid <= i_end, (
        f"markers out of expected order — slice may not cover full body. "
        f"sig@{i_sig}, mid@{i_mid}, end@{i_end}\n---\n{src}"
    )


# --- ancestor_signatures (breadcrumbs for `show`) ------------------------


def test_find_symbols_populates_ancestor_signatures_for_nested(csharp_dir):
    """A method on a class inside a namespace reports both enclosing
    signatures, outer-to-inner."""
    r = CSharpAdapter().parse(csharp_dir / "unity_behaviour.cs")
    [match] = find_symbols(r, "HeroController.TakeDamage")
    assert len(match.ancestor_signatures) == 2
    outer, inner = match.ancestor_signatures
    assert outer.startswith("namespace ")
    assert "class HeroController" in inner


def test_find_symbols_top_level_has_no_ancestors():
    """A top-level declaration (no enclosing type/namespace) reports empty
    ancestor_signatures."""
    from pathlib import Path
    fixtures = Path(__file__).parent.parent / "fixtures"
    from ast_outline.adapters.java import JavaAdapter
    r = JavaAdapter().parse(fixtures / "java" / "no_package.java")
    [cls_match] = [m for m in find_symbols(r, "Top") if m.kind == "class"]
    assert cls_match.ancestor_signatures == []


def test_find_symbols_deeply_nested_reports_full_chain(java_dir):
    """Method on a nested class inside a package: package → outer → inner."""
    from ast_outline.adapters.java import JavaAdapter
    r = JavaAdapter().parse(java_dir / "user_service.java")
    # UserService.Inner.value — picks both the `value` field and the
    # `value()` method; assert on the method one.
    method_match = next(
        m for m in find_symbols(r, "Inner.value") if m.kind == "method"
    )
    # ancestors: package, UserService, Inner
    assert len(method_match.ancestor_signatures) == 3
    assert method_match.ancestor_signatures[0].startswith("package ")
    assert "class UserService" in method_match.ancestor_signatures[1]
    assert "class Inner" in method_match.ancestor_signatures[2]


def test_find_symbols_ancestor_signatures_strip_attributes(java_dir):
    """Ancestor signatures must NOT contain the `@Annotation` prefix —
    attrs live in a separate Declaration field and aren't in `.signature`.
    Keeps the breadcrumb line short and readable."""
    from ast_outline.adapters.java import JavaAdapter
    r = JavaAdapter().parse(java_dir / "user_service.java")
    [match] = find_symbols(r, "UserService.save")
    # UserService has @Service @Deprecated — should NOT leak into breadcrumb
    for sig in match.ancestor_signatures:
        assert not sig.lstrip().startswith("@")


# --- find_symbols: markdown substring matching --------------------------


def test_markdown_substring_matches_decorated_heading(md_dir):
    """`"ТЕКУЩИЙ АНАЛИЗ"` should match `"1. ТЕКУЩИЙ АНАЛИЗ (февраль 2026)"`.

    The markdown contract is loosened to substring containment so that LLM
    agents — which routinely don't remember number prefixes or trailing
    parens — can actually find sections by their meaningful core."""
    r = MarkdownAdapter().parse(md_dir / "decorated_headings.md")
    matches = find_symbols(r, "ТЕКУЩИЙ АНАЛИЗ")
    names = [m.qualified_name for m in matches]
    assert any("ТЕКУЩИЙ АНАЛИЗ (февраль 2026)" in n for n in names), names


def test_markdown_substring_is_case_insensitive(md_dir):
    """Casefold-based — works for non-ASCII and any combination of caps."""
    r = MarkdownAdapter().parse(md_dir / "decorated_headings.md")
    matches = find_symbols(r, "текущий анализ")
    assert len(matches) >= 1


def test_markdown_substring_returns_all_overlapping_hits(md_dir):
    """Querying a fragment shared by multiple headings returns all of them
    so the agent sees the disambiguation set rather than a silent first-hit."""
    r = MarkdownAdapter().parse(md_dir / "decorated_headings.md")
    matches = find_symbols(r, "АНАЛИЗ")
    # Both `1. ТЕКУЩИЙ АНАЛИЗ ...` and `2. РЕТРОСПЕКТИВНЫЙ АНАЛИЗ` should hit
    names = [m.qualified_name for m in matches]
    assert any("ТЕКУЩИЙ" in n for n in names), names
    assert any("РЕТРОСПЕКТИВНЫЙ" in n for n in names), names


def test_markdown_substring_with_dotted_path(md_dir):
    """Dotted queries still work — every part is a substring against the
    contiguous tail of the trail. `"ТЕКУЩИЙ.Политическая"` matches a nested
    heading whose parent contains "ТЕКУЩИЙ" and whose own title contains
    "Политическая"."""
    r = MarkdownAdapter().parse(md_dir / "decorated_headings.md")
    matches = find_symbols(r, "ТЕКУЩИЙ.Политическая")
    assert len(matches) == 1
    assert "Политическая ситуация" in matches[0].qualified_name


def test_code_symbol_matching_remains_exact(csharp_dir):
    """Substring relaxation must NOT leak into code-symbol lookups —
    that would silently broaden every search and break precision."""
    r = CSharpAdapter().parse(csharp_dir / "unity_behaviour.cs")
    # `TakeDam` is a substring of `TakeDamage` — but for code we only
    # accept full-segment equality, so this query should return zero hits.
    matches = find_symbols(r, "TakeDam")
    assert matches == []

