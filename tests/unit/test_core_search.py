"""Tests for find_symbols and find_implementations."""
from __future__ import annotations

from code_outline.adapters.csharp import CSharpAdapter
from code_outline.adapters.java import JavaAdapter
from code_outline.adapters.kotlin import KotlinAdapter
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


# --- transitive mode (default) across all inheriting languages ----------


def test_transitive_default_java_multilevel(java_dir):
    """Java: `implements Animal` in a file with 4 levels (Animal ← Dog
    ← Puppy ← Pomeranian) returns all 5 matches (Dog, Cat, Puppy, Mixed,
    Pomeranian). Each transitive match has a non-empty `via` chain."""
    r = JavaAdapter().parse(java_dir / "hierarchy.java")
    hits = find_implementations([r], "Animal")
    names = {h.name for h in hits}
    assert {"Dog", "Cat", "Puppy", "Pomeranian", "Mixed"}.issubset(names)

    by_name = {h.name: h for h in hits}
    assert by_name["Dog"].via == []          # direct
    assert by_name["Cat"].via == []          # direct
    assert by_name["Puppy"].via == ["Dog"]   # 1 level transitive
    assert by_name["Pomeranian"].via == ["Dog", "Puppy"]  # 2 levels
    assert by_name["Mixed"].via == ["Dog"]   # transitive via Dog


def test_transitive_default_csharp_deep(csharp_dir):
    """C# class chain + interface chain both traversed transitively."""
    r = CSharpAdapter().parse(csharp_dir / "hierarchy.cs")

    # Class chain
    hits = find_implementations([r], "Animal")
    names = {h.name for h in hits}
    assert {"Dog", "Cat", "Puppy", "Pomeranian"}.issubset(names)
    pom = next(h for h in hits if h.name == "Pomeranian")
    assert pom.via == ["Dog", "Puppy"]

    # Interface chain: IService ← IReadService ← UserService (transitive).
    ihits = find_implementations([r], "IService")
    inames = {h.name for h in ihits}
    assert "IReadService" in inames
    assert "UserService" in inames
    us = next(h for h in ihits if h.name == "UserService")
    assert us.via == ["IReadService"]


def test_transitive_default_python(python_dir):
    """Python Animal → Dog → Puppy → Pomeranian chain."""
    r = PythonAdapter().parse(python_dir / "hierarchy.py")
    hits = find_implementations([r], "Animal")
    names = {h.name for h in hits}
    assert {"Dog", "Cat", "Puppy", "Pomeranian"}.issubset(names)
    pom = next(h for h in hits if h.name == "Pomeranian")
    assert pom.via == ["Dog", "Puppy"]


def test_transitive_default_typescript(fixtures_dir):
    """TypeScript class + interface chains."""
    from code_outline.adapters.typescript import TypeScriptAdapter
    r = TypeScriptAdapter().parse(fixtures_dir / "typescript" / "hierarchy.ts")

    hits = find_implementations([r], "Animal")
    names = {h.name for h in hits}
    assert {"Dog", "Cat", "Puppy", "Pomeranian"}.issubset(names)
    pom = next(h for h in hits if h.name == "Pomeranian")
    assert pom.via == ["Dog", "Puppy"]

    # Interface chain
    ihits = find_implementations([r], "IService")
    inames = {h.name for h in ihits}
    assert {"IReadService", "UserService"}.issubset(inames)


def test_transitive_default_kotlin(kotlin_dir):
    """Kotlin: Animal ← Dog ← Puppy ← Pomeranian plus `object Rex : Dog(...)`
    and `data class Husky : Dog(...)`. All five subclasses should surface;
    the two grandchildren carry a `[via Dog]` annotation."""
    r = KotlinAdapter().parse(kotlin_dir / "hierarchy.kt")
    hits = find_implementations([r], "Animal")
    names = {h.name for h in hits}
    # Direct children of Animal: Dog + Skater; transitive: Puppy, Pomeranian, Rex, Husky
    assert {"Dog", "Skater", "Puppy", "Pomeranian", "Rex", "Husky"}.issubset(names)

    by_name = {h.name: h for h in hits}
    assert by_name["Dog"].via == []
    assert by_name["Skater"].via == []
    assert by_name["Puppy"].via == ["Dog"]
    assert by_name["Pomeranian"].via == ["Dog", "Puppy"]
    # `object Rex` and `data class Husky` still appear in implements results —
    # objects and data classes both map onto types the BFS walks over.
    assert by_name["Rex"].via == ["Dog"]
    assert by_name["Husky"].via == ["Dog"]

    # Interface inheritance — `class Skater : Animal("s"), Movable`.
    ihits = find_implementations([r], "Movable")
    inames = {h.name for h in ihits}
    assert "Skater" in inames


# --- --direct flag behaviour --------------------------------------------


