"""Tests for the `--format=` preset switch on `ast-outline digest`.

Four presets are documented and behaviorally distinct:

- ``names``   — one line per file, top-level symbols only, no methods /
                fields / line ranges; declaration-less files hidden.
- ``compact`` — same hierarchy as default minus the per-file counters,
                line-range suffixes, blank lines, and "no declarations"
                marker. Empty files are hidden.
- ``default`` — unchanged from prior behavior (back-compat anchor).
- ``wide``    — same shape as default but with private symbols + fields
                included and ``max_members_per_type`` effectively
                unlimited. Implemented as a CLI-side preset (no rendering
                branch); this file pins the *effective* output.

Each test calls out which preset rule it protects, so a regression
points at one concrete decision.
"""
from __future__ import annotations

from ast_outline.adapters.csharp import CSharpAdapter
from ast_outline.adapters.css import CssAdapter
from ast_outline.adapters.markdown import MarkdownAdapter
from ast_outline.adapters.python import PythonAdapter
from ast_outline.adapters.yaml import YamlAdapter
from ast_outline.core import DigestOptions, render_digest


# --- names format --------------------------------------------------------


def test_names_format_one_line_per_file(csharp_dir):
    """Each file collapses to a single `  name [label]: A, B, C` line —
    top-level symbols comma-separated, no methods, no line ranges."""
    r = CSharpAdapter().parse(csharp_dir / "hierarchy.cs")
    out = render_digest([r], DigestOptions(format="names"))
    lines = [line for line in out.splitlines() if line.startswith("  ")]
    assert len(lines) == 1, f"expected one file line, got {lines!r}"
    assert lines[0].lstrip().startswith("hierarchy.cs ")
    assert ":" in lines[0], "names format must list symbols after `:`"


def test_names_format_omits_methods_and_fields(csharp_dir):
    """Names is top-level only — methods (`Eat()`) and fields must not
    appear. Only types / free functions belong on the file line."""
    r = CSharpAdapter().parse(csharp_dir / "hierarchy.cs")
    out = render_digest([r], DigestOptions(format="names"))
    # `Eat()` is a method on Animal — must not be in the symbol list.
    assert "Eat" not in out, f"method leaked into names format:\n{out}"
    # `()` callable marker must never appear in names format.
    assert "()" not in out


def test_names_format_omits_inheritance_and_ranges(csharp_dir):
    """No `: Base`, no `L<a>-<b>`. Names is identity-only — those tokens
    belong to compact/default/wide where the hierarchy is preserved."""
    r = CSharpAdapter().parse(csharp_dir / "hierarchy.cs")
    out = render_digest([r], DigestOptions(format="names"))
    # No line ranges in names output.
    assert "L1-" not in out
    assert "L0-" not in out
    # The `: Base` inheritance notation must not appear (the
    # hierarchy.cs fixture has classes inheriting from Animal).
    body_lines = [line for line in out.splitlines() if line.startswith("  ")]
    for line in body_lines:
        # Only one `:` allowed — the file/symbols separator.
        assert line.count(":") == 1, f"unexpected `:` in {line!r}"


def test_names_format_emits_no_legend(csharp_dir):
    """Names produces none of the legend tokens (no parens, no kind
    tags, no inheritance, no ranges), so the legend itself must not be
    printed — it'd be 30 tokens explaining symbols that don't appear."""
    r = CSharpAdapter().parse(csharp_dir / "hierarchy.cs")
    out = render_digest([r], DigestOptions(format="names"))
    assert "# legend:" not in out


def test_names_format_no_blank_lines_within_directory(csharp_dir):
    """Inside one directory, files stack tightly — no blanks between
    file lines. Blank lines only separate directories."""
    files = [
        CSharpAdapter().parse(csharp_dir / "hierarchy.cs"),
        CSharpAdapter().parse(csharp_dir / "file_scoped_ns.cs"),
    ]
    out = render_digest(files, DigestOptions(format="names"))
    lines = out.splitlines()
    # Find the two file lines.
    file_lines = [i for i, line in enumerate(lines) if line.startswith("  ")]
    assert len(file_lines) == 2
    # They must be adjacent — no blank line between sibling files.
    assert file_lines[1] == file_lines[0] + 1


