"""Tests for the Markdown adapter."""
from __future__ import annotations

import pytest

from ast_outline.adapters.markdown import MarkdownAdapter
from ast_outline.core import (
    KIND_CODE_BLOCK,
    KIND_HEADING,
    Declaration,
    DigestOptions,
    OutlineOptions,
    render_digest,
    render_outline,
)
from ast_outline.grep import grep


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


# --- Parse smoke ---------------------------------------------------------


def test_parse_populates_metadata(md_dir):
    path = md_dir / "readme_style.md"
    r = MarkdownAdapter().parse(path)
    assert r.path == path
    assert r.language == "markdown"
    assert r.line_count > 0
    assert r.declarations


def test_empty_prose_has_no_decls(md_dir):
    r = MarkdownAdapter().parse(md_dir / "empty.md")
    assert r.declarations == []


# --- Heading hierarchy ---------------------------------------------------


def test_h1_wraps_subsections(md_dir):
    r = MarkdownAdapter().parse(md_dir / "readme_style.md")
    # Single H1 at the top
    assert len(r.declarations) == 1
    h1 = r.declarations[0]
    assert h1.kind == KIND_HEADING
    assert h1.name == "Sample Project"
    assert h1.signature == "# Sample Project"
    # H2s live as children of the H1
    h2_names = {c.name for c in h1.children if c.kind == KIND_HEADING}
    assert {"Installation", "Usage", "Contributing", "License"}.issubset(h2_names)


def test_h2_wraps_h3(md_dir):
    r = MarkdownAdapter().parse(md_dir / "readme_style.md")
    install = _find(r.declarations, kind=KIND_HEADING, name="Installation")
    h3_names = {c.name for c in install.children if c.kind == KIND_HEADING}
    assert {"From source", "Via pipx"}.issubset(h3_names)


def test_deeper_nesting_preserved(md_dir):
    r = MarkdownAdapter().parse(md_dir / "article.md")
    arg = _find(r.declarations, kind=KIND_HEADING, name="The Argument")
    second = _find(arg.children, kind=KIND_HEADING, name="Second Point")
    # H4 nested under H3 nested under H2
    h4 = _find(second.children, kind=KIND_HEADING)
    assert h4 is not None
    assert h4.signature.startswith("#### ")
    assert h4.name == "A nested detail under the second point"


def test_signature_reflects_heading_level(md_dir):
    r = MarkdownAdapter().parse(md_dir / "readme_style.md")
    h1 = r.declarations[0]
    install = _find(h1.children, name="Installation")
    from_src = _find(install.children, name="From source")
    assert h1.signature.startswith("# ")
    assert install.signature.startswith("## ")
    assert from_src.signature.startswith("### ")


def test_line_ranges_span_the_whole_section(md_dir):
    """A section's end_line should be at or before the next same-level heading."""
    path = md_dir / "readme_style.md"
    r = MarkdownAdapter().parse(path)
    h1 = r.declarations[0]
    install = _find(h1.children, name="Installation")
    usage = _find(h1.children, name="Usage")
    # Installation ends before Usage begins
    assert install.end_line <= usage.start_line
    # Installation actually covers several lines
    assert install.end_line > install.start_line


# --- Setext headings -----------------------------------------------------


def test_setext_h1_and_h2_detected(md_dir):
    r = MarkdownAdapter().parse(md_dir / "setext_and_codes.md")
    # Setext H1 is the first top-level heading
    h1 = r.declarations[0]
    assert h1.kind == KIND_HEADING
    assert h1.name == "Setext H1 Title"
    assert h1.signature.startswith("# ")  # level 1
    # Setext H2 should exist as a child
    setext_h2 = _find(h1.children, name="Setext H2 Subheading")
    assert setext_h2 is not None
    assert setext_h2.signature.startswith("## ")


# --- Fenced code blocks --------------------------------------------------


def test_info_string_becomes_code_block_name(md_dir):
    r = MarkdownAdapter().parse(md_dir / "readme_style.md")
    install = _find(r.declarations, kind=KIND_HEADING, name="Installation")
    code_blocks = [c for c in install.children if c.kind == KIND_CODE_BLOCK]
    # The `bash` block at the top of Installation (before any H3)
    assert any(cb.name == "bash" for cb in code_blocks)


def test_unlabelled_fence_gets_default_name(md_dir):
    """A ``` fence with no info string still becomes a KIND_CODE_BLOCK."""
    r = MarkdownAdapter().parse(md_dir / "setext_and_codes.md")
    all_blocks = _find_all(r.declarations, kind=KIND_CODE_BLOCK)
    # One of them has no info string
    assert any(cb.name == "code" for cb in all_blocks)
    # And the labelled ones are also detected
    names = {cb.name for cb in all_blocks}
    assert {"python", "typescript"}.issubset(names)


def test_code_blocks_attached_to_nearest_heading(md_dir):
    """A code fence inside `### From source` should be a child of that H3,
    not of the enclosing `## Installation`."""
    r = MarkdownAdapter().parse(md_dir / "readme_style.md")
    install = _find(r.declarations, kind=KIND_HEADING, name="Installation")
    from_src = _find(install.children, name="From source")
    # The bash block inside "From source"
    from_src_blocks = [c for c in from_src.children if c.kind == KIND_CODE_BLOCK]
    assert len(from_src_blocks) == 1
    assert from_src_blocks[0].name == "bash"


