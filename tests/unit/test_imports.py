"""Per-language tests for `ParseResult.imports`.

Covers all 9 code adapters (csharp/python/typescript/java/kotlin/scala/
go/rust/php). Markdown and YAML adapters have no imports concept so are
not exercised here.

Each test writes a minimal source file to a tmp_path, runs the adapter,
and asserts the normalized source-true import strings match exactly.
The output format is intentionally `language-native` — Python emits
`from .core import X`, Rust emits `use foo::Bar`, Go emits
`import "fmt"`. No synthetic format that an LLM would have to learn.
"""
from __future__ import annotations

from pathlib import Path

from ast_outline.adapters.csharp import CSharpAdapter
from ast_outline.adapters.go import GoAdapter
from ast_outline.adapters.java import JavaAdapter
from ast_outline.adapters.kotlin import KotlinAdapter
from ast_outline.adapters.php import PhpAdapter
from ast_outline.adapters.python import PythonAdapter
from ast_outline.adapters.rust import RustAdapter
from ast_outline.adapters.scala import ScalaAdapter
from ast_outline.adapters.typescript import TypeScriptAdapter


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content)
    return p


# --- Python ---------------------------------------------------------------


def test_python_basic_imports(tmp_path: Path) -> None:
    p = _write(tmp_path, "m.py", (
        "import foo\n"
        "import bar as b\n"
        "from .core import X, Y\n"
        "from typing import Optional as Opt, List\n"
        "from .. import sibling\n"
        "from collections import *\n"
    ))
    r = PythonAdapter().parse(p)
    assert r.imports == [
        "import foo",
        "import bar as b",
        "from .core import X, Y",
        "from typing import Optional as Opt, List",
        "from .. import sibling",
        "from collections import *",
    ]


def test_python_splits_comma_joined_imports(tmp_path: Path) -> None:
    """`import a, b, c as d` becomes three separate `import ...` lines so
    every entry in `imports` is a single-statement string. Joining
    multiple modules under one `import` keyword would force the agent to
    parse comma-lists within entries, which is exactly what we wanted to
    avoid by collapsing to source-true syntax in the first place."""
    p = _write(tmp_path, "m.py", "import a, b, c as d\n")
    r = PythonAdapter().parse(p)
    assert r.imports == ["import a", "import b", "import c as d"]


def test_python_includes_type_checking_block(tmp_path: Path) -> None:
    p = _write(tmp_path, "m.py", (
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    from foo.bar import HeavyType\n"
    ))
    r = PythonAdapter().parse(p)
    assert "from foo.bar import HeavyType" in r.imports


def test_python_includes_try_except_import_fallback(tmp_path: Path) -> None:
    """Common compat pattern: try a fast/optional dep, fall back to
    stdlib. Both branches are real top-level dependencies of this file
    — agents need to see both to understand what's pulled at runtime.

    This pattern is the documented reason `_PY_IMPORT_DESCEND` lists
    `try_statement` and `except_clause`; the test pins that contract
    so a future refactor can't quietly drop it."""
    p = _write(tmp_path, "m.py", (
        "try:\n"
        "    import ujson as json\n"
        "except ImportError:\n"
        "    import json\n"
    ))
    r = PythonAdapter().parse(p)
    assert "import ujson as json" in r.imports
    assert "import json" in r.imports


def test_python_excludes_imports_inside_class_or_function(tmp_path: Path) -> None:
    p = _write(tmp_path, "m.py", (
        "import top_level\n"
        "class Outer:\n"
        "    import inner_only\n"
        "def func():\n"
        "    import another_local\n"
    ))
    r = PythonAdapter().parse(p)
    assert r.imports == ["import top_level"]


def test_python_collapses_multiline_paren_imports(tmp_path: Path) -> None:
    p = _write(tmp_path, "m.py", (
        "from foo import (\n"
        "    A,\n"
        "    B,\n"
        "    C,\n"
        ")\n"
    ))
    r = PythonAdapter().parse(p)
    assert r.imports == ["from foo import A, B, C"]


# --- TypeScript -----------------------------------------------------------


