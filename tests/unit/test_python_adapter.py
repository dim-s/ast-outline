"""Tests for the Python adapter."""
from __future__ import annotations

from ast_outline.adapters.python import PythonAdapter
from ast_outline.core import (
    KIND_CLASS,
    KIND_CTOR,
    KIND_FIELD,
    KIND_FUNCTION,
    KIND_METHOD,
    KIND_PROPERTY,
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


def test_parse_populates_result_metadata(python_dir):
    path = python_dir / "domain_model.py"
    result = PythonAdapter().parse(path)
    assert result.path == path
    assert result.language == "python"
    assert result.line_count > 0
    assert result.declarations, "should find decls"


# --- Top-level constructs -------------------------------------------------


def test_module_level_typed_assignment_is_field(python_dir):
    result = PythonAdapter().parse(python_dir / "domain_model.py")
    field = _find(result.declarations, kind=KIND_FIELD, name="DEFAULT_TIMEOUT")
    assert field is not None
    assert field.signature == "DEFAULT_TIMEOUT: int"


def test_module_level_assignment_without_type_is_field(python_dir):
    result = PythonAdapter().parse(python_dir / "domain_model.py")
    field = _find(result.declarations, kind=KIND_FIELD, name="_PRIVATE_CONSTANT")
    assert field is not None
    assert field.signature == "_PRIVATE_CONSTANT"
    assert field.visibility == "private"


def test_module_level_def_is_function(python_dir):
    result = PythonAdapter().parse(python_dir / "domain_model.py")
    fn = _find(result.declarations, kind=KIND_FUNCTION, name="public_helper")
    assert fn is not None
    # It's a module-level def — not KIND_METHOD, regardless of naming.
    assert fn.kind == KIND_FUNCTION


def test_private_helper_function_has_private_visibility(python_dir):
    result = PythonAdapter().parse(python_dir / "domain_model.py")
    fn = _find(result.declarations, kind=KIND_FUNCTION, name="_encode")
    assert fn is not None
    assert fn.visibility == "private"


# --- Classes --------------------------------------------------------------


def test_class_has_docstring_inside(python_dir):
    result = PythonAdapter().parse(python_dir / "domain_model.py")
    cls = _find(result.declarations, kind=KIND_CLASS, name="BaseEntity")
    assert cls is not None
    assert cls.docs_inside is True
    assert cls.docs
    assert any("entity hierarchy" in line for line in cls.docs)


def test_protocol_class_bases(python_dir):
    result = PythonAdapter().parse(python_dir / "domain_model.py")
    cls = _find(result.declarations, kind=KIND_CLASS, name="Repository")
    assert cls is not None
    assert cls.bases == ["Protocol"]


def test_metaclass_kwarg_stripped_from_bases(python_dir):
    result = PythonAdapter().parse(python_dir / "async_service.py")
    cls = _find(result.declarations, kind=KIND_CLASS, name="Handler")
    assert cls is not None
    # The `metaclass=abc.ABCMeta` kwarg must not appear in bases.
    assert cls.bases == ["abc.ABC"]


def test_generic_base_preserved(python_dir):
    result = PythonAdapter().parse(python_dir / "async_service.py")
    q = _find(result.declarations, kind=KIND_CLASS, name="Queue")
    assert q is not None
    assert q.bases == ["Generic[T]"]


# --- Methods and their kinds ---------------------------------------------


def test_init_becomes_ctor(python_dir):
    result = PythonAdapter().parse(python_dir / "domain_model.py")
    svc = _find(result.declarations, kind=KIND_CLASS, name="UserService")
    init = _find(svc.children, name="__init__")
    assert init is not None
    assert init.kind == KIND_CTOR


def test_property_decorator_promotes_method_to_property(python_dir):
    result = PythonAdapter().parse(python_dir / "domain_model.py")
    # BaseEntity.id has a plain @property → KIND_PROPERTY
    base = _find(result.declarations, kind=KIND_CLASS, name="BaseEntity")
    id_prop = _find(base.children, name="id")
    assert id_prop is not None
    assert id_prop.kind == KIND_PROPERTY


def test_property_setter_stays_method(python_dir):
    """@display_name.setter is NOT the plain @property decorator → should
    remain KIND_METHOD so digests don't double-count."""
    result = PythonAdapter().parse(python_dir / "domain_model.py")
    user = _find(result.declarations, kind=KIND_CLASS, name="User")
    setters = [c for c in user.children if c.name == "display_name"]
    # One property (getter) + one method (setter) — two declarations with the same name.
    assert len(setters) == 2
    kinds = {s.kind for s in setters}
    assert KIND_PROPERTY in kinds
    assert KIND_METHOD in kinds


def test_static_and_classmethod_stay_method(python_dir):
    result = PythonAdapter().parse(python_dir / "async_service.py")
    handler = _find(result.declarations, kind=KIND_CLASS, name="Handler")
    default = _find(handler.children, name="default")
    describe = _find(handler.children, name="describe")
    assert default is not None and default.kind == KIND_METHOD
    assert describe is not None and describe.kind == KIND_METHOD
    # But decorators must be captured as attrs
    assert any("@classmethod" in a for a in default.attrs)
    assert any("@staticmethod" in a for a in describe.attrs)


def test_async_method_is_still_method(python_dir):
    result = PythonAdapter().parse(python_dir / "async_service.py")
    handler = _find(result.declarations, kind=KIND_CLASS, name="Handler")
    handle = _find(handler.children, name="handle")
    assert handle is not None
    assert handle.kind == KIND_METHOD
    assert "async def" in handle.signature


def test_async_top_level_function(python_dir):
    result = PythonAdapter().parse(python_dir / "async_service.py")
    fn = _find(result.declarations, kind=KIND_FUNCTION, name="run_forever")
    assert fn is not None
    assert "async def" in fn.signature


# --- Decorators: stacking, byte range, show-friendly ---------------------


def test_stacked_decorators_all_captured(python_dir):
    result = PythonAdapter().parse(python_dir / "decorators_edge.py")
    widget = _find(result.declarations, kind=KIND_CLASS, name="Widget")
    compute = _find(widget.children, name="compute")
    assert compute is not None
    # Two stacked decorators on `compute`
    joined = "\n".join(compute.attrs)
    assert "@tracing" in joined
    assert "@functools.lru_cache" in joined


def test_decorated_function_byte_range_includes_decorators(python_dir):
    """So `ast-outline show` prints the decorator line together with the def."""
    path = python_dir / "decorators_edge.py"
    result = PythonAdapter().parse(path)
    widget = _find(result.declarations, kind=KIND_CLASS, name="Widget")
    compute = _find(widget.children, name="compute")
    src = path.read_bytes()
    slice_text = src[compute.start_byte : compute.end_byte].decode("utf8")
    # Both decorators must be inside the slice
    assert "@tracing" in slice_text
    assert "@functools.lru_cache" in slice_text
    # And the def itself must start after them
    assert "def compute" in slice_text


# --- Visibility ----------------------------------------------------------


def test_dunder_names_not_private(python_dir):
    result = PythonAdapter().parse(python_dir / "async_service.py")
    q = _find(result.declarations, kind=KIND_CLASS, name="Queue")
    dunder_len = _find(q.children, name="__len__")
    assert dunder_len is not None
    # __dunder__ is conventionally public API
    assert dunder_len.visibility == ""


def test_underscore_method_is_private(python_dir):
    result = PythonAdapter().parse(python_dir / "domain_model.py")
    svc = _find(result.declarations, kind=KIND_CLASS, name="UserService")
    log = _find(svc.children, name="_log")
    assert log is not None and log.visibility == "private"


# --- Function signatures --------------------------------------------------


def test_function_signature_includes_return_type(python_dir):
    """Ensure we pick the UserService.get (returns `User | None`), not the
    similarly-named Repository.get (returns `bytes | None`)."""
    result = PythonAdapter().parse(python_dir / "domain_model.py")
    svc = _find(result.declarations, kind=KIND_CLASS, name="UserService")
    get = _find(svc.children, kind=KIND_METHOD, name="get")
    assert get is not None
    assert "-> User | None" in get.signature
    # Trailing colon should be stripped
    assert not get.signature.rstrip().endswith(":")


# --- Dataclass fields ----------------------------------------------------


def test_dataclass_body_fields_captured(python_dir):
    """`id: int` inside `@dataclass class User` → KIND_FIELD child."""
    result = PythonAdapter().parse(python_dir / "domain_model.py")
    user = _find(result.declarations, kind=KIND_CLASS, name="User")
    field_names = {c.name for c in user.children if c.kind == KIND_FIELD}
    assert {"id", "name", "email"}.issubset(field_names)


def test_dataclass_field_signature_includes_type(python_dir):
    """Typed field signature: `id: int`, not just `id`."""
    result = PythonAdapter().parse(python_dir / "domain_model.py")
    user = _find(result.declarations, kind=KIND_CLASS, name="User")
    id_field = next(c for c in user.children if c.kind == KIND_FIELD and c.name == "id")
    assert id_field.signature == "id: int"
    email_field = next(c for c in user.children if c.kind == KIND_FIELD and c.name == "email")
    assert email_field.signature == "email: str"
