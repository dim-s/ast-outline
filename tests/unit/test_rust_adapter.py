"""Tests for the Rust adapter.

Covers Rust-specific ground (the things other adapters don't exercise):
- `mod foo { ... }` → KIND_NAMESPACE, recursive nesting; `pub mod foo;`
  body-less form surfaces as a namespace leaf
- `struct` in three shapes: regular, tuple, unit
- `union` → KIND_STRUCT (same shape, `union` keyword preserved)
- `enum` with unit / tuple / struct / generic variants → KIND_ENUM with
  KIND_ENUM_MEMBER children; discriminants and per-variant attrs survive
- `trait` → KIND_INTERFACE; supertraits land in `bases`; both
  forward-decl (`function_signature_item`) and default-impl
  (`function_item`) methods surface
- **Two-pass impl-block grouping** — the headline Rust feature: methods
  in `impl Foo { ... }` blocks regroup under the local `Foo` declaration;
  trait impls (`impl Trait for Foo`) ALSO add `Trait` to Foo's bases so
  `ast-outline implements Trait` finds Foo
- Methods on cross-file types (`impl ExternalType { ... }` where
  `ExternalType` is declared elsewhere) spill at file top level rather
  than vanishing
- `extern "C" { ... }` blocks → KIND_NAMESPACE labelled by ABI string
- `macro_rules!` → KIND_DELEGATE
- Type aliases (`type X = Y;`) and associated types (`type Item;` in
  trait bodies) → KIND_DELEGATE
- Visibility classifier: `pub`/`pub(crate)`/`pub(super)`/`pub(self)`/
  `pub(in path)` / absent → "public"/"internal"/"private"
- Doc comments: `///`, `/** */` outer docs; inner docs (`//!`, `/*!`)
  ignored at item level; blank-line gap detaches doc; non-doc `//`
  comments do NOT promote to docs
- Attributes: `#[...]` siblings are collected into `attrs`, including
  multiple attrs and attrs interleaved with doc comments
- Generics, lifetimes (`'a`), `where` clauses preserved verbatim in
  rendered signatures
- `const` and `static` → KIND_FIELD with the keyword surviving in sig
- Broken syntax: error_count > 0, no crash, partial output salvaged
"""
from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