def test_typescript_all_import_shapes(tmp_path: Path) -> None:
    p = _write(tmp_path, "m.ts", (
        'import foo from "foo";\n'
        'import { X, Y } from "./core";\n'
        'import { X as A, Y as B } from "baz";\n'
        'import * as ns from "./util";\n'
        'import "./side-effect";\n'
        'import type { TypeOnly } from "./types";\n'
        'import defaultExport, { named1, named2 } from "./mixed";\n'
    ))
    r = TypeScriptAdapter().parse(p)
    assert r.imports == [
        'import foo from "foo"',
        'import { X, Y } from "./core"',
        'import { X as A, Y as B } from "baz"',
        'import * as ns from "./util"',
        'import "./side-effect"',
        'import type { TypeOnly } from "./types"',
        'import defaultExport, { named1, named2 } from "./mixed"',
    ]


def test_typescript_collapses_multiline(tmp_path: Path) -> None:
    p = _write(tmp_path, "m.ts", (
        "import {\n"
        "  Multi,\n"
        "  Line\n"
        '} from "./long";\n'
    ))
    r = TypeScriptAdapter().parse(p)
    assert r.imports == ['import { Multi, Line } from "./long"']


# --- Java -----------------------------------------------------------------


def test_java_all_import_shapes(tmp_path: Path) -> None:
    p = _write(tmp_path, "M.java", (
        "package com.example;\n"
        "import java.util.List;\n"
        "import java.util.*;\n"
        "import static java.util.Collections.emptyList;\n"
        "import static java.util.stream.Collectors.*;\n"
        "public class M {}\n"
    ))
    r = JavaAdapter().parse(p)
    assert r.imports == [
        "import java.util.List",
        "import java.util.*",
        "import static java.util.Collections.emptyList",
        "import static java.util.stream.Collectors.*",
    ]


# --- Kotlin ---------------------------------------------------------------


def test_kotlin_all_import_shapes(tmp_path: Path) -> None:
    p = _write(tmp_path, "M.kt", (
        "package com.example\n"
        "import foo.Bar\n"
        "import foo.*\n"
        "import foo.Bar as Baz\n"
        "class M\n"
    ))
    r = KotlinAdapter().parse(p)
    assert r.imports == [
        "import foo.Bar",
        "import foo.*",
        "import foo.Bar as Baz",
    ]


# --- Scala ----------------------------------------------------------------


def test_scala_all_import_shapes(tmp_path: Path) -> None:
    p = _write(tmp_path, "M.scala", (
        "package com.example\n"
        "import foo.bar.Baz\n"
        "import foo.bar.{Baz, Qux}\n"
        "import foo.bar.{Baz => Renamed}\n"
        "import foo.bar.*\n"
        "import foo.bar._\n"
        "object M\n"
    ))
    r = ScalaAdapter().parse(p)
    assert r.imports == [
        "import foo.bar.Baz",
        "import foo.bar.{Baz, Qux}",
        "import foo.bar.{Baz => Renamed}",
        "import foo.bar.*",
        "import foo.bar._",
    ]


# --- Go -------------------------------------------------------------------


def test_go_flattens_grouped_imports(tmp_path: Path) -> None:
    """Go's `import (...)` block is purely cosmetic grouping. We flatten
    it so each spec becomes its own `import "..."` line — agents see one
    syntactic shape regardless of source style."""
    p = _write(tmp_path, "m.go", (
        'package main\n'
        'import "fmt"\n'
        'import f "fmt"\n'
        'import _ "side/effect"\n'
        'import (\n'
        '    "os"\n'
        '    "strings"\n'
        '    custom "github.com/foo/bar"\n'
        '    _ "side/two"\n'
        ')\n'
        'func main() {}\n'
    ))
    r = GoAdapter().parse(p)
    assert r.imports == [
        'import "fmt"',
        'import f "fmt"',
        'import _ "side/effect"',
        'import "os"',
        'import "strings"',
        'import custom "github.com/foo/bar"',
        'import _ "side/two"',
    ]


# --- Rust -----------------------------------------------------------------


def test_rust_all_use_shapes(tmp_path: Path) -> None:
    p = _write(tmp_path, "m.rs", (
        "use std::collections::HashMap;\n"
        "use foo::Bar;\n"
        "use foo::{Bar, Baz};\n"
        "use foo::Bar as Qux;\n"
        "use foo::*;\n"
        "pub use crate::utils::Foo;\n"
        "extern crate serde;\n"
        "mod local;\n"
        "fn main() {}\n"
    ))
    r = RustAdapter().parse(p)
    assert r.imports == [
        "use std::collections::HashMap",
        "use foo::Bar",
        "use foo::{Bar, Baz}",
        "use foo::Bar as Qux",
        "use foo::*",
        "pub use crate::utils::Foo",
        "extern crate serde",
    ]


