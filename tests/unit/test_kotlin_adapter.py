"""Tests for the Kotlin adapter.

Covers Kotlin-specific ground that Java tests don't exercise:
- `package` → namespace absorbing top-level declarations
- `class` / `interface` / `fun interface` / `object` / `companion object`
- `data` / `sealed` / `enum` / `annotation` class variants
- primary-constructor val/var components → implicit fields
- secondary constructors + `init` blocks (init blocks are anonymous, skipped)
- `val`/`var` properties: plain storage vs. custom getter/setter (FIELD vs PROPERTY)
- top-level functions + extension functions (receiver preserved in signature)
- `suspend`, `inline`, `const`, `lateinit`, `override`, `operator`, `infix` modifiers
- generics with bounds, `where` constraints
- `typealias` → KIND_DELEGATE
- KDoc `/** ... */` vs plain `/* */` / `//` comments
- nullable types (`Foo?`), receiver types on extension functions
- Kotlin default visibility is `public` everywhere (unlike Java's package-private)
"""
from __future__ import annotations

from ast_outline.adapters.kotlin import KotlinAdapter
from ast_outline.core import (
    KIND_CLASS,
    KIND_CTOR,
    KIND_DELEGATE,
    KIND_ENUM,
    KIND_ENUM_MEMBER,
    KIND_FIELD,
    KIND_FUNCTION,
    KIND_INTERFACE,
    KIND_METHOD,
    KIND_NAMESPACE,
    KIND_PROPERTY,
    KIND_RECORD,
    Declaration,
)


# --- Helpers --------------------------------------------------------------


def _find(decls, kind=None, name=None):
    for d in decls:
        if (kind is None or d.kind == kind) and (name is None or d.name == name):
            return d
        hit = _find(d.children, kind=kind, name=name)
        if hit is not None:
            return hit
    return None


def _find_all(decls, kind=None, name=None):
    out: list[Declaration] = []
    for d in decls:
        if (kind is None or d.kind == kind) and (name is None or d.name == name):
            out.append(d)
        out.extend(_find_all(d.children, kind=kind, name=name))
    return out


# --- Parse smoke ----------------------------------------------------------


def test_parse_populates_result_metadata(kotlin_dir):
    path = kotlin_dir / "user_service.kt"
    result = KotlinAdapter().parse(path)
    assert result.path == path
    assert result.language == "kotlin"
    assert result.line_count > 0
    assert result.source == path.read_bytes()
    assert result.declarations


def test_adapter_extension_set():
    assert KotlinAdapter().extensions == {".kt", ".kts"}


def test_kotlin_files_discovered_via_collect_files(kotlin_dir):
    from ast_outline.adapters import collect_files, get_adapter_for

    files = collect_files([kotlin_dir])
    kt_files = [f for f in files if f.suffix in {".kt", ".kts"}]
    # The top-level fixtures + 4 files under multidir/
    assert len(kt_files) >= 10
    for f in kt_files:
        assert isinstance(get_adapter_for(f), KotlinAdapter)


# --- Package / top level --------------------------------------------------


def test_package_creates_namespace(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "user_service.kt")
    ns = _find(r.declarations, kind=KIND_NAMESPACE)
    assert ns is not None
    assert ns.name == "com.example.demo.service"
    assert ns.signature == "package com.example.demo.service"


def test_package_absorbs_sibling_declarations(kotlin_dir):
    """Kotlin types are siblings of `package_header` in the AST — the
    adapter must pull them inside the namespace."""
    r = KotlinAdapter().parse(kotlin_dir / "data_and_sealed.kt")
    ns = _find(r.declarations, kind=KIND_NAMESPACE, name="com.example.demo.model")
    assert ns is not None
    type_names = {
        c.name for c in ns.children if c.kind in (KIND_CLASS, KIND_RECORD, KIND_ENUM)
    }
    assert {"Point", "Shape", "Circle", "Square", "UnitShape", "Status"}.issubset(
        type_names
    )


def test_no_package_file(kotlin_dir):
    """A file without `package` keeps declarations at the top level."""
    r = KotlinAdapter().parse(kotlin_dir / "no_package.kt")
    assert _find(r.declarations, kind=KIND_NAMESPACE) is None
    assert _find(r.declarations, kind=KIND_CLASS, name="Top") is not None
    assert _find(r.declarations, kind=KIND_CLASS, name="Helper") is not None
    # Free function / val at module level
    assert _find(r.declarations, kind=KIND_FUNCTION, name="freeFunction") is not None
    assert _find(r.declarations, kind=KIND_FIELD, name="freeVal") is not None


