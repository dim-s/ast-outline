"""Canonical LLM-agent prompt snippet.

This module holds the text that steers coding agents (Claude, Cursor,
etc.) to prefer `ast-outline` over full-file reads. It's the single
source of truth for:

- The `ast-outline prompt` CLI subcommand (prints this verbatim)
- The "Prompt snippet (copy-paste)" section of the README (kept in
  sync by hand — when you change AGENT_PROMPT, update the README too)

Keep AGENT_PROMPT a pure markdown string. No placeholders, no
language-switching — the snippet is intentionally universal across
Claude Opus 4.7 / Sonnet 4.6 / Haiku 4.5 and English-first for maximum
compatibility with LLM instruction-tuning.
"""
from __future__ import annotations


AGENT_PROMPT = """## Code exploration — prefer `ast-outline` over full reads

For `.cs`, `.py`, `.pyi`, `.ts`, `.tsx`, `.js`, `.jsx`, `.java`, `.kt`, `.kts`,
`.scala`, `.sc`, `.go`, and `.md` files, read structure with `ast-outline`
before opening full contents.
Pull method bodies only once you know which ones you need.

Stop at the step that answers the question:

1. **Unfamiliar directory** — `ast-outline digest <dir>`: one-page map
   of every file's types and public methods.

2. **One file's shape** — `ast-outline <file>`: signatures with line
   ranges, no bodies (5–10× smaller than a full read).

3. **One method, class, or markdown section** — `ast-outline show <file>
   <Symbol>`. Suffix matching: `TakeDamage`, or `Player.TakeDamage` when
   ambiguous. Multiple at once: `ast-outline show Player.cs TakeDamage
   Heal Die`. For markdown, the symbol is the heading text.

4. **Who implements/extends a type** — `ast-outline implements <Type>
   <dir>`: AST-accurate (skip `grep`), transitive by default with
   `[via Parent]` tags on indirect matches. Add `--direct` for level-1 only.

Fall back to a full read only when you need context beyond the body
`show` returned.

If the outline header contains `# WARNING: N parse errors`, the outline
for that file is partial — read the source directly for the affected region.

`ast-outline help` for flags and rare options. The legacy binary name
`code-outline` works as an alias through 0.4.x for backward compatibility.
"""
