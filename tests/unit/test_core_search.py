"""Tests for find_symbols and find_implementations."""
from __future__ import annotations

from code_outline.adapters.csharp import CSharpAdapter
from code_outline.adapters.python import PythonAdapter
from code_outline.core import (
    find_implementations,
    find_symbols,
    _normalize_type_name,
)


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
    from code_outline.adapters.java import JavaAdapter
    r = JavaAdapter().parse(fixtures / "java" / "no_package.java")
    [cls_match] = [m for m in find_symbols(r, "Top") if m.kind == "class"]
    assert cls_match.ancestor_signatures == []


def test_find_symbols_deeply_nested_reports_full_chain(java_dir):
    """Method on a nested class inside a package: package → outer → inner."""
    from code_outline.adapters.java import JavaAdapter
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
    from code_outline.adapters.java import JavaAdapter
    r = JavaAdapter().parse(java_dir / "user_service.java")
    [match] = find_symbols(r, "UserService.save")
    # UserService has @Service @Deprecated — should NOT leak into breadcrumb
    for sig in match.ancestor_signatures:
        assert not sig.lstrip().startswith("@")


# --- find_implementations -----------------------------------------------


def test_find_implementations_finds_interface_impl(csharp_dir):
    a = CSharpAdapter().parse(csharp_dir / "unity_behaviour.cs")
    hits = find_implementations([a], "IDamageable")
    assert len(hits) == 1
    assert hits[0].name == "HeroController"


def test_find_implementations_strips_generics(csharp_dir):
    """`IRepository<UserDto>` should match a query for `IRepository`."""
    r = CSharpAdapter().parse(csharp_dir / "file_scoped_ns.cs")
    hits = find_implementations([r], "IRepository")
    names = [h.name for h in hits]
    assert "UserRepository" in names


def test_find_implementations_ignores_non_matches(csharp_dir):
    r = CSharpAdapter().parse(csharp_dir / "unity_behaviour.cs")
    hits = find_implementations([r], "SomethingUnrelated")
    assert hits == []


def test_find_implementations_python(python_dir):
    r = PythonAdapter().parse(python_dir / "domain_model.py")
    hits = find_implementations([r], "BaseEntity")
    names = [h.name for h in hits]
    assert "User" in names


# --- _normalize_type_name -----------------------------------------------


def test_normalize_strips_csharp_generics():
    assert _normalize_type_name("IRepository<UserDto>") == "IRepository"
    assert _normalize_type_name("System.Collections.Generic.List<T>") == "List"


def test_normalize_strips_python_generics():
    assert _normalize_type_name("List[int]") == "List"
    assert _normalize_type_name("abc.ABCMeta") == "ABCMeta"


def test_normalize_plain_name_unchanged():
    assert _normalize_type_name("IDamageable") == "IDamageable"
    assert _normalize_type_name("  IDamageable  ") == "IDamageable"
