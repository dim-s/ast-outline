"""Tests for the TypeScript / JavaScript adapter (.ts .tsx .js .jsx)."""
from __future__ import annotations

from code_outline.adapters.typescript import TypeScriptAdapter
from code_outline.core import (
    KIND_CLASS,
    KIND_CTOR,
    KIND_ENUM,
    KIND_ENUM_MEMBER,
    KIND_FIELD,
    KIND_FUNCTION,
    KIND_INTERFACE,
    KIND_METHOD,
    Declaration,
)


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


def test_parse_ts_file(fixtures_dir):
    path = fixtures_dir / "typescript" / "storage_service.ts"
    result = TypeScriptAdapter().parse(path)
    assert result.path == path
    assert result.language == "typescript"
    assert result.line_count > 0
    assert result.declarations


def test_parse_tsx_file(fixtures_dir):
    path = fixtures_dir / "typescript" / "react_page.tsx"
    result = TypeScriptAdapter().parse(path)
    assert result.language == "typescript"
    assert result.declarations


def test_parse_js_file(fixtures_dir):
    """JS is parsed by the TS grammar (superset); adapter should still produce IR."""
    path = fixtures_dir / "typescript" / "plain_module.js"
    result = TypeScriptAdapter().parse(path)
    assert result.declarations
    # `greet` and `add` are exported functions, `Counter` is a class
    assert _find(result.declarations, kind=KIND_FUNCTION, name="greet") is not None
    assert _find(result.declarations, kind=KIND_FUNCTION, name="add") is not None
    assert _find(result.declarations, kind=KIND_CLASS, name="Counter") is not None


# --- Classes --------------------------------------------------------------


def test_class_basic_structure(fixtures_dir):
    r = TypeScriptAdapter().parse(fixtures_dir / "typescript" / "storage_service.ts")
    svc = _find(r.declarations, kind=KIND_CLASS, name="StorageService")
    assert svc is not None
    # Class has fields + methods
    method_names = {c.name for c in svc.children if c.kind in (KIND_METHOD, KIND_CTOR)}
    assert {"init", "doInit", "getAll", "getProject", "saveProject", "log"}.issubset(method_names)
    field_names = {c.name for c in svc.children if c.kind == KIND_FIELD}
    assert {"db", "initPromise"}.issubset(field_names)


def test_class_method_visibility_modifiers(fixtures_dir):
    r = TypeScriptAdapter().parse(fixtures_dir / "typescript" / "storage_service.ts")
    svc = _find(r.declarations, kind=KIND_CLASS, name="StorageService")
    methods = {c.name: c for c in svc.children if c.kind == KIND_METHOD}
    # `async init(): ...` has no modifier → default public in TS
    assert methods["init"].visibility == "public"
    # `private async doInit`
    assert methods["doInit"].visibility == "private"
    # `protected log`
    assert methods["log"].visibility == "protected"


def test_class_field_visibility(fixtures_dir):
    r = TypeScriptAdapter().parse(fixtures_dir / "typescript" / "storage_service.ts")
    svc = _find(r.declarations, kind=KIND_CLASS, name="StorageService")
    fields = {c.name: c for c in svc.children if c.kind == KIND_FIELD}
    assert fields["db"].visibility == "private"
    assert fields["initPromise"].visibility == "private"


def test_class_field_signature_drops_default_value(fixtures_dir):
    r = TypeScriptAdapter().parse(fixtures_dir / "typescript" / "storage_service.ts")
    svc = _find(r.declarations, kind=KIND_CLASS, name="StorageService")
    db = next(c for c in svc.children if c.name == "db")
    # Signature should keep the type but drop the `= null` default
    assert "IDBDatabase" in db.signature
    assert "= null" not in db.signature


def test_constructor_mapped_to_kind_ctor(fixtures_dir):
    r = TypeScriptAdapter().parse(fixtures_dir / "typescript" / "plain_module.js")
    counter = _find(r.declarations, kind=KIND_CLASS, name="Counter")
    ctor = _find(counter.children, name="constructor")
    assert ctor is not None
    assert ctor.kind == KIND_CTOR


def test_class_extends_captured_as_base(fixtures_dir):
    """`class User extends Entity` → bases == ['Entity']. Uses types.ts
    which has an `interface User extends Entity` — tests the interface path;
    heritage for classes is covered in storage_service / decorators."""
    r = TypeScriptAdapter().parse(fixtures_dir / "typescript" / "types.ts")
    user = _find(r.declarations, kind=KIND_INTERFACE, name="User")
    assert user is not None
    assert "Entity" in user.bases


def test_generic_heritage_preserved(fixtures_dir):
    """`interface Repository<T extends Entity>` keeps its type parameters in
    the signature."""
    r = TypeScriptAdapter().parse(fixtures_dir / "typescript" / "types.ts")
    repo = _find(r.declarations, kind=KIND_INTERFACE, name="Repository")
    assert repo is not None
    assert "<T extends Entity>" in repo.signature