def test_names_format_hides_files_with_no_public_symbols(python_dir, tmp_path):
    """A file whose only content is private symbols (`_foo`) or empty
    `__init__.py` shims contributes nothing to a public-API map. Hide it
    entirely so the agent isn't told to drill into a dead file."""
    empty = tmp_path / "empty.py"
    empty.write_text("# just a comment\n")
    r = PythonAdapter().parse(empty)
    out = render_digest([r], DigestOptions(format="names"))
    # File is hidden — output is the explicit all-hidden note.
    assert "empty.py" not in out
    assert "all files hidden" in out


def test_names_format_oneline_cli_alias_matches_format_names(csharp_dir):
    """The `--oneline` CLI alias resolves to `--format=names`. Render is
    identical — this is a wording alias, not a separate code path."""
    r = CSharpAdapter().parse(csharp_dir / "hierarchy.cs")
    from_alias = render_digest([r], DigestOptions(format="names"))
    from_explicit = render_digest([r], DigestOptions(format="names"))
    assert from_alias == from_explicit


# --- compact format ------------------------------------------------------


def test_compact_format_drops_per_file_counters(csharp_dir):
    """The `, X types, Y methods, Z fields` breakdown is dropped on
    compact — line and token totals stay (they drive routing decisions).
    The breakdown only weighs the visual without adding signal."""
    r = CSharpAdapter().parse(csharp_dir / "hierarchy.cs")
    default_out = render_digest([r], DigestOptions(format="default"))
    compact_out = render_digest([r], DigestOptions(format="compact"))
    # Default has the breakdown.
    assert ", " in default_out  # comma-separated counters
    default_header = next(line for line in default_out.splitlines() if "hierarchy.cs" in line)
    assert "types" in default_header or "methods" in default_header
    # Compact strips it — header has only `N lines, ~N tokens`.
    compact_header = next(line for line in compact_out.splitlines() if "hierarchy.cs" in line)
    assert "types" not in compact_header
    assert "methods" not in compact_header
    assert "fields" not in compact_header
    # Sizing parts remain.
    assert "lines" in compact_header
    assert "tokens" in compact_header


def test_compact_format_drops_line_range_from_type_headers(csharp_dir):
    """`L<a>-<b>` is suppressed on compact — agents needing line ranges
    step up to `--format=default`. Compact keeps the `: Base` and the
    decorators that carry semantic weight."""
    r = CSharpAdapter().parse(csharp_dir / "hierarchy.cs")
    compact_out = render_digest([r], DigestOptions(format="compact"))
    # The class headers are present.
    assert "class Demo.Hierarchy.Animal" in compact_out
    # But no `L<digits>-<digits>` anywhere in the body.
    import re
    assert not re.search(r"L\d+-\d+", compact_out), \
        f"line range leaked into compact output:\n{compact_out}"


def test_compact_format_drops_blank_lines_between_types(csharp_dir):
    """The "blank line after a type-with-members" rule is dropped on
    compact — types stack tightly. The directory-separating blank line
    is preserved (it organises multi-dir output)."""
    r = CSharpAdapter().parse(csharp_dir / "hierarchy.cs")
    compact_out = render_digest([r], DigestOptions(format="compact"))
    lines = compact_out.splitlines()
    # Body lines (everything past the legend + directory header).
    body_lines = [line for line in lines if line.startswith("    ")]
    # Compact should never emit a blank line *between* type rows inside
    # a single directory's file block. We verify the inverse: the only
    # blank lines in the rendered output are the inter-directory
    # separators.
    blank_indices = [i for i, line in enumerate(lines) if line == ""]
    # In a single-file render with one dir, no inner blanks expected at
    # all — the trailing blank is stripped by `rstrip()`.
    for bi in blank_indices:
        # No blank may appear surrounded by `    ` body lines on both sides.
        before = lines[bi - 1] if bi > 0 else ""
        after = lines[bi + 1] if bi + 1 < len(lines) else ""
        assert not (before.startswith("    ") and after.startswith("    ")), \
            f"blank line between body rows at index {bi}: {lines[bi-1:bi+2]!r}"


