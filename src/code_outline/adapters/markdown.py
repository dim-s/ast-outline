"""Markdown adapter (.md, .markdown, .mdx, .mdown).

Produces an IR that looks like a table of contents:

    # README.md (342 lines)
    # code-outline                          L1-356
        ## Purpose                          L15-58
        ## Supported languages              L62-74
        ## Install                          L76-124
            ### One-liner                   L79-92
            ### pipx                        L105-111
        ## Commands                         L201-260

Additionally, fenced code blocks are recorded as children of their
surrounding heading so the outline shows things like:

        ### One-liner                       L79-92
            bash code block                 L83-86

Design:
- Each markdown `section` (tree-sitter's synthetic wrapper) → one
  KIND_HEADING declaration whose `children` are its sub-sections and
  fenced code blocks.
- Heading level (1-6) comes from the `atx_h{n}_marker` child, or from
  the `=`/`-` underline for setext headings.
- `signature` is `#` * level + " " + title, so the outline is
  immediately readable as markdown itself.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import tree_sitter_markdown as tsmd
from tree_sitter import Language, Node, Parser

from .base import count_parse_errors
from ..core import (
    KIND_CODE_BLOCK,
    KIND_HEADING,
    Declaration,
    ParseResult,
)


_LANGUAGE = Language(tsmd.language())
_PARSER = Parser(_LANGUAGE)


class MarkdownAdapter:
    language_name = "markdown"
    extensions = {".md", ".markdown", ".mdx", ".mdown"}

    def parse(self, path: Path) -> ParseResult:
        src = path.read_bytes()
        tree = _PARSER.parse(src)
        decls: list[Declaration] = []
        _walk(tree.root_node, src, decls)
        return ParseResult(
            path=path,
            language=self.language_name,
            source=src,
            line_count=src.count(b"\n") + 1,
            declarations=decls,
            error_count=count_parse_errors(tree.root_node),
        )


# --- Walk -----------------------------------------------------------------


def _walk(node: Node, src: bytes, out: list[Declaration]) -> None:
    """Top-level walk — the document root's named children are either
    `section` (wraps a heading) or orphan blocks (paragraph before the
    first heading, which we skip since they have no name)."""
    for child in node.named_children:
        if child.type == "section":
            decl = _section_to_decl(child, src)
            if decl is not None:
                out.append(decl)
        elif child.type == "fenced_code_block":
            # A code block at document top, before any heading
            out.append(_code_block_to_decl(child, src))


def _section_to_decl(node: Node, src: bytes) -> Optional[Declaration]:
    """Convert a `section` node into a KIND_HEADING declaration."""
    heading = _find_heading(node)
    if heading is None:
        return None
    level, title = _heading_level_and_title(heading, src)
    signature = ("#" * level) + " " + title if title else ("#" * level)

    children: list[Declaration] = []
    # Collect the well-formed children: sub-sections and code blocks.
    seen_heading = False
    for c in node.named_children:
        if c is heading:
            seen_heading = True
            continue
        if c.type == "section":
            sub = _section_to_decl(c, src)
            if sub is not None:
                children.append(sub)
        elif c.type == "fenced_code_block":
            children.append(_code_block_to_decl(c, src))
        elif c.type in ("atx_heading", "setext_heading") and seen_heading:
            # tree-sitter-markdown only creates a `section` wrapper when the
            # next heading is of a STRICTLY higher level. Same-or-deeper
            # headings end up as bare sibling nodes inside the outer section.
            # Promote them into their own pseudo-sections so the TOC is
            # still hierarchical.
            pseudo = _pseudo_section_from_heading(c, node, src)
            if pseudo is not None:
                children.append(pseudo)

    return Declaration(
        kind=KIND_HEADING,
        name=title or "?",
        signature=signature,
        visibility="public",
        start_line=node.start_point[0] + 1,
        end_line=_end_line(node),
        start_byte=node.start_byte,
        end_byte=node.end_byte,
        doc_start_byte=node.start_byte,
        children=children,
    )


def _pseudo_section_from_heading(
    heading: Node, parent_section: Node, src: bytes
) -> Optional[Declaration]:
    """Build a KIND_HEADING decl for a heading that wasn't wrapped in its
    own `section` (e.g. a setext H2 appearing after a setext H1 within the
    same tree-sitter section).

    The pseudo-section spans from the heading to the next heading sibling
    (of any level) or the end of the parent section.
    """
    level, title = _heading_level_and_title(heading, src)
    signature = ("#" * level) + " " + title if title else ("#" * level)

    # Find where this logical section ends: the next heading or section
    # sibling inside `parent_section`, or the parent's end.
    siblings = list(parent_section.named_children)
    try:
        idx = siblings.index(heading)
    except ValueError:
        return None
    end_byte = parent_section.end_byte
    end_point = parent_section.end_point
    for later in siblings[idx + 1 :]:
        if later.type in ("atx_heading", "setext_heading", "section"):
            end_byte = later.start_byte
            end_point = later.start_point
            break

    return Declaration(
        kind=KIND_HEADING,
        name=title or "?",
        signature=signature,
        visibility="public",
        start_line=heading.start_point[0] + 1,
        end_line=end_point[0] if end_point[1] == 0 else end_point[0] + 1,
        start_byte=heading.start_byte,
        end_byte=end_byte,
        doc_start_byte=heading.start_byte,
    )


def _code_block_to_decl(node: Node, src: bytes) -> Declaration:
    """Represent a fenced code block as a KIND_CODE_BLOCK declaration.

    Name is the info-string language (`bash`, `typescript`, …) when present,
    otherwise a synthetic `code` so the user has something to target with
    `code-outline show`.
    """
    info = _info_string(node, src) or "code"
    signature = f"{info} code block"
    return Declaration(
        kind=KIND_CODE_BLOCK,
        name=info,
        signature=signature,
        visibility="public",
        start_line=node.start_point[0] + 1,
        end_line=_end_line(node),
        start_byte=node.start_byte,
        end_byte=node.end_byte,
        doc_start_byte=node.start_byte,
    )


def _end_line(node: Node) -> int:
    """Convert tree-sitter's exclusive end_point to an inclusive 1-based line.

    tree-sitter-markdown frequently extends a node's range through the
    trailing newline, so `end_point` lands at column 0 of the line AFTER the
    node's last actual line. Treat that case as ending on the previous line.
    """
    end_row, end_col = node.end_point
    if end_col == 0 and end_row > node.start_point[0]:
        return end_row
    return end_row + 1


# --- Helpers --------------------------------------------------------------


def _find_heading(section: Node) -> Optional[Node]:
    for c in section.named_children:
        if c.type in ("atx_heading", "setext_heading"):
            return c
    return None


def _heading_level_and_title(heading: Node, src: bytes) -> tuple[int, str]:
    if heading.type == "atx_heading":
        level = 1
        for c in heading.children:
            if c.type.startswith("atx_h") and c.type.endswith("_marker"):
                # atx_h1_marker .. atx_h6_marker
                try:
                    level = int(c.type[len("atx_h")])
                except (ValueError, IndexError):
                    level = 1
                break
        inline = next((c for c in heading.named_children if c.type == "inline"), None)
        title = _text(inline, src).strip() if inline is not None else ""
        return level, title
    # setext_heading — level 1 with `===` underline, level 2 with `---`
    if heading.type == "setext_heading":
        level = 2
        for c in heading.children:
            if c.type == "setext_h1_underline":
                level = 1
                break
            if c.type == "setext_h2_underline":
                level = 2
                break
        paragraph = next((c for c in heading.named_children if c.type == "paragraph"), None)
        title = _text(paragraph, src).strip() if paragraph is not None else ""
        return level, title
    return 1, ""


def _info_string(fenced: Node, src: bytes) -> Optional[str]:
    for c in fenced.named_children:
        if c.type == "info_string":
            return _text(c, src).strip()
    return None


def _text(node: Optional[Node], src: bytes) -> str:
    if node is None:
        return ""
    return src[node.start_byte:node.end_byte].decode("utf8", errors="replace")