# --- Classes --------------------------------------------------------------


def test_class_basic_structure(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "user_service.kt")
    svc = _find(r.declarations, kind=KIND_CLASS, name="UserService")
    assert svc is not None
    assert svc.visibility == "public"  # Kotlin default
    method_names = {c.name for c in svc.children if c.kind in (KIND_METHOD, KIND_CTOR)}
    assert {"save", "findMax", "compute", "close"}.issubset(method_names)
    # Primary-ctor val/var become FIELD children
    field_names = {c.name for c in svc.children if c.kind == KIND_FIELD}
    assert {"name", "items", "packagePrivateField"}.issubset(field_names)


def test_class_bases_extends_and_implements(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "user_service.kt")
    svc = _find(r.declarations, kind=KIND_CLASS, name="UserService")
    assert svc is not None
    # `: BaseService(), UserRepository, AutoCloseable`
    assert "BaseService" in svc.bases
    assert "UserRepository" in svc.bases
    assert "AutoCloseable" in svc.bases


def test_class_signature_strips_leading_annotations(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "user_service.kt")
    svc = _find(r.declarations, kind=KIND_CLASS, name="UserService")
    assert not svc.signature.lstrip().startswith("@")
    assert svc.signature.lstrip().startswith("open class UserService")
    # Annotations captured into attrs instead
    assert any("@Service" in a for a in svc.attrs)
    assert any("@Deprecated" in a for a in svc.attrs)


def test_kotlin_default_visibility_is_public(kotlin_dir):
    """Unlike Java (package-private) or C# (internal), Kotlin defaults to
    `public` at every scope."""
    r = KotlinAdapter().parse(kotlin_dir / "no_package.kt")
    top = _find(r.declarations, kind=KIND_CLASS, name="Top")
    assert top.visibility == "public"
    free_fn = _find(r.declarations, kind=KIND_FUNCTION, name="freeFunction")
    assert free_fn.visibility == "public"


def test_explicit_visibility_modifier(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "user_service.kt")
    svc = _find(r.declarations, kind=KIND_CLASS, name="UserService")
    items = next(c for c in svc.children if c.name == "items")
    assert items.visibility == "private"
    cache = next(c for c in svc.children if c.name == "cache")
    assert cache.visibility == "protected"
    pkg_private = next(c for c in svc.children if c.name == "packagePrivateField")
    assert pkg_private.visibility == "internal"


def test_nested_class_default_public(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "user_service.kt")
    inner = _find(r.declarations, kind=KIND_CLASS, name="Inner")
    assert inner is not None
    assert inner.visibility == "public"
    member_names = {c.name for c in inner.children}
    assert "value" in member_names


# --- Interfaces -----------------------------------------------------------


def test_interface_kind(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "hierarchy.kt")
    movable = _find(r.declarations, kind=KIND_INTERFACE, name="Movable")
    assert movable is not None


def test_fun_interface_still_interface(kotlin_dir):
    """`fun interface Callback` — SAM type, but still KIND_INTERFACE."""
    r = KotlinAdapter().parse(kotlin_dir / "user_service.kt")
    cb = _find(r.declarations, kind=KIND_INTERFACE, name="Callback")
    assert cb is not None
    assert "fun interface" in cb.signature


def test_interface_method_is_public_by_default(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "hierarchy.kt")
    movable = _find(r.declarations, kind=KIND_INTERFACE, name="Movable")
    move = next(c for c in movable.children if c.name == "move")
    assert move.kind == KIND_METHOD
    assert move.visibility == "public"


# --- Data / sealed / enum / annotation classes ---------------------------


def test_data_class_is_record_kind(kotlin_dir):
    """Kotlin data classes map onto KIND_RECORD (structurally closest to
    Java records)."""
    r = KotlinAdapter().parse(kotlin_dir / "data_and_sealed.kt")
    point = _find(r.declarations, kind=KIND_RECORD, name="Point")
    assert point is not None
    # Primary-ctor components are emitted as fields
    field_names = {c.name for c in point.children if c.kind == KIND_FIELD}
    assert {"x", "y"}.issubset(field_names)