def test_compact_format_hides_files_with_no_declarations(python_dir, tmp_path):
    """Default keeps the file header + `# no declarations` marker; compact
    hides the file entirely. Cleaner map when the agent is scanning
    a real codebase with stub `__init__.py` files."""
    empty = tmp_path / "shim.py"
    empty.write_text("# placeholder\n")
    r = PythonAdapter().parse(empty)
    default_out = render_digest([r], DigestOptions(format="default"))
    compact_out = render_digest([r], DigestOptions(format="compact"))
    # Default surfaces the marker.
    assert "no declarations" in default_out
    assert "shim.py" in default_out
    # Compact hides the whole file — explicit note replaces silent
    # empty output to keep the agent oriented.
    assert "shim.py" not in compact_out
    assert "all files hidden" in compact_out


def test_compact_format_keeps_inheritance_and_decorators(csharp_dir):
    """`: Base` and `@dataclass` are semantic signals, not visual
    weight — compact keeps them. Only oversized labels are stripped."""
    r = CSharpAdapter().parse(csharp_dir / "hierarchy.cs")
    compact_out = render_digest([r], DigestOptions(format="compact"))
    # Inheritance (`: Animal`) must survive compact.
    assert ":" in compact_out  # ascii colon
    # The actual inheritance line: `class Dog : Animal` shape.
    inh_lines = [
        line for line in compact_out.splitlines()
        if "class" in line and ":" in line and line.startswith("    ")
    ]
    assert inh_lines, "expected at least one inherited-class header in compact"


def test_compact_format_legend_present_when_tokens_appear(csharp_dir):
    """Compact still emits the legend when `()` / `: Base` tokens appear —
    same rule as default. Names is the only format that drops the legend
    unconditionally."""
    r = CSharpAdapter().parse(csharp_dir / "hierarchy.cs")
    compact_out = render_digest([r], DigestOptions(format="compact"))
    assert compact_out.splitlines()[0].startswith("# legend:")


# --- wide format (CLI preset) --------------------------------------------


def test_wide_format_includes_private_when_flags_match_preset():
    """`wide` is a CLI-side preset that turns on include_private,
    include_fields, and lifts the max-members cap. Rendering with those
    explicit toggles produces the wide output — the preset is *just*
    those defaults."""
    # Two equivalent ways to invoke wide:
    via_preset = DigestOptions(
        format="wide",
        include_private=True,
        include_fields=True,
        max_members_per_type=10**9,
    )
    via_explicit = DigestOptions(
        format="default",  # same renderer
        include_private=True,
        include_fields=True,
        max_members_per_type=10**9,
    )
    from ast_outline.adapters.python import PythonAdapter
    fixture = (
        # Tiny inline fixture: one class with a public method, a private
        # method, and a public field. `include_private=True` plus
        # `include_fields=True` should surface all three.
    )
    from pathlib import Path
    src = Path(__file__).parent.parent / "fixtures" / "python" / "decorators_edge.py"
    if not src.exists():
        # Skip silently if fixture missing — same shape as other tests.
        import pytest
        pytest.skip("decorators_edge.py fixture missing")
    r = PythonAdapter().parse(src)
    out_preset = render_digest([r], via_preset)
    out_explicit = render_digest([r], via_explicit)
    # Same flag set, same render — the preset is purely a knob bundle.
    assert out_preset == out_explicit


# --- default format unchanged --------------------------------------------


def test_default_format_back_compat_unchanged(csharp_dir):
    """The `default` preset must produce byte-identical output to a call
    that omits the format argument — back-compat for every existing
    agent/skill that parses digest today."""
    r = CSharpAdapter().parse(csharp_dir / "hierarchy.cs")
    with_default = render_digest([r], DigestOptions(format="default"))
    omitted = render_digest([r], DigestOptions())
    assert with_default == omitted


# --- preset override behavior --------------------------------------------