def test_direct_flag_excludes_transitive_java(java_dir):
    """With transitive=False, grandchildren must be dropped."""
    r = JavaAdapter().parse(java_dir / "hierarchy.java")
    direct = find_implementations([r], "Animal", transitive=False)
    names = {h.name for h in direct}
    assert "Dog" in names
    assert "Cat" in names
    # Grandchildren should NOT appear in direct-only mode
    assert "Puppy" not in names
    assert "Pomeranian" not in names
    # All matches have empty `via` when transitive is off
    for h in direct:
        assert h.via == []


def test_direct_flag_python(python_dir):
    r = PythonAdapter().parse(python_dir / "hierarchy.py")
    direct = find_implementations([r], "Animal", transitive=False)
    names = {h.name for h in direct}
    assert names == {"Dog", "Cat"}


def test_direct_flag_kotlin(kotlin_dir):
    """Kotlin `--direct` trims grandchildren and transitive object/data subclasses."""
    r = KotlinAdapter().parse(kotlin_dir / "hierarchy.kt")
    direct = find_implementations([r], "Animal", transitive=False)
    names = {h.name for h in direct}
    assert "Dog" in names
    assert "Skater" in names
    # Grandchildren of Animal (via Dog) must be absent
    assert "Puppy" not in names
    assert "Pomeranian" not in names
    assert "Rex" not in names
    assert "Husky" not in names
    for h in direct:
        assert h.via == []


# --- Cross-file / cross-directory ---------------------------------------


def test_transitive_walks_across_files_and_directories(java_dir):
    """Animal in base/, Dog & Puppy in mammals/, Cat in felines/.
    Parsing the whole multidir/ tree must connect the chain across
    directory boundaries — no matching by filename, just by declared
    type name inside the IR."""
    from code_outline.adapters import collect_files

    multidir = java_dir / "multidir"
    files = collect_files([multidir])
    results = [JavaAdapter().parse(f) for f in files if f.suffix == ".java"]

    hits = find_implementations(results, "Animal")
    names = {h.name for h in hits}
    assert {"Dog", "Cat", "Puppy"}.issubset(names), f"got {names}"

    puppy = next(h for h in hits if h.name == "Puppy")
    assert puppy.via == ["Dog"]
    # Puppy is declared in mammals/Puppy.java — paths in the IR reflect
    # the actual file, not something inferred from the class name.
    assert "mammals" in puppy.path
    assert puppy.path.endswith("Puppy.java")

    # Dog is in a different directory than Animal (mammals vs base).
    dog = next(h for h in hits if h.name == "Dog")
    cat = next(h for h in hits if h.name == "Cat")
    assert "mammals" in dog.path
    assert "felines" in cat.path


def test_transitive_walks_across_directories_kotlin(kotlin_dir):
    """Kotlin variant of the cross-directory test — Animal in base/, Dog &
    Puppy in mammals/, Cat in felines/. BFS must connect them regardless
    of directory layout or Kotlin's file-package decoupling (a Kotlin
    file can contain any package; there's no filename↔class mapping)."""
    from code_outline.adapters import collect_files

    multidir = kotlin_dir / "multidir"
    files = collect_files([multidir])
    results = [KotlinAdapter().parse(f) for f in files if f.suffix in {".kt", ".kts"}]

    hits = find_implementations(results, "Animal")
    names = {h.name for h in hits}
    assert {"Dog", "Cat", "Puppy"}.issubset(names), f"got {names}"

    puppy = next(h for h in hits if h.name == "Puppy")
    assert puppy.via == ["Dog"]
    assert "mammals" in puppy.path
    assert puppy.path.endswith("Puppy.kt")

    dog = next(h for h in hits if h.name == "Dog")
    cat = next(h for h in hits if h.name == "Cat")
    assert "mammals" in dog.path
    assert "felines" in cat.path


# --- Cycle safety -------------------------------------------------------


def test_cycle_safety_self_reference(java_dir):
    """`class Loopy extends Loopy` is nonsense but syntactically valid —
    the BFS must not loop forever on it."""
    r = JavaAdapter().parse(java_dir / "hierarchy.java")
    # Searching for Loopy finds Loopy itself (it has Loopy in its bases).
    # Must return and not hang.
    hits = find_implementations([r], "Loopy")
    # Loopy does match its own base name; just check we terminate and
    # don't explode the result list.
    assert len(hits) < 10


# --- ImplMatch.via is empty for direct queries --------------------------


def test_direct_matches_have_empty_via(csharp_dir):
    """A class whose bases[] contains the target is a direct match and
    must have via=[]."""
    r = CSharpAdapter().parse(csharp_dir / "unity_behaviour.cs")
    hits = find_implementations([r], "IDamageable")
    assert hits
    for h in hits:
        assert h.via == []


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