def test_sealed_class_signature_contains_sealed(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "data_and_sealed.kt")
    shape = _find(r.declarations, kind=KIND_CLASS, name="Shape")
    assert shape is not None
    assert "sealed" in shape.signature


def test_enum_class_kind_and_constants(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "data_and_sealed.kt")
    status = _find(r.declarations, kind=KIND_ENUM, name="Status")
    assert status is not None
    entries = [c for c in status.children if c.kind == KIND_ENUM_MEMBER]
    names = [e.name for e in entries]
    assert names == ["ACTIVE", "INACTIVE", "BANNED", "UNKNOWN"]


def test_enum_primary_ctor_fields_included(kotlin_dir):
    """`enum class Status(val label: String, val weight: Int)` — the two
    ctor params must surface as FIELD children of the enum."""
    r = KotlinAdapter().parse(kotlin_dir / "data_and_sealed.kt")
    status = _find(r.declarations, kind=KIND_ENUM, name="Status")
    fields = {c.name for c in status.children if c.kind == KIND_FIELD}
    assert {"label", "weight"}.issubset(fields)


def test_enum_method_declared_after_constants(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "data_and_sealed.kt")
    status = _find(r.declarations, kind=KIND_ENUM, name="Status")
    method_names = {c.name for c in status.children if c.kind == KIND_METHOD}
    assert "display" in method_names


def test_enum_companion_object_nested(kotlin_dir):
    """An enum class can have a companion; that companion must appear as a
    nested KIND_CLASS member."""
    r = KotlinAdapter().parse(kotlin_dir / "data_and_sealed.kt")
    companions = _find_all(r.declarations, kind=KIND_CLASS, name="Companion")
    assert companions, "status enum's unnamed companion should surface as 'Companion'"


def test_enum_implements_interface(kotlin_dir):
    """Enum with `: java.io.Serializable` — serialisable interface goes to bases."""
    r = KotlinAdapter().parse(kotlin_dir / "data_and_sealed.kt")
    status = _find(r.declarations, kind=KIND_ENUM, name="Status")
    assert any("Serializable" in b for b in status.bases)


def test_annotation_class_is_interface(kotlin_dir):
    """Kotlin `annotation class Marker(...)` — maps to KIND_INTERFACE,
    mirroring how Java `@interface` is classified."""
    r = KotlinAdapter().parse(kotlin_dir / "annotations_generics.kt")
    marker = _find(r.declarations, kind=KIND_INTERFACE, name="Marker")
    assert marker is not None
    assert "annotation class" in marker.signature


# --- Objects / companion objects -----------------------------------------


def test_top_level_object(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "companion_and_objects.kt")
    logger = _find(r.declarations, kind=KIND_CLASS, name="Logger")
    assert logger is not None
    assert logger.signature.lstrip().startswith("object Logger")
    log_fn = next(c for c in logger.children if c.name == "log")
    assert log_fn.kind == KIND_METHOD


def test_object_with_delegation_specifiers(kotlin_dir):
    """`object RootHandler : BaseHandler(), Named` — base list should be parsed."""
    r = KotlinAdapter().parse(kotlin_dir / "companion_and_objects.kt")
    root = _find(r.declarations, kind=KIND_CLASS, name="RootHandler")
    assert root is not None
    assert "BaseHandler" in root.bases
    assert "Named" in root.bases


def test_named_companion(kotlin_dir):
    """`companion object Factory { ... }` — name comes from the identifier."""
    r = KotlinAdapter().parse(kotlin_dir / "companion_and_objects.kt")
    factory = _find(r.declarations, kind=KIND_CLASS, name="Factory")
    assert factory is not None
    assert "companion object Factory" in factory.signature


def test_unnamed_companion_defaults_to_companion(kotlin_dir):
    """`companion object { ... }` without an identifier compiles to a class
    named `Companion` — outline mirrors that."""
    r = KotlinAdapter().parse(kotlin_dir / "companion_and_objects.kt")
    cache = _find(r.declarations, kind=KIND_CLASS, name="Cache")
    assert cache is not None
    companion = next(c for c in cache.children if c.kind == KIND_CLASS)
    assert companion.name == "Companion"


# --- Properties -----------------------------------------------------------


def test_plain_property_is_field(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "properties.kt")
    container = _find(r.declarations, kind=KIND_CLASS, name="Container")
    weight = next(c for c in container.children if c.name == "weight")
    assert weight.kind == KIND_FIELD