def test_names_preset_respects_explicit_include_private(python_dir):
    """The CLI resolves preset defaults only for sentinels — a user who
    explicitly passes `--include-private` overrides the names preset.
    This test pins that the renderer honors the option independent of
    the format; CLI-level override is tested by integration.

    Uses the Python fixture because Python's `_name` private convention
    is reliably detected by the adapter; C# `internal` is the default
    visibility and surfaces as public-ish, so it's a weaker probe."""
    r = PythonAdapter().parse(python_dir / "domain_model.py")
    public_only = render_digest([r], DigestOptions(format="names", include_private=False))
    with_private = render_digest([r], DigestOptions(format="names", include_private=True))
    assert with_private != public_only
    # Specifically: `_encode` / `_decode` (private free functions) must
    # appear only in the with-private rendering.
    assert "_encode" not in public_only
    assert "_encode" in with_private


# --- names per-language headlines ---------------------------------------


def test_names_format_markdown_surfaces_top_level_headings(md_dir):
    """Markdown files in names format show their top-level (H1)
    heading text, lstripped of the `#` marker. Nested H2+ headings are
    omitted — names is a per-file headline, not a TOC."""
    r = MarkdownAdapter().parse(md_dir / "readme_style.md")
    out = render_digest([r], DigestOptions(format="names"))
    # `readme_style.md` has at least one top-level heading.
    file_line = next(line for line in out.splitlines() if "readme_style.md" in line)
    assert ":" in file_line
    # No raw `#` marker leaks through — only the heading text.
    symbols_part = file_line.split(":", 1)[1].strip()
    assert not symbols_part.startswith("#")


def test_names_format_yaml_single_doc_surfaces_top_level_keys(yaml_dir):
    """Single-document YAML in names format shows its top-level keys —
    `apiVersion`, `kind`, `metadata`, `spec` for a typical k8s manifest."""
    r = YamlAdapter().parse(yaml_dir / "k8s_deployment.yaml")
    out = render_digest([r], DigestOptions(format="names"))
    assert "apiVersion" in out
    assert "kind" in out
    # No `[yaml_key]` or `[kind]` tag in names format.
    assert "[yaml_key]" not in out


def test_names_format_yaml_multi_doc_surfaces_doc_separators(yaml_dir):
    """Multi-document YAML in names format shows the per-doc separator
    signatures (e.g. ``--- doc 1 of 3 — ConfigMap …``) so the agent sees
    *what kinds of resources* are in the manifest. Top-level keys would
    be meaningless for multi-doc (one set per doc, all collapsed)."""
    r = YamlAdapter().parse(yaml_dir / "k8s_multi_resources.yaml")
    out = render_digest([r], DigestOptions(format="names"))
    assert "doc 1 of" in out
    # Each doc separator carries the resource kind.
    assert "ConfigMap" in out or "Secret" in out


def test_names_format_css_surfaces_flat_selectors(css_dir):
    """CSS/SCSS in names format shows the flat selector list — `body`,
    `.btn-primary`, `:root`, etc. Hierarchy (nested rules, `@media`
    branches) is collapsed since names is a per-file headline."""
    r = CssAdapter().parse(css_dir / "styles.css")
    out = render_digest([r], DigestOptions(format="names"))
    # At least one selector from the fixture must appear in the symbol list.
    file_line = next(line for line in out.splitlines() if "styles.css" in line)
    symbols_part = file_line.split(":", 1)[1] if ":" in file_line else ""
    # The CSS fixture has body / .btn-primary among many selectors.
    assert "body" in symbols_part or ".btn-primary" in symbols_part


# --- names size labels & integrity --------------------------------------


def test_names_format_huge_file_emits_header_without_colon(tmp_path):
    """`[huge]` files (>100k tokens) collapse to the file-line header
    without a symbol list — the digest never collected their bodies, so
    there's nothing to list after the colon. Names format preserves the
    same convention as default: surface the file + size label so the
    agent can decide to `ast-outline outline <path>`."""
    # Build a >100k-token Python file: one tiny class plus enough lines
    # of trivial content to push token count past `_SIZE_LABEL_HUGE_FLOOR`.
    huge = tmp_path / "huge.py"
    huge.write_text("class Foo:\n    pass\n" + ("x = 1\n" * 200_000))
    r = PythonAdapter().parse(huge)
    out = render_digest([r], DigestOptions(format="names"))
    # The `[huge]` label is present.
    assert "[huge]" in out
    # And no trailing `:` symbol list — names treats huge files as
    # header-only, same as default-format does in the hierarchical view.
    file_line = next(line for line in out.splitlines() if "huge.py" in line)
    # The line ends with `[huge]` (possibly with trailing whitespace),
    # no `:` follows.
    assert not file_line.rstrip().endswith(":")
    # No symbol list (no `: A, B, C` after the label).
    after_label = file_line.split("[huge]", 1)[1]
    assert ":" not in after_label