from ast_outline.adapters.rust import RustAdapter
from ast_outline.core import (
    KIND_DELEGATE,
    KIND_ENUM,
    KIND_ENUM_MEMBER,
    KIND_FIELD,
    KIND_FUNCTION,
    KIND_INTERFACE,
    KIND_METHOD,
    KIND_NAMESPACE,
    KIND_STRUCT,
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


@contextmanager
def _inline_rust(src: bytes):
    """Spit `src` to a temp .rs file, yield its Path, then clean up.

    Closes the fd from `mkstemp` (which would otherwise leak per call).
    """
    fd, path_str = tempfile.mkstemp(suffix=".rs")
    os.close(fd)
    p = Path(path_str)
    try:
        p.write_bytes(src)
        yield p
    finally:
        p.unlink()


# --- Parse smoke ----------------------------------------------------------


def test_parse_populates_result_metadata(rust_dir):
    path = rust_dir / "user_service.rs"
    result = RustAdapter().parse(path)
    assert result.path == path
    assert result.language == "rust"
    assert result.line_count > 0
    assert result.source == path.read_bytes()
    assert result.declarations


def test_adapter_extension_set():
    assert RustAdapter().extensions == {".rs"}


def test_rust_files_discovered_via_collect_files(rust_dir):
    from ast_outline.adapters import collect_files, get_adapter_for

    files = collect_files([rust_dir])
    rust_files = [f for f in files if f.suffix == ".rs"]
    assert len(rust_files) >= 10
    for f in rust_files:
        assert isinstance(get_adapter_for(f), RustAdapter)


def test_supported_extensions_includes_rs():
    from ast_outline.adapters import supported_extensions

    assert ".rs" in supported_extensions()


# --- Top-level structures -------------------------------------------------


def test_user_struct_present(rust_dir):
    r = RustAdapter().parse(rust_dir / "user_service.rs")
    user = _find(r.declarations, kind=KIND_STRUCT, name="User")
    assert user is not None
    assert "pub struct User" in user.signature
    assert user.visibility == "public"


def test_struct_named_fields(rust_dir):
    r = RustAdapter().parse(rust_dir / "user_service.rs")
    user = _find(r.declarations, kind=KIND_STRUCT, name="User")
    field_names = {c.name for c in user.children if c.kind == KIND_FIELD}
    assert {"name", "email", "id"}.issubset(field_names)


def test_struct_field_visibility(rust_dir):
    r = RustAdapter().parse(rust_dir / "user_service.rs")
    user = _find(r.declarations, kind=KIND_STRUCT, name="User")
    name_field = _find(user.children, kind=KIND_FIELD, name="name")
    id_field = _find(user.children, kind=KIND_FIELD, name="id")
    assert name_field.visibility == "public"
    assert id_field.visibility == "private"


def test_struct_doc_comment(rust_dir):
    r = RustAdapter().parse(rust_dir / "user_service.rs")
    user = _find(r.declarations, kind=KIND_STRUCT, name="User")
    assert any("Represents a registered user account" in d for d in user.docs)


def test_struct_attributes(rust_dir):
    r = RustAdapter().parse(rust_dir / "user_service.rs")
    user = _find(r.declarations, kind=KIND_STRUCT, name="User")
    assert any("derive" in a for a in user.attrs)


def test_tuple_struct(rust_dir):
    r = RustAdapter().parse(rust_dir / "edge_cases.rs")
    one = _find(r.declarations, kind=KIND_STRUCT, name="OneTuple")
    assert one is not None
    assert "(" in one.signature  # tuple-struct shape preserved


def test_unit_struct(rust_dir):
    r = RustAdapter().parse(rust_dir / "edge_cases.rs")
    empty = _find(r.declarations, kind=KIND_STRUCT, name="Empty")
    assert empty is not None
    # Unit structs have no body — no field children.
    assert not [c for c in empty.children if c.kind == KIND_FIELD]


def test_union_treated_as_struct(rust_dir):
    r = RustAdapter().parse(rust_dir / "unions_and_macros.rs")
    u = _find(r.declarations, kind=KIND_STRUCT, name="NumOrFloat")
    assert u is not None
    assert "union" in u.signature
    field_names = {c.name for c in u.children}
    assert {"i", "f"}.issubset(field_names)


# --- Enums ----------------------------------------------------------------


def test_enum_kind_and_variants(rust_dir):
    r = RustAdapter().parse(rust_dir / "enum_advanced.rs")
    direction = _find(r.declarations, kind=KIND_ENUM, name="Direction")
    assert direction is not None
    variant_names = {c.name for c in direction.children if c.kind == KIND_ENUM_MEMBER}
    assert variant_names == {"North", "South", "East", "West"}


def test_enum_tuple_variants_keep_payload(rust_dir):
    r = RustAdapter().parse(rust_dir / "enum_advanced.rs")
    event = _find(r.declarations, kind=KIND_ENUM, name="Event")
    started = _find(event.children, kind=KIND_ENUM_MEMBER, name="Started")
    assert "u64" in started.signature


def test_enum_struct_variants_keep_payload(rust_dir):
    r = RustAdapter().parse(rust_dir / "enum_advanced.rs")
    event = _find(r.declarations, kind=KIND_ENUM, name="Event")
    completed = _find(event.children, kind=KIND_ENUM_MEMBER, name="Completed")
    assert "id" in completed.signature
    assert "duration_ms" in completed.signature


def test_enum_generic_variant(rust_dir):
    r = RustAdapter().parse(rust_dir / "enum_advanced.rs")
    event = _find(r.declarations, kind=KIND_ENUM, name="Event")
    custom = _find(event.children, kind=KIND_ENUM_MEMBER, name="Custom")
    assert "T" in custom.signature


def test_enum_signature_includes_generic_params(rust_dir):
    r = RustAdapter().parse(rust_dir / "enum_advanced.rs")
    event = _find(r.declarations, kind=KIND_ENUM, name="Event")
    assert "<T>" in event.signature


def test_enum_discriminant_preserved(rust_dir):
    r = RustAdapter().parse(rust_dir / "enum_advanced.rs")
    code = _find(r.declarations, kind=KIND_ENUM, name="Code")
    ok = _find(code.children, kind=KIND_ENUM_MEMBER, name="Ok")
    assert "= 0" in ok.signature


def test_enum_carries_attribute(rust_dir):
    r = RustAdapter().parse(rust_dir / "enum_advanced.rs")
    code = _find(r.declarations, kind=KIND_ENUM, name="Code")
    assert any("repr" in a for a in code.attrs)


# --- Traits ---------------------------------------------------------------


def test_trait_kind_is_interface(rust_dir):
    r = RustAdapter().parse(rust_dir / "user_service.rs")
    has_id = _find(r.declarations, kind=KIND_INTERFACE, name="HasId")
    assert has_id is not None


def test_trait_methods_are_methods(rust_dir):
    r = RustAdapter().parse(rust_dir / "user_service.rs")
    has_id = _find(r.declarations, kind=KIND_INTERFACE, name="HasId")
    methods = [c for c in has_id.children if c.kind == KIND_METHOD]
    assert any(m.name == "id" for m in methods)


def test_trait_default_method_surfaces(rust_dir):
    r = RustAdapter().parse(rust_dir / "hierarchy.rs")
    quad = _find(r.declarations, kind=KIND_INTERFACE, name="Quadruped")
    legs = _find(quad.children, kind=KIND_METHOD, name="legs")
    assert legs is not None
    assert "u32" in legs.signature


def test_trait_supertraits_become_bases(rust_dir):
    r = RustAdapter().parse(rust_dir / "hierarchy.rs")
    quad = _find(r.declarations, kind=KIND_INTERFACE, name="Quadruped")
    assert "Animal" in quad.bases


def test_trait_multiple_supertraits(rust_dir):
    """`pub trait Greeter: Send + Sync` — both supertraits collected."""
    r = RustAdapter().parse(rust_dir / "user_service.rs")
    # user_service has no multi-supertrait; do an inline parse.
    _ = r  # keep the fixture parse warm
    src = b"pub trait Greeter: Send + Sync {}\n"
    with _inline_rust(src) as p:
        result = RustAdapter().parse(p)
        greeter = _find(result.declarations, kind=KIND_INTERFACE, name="Greeter")
        assert "Send" in greeter.bases
        assert "Sync" in greeter.bases


def test_trait_lifetime_supertraits_skipped():
    """`'static` and other lifetimes shouldn't pollute `bases`."""
    src = b"pub trait Sub: Super1 + 'static {}\n"
    with _inline_rust(src) as p:
        result = RustAdapter().parse(p)
        sub = _find(result.declarations, kind=KIND_INTERFACE, name="Sub")
        assert "Super1" in sub.bases
        assert "'static" not in sub.bases


def test_trait_associated_type(rust_dir):
    r = RustAdapter().parse(rust_dir / "generics.rs")
    container = _find(r.declarations, kind=KIND_INTERFACE, name="Container")
    item = _find(container.children, kind=KIND_DELEGATE, name="Item")
    assert item is not None


def test_trait_associated_const(rust_dir):
    src = b"pub trait T { const MAX: u32 = 100; }\n"
    with _inline_rust(src) as p:
        r = RustAdapter().parse(p)
        t = _find(r.declarations, kind=KIND_INTERFACE, name="T")
        max_const = _find(t.children, kind=KIND_FIELD, name="MAX")
        assert max_const is not None


# --- Impl-block regrouping (the headline Rust feature) ------------------


def test_inherent_impl_methods_grouped_under_type(rust_dir):
    r = RustAdapter().parse(rust_dir / "user_service.rs")
    user = _find(r.declarations, kind=KIND_STRUCT, name="User")
    methods = [c for c in user.children if c.kind == KIND_METHOD]
    method_names = {m.name for m in methods}
    assert {"new", "raw_id", "internal_check"}.issubset(method_names)


def test_trait_impl_methods_also_grouped_under_type(rust_dir):
    """`impl HasId for User` methods land on User too, alongside inherent ones."""
    r = RustAdapter().parse(rust_dir / "user_service.rs")
    user = _find(r.declarations, kind=KIND_STRUCT, name="User")
    method_names = {c.name for c in user.children if c.kind == KIND_METHOD}
    assert "id" in method_names  # this is from `impl HasId for User`


def test_trait_impl_adds_trait_to_bases(rust_dir):
    """The killer feature: `impl HasId for User` → User.bases contains "HasId"."""
    r = RustAdapter().parse(rust_dir / "user_service.rs")
    user = _find(r.declarations, kind=KIND_STRUCT, name="User")
    assert "HasId" in user.bases


def test_inherent_impl_does_not_add_to_bases(rust_dir):
    """Inherent `impl User { ... }` is not a trait impl — no base added."""
    r = RustAdapter().parse(rust_dir / "user_service.rs")
    user = _find(r.declarations, kind=KIND_STRUCT, name="User")
    # The only base recorded should be the trait impl ("HasId"), not "User" itself.
    assert "User" not in user.bases


def test_multiple_trait_impls_accumulate_bases(rust_dir):
    """`impl Animal for Dog` and `impl Quadruped for Dog` both land in bases."""
    r = RustAdapter().parse(rust_dir / "hierarchy.rs")
    dog = _find(r.declarations, kind=KIND_STRUCT, name="Dog")
    assert "Animal" in dog.bases
    assert "Quadruped" in dog.bases


def test_method_visibility_preserved_through_impl_grouping(rust_dir):
    """`pub fn new` inside `impl User` keeps visibility=public after regrouping."""
    r = RustAdapter().parse(rust_dir / "user_service.rs")
    user = _find(r.declarations, kind=KIND_STRUCT, name="User")
    new = _find(user.children, kind=KIND_METHOD, name="new")
    private_helper = _find(user.children, kind=KIND_METHOD, name="internal_check")
    assert new.visibility == "public"
    assert private_helper.visibility == "private"


def test_method_doc_preserved_through_impl_grouping(rust_dir):
    r = RustAdapter().parse(rust_dir / "user_service.rs")
    user = _find(r.declarations, kind=KIND_STRUCT, name="User")
    new = _find(user.children, kind=KIND_METHOD, name="new")
    assert any("Constructor" in d for d in new.docs)


def test_cross_file_impl_methods_spill_at_top_level(rust_dir):
    """`impl ExternalType` where ExternalType isn't local → methods at top level."""
    r = RustAdapter().parse(rust_dir / "cross_file_impl.rs")
    top_level_method_names = {d.name for d in r.declarations if d.kind == KIND_METHOD}
    assert {"extension_method", "another_extension"}.issubset(top_level_method_names)
    # The local-on-local impl still groups correctly.
    local = _find(r.declarations, kind=KIND_STRUCT, name="LocalType")
    assert _find(local.children, kind=KIND_METHOD, name="local_method") is not None


def test_cross_file_trait_impl_methods_spill(rust_dir):
    """`impl LocalTrait for ExternalType` → marker spills, no crash."""
    r = RustAdapter().parse(rust_dir / "cross_file_impl.rs")
    spilled = {d.name for d in r.declarations if d.kind == KIND_METHOD}
    assert "marker" in spilled


def test_impl_extends_type_line_range(rust_dir):
    """When an impl block adds children, the type's end_line stretches.

    User starts at line 10 but the second `impl HasId for User` block
    extends past the inherent impl block — User's reported end_line
    should reach into the trait-impl region.
    """
    r = RustAdapter().parse(rust_dir / "user_service.rs")
    user = _find(r.declarations, kind=KIND_STRUCT, name="User")
    # Trait impl ends around line 46; struct body alone ends around line 14.
    assert user.end_line > 14


# --- Functions / methods --------------------------------------------------


def test_top_level_function(rust_dir):
    r = RustAdapter().parse(rust_dir / "user_service.rs")
    fmt = _find(r.declarations, kind=KIND_FUNCTION, name="format_user")
    assert fmt is not None
    assert "pub fn format_user" in fmt.signature


def test_function_signature_omits_body(rust_dir):
    r = RustAdapter().parse(rust_dir / "user_service.rs")
    fmt = _find(r.declarations, kind=KIND_FUNCTION, name="format_user")
    assert "{" not in fmt.signature
    assert "format!" not in fmt.signature  # body content excluded


def test_function_with_lifetimes(rust_dir):
    r = RustAdapter().parse(rust_dir / "generics.rs")
    longest = _find(r.declarations, kind=KIND_FUNCTION, name="longest")
    assert "'a" in longest.signature


def test_function_with_where_clause(rust_dir):
    r = RustAdapter().parse(rust_dir / "generics.rs")
    complex_ = _find(r.declarations, kind=KIND_FUNCTION, name="complex")
    assert "where" in complex_.signature
    assert "Debug" in complex_.signature


def test_function_with_generic_bounds(rust_dir):
    r = RustAdapter().parse(rust_dir / "generics.rs")
    process = _find(r.declarations, kind=KIND_FUNCTION, name="process")
    assert "Fn(T) -> T" in process.signature


def test_function_signature_item_in_trait_is_method(rust_dir):
    """`fn foo(&self) -> X;` inside trait body — has no body, still KIND_METHOD."""
    r = RustAdapter().parse(rust_dir / "user_service.rs")
    has_id = _find(r.declarations, kind=KIND_INTERFACE, name="HasId")
    id_method = _find(has_id.children, kind=KIND_METHOD, name="id")
    assert id_method is not None
    assert id_method.signature.endswith("u64")  # signature ends at return type


# --- Const / static ------------------------------------------------------


def test_const_is_field(rust_dir):
    r = RustAdapter().parse(rust_dir / "user_service.rs")
    max_users = _find(r.declarations, kind=KIND_FIELD, name="MAX_USERS")
    assert max_users is not None
    assert "const" in max_users.signature


def test_static_is_field(rust_dir):
    r = RustAdapter().parse(rust_dir / "user_service.rs")
    name = _find(r.declarations, kind=KIND_FIELD, name="SERVICE_NAME")
    assert name is not None
    assert "static" in name.signature


# --- Type aliases / macros -----------------------------------------------


def test_type_alias_is_delegate():
    src = b"pub type UserMap = std::collections::HashMap<u64, String>;\n"
    with _inline_rust(src) as p:
        r = RustAdapter().parse(p)
        alias = _find(r.declarations, kind=KIND_DELEGATE, name="UserMap")
        assert alias is not None
        assert "type UserMap" in alias.signature


def test_macro_definition_is_delegate(rust_dir):
    r = RustAdapter().parse(rust_dir / "unions_and_macros.rs")
    my_vec = _find(r.declarations, kind=KIND_DELEGATE, name="my_vec")
    assert my_vec is not None
    assert "macro_rules!" in my_vec.signature


def test_multiple_macros(rust_dir):
    r = RustAdapter().parse(rust_dir / "unions_and_macros.rs")
    macros = _find_all(r.declarations, kind=KIND_DELEGATE)
    macro_names = {m.name for m in macros}
    assert {"my_vec", "square"}.issubset(macro_names)


# --- Modules --------------------------------------------------------------


def test_inline_module_is_namespace(rust_dir):
    r = RustAdapter().parse(rust_dir / "modules.rs")
    outer = _find(r.declarations, kind=KIND_NAMESPACE, name="outer")
    assert outer is not None


def test_module_contains_items(rust_dir):
    r = RustAdapter().parse(rust_dir / "modules.rs")
    outer = _find(r.declarations, kind=KIND_NAMESPACE, name="outer")
    child_names = {c.name for c in outer.children}
    assert "Public" in child_names
    assert "exported" in child_names


def test_nested_modules(rust_dir):
    """`mod outer { mod nested { mod even_deeper { struct DeepStruct } } }`."""
    r = RustAdapter().parse(rust_dir / "modules.rs")
    deep = _find(r.declarations, kind=KIND_STRUCT, name="DeepStruct")
    assert deep is not None  # found via deep recursion


def test_external_module_reference_is_leaf_namespace(rust_dir):
    """`pub mod external_a;` → namespace with no children."""
    r = RustAdapter().parse(rust_dir / "modules.rs")
    ext = _find(r.declarations, kind=KIND_NAMESPACE, name="external_a")
    assert ext is not None
    assert ext.children == []


def test_module_visibility_classified(rust_dir):
    r = RustAdapter().parse(rust_dir / "modules.rs")
    restricted = _find(r.declarations, kind=KIND_NAMESPACE, name="restricted_external")
    assert restricted.visibility == "internal"


# --- Visibility classifier matrix ----------------------------------------


def test_visibility_pub_is_public(rust_dir):
    r = RustAdapter().parse(rust_dir / "visibility_matrix.rs")
    fn = _find(r.declarations, kind=KIND_FUNCTION, name="fully_public")
    assert fn.visibility == "public"


def test_visibility_pub_crate_is_internal(rust_dir):
    r = RustAdapter().parse(rust_dir / "visibility_matrix.rs")
    fn = _find(r.declarations, kind=KIND_FUNCTION, name="crate_only")
    assert fn.visibility == "internal"


def test_visibility_pub_super_is_internal(rust_dir):
    r = RustAdapter().parse(rust_dir / "visibility_matrix.rs")
    fn = _find(r.declarations, kind=KIND_FUNCTION, name="super_only")
    assert fn.visibility == "internal"


def test_visibility_pub_self_is_internal(rust_dir):
    r = RustAdapter().parse(rust_dir / "visibility_matrix.rs")
    fn = _find(r.declarations, kind=KIND_FUNCTION, name="self_only")
    assert fn.visibility == "internal"


def test_visibility_pub_in_path_is_internal(rust_dir):
    r = RustAdapter().parse(rust_dir / "visibility_matrix.rs")
    fn = _find(r.declarations, kind=KIND_FUNCTION, name="in_path")
    assert fn.visibility == "internal"


def test_visibility_default_is_private(rust_dir):
    r = RustAdapter().parse(rust_dir / "visibility_matrix.rs")
    fn = _find(r.declarations, kind=KIND_FUNCTION, name="private_default")
    assert fn.visibility == "private"


# --- Doc comments / attributes ------------------------------------------


def test_single_line_outer_doc_attaches(rust_dir):
    r = RustAdapter().parse(rust_dir / "comments_edge.rs")
    fn = _find(r.declarations, kind=KIND_FUNCTION, name="single_doc")
    assert any("Single-line outer doc" in d for d in fn.docs)


def test_multiline_outer_docs_attach_in_order(rust_dir):
    r = RustAdapter().parse(rust_dir / "comments_edge.rs")
    fn = _find(r.declarations, kind=KIND_FUNCTION, name="multiline_doc")
    assert len(fn.docs) == 3
    assert "First" in fn.docs[0]
    assert "Second" in fn.docs[1]
    assert "Third" in fn.docs[2]


def test_block_doc_comment_attaches(rust_dir):
    r = RustAdapter().parse(rust_dir / "comments_edge.rs")
    fn = _find(r.declarations, kind=KIND_FUNCTION, name="block_single")
    assert fn.docs
    assert any("Block doc" in d for d in fn.docs)


def test_multiline_block_doc_attaches(rust_dir):
    r = RustAdapter().parse(rust_dir / "comments_edge.rs")
    fn = _find(r.declarations, kind=KIND_FUNCTION, name="block_multi")
    assert fn.docs


def test_non_doc_comment_does_not_attach(rust_dir):
    """Plain `// ...` comment must NOT promote to docs on the next item."""
    r = RustAdapter().parse(rust_dir / "comments_edge.rs")
    fn = _find(r.declarations, kind=KIND_FUNCTION, name="no_docs")
    assert fn.docs == []


def test_blank_line_gap_detaches_doc(rust_dir):
    r = RustAdapter().parse(rust_dir / "comments_edge.rs")
    fn = _find(r.declarations, kind=KIND_FUNCTION, name="after_gap")
    assert fn.docs == []


def test_inner_doc_comment_does_not_attach(rust_dir):
    """`//!` at the top of the file is for the enclosing module — must not
    attach to the first item below it.
    """
    r = RustAdapter().parse(rust_dir / "user_service.rs")
    user = _find(r.declarations, kind=KIND_STRUCT, name="User")
    # The first User doc should be the `///` outer doc, not the `//!`.
    assert all("Module-level inner doc" not in d for d in user.docs)


def test_attribute_collected_in_attrs(rust_dir):
    r = RustAdapter().parse(rust_dir / "comments_edge.rs")
    s = _find(r.declarations, kind=KIND_STRUCT, name="InterleavedDocAttrs")
    assert any("derive" in a for a in s.attrs)
    assert any("repr" in a for a in s.attrs)


def test_doc_between_attributes_still_collected(rust_dir):
    r = RustAdapter().parse(rust_dir / "comments_edge.rs")
    s = _find(r.declarations, kind=KIND_STRUCT, name="InterleavedDocAttrs")
    # Both the top doc AND the doc between attributes should be present.
    assert len(s.docs) >= 2


def test_doc_above_attribute_collected(rust_dir):
    """`/// doc` followed by `#[derive(...)]` followed by `fn foo` — doc
    should still attach despite the attr in the middle.
    """
    r = RustAdapter().parse(rust_dir / "comments_edge.rs")
    fn = _find(r.declarations, kind=KIND_FUNCTION, name="doc_after_attr")
    assert any("Doc AFTER attribute" in d for d in fn.docs)


# --- Generics & associated types ----------------------------------------


def test_struct_generic_parameters_in_signature(rust_dir):
    r = RustAdapter().parse(rust_dir / "generics.rs")
    wrapper = _find(r.declarations, kind=KIND_STRUCT, name="Wrapper")
    assert "<T:" in wrapper.signature
    assert "Send + Sync" in wrapper.signature


def test_associated_type_with_bounds(rust_dir):
    r = RustAdapter().parse(rust_dir / "generics.rs")
    container = _find(r.declarations, kind=KIND_INTERFACE, name="Container")
    iter_type = _find(container.children, kind=KIND_DELEGATE, name="Iter")
    assert iter_type is not None
    assert "Iterator" in iter_type.signature


def test_impl_block_associated_type_assigned(rust_dir):
    """`type Item = T;` inside `impl Container for VecContainer<T>` should
    surface as a delegate child of VecContainer.
    """
    r = RustAdapter().parse(rust_dir / "generics.rs")
    vc = _find(r.declarations, kind=KIND_STRUCT, name="VecContainer")
    item = _find(vc.children, kind=KIND_DELEGATE, name="Item")
    assert item is not None


# --- Foreign / extern blocks --------------------------------------------


def test_extern_c_block_creates_namespace(rust_dir):
    r = RustAdapter().parse(rust_dir / "extern_block.rs")
    ext_c = _find(r.declarations, kind=KIND_NAMESPACE, name='extern "C"')
    assert ext_c is not None


def test_extern_block_function_signature_is_function(rust_dir):
    r = RustAdapter().parse(rust_dir / "extern_block.rs")
    ext_c = _find(r.declarations, kind=KIND_NAMESPACE, name='extern "C"')
    abs_fn = _find(ext_c.children, kind=KIND_FUNCTION, name="abs")
    assert abs_fn is not None
    assert "c_int" in abs_fn.signature


def test_extern_block_static_is_field(rust_dir):
    r = RustAdapter().parse(rust_dir / "extern_block.rs")
    ext_c = _find(r.declarations, kind=KIND_NAMESPACE, name='extern "C"')
    var = _find(ext_c.children, kind=KIND_FIELD, name="MAX_VALUE")
    assert var is not None
    assert "static" in var.signature


def test_multiple_extern_abis(rust_dir):
    """`extern "C" { ... }` and `extern "Rust" { ... }` produce two namespaces."""
    r = RustAdapter().parse(rust_dir / "extern_block.rs")
    abis = {
        d.name for d in r.declarations
        if d.kind == KIND_NAMESPACE and d.name.startswith("extern")
    }
    assert 'extern "C"' in abis
    assert 'extern "Rust"' in abis


def test_extern_fn_with_body_is_top_level(rust_dir):
    """`pub extern "C" fn export_to_c` (with body) is NOT inside an extern
    block — it's a top-level function with an extern modifier.
    """
    r = RustAdapter().parse(rust_dir / "extern_block.rs")
    export = _find(r.declarations, kind=KIND_FUNCTION, name="export_to_c")
    assert export is not None
    assert "extern" in export.signature


# --- Implements query (transitive) --------------------------------------


def test_implements_finds_direct_trait_impl(rust_dir):
    """`implements HasId` should find User."""
    from ast_outline.adapters import collect_files
    from ast_outline.core import find_implementations

    files = [rust_dir / "user_service.rs"]
    parsed = [RustAdapter().parse(f) for f in files]
    matches = find_implementations(parsed, "HasId")
    names = {m.name for m in matches}
    assert "User" in names


def test_implements_finds_transitive_trait(rust_dir):
    """`implements Animal` should find Dog/Wolf/Cat (direct via `impl Animal for X`)
    and Quadruped/PackAnimal (transitive via supertrait chain).
    """
    from ast_outline.core import find_implementations

    parsed = [RustAdapter().parse(rust_dir / "hierarchy.rs")]
    matches = find_implementations(parsed, "Animal")
    names = {m.name for m in matches}
    assert {"Dog", "Wolf", "Cat", "Quadruped"}.issubset(names)


def test_implements_via_chain_recorded(rust_dir):
    """PackAnimal → Quadruped → Animal — query Animal should report the chain."""
    from ast_outline.core import find_implementations

    parsed = [RustAdapter().parse(rust_dir / "hierarchy.rs")]
    matches = find_implementations(parsed, "Animal")
    pack = next((m for m in matches if m.name == "PackAnimal"), None)
    assert pack is not None
    assert "Quadruped" in pack.via


def test_implements_direct_only_filter(rust_dir):
    """`transitive=False` should exclude transitive matches."""
    from ast_outline.core import find_implementations

    parsed = [RustAdapter().parse(rust_dir / "hierarchy.rs")]
    direct = find_implementations(parsed, "Animal", transitive=False)
    names = {m.name for m in direct}
    # Quadruped is direct (`pub trait Quadruped: Animal`), Dog/Wolf/Cat
    # are direct (via `impl Animal for X`), but PackAnimal goes through
    # Quadruped — must NOT appear.
    assert "PackAnimal" not in names


# --- Symbol search (find_symbols / show) --------------------------------


def test_find_symbols_top_level_function(rust_dir):
    from ast_outline.core import find_symbols

    r = RustAdapter().parse(rust_dir / "user_service.rs")
    matches = find_symbols(r, "format_user")
    assert len(matches) == 1
    assert matches[0].kind == KIND_FUNCTION


def test_find_symbols_method_via_qualified_name(rust_dir):
    from ast_outline.core import find_symbols

    r = RustAdapter().parse(rust_dir / "user_service.rs")
    matches = find_symbols(r, "User.new")
    assert len(matches) == 1
    assert matches[0].kind == KIND_METHOD
    # Source slice should contain the method body.
    assert "Foo" in matches[0].source or "User" in matches[0].source


def test_find_symbols_nested_module(rust_dir):
    from ast_outline.core import find_symbols

    r = RustAdapter().parse(rust_dir / "modules.rs")
    matches = find_symbols(r, "outer.nested.deep_call")
    assert len(matches) == 1


# --- Broken syntax -------------------------------------------------------


def test_broken_syntax_does_not_crash(rust_dir):
    r = RustAdapter().parse(rust_dir / "broken_syntax.rs")
    assert r is not None
    assert r.error_count > 0


def test_broken_syntax_salvages_valid_items(rust_dir):
    r = RustAdapter().parse(rust_dir / "broken_syntax.rs")
    valid = _find(r.declarations, kind=KIND_STRUCT, name="Valid")
    assert valid is not None


# --- Outline / digest rendering smoke ------------------------------------


def test_outline_renders_user_service(rust_dir):
    from ast_outline.core import OutlineOptions, render_outline

    r = RustAdapter().parse(rust_dir / "user_service.rs")
    out = render_outline(r, OutlineOptions())
    assert "pub struct User" in out
    assert "pub trait HasId" in out or "trait HasId" in out
    # Method grouped under struct (line numbers in indented child line).
    assert "pub fn new" in out


def test_digest_shows_trait_in_bases(rust_dir):
    """`User : HasId` should appear in the digest line because the trait
    impl recorded HasId in User's bases.
    """
    from ast_outline.core import DigestOptions, render_digest

    r = RustAdapter().parse(rust_dir / "user_service.rs")
    digest = render_digest([r], DigestOptions())
    assert "User : HasId" in digest


def test_digest_shows_size_label_and_line_count(rust_dir):
    from ast_outline.core import DigestOptions, render_digest

    r = RustAdapter().parse(rust_dir / "user_service.rs")
    digest = render_digest([r], DigestOptions())
    assert "[tiny]" in digest or "[medium]" in digest or "[large]" in digest


def test_digest_marks_broken_file(rust_dir):
    from ast_outline.core import DigestOptions, render_digest

    r = RustAdapter().parse(rust_dir / "broken_syntax.rs")
    digest = render_digest([r], DigestOptions())
    assert "[broken]" in digest


# --- Line-range integrity ------------------------------------------------


def test_line_ranges_are_one_based(rust_dir):
    r = RustAdapter().parse(rust_dir / "user_service.rs")
    user = _find(r.declarations, kind=KIND_STRUCT, name="User")
    assert user.start_line >= 1
    assert user.end_line >= user.start_line


def test_method_line_range_lies_inside_impl_block(rust_dir):
    """Methods regrouped under User must still report their actual source
    line numbers, not the struct's.
    """
    r = RustAdapter().parse(rust_dir / "user_service.rs")
    user = _find(r.declarations, kind=KIND_STRUCT, name="User")
    new = _find(user.children, kind=KIND_METHOD, name="new")
    # User struct body itself is around lines 10-14; `new` is in the
    # impl block much later.
    assert new.start_line > user.start_line + 3


# --- Edge cases ----------------------------------------------------------


def test_use_declarations_skipped(rust_dir):
    """`use std::...;` should not produce any declarations."""
    r = RustAdapter().parse(rust_dir / "user_service.rs")
    use_like = [d for d in r.declarations if "use " in d.signature]
    assert use_like == []


def test_extern_crate_skipped(rust_dir):
    r = RustAdapter().parse(rust_dir / "edge_cases.rs")
    extern_crate = [d for d in r.declarations if "extern crate" in d.signature]
    assert extern_crate == []


def test_empty_trait():
    src = b"pub trait Marker {}\n"
    with _inline_rust(src) as p:
        r = RustAdapter().parse(p)
        marker = _find(r.declarations, kind=KIND_INTERFACE, name="Marker")
        assert marker is not None
        assert marker.children == []


def test_empty_file():
    src = b"\n\n"
    with _inline_rust(src) as p:
        r = RustAdapter().parse(p)
        assert r.declarations == []
        assert r.error_count == 0


def test_only_comments_file():
    src = b"// just a comment\n// another\n"
    with _inline_rust(src) as p:
        r = RustAdapter().parse(p)
        assert r.declarations == []


def test_function_with_no_return_type():
    src = b"pub fn no_return() { println!(\"hi\"); }\n"
    with _inline_rust(src) as p:
        r = RustAdapter().parse(p)
        fn = _find(r.declarations, kind=KIND_FUNCTION, name="no_return")
        assert fn is not None
        assert "pub fn no_return()" in fn.signature


def test_async_fn_signature():
    src = b"pub async fn fetch() -> u32 { 0 }\n"
    with _inline_rust(src) as p:
        r = RustAdapter().parse(p)
        fn = _find(r.declarations, kind=KIND_FUNCTION, name="fetch")
        assert fn is not None
        assert "async" in fn.signature


def test_unsafe_fn_signature():
    src = b"pub unsafe fn raw_ptr_op() -> *mut u8 { std::ptr::null_mut() }\n"
    with _inline_rust(src) as p:
        r = RustAdapter().parse(p)
        fn = _find(r.declarations, kind=KIND_FUNCTION, name="raw_ptr_op")
        assert fn is not None
        assert "unsafe" in fn.signature


def test_const_fn_signature():
    src = b"pub const fn compute() -> u32 { 42 }\n"
    with _inline_rust(src) as p:
        r = RustAdapter().parse(p)
        fn = _find(r.declarations, kind=KIND_FUNCTION, name="compute")
        assert fn is not None
        # The full keyword chain `pub const fn` should be in the sig.
        assert "const fn" in fn.signature


def test_impl_on_reference_type():
    """`impl<T> MyTrait for &T` — receiver is a `reference_type`. The
    drilling helper should resolve to T (the type_identifier inside the
    reference).
    """
    src = b"""
pub trait MyTrait {}
pub struct Holder;
impl MyTrait for &Holder {}
"""
    with _inline_rust(src) as p:
        r = RustAdapter().parse(p)
        holder = _find(r.declarations, kind=KIND_STRUCT, name="Holder")
        assert holder is not None
        assert "MyTrait" in holder.bases


def test_impl_on_generic_type():
    """`impl Foo<u32> { ... }` — drill should resolve to "Foo"."""
    src = b"""
pub struct Foo<T> { _x: T }
impl Foo<u32> {
    pub fn specific() {}
}
"""
    with _inline_rust(src) as p:
        r = RustAdapter().parse(p)
        foo = _find(r.declarations, kind=KIND_STRUCT, name="Foo")
        method = _find(foo.children, kind=KIND_METHOD, name="specific")
        assert method is not None


def test_impl_on_scoped_type_does_not_match_local():
    """`impl std::fmt::Display for Foo` — Foo is local but the trait is
    scoped. Resolving to the trailing identifier (`Display`) is the
    right behaviour for `bases`.
    """
    src = b"""
pub struct Foo;
impl std::fmt::Display for Foo {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result { Ok(()) }
}
"""
    with _inline_rust(src) as p:
        r = RustAdapter().parse(p)
        foo = _find(r.declarations, kind=KIND_STRUCT, name="Foo")
        assert "Display" in foo.bases


def test_const_signature_strips_trailing_semicolon():
    src = b"pub const X: u32 = 42;\n"
    with _inline_rust(src) as p:
        r = RustAdapter().parse(p)
        x = _find(r.declarations, kind=KIND_FIELD, name="X")
        assert not x.signature.endswith(";")


# --- Tuple-struct positional fields -------------------------------------


def test_tuple_struct_field_count():
    """`pub struct Pair(pub i32, i32)` produces two positional fields
    named `0` and `1` (matching how they're accessed in source: `pair.0`).
    """
    src = b"pub struct Pair(pub i32, i32);\n"
    with _inline_rust(src) as p:
        r = RustAdapter().parse(p)
        pair = _find(r.declarations, kind=KIND_STRUCT, name="Pair")
        fields = [c for c in pair.children if c.kind == KIND_FIELD]
        assert [f.name for f in fields] == ["0", "1"]


def test_tuple_struct_field_visibility():
    """The first positional field is `pub`, the second is private."""
    src = b"pub struct Pair(pub i32, i32);\n"
    with _inline_rust(src) as p:
        r = RustAdapter().parse(p)
        pair = _find(r.declarations, kind=KIND_STRUCT, name="Pair")
        fields = [c for c in pair.children if c.kind == KIND_FIELD]
        assert fields[0].visibility == "public"
        assert fields[1].visibility == "private"


def test_tuple_struct_field_signature_carries_type():
    src = b"pub struct Sized(pub Vec<u8>, String);\n"
    with _inline_rust(src) as p:
        r = RustAdapter().parse(p)
        sized = _find(r.declarations, kind=KIND_STRUCT, name="Sized")
        fields = [c for c in sized.children if c.kind == KIND_FIELD]
        assert "Vec<u8>" in fields[0].signature
        assert "String" in fields[1].signature


def test_unit_struct_has_no_field_children_after_tuple_path():
    """Regression: the new tuple-field path must not generate any children
    for unit structs (which have no body at all).
    """
    src = b"pub struct Unit;\n"
    with _inline_rust(src) as p:
        r = RustAdapter().parse(p)
        unit = _find(r.declarations, kind=KIND_STRUCT, name="Unit")
        assert [c for c in unit.children if c.kind == KIND_FIELD] == []


# --- Enum variant visibility (so --no-private keeps them) ---------------


def test_enum_variants_are_public_for_filter_purposes(rust_dir):
    """Bug fix: previously variants got `_visibility(v) → "private"`,
    which made `--no-private` hide every variant of a `pub enum`.
    """
    r = RustAdapter().parse(rust_dir / "enum_advanced.rs")
    direction = _find(r.declarations, kind=KIND_ENUM, name="Direction")
    for v in direction.children:
        if v.kind == KIND_ENUM_MEMBER:
            assert v.visibility == "public"


def test_outline_with_no_private_keeps_enum_variants(rust_dir):
    """End-to-end check: `--no-private` (include_private=False) does NOT
    drop enum variants of a public enum.
    """
    from ast_outline.core import OutlineOptions, render_outline

    r = RustAdapter().parse(rust_dir / "enum_advanced.rs")
    out = render_outline(r, OutlineOptions(include_private=False))
    # Each variant of `pub enum Direction` should still appear.
    assert "North" in out
    assert "South" in out
    assert "East" in out
    assert "West" in out


# --- Macro visibility -----------------------------------------------------


def test_macro_without_export_is_private():
    """`macro_rules! foo` without `#[macro_export]` is module-local —
    treat as private so `--no-private` correctly hides it.
    """
    src = b"macro_rules! my_macro { () => { 1 }; }\n"
    with _inline_rust(src) as p:
        r = RustAdapter().parse(p)
        m = _find(r.declarations, kind=KIND_DELEGATE, name="my_macro")
        assert m.visibility == "private"


def test_macro_with_export_is_public():
    src = b"#[macro_export]\nmacro_rules! my_macro { () => { 1 }; }\n"
    with _inline_rust(src) as p:
        r = RustAdapter().parse(p)
        m = _find(r.declarations, kind=KIND_DELEGATE, name="my_macro")
        assert m.visibility == "public"


def test_macro_export_attached_attr_is_visible(rust_dir):
    """The fixture `unions_and_macros.rs` has `#[macro_export]` on
    `my_vec` — it should classify as public.
    """
    r = RustAdapter().parse(rust_dir / "unions_and_macros.rs")
    my_vec = _find(r.declarations, kind=KIND_DELEGATE, name="my_vec")
    square = _find(r.declarations, kind=KIND_DELEGATE, name="square")
    assert my_vec.visibility == "public"
    assert square.visibility == "private"  # no #[macro_export]