def test_property_with_custom_getter_is_property(kotlin_dir):
    """A `val x: Int get() = ...` must be KIND_PROPERTY, not KIND_FIELD —
    the accessor promotes it."""
    r = KotlinAdapter().parse(kotlin_dir / "properties.kt")
    container = _find(r.declarations, kind=KIND_CLASS, name="Container")
    square = next(c for c in container.children if c.name == "square")
    assert square.kind == KIND_PROPERTY


def test_property_with_getter_and_setter_is_property(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "properties.kt")
    container = _find(r.declarations, kind=KIND_CLASS, name="Container")
    cached = next(c for c in container.children if c.name == "cached")
    assert cached.kind == KIND_PROPERTY


def test_property_signature_cuts_before_accessor(kotlin_dir):
    """`val species: String get() = ...` — signature should not include
    the getter body (`get() = ...`)."""
    r = KotlinAdapter().parse(kotlin_dir / "properties.kt")
    container = _find(r.declarations, kind=KIND_CLASS, name="Container")
    square = next(c for c in container.children if c.name == "square")
    assert "get()" not in square.signature


def test_primary_ctor_val_is_field(kotlin_dir):
    """`class Container(val id: Int, var label: String)` — both become
    FIELD children."""
    r = KotlinAdapter().parse(kotlin_dir / "properties.kt")
    container = _find(r.declarations, kind=KIND_CLASS, name="Container")
    fields = {c.name for c in container.children if c.kind == KIND_FIELD}
    assert {"id", "label"}.issubset(fields)


def test_top_level_val_is_field(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "properties.kt")
    # Under the `props` namespace
    top_const = _find(r.declarations, kind=KIND_FIELD, name="TOP_CONST")
    assert top_const is not None
    assert "const val" in top_const.signature
    assert "= 42" in top_const.signature


def test_lateinit_var_is_field(kotlin_dir):
    """`lateinit var` has no initialiser but is still plain storage (FIELD)."""
    r = KotlinAdapter().parse(kotlin_dir / "properties.kt")
    container = _find(r.declarations, kind=KIND_CLASS, name="Container")
    pending = next(c for c in container.children if c.name == "pending")
    assert pending.kind == KIND_FIELD
    assert "lateinit" in pending.signature


# --- Functions / extensions / modifiers ----------------------------------


def test_top_level_function_kind(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "extensions_and_toplevel.kt")
    fetch = _find(r.declarations, kind=KIND_FUNCTION, name="fetch")
    assert fetch is not None


def test_extension_function_name_and_signature(kotlin_dir):
    """`fun String.reversed2()` — name is `reversed2`, receiver `String`
    kept in the signature."""
    r = KotlinAdapter().parse(kotlin_dir / "extensions_and_toplevel.kt")
    ext = _find(r.declarations, kind=KIND_FUNCTION, name="reversed2")
    assert ext is not None
    assert "String.reversed2" in ext.signature


def test_generic_extension_function(kotlin_dir):
    """`fun <T : Number> List<T>.sumAs()` — both type params and receiver
    generics survive to the signature."""
    r = KotlinAdapter().parse(kotlin_dir / "extensions_and_toplevel.kt")
    fn = _find(r.declarations, kind=KIND_FUNCTION, name="sumAs")
    assert fn is not None
    assert "<T : Number>" in fn.signature
    assert "List<T>" in fn.signature


def test_suspend_modifier_in_signature(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "extensions_and_toplevel.kt")
    fetch = _find(r.declarations, kind=KIND_FUNCTION, name="fetch")
    assert "suspend" in fetch.signature


def test_inline_reified_modifier_in_signature(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "extensions_and_toplevel.kt")
    cast = _find(r.declarations, kind=KIND_FUNCTION, name="cast")
    assert "inline" in cast.signature
    assert "reified" in cast.signature


def test_operator_and_infix_modifiers(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "extensions_and_toplevel.kt")
    vec = _find(r.declarations, kind=KIND_CLASS, name="Vec2")
    plus = next(c for c in vec.children if c.name == "plus")
    assert "operator" in plus.signature
    dot = next(c for c in vec.children if c.name == "dot")
    assert "infix" in dot.signature


def test_vararg_and_default_args_in_signature(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "extensions_and_toplevel.kt")
    pick = _find(r.declarations, kind=KIND_FUNCTION, name="pick")
    assert "vararg values: Int" in pick.signature
    assert 'prefix: String = ">"' in pick.signature