def test_rust_excludes_mod_declarations(tmp_path: Path) -> None:
    """`mod foo;` is a submodule declaration, not an import. Including
    it would mix two distinct concepts (consumption vs structural file
    layout) under the same `--imports` flag."""
    p = _write(tmp_path, "m.rs", (
        "use foo::Bar;\n"
        "mod sibling;\n"
        "mod inline { pub fn x() {} }\n"
    ))
    r = RustAdapter().parse(p)
    assert r.imports == ["use foo::Bar"]


# --- PHP ------------------------------------------------------------------


def test_php_basic_imports(tmp_path: Path) -> None:
    p = _write(tmp_path, "m.php", (
        "<?php\n"
        "namespace App;\n"
        "use App\\Foo;\n"
        "use App\\Bar as B;\n"
        "use function strlen;\n"
        "use const PHP_INT_MAX;\n"
        "class M {}\n"
    ))
    r = PhpAdapter().parse(p)
    assert r.imports == [
        "use App\\Foo",
        "use App\\Bar as B",
        "use function strlen",
        "use const PHP_INT_MAX",
    ]


def test_php_grouped_imports_expanded(tmp_path: Path) -> None:
    """`use Foo\\{A, B as Bb};` → one entry per leaf, each a complete
    source-true `use ...` statement. The prefix is reattached so each
    entry stands alone — no implicit "all share `Foo\\`" knowledge
    required of the reader."""
    p = _write(tmp_path, "m.php", (
        "<?php\n"
        "use App\\{Foo, Bar as Bb};\n"
        "use function App\\Helpers\\{render, escape as e};\n"
        "use const App\\Config\\{LIMIT, MAX};\n"
        "class M {}\n"
    ))
    r = PhpAdapter().parse(p)
    assert r.imports == [
        "use App\\Foo",
        "use App\\Bar as Bb",
        "use function App\\Helpers\\render",
        "use function App\\Helpers\\escape as e",
        "use const App\\Config\\LIMIT",
        "use const App\\Config\\MAX",
    ]


def test_php_imports_inside_bracketed_namespace(tmp_path: Path) -> None:
    """`namespace Foo { use Bar; }` — `use` inside the namespace block
    must still surface in `imports`, since adapters report the file's
    full dependency surface regardless of which namespace block declared
    each `use`."""
    p = _write(tmp_path, "m.php", (
        "<?php\n"
        "namespace App\\First {\n"
        "    use App\\Foo;\n"
        "    class A {}\n"
        "}\n"
        "namespace App\\Second {\n"
        "    use App\\Bar;\n"
        "    class B {}\n"
        "}\n"
    ))
    r = PhpAdapter().parse(p)
    assert "use App\\Foo" in r.imports
    assert "use App\\Bar" in r.imports


# --- C# -------------------------------------------------------------------


def test_csharp_all_using_shapes(tmp_path: Path) -> None:
    p = _write(tmp_path, "M.cs", (
        "using System;\n"
        "using System.Collections.Generic;\n"
        "using static System.Math;\n"
        "using Foo = System.Bar;\n"
        "global using System.Linq;\n"
        "namespace Demo {\n"
        "  using Inside;\n"
        "  public class C {}\n"
        "}\n"
    ))
    r = CSharpAdapter().parse(p)
    assert r.imports == [
        "using System",
        "using System.Collections.Generic",
        "using static System.Math",
        "using Foo = System.Bar",
        "global using System.Linq",
    ]


# --- Empty / no-imports cases --------------------------------------------