def test_code_block_line_range_matches_fence(md_dir):
    r = MarkdownAdapter().parse(md_dir / "setext_and_codes.md")
    py_block = next(cb for cb in _find_all(r.declarations, kind=KIND_CODE_BLOCK) if cb.name == "python")
    src_lines = (md_dir / "setext_and_codes.md").read_text().splitlines()
    # The line at start_line should be the opening ```python fence
    assert src_lines[py_block.start_line - 1].strip().startswith("```python")
    # The line at end_line should be the closing fence
    assert src_lines[py_block.end_line - 1].strip() == "```"


# --- Rendering (outline + digest) ----------------------------------------


def test_outline_prints_hierarchical_structure(md_dir):
    r = MarkdownAdapter().parse(md_dir / "readme_style.md")
    out = render_outline(r, OutlineOptions())
    # Headings appear with their `#` prefix
    assert "# Sample Project" in out
    assert "## Installation" in out
    assert "### From source" in out
    # Code blocks appear too (default options include fields=True)
    assert "bash code block" in out


def test_digest_renders_markdown_as_toc(md_dir):
    r = MarkdownAdapter().parse(md_dir / "readme_style.md")
    out = render_digest([r], DigestOptions())
    # TOC lines with indented `#` signatures
    assert "# Sample Project" in out
    assert "## Installation" in out
    # By default code blocks are NOT shown in TOC digest
    assert "bash code block" not in out


def test_digest_respects_max_heading_depth(md_dir):
    r = MarkdownAdapter().parse(md_dir / "article.md")
    # Default max_heading_depth = 3 → H4 is hidden
    default_out = render_digest([r], DigestOptions())
    assert "#### A nested detail" not in default_out
    # Raise cap → H4 shows up
    deep_out = render_digest([r], DigestOptions(max_heading_depth=4))
    assert "#### A nested detail" in deep_out


def test_digest_code_blocks_only_with_include_fields(md_dir):
    r = MarkdownAdapter().parse(md_dir / "readme_style.md")
    with_blocks = render_digest([r], DigestOptions(include_fields=True))
    assert "bash code block" in with_blocks


def test_digest_marks_empty_file(md_dir):
    r = MarkdownAdapter().parse(md_dir / "empty.md")
    out = render_digest([r], DigestOptions())
    assert "# empty" in out


# --- noise_regions for fenced code blocks --------------------------------


def test_noise_regions_populated_for_fenced_blocks(md_dir):
    """Each fenced code block contributes a (start, end, kind) region."""
    r = MarkdownAdapter().parse(md_dir / "grep_noise.md")
    assert r.noise_regions, "expected noise_regions to be populated"
    # Two fenced blocks in grep_noise.md — javascript + python.
    assert len(r.noise_regions) == 2
    # Kind tag is "string" so the existing grep noise filter picks it up.
    assert all(kind == "string" for _start, _end, kind in r.noise_regions)


def test_noise_regions_exclude_fence_delimiters_and_info_string(md_dir):
    r"""Region bytes cover the body — never the ``\`\`\`python`` line or
    the closing ``\`\`\```. That keeps the info-string searchable so an
    agent can grep for ``python`` to find code blocks by language."""
    src = (md_dir / "grep_noise.md").read_bytes()
    r = MarkdownAdapter().parse(md_dir / "grep_noise.md")
    for start, end, _ in r.noise_regions:
        body = src[start:end]
        # No fence delimiter inside the masked region.
        assert b"```" not in body
        # No language token at the very start (info string lives on the
        # opening fence line, before the body).
        assert not body.startswith(b"javascript")
        assert not body.startswith(b"python")


def test_grep_filters_matches_inside_fenced_code_block(md_dir):
    """Matches inside fenced code blocks vanish under default noise filter."""
    path = md_dir / "grep_noise.md"
    results, _ignored, _excluded = grep("useState", [path])
    # Pattern lives in both prose and fenced examples — prose hits stay,
    # the fence content gets filtered.
    assert results, "expected at least the prose matches to survive"
    fr = results[0]
    visible_lines = {m.line for m in fr.matches}
    # Every visible match line should be prose, never inside a fence.
    src_lines = path.read_text().splitlines()
    for line_no in visible_lines:
        line = src_lines[line_no - 1]
        # A prose mention of useState — never the JS literal call or the
        # python assignment.
        assert "useState(0)" not in line
        assert 'useState = "this is python' not in line
    # Filtered count tracks how many were swallowed.
    assert fr.filtered_count > 0


def test_grep_include_noise_surfaces_fenced_block_matches(md_dir):
    """``include_noise=True`` re-surfaces matches inside fenced blocks."""
    path = md_dir / "grep_noise.md"
    visible_default, _, _ = grep("useState", [path])
    all_with_noise, _, _ = grep("useState", [path], include_noise=True)
    # Strictly more matches with noise enabled — the previously filtered
    # in-fence hits show up.
    assert (
        sum(len(fr.matches) for fr in all_with_noise)
        > sum(len(fr.matches) for fr in visible_default)
    )