def test_abstract_method_no_body(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "user_service.kt")
    compute = _find(r.declarations, kind=KIND_METHOD, name="compute")
    assert compute is not None
    assert "abstract" in compute.signature
    assert compute.start_line == compute.end_line


def test_method_visibility_explicit(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "user_service.kt")
    find_max = _find(r.declarations, kind=KIND_METHOD, name="findMax")
    assert find_max.visibility == "private"


def test_method_generics_with_bounds(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "user_service.kt")
    find_max = _find(r.declarations, kind=KIND_METHOD, name="findMax")
    assert "<T : Comparable<T>>" in find_max.signature


def test_override_modifier_preserved_in_signature(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "user_service.kt")
    save = _find(r.declarations, kind=KIND_METHOD, name="save")
    assert "override" in save.signature


def test_method_annotations_in_attrs(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "user_service.kt")
    save = _find(r.declarations, kind=KIND_METHOD, name="save")
    assert any("@Throws" in a for a in save.attrs)


# --- Constructors --------------------------------------------------------


def test_secondary_constructors_captured(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "secondary_ctor.kt")
    conn = _find(r.declarations, kind=KIND_CLASS, name="Connection")
    ctors = [c for c in conn.children if c.kind == KIND_CTOR]
    assert len(ctors) == 2  # two secondary constructors
    # primary ctor parameters become fields, not ctors
    for c in ctors:
        assert c.name == "constructor"


def test_init_block_is_skipped(kotlin_dir):
    """`init { }` has no declared name — must not appear as a child."""
    r = KotlinAdapter().parse(kotlin_dir / "secondary_ctor.kt")
    conn = _find(r.declarations, kind=KIND_CLASS, name="Connection")
    names = {c.name for c in conn.children}
    # `init` is anonymous; if it leaks it'd show up with an empty/"?" name
    assert "init" not in names
    assert "?" not in names


def test_primary_ctor_params_become_fields(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "secondary_ctor.kt")
    conn = _find(r.declarations, kind=KIND_CLASS, name="Connection")
    fields = {c.name for c in conn.children if c.kind == KIND_FIELD}
    assert {"host", "port"}.issubset(fields)


# --- Generics / where constraints ---------------------------------------


def test_class_generics_in_signature(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "annotations_generics.kt")
    graph = _find(r.declarations, kind=KIND_CLASS, name="Graph")
    assert graph is not None
    assert "<N : Comparable<N>, E>" in graph.signature


def test_where_clause_in_signature(kotlin_dir):
    """A Kotlin `where` constraint must survive into the signature text —
    it's part of the type declaration that an LLM may need to reason
    about, so the adapter slices it in verbatim."""
    r = KotlinAdapter().parse(kotlin_dir / "annotations_generics.kt")
    graph = _find(r.declarations, kind=KIND_CLASS, name="Graph")
    assert "where N : Cloneable" in graph.signature


def test_generic_method_throws_and_generics(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "annotations_generics.kt")
    traverse = _find(r.declarations, kind=KIND_METHOD, name="traverse")
    assert traverse is not None
    assert "<R : Any>" in traverse.signature
    assert any("@Throws" in a for a in traverse.attrs)


def test_annotation_with_parens_in_string_literal(kotlin_dir):
    """The annotation stripper must skip over string literals when
    balancing parens — otherwise `@SuppressWarnings("unused(value)")`
    would leak a trailing `)` into the signature."""
    r = KotlinAdapter().parse(kotlin_dir / "annotations_generics.kt")
    tricky = _find(r.declarations, kind=KIND_CLASS, name="TrickyAnnotated")
    assert tricky is not None
    assert not tricky.signature.startswith(")")
    assert not tricky.signature.startswith('"')
    assert tricky.signature.lstrip().startswith("class TrickyAnnotated")
    assert any("@SuppressWarnings" in a for a in tricky.attrs)


def test_annotation_stripper_handles_use_site_target():
    """`@file:JvmName(...)` and `@get:JvmStatic` have a `use-site target`
    followed by a colon before the identifier — the stripper must consume
    both segments."""
    from ast_outline.adapters.kotlin import _strip_leading_annotations

    assert _strip_leading_annotations("@file:JvmName(\"X\") class Foo").startswith(
        "class Foo"
    )
    assert _strip_leading_annotations("@get:JvmStatic fun foo()").startswith("fun foo()")