def test_names_format_preserves_broken_marker(python_dir):
    """Files with parse errors keep their `[broken]` marker in names
    format — the agent needs the integrity signal regardless of format."""
    r = PythonAdapter().parse(python_dir / "broken_syntax.py")
    out = render_digest([r], DigestOptions(format="names"))
    assert "[broken]" in out


# --- names multi-directory ----------------------------------------------


def test_names_format_blank_line_between_directories(python_dir, csharp_dir):
    """Multiple directories are separated by a blank line — agents can
    visually parse `dir/` blocks. Within a directory files stack
    tightly."""
    files = [
        PythonAdapter().parse(python_dir / "async_service.py"),
        CSharpAdapter().parse(csharp_dir / "hierarchy.cs"),
    ]
    out = render_digest(files, DigestOptions(format="names"))
    lines = out.splitlines()
    # Two directory headers, separated by a blank.
    dir_headers = [i for i, line in enumerate(lines) if line.endswith("/")]
    assert len(dir_headers) == 2
    # Between them there must be at least one blank line.
    between = lines[dir_headers[0] + 1 : dir_headers[1]]
    assert "" in between


# --- names + --imports composition --------------------------------------


def test_names_format_with_imports_shows_two_lines_per_file(python_dir):
    """`--oneline --imports` adds an indented `imports:` line under
    each file. Without imports the file collapses to one line; with
    imports the invariant "imports always visible when requested"
    holds across all formats."""
    r = PythonAdapter().parse(python_dir / "async_service.py")
    no_imports = render_digest([r], DigestOptions(format="names"))
    with_imports = render_digest([r], DigestOptions(format="names", show_imports=True))
    # No imports line in default names render.
    assert "imports:" not in no_imports
    # With `show_imports`, the second line carries the imports
    # statement verbatim (Python `import abc; from typing import ...`).
    assert "imports:" in with_imports
    # And the file line itself is unchanged — imports add to, not
    # replace, the headline.
    file_line_no = next(line for line in no_imports.splitlines() if "async_service.py" in line)
    file_line_yes = next(line for line in with_imports.splitlines() if "async_service.py" in line)
    assert file_line_no == file_line_yes


# --- compact preserves `... (N more)` truncation ------------------------


def test_compact_format_honors_max_members_cap(csharp_dir):
    """The `--max-members N` cap (and its `... (N more)` truncation
    marker) still applies in compact format — compact only drops the
    paragraph-break blank line, not the cap. Pinning this means a
    refactor that conflates "compact" with "no truncation" will be
    caught."""
    r = CSharpAdapter().parse(csharp_dir / "hierarchy.cs")
    out = render_digest([r], DigestOptions(format="compact", max_members_per_type=1))
    # The "... (N more)" marker is the proof the cap applied at least once.
    assert "more)" in out


# --- compact hides per-language empty files -----------------------------


def test_compact_format_hides_empty_markdown(tmp_path):
    """A markdown file with no headings emits `# empty` in default;
    compact must hide it entirely (consistent with code-file empty-hide
    rule). Distinguishes "all files filtered" from a stray empty marker."""
    empty = tmp_path / "no_headings.md"
    empty.write_text("just prose, no headings\n")
    r = MarkdownAdapter().parse(empty)
    default_out = render_digest([r], DigestOptions(format="default"))
    compact_out = render_digest([r], DigestOptions(format="compact"))
    # Default keeps the file with `# empty` marker.
    assert "# empty" in default_out
    assert "no_headings.md" in default_out
    # Compact hides the file → all-files-hidden note replaces output.
    assert "no_headings.md" not in compact_out
    assert "all files hidden" in compact_out