def test_empty_imports_for_file_with_none(tmp_path: Path) -> None:
    """Per-adapter sanity: a code file with no imports yields an empty
    list. Each adapter must wire the `imports=imports` keyword into its
    `ParseResult(...)` call — silently omitting it would still default
    to `[]` via the dataclass `field(default_factory=list)`, so this
    test alone does NOT prove `_collect_imports` runs. See
    `test_each_adapter_wires_collect_imports_into_parse_result` below
    for the live-collection check."""
    cases = [
        (PythonAdapter(), "m.py", "x = 1\n"),
        (TypeScriptAdapter(), "m.ts", "const x = 1;\n"),
        (JavaAdapter(), "M.java", "package x; public class M {}\n"),
        (KotlinAdapter(), "M.kt", "package x\nclass M\n"),
        (ScalaAdapter(), "M.scala", "package x\nobject M\n"),
        (GoAdapter(), "m.go", "package main\nfunc main(){}\n"),
        (RustAdapter(), "m.rs", "fn main() {}\n"),
        (CSharpAdapter(), "M.cs", "namespace X { class M {} }\n"),
        (PhpAdapter(), "m.php", "<?php\nnamespace X;\nclass M {}\n"),
    ]
    for adapter, name, content in cases:
        p = _write(tmp_path, name, content)
        r = adapter.parse(p)
        assert r.imports == [], f"{adapter.language_name} expected empty imports"
        # Default for the conditional-imports counter is 0; only PHP
        # currently populates it. A non-zero value here would mean the
        # adapter spuriously flagged a conditional dependency on a file
        # that has none.
        assert r.conditional_imports_count == 0, (
            f"{adapter.language_name} expected conditional_imports_count=0"
        )


def test_each_adapter_wires_collect_imports_into_parse_result(tmp_path: Path) -> None:
    """Live-collection regression: every adapter must populate
    `ParseResult.imports` from real source. If an adapter drops the
    `imports=imports` keyword from its `ParseResult(...)` call, the
    field defaults to `[]` and the empty-imports test above passes
    misleadingly — this test fails because we expect a non-empty list
    and would catch the regression."""
    cases = [
        (PythonAdapter(), "m.py", "import os\n", "import os"),
        (TypeScriptAdapter(), "m.ts", 'import x from "y";\n', 'import x from "y"'),
        (JavaAdapter(), "M.java", "import java.util.List;\nclass M {}\n", "import java.util.List"),
        (KotlinAdapter(), "M.kt", "import foo.Bar\nclass M\n", "import foo.Bar"),
        (ScalaAdapter(), "M.scala", "import foo.Bar\nobject M\n", "import foo.Bar"),
        (GoAdapter(), "m.go", 'package main\nimport "fmt"\nfunc main(){}\n', 'import "fmt"'),
        (RustAdapter(), "m.rs", "use foo::Bar;\nfn main() {}\n", "use foo::Bar"),
        (CSharpAdapter(), "M.cs", "using System;\nnamespace X { class M {} }\n", "using System"),
        (PhpAdapter(), "m.php", "<?php\nuse App\\Foo;\nclass M {}\n", "use App\\Foo"),
    ]
    for adapter, name, content, expected_first in cases:
        p = _write(tmp_path, name, content)
        r = adapter.parse(p)
        assert r.imports, f"{adapter.language_name} returned empty imports for non-empty source"
        assert r.imports[0] == expected_first, (
            f"{adapter.language_name}: expected first import {expected_first!r}, got {r.imports[0]!r}"
        )


# --- Renderer integration ------------------------------------------------


def test_outline_with_show_imports_emits_imports_line(tmp_path: Path) -> None:
    """The `# imports: ...` annotation appears under the file header
    only when `OutlineOptions.show_imports` is True. Off by default."""
    from ast_outline.core import OutlineOptions, render_outline

    p = _write(tmp_path, "m.py", "import foo\nfrom .core import X\n")
    r = PythonAdapter().parse(p)
    out_default = render_outline(r, OutlineOptions())
    assert "imports:" not in out_default

    out_with = render_outline(r, OutlineOptions(show_imports=True))
    assert "# imports: import foo; from .core import X" in out_with


def test_digest_with_show_imports_emits_imports_line(tmp_path: Path) -> None:
    from ast_outline.core import DigestOptions, render_digest

    p = _write(tmp_path, "m.py", "import foo\nfrom .core import X\n")
    r = PythonAdapter().parse(p)
    out_default = render_digest([r], DigestOptions())
    assert "imports:" not in out_default

    out_with = render_digest([r], DigestOptions(show_imports=True))
    assert "imports: import foo; from .core import X" in out_with