# --- Interfaces -----------------------------------------------------------


def test_interface_properties_become_fields(fixtures_dir):
    r = TypeScriptAdapter().parse(fixtures_dir / "typescript" / "storage_service.ts")
    iface = _find(r.declarations, kind=KIND_INTERFACE, name="DBSchema")
    names = {c.name for c in iface.children if c.kind == KIND_FIELD}
    assert {"projects", "documents", "settings"}.issubset(names)


def test_interface_method_signatures_become_methods(fixtures_dir):
    r = TypeScriptAdapter().parse(fixtures_dir / "typescript" / "types.ts")
    repo = _find(r.declarations, kind=KIND_INTERFACE, name="Repository")
    method_names = {c.name for c in repo.children if c.kind == KIND_METHOD}
    assert {"get", "list", "save"}.issubset(method_names)


# --- Enums ---------------------------------------------------------------


def test_numeric_enum_members(fixtures_dir):
    r = TypeScriptAdapter().parse(fixtures_dir / "typescript" / "types.ts")
    e = _find(r.declarations, kind=KIND_ENUM, name="Status")
    assert e is not None
    members = [c.name for c in e.children if c.kind == KIND_ENUM_MEMBER]
    assert members == ["Idle", "Loading", "Ready", "Error"]


def test_string_enum_members(fixtures_dir):
    r = TypeScriptAdapter().parse(fixtures_dir / "typescript" / "types.ts")
    e = _find(r.declarations, kind=KIND_ENUM, name="Priority")
    members = [c.name for c in e.children if c.kind == KIND_ENUM_MEMBER]
    assert members == ["Low", "Medium", "High"]


# --- Functions -----------------------------------------------------------


def test_top_level_function_declaration(fixtures_dir):
    r = TypeScriptAdapter().parse(fixtures_dir / "typescript" / "react_page.tsx")
    # `function wrapBody(content: string): string`
    fn = _find(r.declarations, kind=KIND_FUNCTION, name="wrapBody")
    assert fn is not None
    assert "function wrapBody" in fn.signature
    assert "): string" in fn.signature


def test_async_function_keeps_async_keyword(fixtures_dir):
    r = TypeScriptAdapter().parse(fixtures_dir / "typescript" / "react_page.tsx")
    gen = _find(r.declarations, kind=KIND_FUNCTION, name="generateStaticParams")
    assert gen is not None
    assert "async" in gen.signature


def test_export_default_function_component(fixtures_dir):
    """`export default function Page(...) {...}` is captured and retains its
    signature; the byte range starts at `export`."""
    path = fixtures_dir / "typescript" / "react_page.tsx"
    r = TypeScriptAdapter().parse(path)
    page = _find(r.declarations, kind=KIND_FUNCTION, name="Page")
    assert page is not None
    assert "function Page" in page.signature
    # Byte range should start at the `export` keyword so `show` prints it too
    slice_text = path.read_bytes()[page.start_byte : page.end_byte].decode("utf8")
    assert slice_text.startswith("export default function Page")


def test_arrow_function_assigned_to_const_is_function(fixtures_dir):
    """`export const Sidebar = ({ items }: ...): JSX.Element => (...)` → KIND_FUNCTION."""
    r = TypeScriptAdapter().parse(fixtures_dir / "typescript" / "react_page.tsx")
    sidebar = _find(r.declarations, kind=KIND_FUNCTION, name="Sidebar")
    assert sidebar is not None
    assert "Sidebar" in sidebar.signature
    # `=>` present at the end of the signature line (body starts after)
    assert "=>" in sidebar.signature


def test_const_with_primitive_value_is_field(fixtures_dir):
    """`const DB_NAME = "demo-db"` → KIND_FIELD, not KIND_FUNCTION."""
    r = TypeScriptAdapter().parse(fixtures_dir / "typescript" / "storage_service.ts")
    dbname = _find(r.declarations, kind=KIND_FIELD, name="DB_NAME")
    assert dbname is not None
    assert dbname.signature.startswith("const DB_NAME")


# --- Exports handling ----------------------------------------------------


def test_exported_class_preserves_export_in_byte_range(fixtures_dir):
    """`export class Foo` — byte range starts at `export`, so `show` prints
    the export keyword."""
    path = fixtures_dir / "typescript" / "storage_service.ts"
    r = TypeScriptAdapter().parse(path)
    svc = _find(r.declarations, kind=KIND_CLASS, name="StorageService")
    slice_text = path.read_bytes()[svc.start_byte : svc.end_byte].decode("utf8")
    assert slice_text.startswith("export class StorageService")


def test_non_exported_interface_still_captured(fixtures_dir):
    """`interface DBSchema` (no export) should still appear in the IR."""
    r = TypeScriptAdapter().parse(fixtures_dir / "typescript" / "storage_service.ts")
    schema = _find(r.declarations, kind=KIND_INTERFACE, name="DBSchema")
    assert schema is not None


