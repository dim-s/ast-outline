"""Tests for the Java adapter.

Covers:
- file-level: package declaration absorbing sibling types, no-package files
- types: class / interface / @interface / enum / record / sealed hierarchy
- members: methods, ctors, compact record ctors, fields (incl. multi-var),
  enum constants, annotation type elements
- modifiers & annotations: visibility defaults, stripping `@Foo(...)` from
  signatures, preserving `@interface` keyword
- generics: type parameters on class + method, bounded wildcards
- throws clauses
- Javadoc (`/** ... */`) vs plain block comments and `//` comments
- bases: `extends` + `implements` (but not `permits`)
"""
from __future__ import annotations

from code_outline.adapters.java import JavaAdapter
from code_outline.core import (
    KIND_CLASS,
    KIND_CTOR,
    KIND_ENUM,
    KIND_ENUM_MEMBER,
    KIND_FIELD,
    KIND_INTERFACE,
    KIND_METHOD,
    KIND_NAMESPACE,
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


def test_parse_populates_result_metadata(java_dir):
    path = java_dir / "user_service.java"
    result = JavaAdapter().parse(path)
    assert result.path == path
    assert result.language == "java"
    assert result.line_count > 0
    assert result.source == path.read_bytes()
    assert result.declarations


def test_adapter_extension_set():
    assert JavaAdapter().extensions == {".java"}


def test_java_files_discovered_via_collect_files(java_dir):
    from code_outline.adapters import collect_files, get_adapter_for

    files = collect_files([java_dir])
    java_files = [f for f in files if f.suffix == ".java"]
    assert len(java_files) >= 7  # we ship 7 Java fixtures
    for f in java_files:
        assert isinstance(get_adapter_for(f), JavaAdapter)


# --- Package declaration -------------------------------------------------


def test_package_creates_namespace(java_dir):
    r = JavaAdapter().parse(java_dir / "user_service.java")
    ns = _find(r.declarations, kind=KIND_NAMESPACE)
    assert ns is not None
    assert ns.name == "com.example.demo.service"
    assert ns.signature == "package com.example.demo.service"


def test_package_absorbs_sibling_types(java_dir):
    """Java types are siblings of package_declaration in the AST; adapter
    must put them inside the namespace declaration."""
    r = JavaAdapter().parse(java_dir / "records_and_sealed.java")
    ns = _find(r.declarations, kind=KIND_NAMESPACE, name="com.example.demo.model")
    assert ns is not None
    type_names = {c.name for c in ns.children if c.kind in (KIND_CLASS, KIND_RECORD)}
    assert {"Point", "Shape", "Circle", "Square", "Triangle"}.issubset(type_names)


def test_no_package_file(java_dir):
    """Files without a package declaration put types at top level."""
    r = JavaAdapter().parse(java_dir / "no_package.java")
    assert _find(r.declarations, kind=KIND_NAMESPACE) is None
    assert _find(r.declarations, kind=KIND_CLASS, name="Top") is not None
    assert _find(r.declarations, kind=KIND_CLASS, name="Helper") is not None


# --- Classes --------------------------------------------------------------


def test_class_basic_structure(java_dir):
    r = JavaAdapter().parse(java_dir / "user_service.java")
    svc = _find(r.declarations, kind=KIND_CLASS, name="UserService")
    assert svc is not None
    assert svc.visibility == "public"
    method_names = {c.name for c in svc.children if c.kind in (KIND_METHOD, KIND_CTOR)}
    assert {"UserService", "save", "findMax", "compute", "close"}.issubset(method_names)
    field_names = {c.name for c in svc.children if c.kind == KIND_FIELD}
    assert {"MAX_USERS", "name", "items", "packagePrivateField"}.issubset(field_names)


def test_class_bases_extends_and_implements(java_dir):
    r = JavaAdapter().parse(java_dir / "user_service.java")
    svc = _find(r.declarations, kind=KIND_CLASS, name="UserService")
    assert svc is not None
    assert "BaseService" in svc.bases
    assert "UserRepository" in svc.bases
    assert "AutoCloseable" in svc.bases


def test_class_signature_strips_annotations(java_dir):
    r = JavaAdapter().parse(java_dir / "user_service.java")
    svc = _find(r.declarations, kind=KIND_CLASS, name="UserService")
    # Signature itself shouldn't start with @Service / @Deprecated —
    # they are collected into attrs instead.
    assert not svc.signature.startswith("@")
    assert svc.signature.startswith("public class UserService") or svc.signature.startswith(
        "public"
    )
    # Annotations preserved in attrs
    assert any("@Service" in a for a in svc.attrs)
    assert any("@Deprecated" in a for a in svc.attrs)


def test_class_with_multiple_annotations(java_dir):
    r = JavaAdapter().parse(java_dir / "user_service.java")
    svc = _find(r.declarations, kind=KIND_CLASS, name="UserService")
    assert len(svc.attrs) == 2


def test_nested_class(java_dir):
    r = JavaAdapter().parse(java_dir / "user_service.java")
    inner = _find(r.declarations, kind=KIND_CLASS, name="Inner")
    assert inner is not None
    assert inner.visibility == "public"
    # Nested Inner has its own ctor + value() method
    member_names = {c.name for c in inner.children}
    assert {"value", "Inner"}.issubset(member_names)


def test_nested_interface_in_class(java_dir):
    """An `interface Callback {}` declared inside a class body."""
    r = JavaAdapter().parse(java_dir / "user_service.java")
    cb = _find(r.declarations, kind=KIND_INTERFACE, name="Callback")
    assert cb is not None
    method_names = {c.name for c in cb.children if c.kind == KIND_METHOD}
    assert "onDone" in method_names


# --- Interfaces -----------------------------------------------------------


def test_interface_basic(java_dir):
    r = JavaAdapter().parse(java_dir / "repository.java")
    repo = _find(r.declarations, kind=KIND_INTERFACE, name="Repository")
    assert repo is not None
    assert repo.visibility == "public"
    method_names = {c.name for c in repo.children if c.kind == KIND_METHOD}
    assert {"findById", "findAll", "exists", "empty", "close"}.issubset(method_names)


def test_interface_methods_default_public(java_dir):
    """Java spec: members of interfaces are public by default (no modifier)."""
    r = JavaAdapter().parse(java_dir / "repository.java")
    repo = _find(r.declarations, kind=KIND_INTERFACE, name="Repository")
    findById = next(c for c in repo.children if c.name == "findById")
    assert findById.visibility == "public"
    # Default methods — have `default` modifier but still public
    exists = next(c for c in repo.children if c.name == "exists")
    assert exists.visibility == "public"
    assert "default" in exists.signature


def test_interface_bases_extends_list(java_dir):
    r = JavaAdapter().parse(java_dir / "repository.java")
    repo = _find(r.declarations, kind=KIND_INTERFACE, name="Repository")
    assert "AutoCloseable" in repo.bases


def test_package_private_interface(java_dir):
    """`interface Marker {}` with no visibility modifier → internal."""
    r = JavaAdapter().parse(java_dir / "repository.java")
    marker = _find(r.declarations, kind=KIND_INTERFACE, name="Marker")
    assert marker is not None
    assert marker.visibility == "internal"


def test_functional_interface_annotation(java_dir):
    r = JavaAdapter().parse(java_dir / "repository.java")
    mapper = _find(r.declarations, kind=KIND_INTERFACE, name="Mapper")
    assert mapper is not None
    assert any("@FunctionalInterface" in a for a in mapper.attrs)


def test_nested_type_inside_interface_defaults_public(java_dir):
    """Java spec: a nested class/interface declared inside an `interface`
    with no modifier is implicitly `public`."""
    r = JavaAdapter().parse(java_dir / "repository.java")
    not_found = _find(r.declarations, kind=KIND_CLASS, name="NotFound")
    assert not_found is not None
    assert not_found.visibility == "public"


# --- Enums ----------------------------------------------------------------


def test_enum_structure(java_dir):
    r = JavaAdapter().parse(java_dir / "status_enum.java")
    e = _find(r.declarations, kind=KIND_ENUM, name="Status")
    assert e is not None
    constants = [c for c in e.children if c.kind == KIND_ENUM_MEMBER]
    names = [c.name for c in constants]
    assert names == ["ACTIVE", "INACTIVE", "BANNED", "UNKNOWN"]
    for c in constants:
        assert c.visibility == "public"


def test_enum_has_fields_ctors_methods_after_constants(java_dir):
    """enum_body_declarations siblings after enum_constants are picked up."""
    r = JavaAdapter().parse(java_dir / "status_enum.java")
    e = _find(r.declarations, kind=KIND_ENUM, name="Status")
    field_names = {c.name for c in e.children if c.kind == KIND_FIELD}
    assert {"label", "weight"}.issubset(field_names)
    ctor_names = {c.name for c in e.children if c.kind == KIND_CTOR}
    assert "Status" in ctor_names
    method_names = {c.name for c in e.children if c.kind == KIND_METHOD}
    assert {"label", "weight", "parse"}.issubset(method_names)


def test_enum_constant_signature_includes_args(java_dir):
    r = JavaAdapter().parse(java_dir / "status_enum.java")
    active = _find(r.declarations, kind=KIND_ENUM_MEMBER, name="ACTIVE")
    assert active is not None
    # Signature has the constructor args
    assert "Active" in active.signature or "(" in active.signature


def test_enum_constant_without_args(java_dir):
    r = JavaAdapter().parse(java_dir / "status_enum.java")
    unknown = _find(r.declarations, kind=KIND_ENUM_MEMBER, name="UNKNOWN")
    assert unknown is not None


def test_enum_ctor_without_modifier_is_private(java_dir):
    """Java spec: enum ctors are implicitly private."""
    r = JavaAdapter().parse(java_dir / "status_enum.java")
    e = _find(r.declarations, kind=KIND_ENUM, name="Status")
    ctors = [c for c in e.children if c.kind == KIND_CTOR]
    assert ctors
    for ctor in ctors:
        assert ctor.visibility == "private"


def test_enum_implements_interface(java_dir):
    """Enum `implements` clause is picked up via the `interfaces` field —
    same path as class/record implements."""
    r = JavaAdapter().parse(java_dir / "status_enum.java")
    e = _find(r.declarations, kind=KIND_ENUM, name="Status")
    assert "Serializable" in e.bases


# --- Records --------------------------------------------------------------


def test_record_declaration(java_dir):
    r = JavaAdapter().parse(java_dir / "records_and_sealed.java")
    point = _find(r.declarations, kind=KIND_RECORD, name="Point")
    assert point is not None
    assert point.visibility == "public"
    # record components become FIELD children
    component_fields = [c for c in point.children if c.kind == KIND_FIELD]
    field_names = {c.name for c in component_fields}
    assert {"x", "y"}.issubset(field_names)
    assert {"ORIGIN"}.issubset(field_names)


def test_record_bases(java_dir):
    r = JavaAdapter().parse(java_dir / "records_and_sealed.java")
    point = _find(r.declarations, kind=KIND_RECORD, name="Point")
    assert "Comparable<Point>" in point.bases


def test_record_compact_constructor(java_dir):
    """Compact ctor: `public Point { ... }` — no formal_parameters node."""
    r = JavaAdapter().parse(java_dir / "records_and_sealed.java")
    point = _find(r.declarations, kind=KIND_RECORD, name="Point")
    ctors = [c for c in point.children if c.kind == KIND_CTOR]
    assert len(ctors) >= 2  # compact + explicit (double xy)
    # The compact ctor signature is `public Point` (no parens)
    compact = next(c for c in ctors if "(" not in c.signature)
    assert compact.name == "Point"


def test_record_explicit_constructor(java_dir):
    """Non-compact ctor in a record has formal_parameters and appears separately."""
    r = JavaAdapter().parse(java_dir / "records_and_sealed.java")
    point = _find(r.declarations, kind=KIND_RECORD, name="Point")
    ctors = [c for c in point.children if c.kind == KIND_CTOR]
    non_compact = [c for c in ctors if "(" in c.signature]
    assert non_compact, "must capture the Point(double xy) non-compact ctor"


# --- Sealed hierarchy ----------------------------------------------------


def test_sealed_class_signature(java_dir):
    r = JavaAdapter().parse(java_dir / "records_and_sealed.java")
    shape = _find(r.declarations, kind=KIND_CLASS, name="Shape")
    assert shape is not None
    assert "sealed" in shape.signature
    assert "permits" in shape.signature


def test_sealed_class_bases_excludes_permits(java_dir):
    """`permits Circle, Square, Triangle` is NOT a base type — it's sealing metadata."""
    r = JavaAdapter().parse(java_dir / "records_and_sealed.java")
    shape = _find(r.declarations, kind=KIND_CLASS, name="Shape")
    # Shape has no extends/implements, only permits → bases empty
    assert shape.bases == []


def test_non_sealed_class(java_dir):
    r = JavaAdapter().parse(java_dir / "records_and_sealed.java")
    sq = _find(r.declarations, kind=KIND_CLASS, name="Square")
    assert sq is not None
    assert "non-sealed" in sq.signature
    assert sq.bases == ["Shape"]


def test_final_class(java_dir):
    r = JavaAdapter().parse(java_dir / "records_and_sealed.java")
    c = _find(r.declarations, kind=KIND_CLASS, name="Circle")
    assert c is not None
    assert "final" in c.signature
    assert c.bases == ["Shape"]


# --- Annotation types (@interface) ---------------------------------------


def test_annotation_type_declaration(java_dir):
    r = JavaAdapter().parse(java_dir / "annotation_type.java")
    tag = _find(r.declarations, kind=KIND_INTERFACE, name="Tagged")
    assert tag is not None
    # Signature must preserve `@interface` keyword (NOT stripped as annotation)
    assert "@interface" in tag.signature
    # Meta-annotations collected into attrs
    assert any("@Retention" in a for a in tag.attrs)
    assert any("@Target" in a for a in tag.attrs)


def test_annotation_type_elements_are_methods(java_dir):
    r = JavaAdapter().parse(java_dir / "annotation_type.java")
    tag = _find(r.declarations, kind=KIND_INTERFACE, name="Tagged")
    method_names = {c.name for c in tag.children if c.kind == KIND_METHOD}
    assert {"value", "priority", "aliases", "consumers"}.issubset(method_names)


def test_annotation_element_signature_preserves_default(java_dir):
    r = JavaAdapter().parse(java_dir / "annotation_type.java")
    tag = _find(r.declarations, kind=KIND_INTERFACE, name="Tagged")
    priority = next(c for c in tag.children if c.name == "priority")
    assert "default" in priority.signature
    assert "0" in priority.signature


def test_package_private_annotation_type(java_dir):
    r = JavaAdapter().parse(java_dir / "annotation_type.java")
    marker = _find(r.declarations, kind=KIND_INTERFACE, name="PackagePrivateMarker")
    assert marker is not None
    assert marker.visibility == "internal"


def test_annotation_with_parens_in_string_literal(java_dir):
    """`@SuppressWarnings("(foo)")` has parens INSIDE a string literal.
    The stripper must skip over the literal and not exit mid-value."""
    r = JavaAdapter().parse(java_dir / "annotation_type.java")
    tricky = _find(r.declarations, kind=KIND_CLASS, name="TrickyAnnotated")
    assert tricky is not None
    # Signature should not start with a leading `)` or `"` — annotation fully stripped.
    assert not tricky.signature.startswith(")")
    assert not tricky.signature.startswith('"')
    assert tricky.signature.startswith("class TrickyAnnotated") or tricky.signature.startswith(
        "class"
    )
    # Annotation is captured into attrs
    assert any("@SuppressWarnings" in a for a in tricky.attrs)


def test_annotation_name_starting_with_interface_keyword_is_stripped():
    """An annotation `@interfaceAware` (starts with `interface` but has more
    identifier chars) must be stripped as a normal annotation — the
    `@interface` keyword check enforces a word boundary."""
    from code_outline.adapters.java import _strip_leading_annotations

    assert _strip_leading_annotations("@interfaceAware class Foo") == "class Foo"
    # But the real keyword is preserved
    assert (
        _strip_leading_annotations("@interface MyAnn { }").startswith("@interface")
    )


# --- Methods --------------------------------------------------------------


def test_method_signature_includes_throws(java_dir):
    r = JavaAdapter().parse(java_dir / "user_service.java")
    save = _find(r.declarations, kind=KIND_METHOD, name="save")
    assert save is not None
    assert "throws" in save.signature
    assert "IOException" in save.signature
    assert "IllegalArgumentException" in save.signature


def test_method_signature_strips_override_annotation(java_dir):
    r = JavaAdapter().parse(java_dir / "user_service.java")
    save = _find(r.declarations, kind=KIND_METHOD, name="save")
    # @Override should be in attrs, not in signature
    assert not save.signature.startswith("@Override")
    assert any("@Override" in a for a in save.attrs)


def test_abstract_method_no_body(java_dir):
    r = JavaAdapter().parse(java_dir / "user_service.java")
    compute = _find(r.declarations, kind=KIND_METHOD, name="compute")
    assert compute is not None
    assert "abstract" in compute.signature
    # Single-line abstract method → start_line == end_line
    assert compute.start_line == compute.end_line


def test_generic_method_signature(java_dir):
    r = JavaAdapter().parse(java_dir / "user_service.java")
    find_max = _find(r.declarations, kind=KIND_METHOD, name="findMax")
    assert find_max is not None
    assert "<T extends Comparable<T>>" in find_max.signature


def test_method_visibility_modifiers(java_dir):
    r = JavaAdapter().parse(java_dir / "user_service.java")
    svc = _find(r.declarations, kind=KIND_CLASS, name="UserService")
    methods = {c.name: c for c in svc.children if c.kind in (KIND_METHOD, KIND_CTOR)}
    assert methods["save"].visibility == "public"
    assert methods["findMax"].visibility == "private"
    assert methods["compute"].visibility == "public"


def test_ctor_overloads_both_captured(java_dir):
    r = JavaAdapter().parse(java_dir / "user_service.java")
    svc = _find(r.declarations, kind=KIND_CLASS, name="UserService")
    ctors = [c for c in svc.children if c.kind == KIND_CTOR]
    visibilities = {c.visibility for c in ctors}
    # Class has `public UserService(String name)` + `protected UserService()`
    assert "public" in visibilities
    assert "protected" in visibilities


# --- Fields ---------------------------------------------------------------


def test_field_kinds_and_visibility(java_dir):
    r = JavaAdapter().parse(java_dir / "user_service.java")
    svc = _find(r.declarations, kind=KIND_CLASS, name="UserService")
    fields = {c.name: c for c in svc.children if c.kind == KIND_FIELD}
    assert fields["MAX_USERS"].visibility == "public"
    assert fields["name"].visibility == "private"
    assert fields["items"].visibility == "protected"
    # No modifier → package-private (internal)
    assert fields["packagePrivateField"].visibility == "internal"


def test_multi_variable_field_first_name_wins(java_dir):
    r = JavaAdapter().parse(java_dir / "multi_var_fields.java")
    vectors = _find(r.declarations, kind=KIND_CLASS, name="Vectors")
    assert vectors is not None
    fields = [c for c in vectors.children if c.kind == KIND_FIELD]
    field_names = [c.name for c in fields]
    # `int a, b, c;` → one entry for `a`, not three.
    assert "a" in field_names
    assert "b" not in field_names  # multi-declarator: only first is captured


def test_array_field(java_dir):
    r = JavaAdapter().parse(java_dir / "multi_var_fields.java")
    vectors = _find(r.declarations, kind=KIND_CLASS, name="Vectors")
    arr = next(c for c in vectors.children if c.name == "arr")
    assert "int[]" in arr.signature


def test_wildcard_generic_field(java_dir):
    r = JavaAdapter().parse(java_dir / "multi_var_fields.java")
    vectors = _find(r.declarations, kind=KIND_CLASS, name="Vectors")
    items = next(c for c in vectors.children if c.name == "items")
    assert "? extends Number" in items.signature


def test_field_signature_preserves_initialiser(java_dir):
    """Current behaviour: field signature includes the initialiser text.
    (C# adapter does the same — we preserve it as informative context.)"""
    r = JavaAdapter().parse(java_dir / "user_service.java")
    svc = _find(r.declarations, kind=KIND_CLASS, name="UserService")
    max_users = next(c for c in svc.children if c.name == "MAX_USERS")
    assert "100" in max_users.signature


# --- Generics + throws on class-level ------------------------------------


def test_class_generics_in_signature(java_dir):
    r = JavaAdapter().parse(java_dir / "generics_throws.java")
    graph = _find(r.declarations, kind=KIND_CLASS, name="Graph")
    assert graph is not None
    assert "<N extends Comparable<N>, E>" in graph.signature


def test_method_wildcard_generics(java_dir):
    r = JavaAdapter().parse(java_dir / "generics_throws.java")
    traverse = _find(r.declarations, kind=KIND_METHOD, name="traverse")
    assert traverse is not None
    assert "? super N" in traverse.signature
    assert "? extends R" in traverse.signature
    assert "throws IOException" in traverse.signature


def test_method_multi_throws(java_dir):
    r = JavaAdapter().parse(java_dir / "generics_throws.java")
    collect = _find(r.declarations, kind=KIND_METHOD, name="collect")
    assert collect is not None
    assert "IOException" in collect.signature
    assert "InterruptedException" in collect.signature


def test_varargs_method(java_dir):
    r = JavaAdapter().parse(java_dir / "generics_throws.java")
    accept = _find(r.declarations, kind=KIND_METHOD, name="accept")
    assert accept is not None
    assert "X..." in accept.signature
    assert any("@SafeVarargs" in a for a in accept.attrs)


# --- Javadoc handling ----------------------------------------------------


def test_javadoc_collected(java_dir):
    r = JavaAdapter().parse(java_dir / "user_service.java")
    svc = _find(r.declarations, kind=KIND_CLASS, name="UserService")
    assert svc.docs, "Javadoc above UserService must be captured"
    assert svc.docs[0].startswith("/**")


def test_method_javadoc_collected(java_dir):
    r = JavaAdapter().parse(java_dir / "user_service.java")
    save = _find(r.declarations, kind=KIND_METHOD, name="save")
    assert save.docs
    assert "Saves" in save.docs[0]


def test_plain_block_comment_not_treated_as_javadoc(java_dir):
    """A regular `/* ... */` comment above a class must NOT become docs."""
    r = JavaAdapter().parse(java_dir / "plain_block_comment.java")
    foo = _find(r.declarations, kind=KIND_CLASS, name="Foo")
    assert foo is not None
    assert foo.docs == []


def test_line_comment_not_treated_as_javadoc(java_dir):
    r = JavaAdapter().parse(java_dir / "line_comment.java")
    foo = _find(r.declarations, kind=KIND_CLASS, name="Foo")
    assert foo is not None
    assert foo.docs == []


# --- Line ranges ---------------------------------------------------------


def test_line_ranges_reasonable(java_dir):
    r = JavaAdapter().parse(java_dir / "records_and_sealed.java")
    point = _find(r.declarations, kind=KIND_RECORD, name="Point")
    assert point.start_line < point.end_line
    assert point.start_line >= 1
    assert point.end_line <= r.line_count


def test_nested_child_line_range_within_parent(java_dir):
    r = JavaAdapter().parse(java_dir / "user_service.java")
    svc = _find(r.declarations, kind=KIND_CLASS, name="UserService")
    for child in svc.children:
        assert child.start_line >= svc.start_line
        assert child.end_line <= svc.end_line


# --- Byte ranges for `show` ---------------------------------------------


def test_doc_start_byte_precedes_declaration(java_dir):
    """doc_start_byte (used by `show`) points to `/**` when Javadoc exists,
    otherwise equals start_byte."""
    r = JavaAdapter().parse(java_dir / "user_service.java")
    svc = _find(r.declarations, kind=KIND_CLASS, name="UserService")
    # Class has Javadoc preceding it, so doc_start_byte < start_byte
    assert svc.doc_start_byte < svc.start_byte


def test_doc_start_byte_equals_start_byte_without_doc(java_dir):
    r = JavaAdapter().parse(java_dir / "no_package.java")
    helper = _find(r.declarations, kind=KIND_CLASS, name="Helper")
    assert helper.doc_start_byte == helper.start_byte


# --- End-to-end renderer check -------------------------------------------


def test_outline_renderer_smoke(java_dir):
    """Outline renderer works on Java output (no exceptions, contains expected names)."""
    from code_outline.core import OutlineOptions, render_outline

    r = JavaAdapter().parse(java_dir / "user_service.java")
    text = render_outline(r, OutlineOptions())
    assert "UserService" in text
    assert "namespace com.example.demo.service" in text
    assert "public void save" in text


def test_digest_includes_java_types(java_dir):
    """Digest renderer works on Java parse results."""
    from code_outline.adapters import collect_files
    from code_outline.core import DigestOptions, render_digest

    files = collect_files([java_dir])
    java_files = [f for f in files if f.suffix == ".java"]
    assert java_files
    results = [JavaAdapter().parse(f) for f in java_files]
    text = render_digest(results, DigestOptions(), root=java_dir)
    assert "UserService" in text
    assert "Point" in text
    assert "record" in text