# --- Typealias ------------------------------------------------------------


def test_typealias_is_delegate_kind(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "extensions_and_toplevel.kt")
    handler = _find(r.declarations, kind=KIND_DELEGATE, name="Handler")
    assert handler is not None
    assert "typealias Handler" in handler.signature
    assert "(String) -> Unit" in handler.signature


def test_generic_typealias(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "extensions_and_toplevel.kt")
    pair2 = _find(r.declarations, kind=KIND_DELEGATE, name="Pair2")
    assert pair2 is not None
    assert "Pair2<A>" in pair2.signature


# --- KDoc handling -------------------------------------------------------


def test_kdoc_collected_for_class(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "user_service.kt")
    svc = _find(r.declarations, kind=KIND_CLASS, name="UserService")
    assert svc.docs, "KDoc above UserService must be captured"
    assert svc.docs[0].startswith("/**")


def test_kdoc_collected_for_method(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "user_service.kt")
    save = _find(r.declarations, kind=KIND_METHOD, name="save")
    assert save.docs
    assert "Persists" in save.docs[0]


def test_plain_block_comment_not_treated_as_kdoc(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "plain_block_comment.kt")
    foo = _find(r.declarations, kind=KIND_CLASS, name="Foo")
    assert foo is not None
    assert foo.docs == []


def test_line_comment_not_treated_as_kdoc(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "line_comment.kt")
    foo = _find(r.declarations, kind=KIND_CLASS, name="Foo")
    assert foo is not None
    assert foo.docs == []


# --- Line / byte ranges --------------------------------------------------


def test_line_ranges_reasonable(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "data_and_sealed.kt")
    point = _find(r.declarations, kind=KIND_RECORD, name="Point")
    assert point.start_line < point.end_line
    assert point.start_line >= 1
    assert point.end_line <= r.line_count


def test_nested_child_line_range_within_parent(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "user_service.kt")
    svc = _find(r.declarations, kind=KIND_CLASS, name="UserService")
    for child in svc.children:
        assert child.start_line >= svc.start_line
        assert child.end_line <= svc.end_line


def test_doc_start_byte_precedes_declaration(kotlin_dir):
    """When KDoc is present, `doc_start_byte` points at `/**`, earlier than
    `start_byte`."""
    r = KotlinAdapter().parse(kotlin_dir / "user_service.kt")
    svc = _find(r.declarations, kind=KIND_CLASS, name="UserService")
    assert svc.doc_start_byte < svc.start_byte


def test_doc_start_byte_equals_start_byte_without_doc(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "no_package.kt")
    helper = _find(r.declarations, kind=KIND_CLASS, name="Helper")
    assert helper.doc_start_byte == helper.start_byte


# --- Broken / partial parses ---------------------------------------------


def test_broken_syntax_reports_error_count(kotlin_dir):
    r = KotlinAdapter().parse(kotlin_dir / "broken_syntax.kt")
    assert r.error_count > 0
    # Adapter should still surface the intact parts
    broken = _find(r.declarations, kind=KIND_CLASS, name="Broken")
    assert broken is not None
    good = next(c for c in broken.children if c.name == "good")
    assert good.kind == KIND_METHOD


# --- End-to-end renderer check -------------------------------------------


def test_outline_renderer_smoke(kotlin_dir):
    from ast_outline.core import OutlineOptions, render_outline

    r = KotlinAdapter().parse(kotlin_dir / "user_service.kt")
    text = render_outline(r, OutlineOptions())
    assert "UserService" in text
    assert "namespace com.example.demo.service" in text
    assert "override fun save" in text


def test_digest_includes_kotlin_types(kotlin_dir):
    from ast_outline.adapters import collect_files
    from ast_outline.core import DigestOptions, render_digest

    files = collect_files([kotlin_dir])
    kt_files = [f for f in files if f.suffix in {".kt", ".kts"}]
    assert kt_files
    results = [KotlinAdapter().parse(f) for f in kt_files]
    text = render_digest(results, DigestOptions(), root=kotlin_dir)
    assert "UserService" in text
    assert "Point" in text
    # Digest carries the source-true keyword `data class` (Kotlin maps
    # to KIND_RECORD canonically but renders the native keyword).
    assert "data class" in text