# --- Type aliases --------------------------------------------------------


def test_type_alias_becomes_field(fixtures_dir):
    r = TypeScriptAdapter().parse(fixtures_dir / "typescript" / "types.ts")
    ta = _find(r.declarations, kind=KIND_FIELD, name="UserId")
    assert ta is not None
    assert ta.signature.startswith("export type UserId")


def test_generic_type_alias(fixtures_dir):
    r = TypeScriptAdapter().parse(fixtures_dir / "typescript" / "types.ts")
    ta = _find(r.declarations, kind=KIND_FIELD, name="Result")
    assert ta is not None
    assert "Result<T>" in ta.signature


# --- Decorators ----------------------------------------------------------


def test_class_decorator_captured(fixtures_dir):
    r = TypeScriptAdapter().parse(fixtures_dir / "typescript" / "decorators.ts")
    ctl = _find(r.declarations, kind=KIND_CLASS, name="UserController")
    assert ctl is not None
    # `@Controller("/users")`
    assert any("@Controller" in a for a in ctl.attrs)


def test_method_decorators_captured(fixtures_dir):
    r = TypeScriptAdapter().parse(fixtures_dir / "typescript" / "decorators.ts")
    ctl = _find(r.declarations, kind=KIND_CLASS, name="UserController")
    find_all = _find(ctl.children, name="findAll")
    create = _find(ctl.children, name="create")
    assert find_all is not None
    assert create is not None
    assert any("@Get" in a for a in find_all.attrs)
    assert any("@Post" in a for a in create.attrs)


def test_decorated_class_byte_range_includes_decorator(fixtures_dir):
    """`show` should print the @Controller line together with the class."""
    path = fixtures_dir / "typescript" / "decorators.ts"
    r = TypeScriptAdapter().parse(path)
    ctl = _find(r.declarations, kind=KIND_CLASS, name="UserController")
    slice_text = path.read_bytes()[ctl.doc_start_byte : ctl.end_byte].decode("utf8")
    # The decorator line must be present before `class`
    assert "@Controller" in slice_text
    assert "export class UserController" in slice_text


# --- Visibility ----------------------------------------------------------


def test_class_member_without_modifier_defaults_to_public(fixtures_dir):
    r = TypeScriptAdapter().parse(fixtures_dir / "typescript" / "visibility.ts")
    cls = _find(r.declarations, kind=KIND_CLASS, name="Visibility")
    m = next(c for c in cls.children if c.name == "publicByDefault")
    assert m.visibility == "public"


def test_explicit_private_modifier_captured(fixtures_dir):
    r = TypeScriptAdapter().parse(fixtures_dir / "typescript" / "visibility.ts")
    cls = _find(r.declarations, kind=KIND_CLASS, name="Visibility")
    m = next(c for c in cls.children if c.name == "explicitPrivate")
    assert m.visibility == "private"


def test_protected_modifier_captured(fixtures_dir):
    r = TypeScriptAdapter().parse(fixtures_dir / "typescript" / "visibility.ts")
    cls = _find(r.declarations, kind=KIND_CLASS, name="Visibility")
    m = next(c for c in cls.children if c.name == "explicitProtected")
    assert m.visibility == "protected"


def test_hash_private_name_is_private(fixtures_dir):
    """`#truePrivate()` — TS 4.3+ hard-private names should be flagged private."""
    r = TypeScriptAdapter().parse(fixtures_dir / "typescript" / "visibility.ts")
    cls = _find(r.declarations, kind=KIND_CLASS, name="Visibility")
    m = next((c for c in cls.children if "truePrivate" in c.name), None)
    assert m is not None
    assert m.visibility == "private"


def test_underscore_prefix_is_conventionally_private(fixtures_dir):
    r = TypeScriptAdapter().parse(fixtures_dir / "typescript" / "visibility.ts")
    cls = _find(r.declarations, kind=KIND_CLASS, name="Visibility")
    m = next(c for c in cls.children if c.name == "_conventionallyPrivate")
    assert m.visibility == "private"


# --- Docs (preceding comments) -------------------------------------------


def test_jsdoc_above_function_captured_as_docs(fixtures_dir):
    r = TypeScriptAdapter().parse(fixtures_dir / "typescript" / "react_page.tsx")
    fn = _find(r.declarations, kind=KIND_FUNCTION, name="generateMetadata")
    assert fn.docs
    joined = "\n".join(fn.docs)
    assert "Generate metadata" in joined


def test_line_comments_above_function_captured_as_docs(fixtures_dir):
    r = TypeScriptAdapter().parse(fixtures_dir / "typescript" / "react_page.tsx")
    fn = _find(r.declarations, kind=KIND_FUNCTION, name="wrapBody")
    assert fn.docs
    assert any("plain helper" in d for d in fn.docs)
