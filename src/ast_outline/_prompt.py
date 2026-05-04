"""Canonical LLM-agent prompt snippet.

This module holds the text that steers coding agents (Claude, Cursor,
etc.) to prefer `ast-outline` over full-file reads. It's the single
source of truth for:

- The `ast-outline prompt` CLI subcommand (prints this verbatim)
- The "Prompt snippet (copy-paste)" section of the README (kept in
  sync by hand — when you change AGENT_PROMPT, update the README too)

Keep AGENT_PROMPT a pure markdown string. No placeholders, no
language-switching — the snippet is intentionally cross-vendor
universal: Claude Opus 4.7 / Sonnet 4.6 / Haiku 4.5 AND OpenAI
GPT-5.x (5.3-codex, 5.4, 5.5). English-first for maximum
compatibility with LLM instruction-tuning.

Cross-vendor constraints when editing — keep all of these intact:
outcome-first phrasing (the heading states the goal); steps framed
as a menu, not a sequence (GPT-5.5 reads numbered prescriptions as
noise); no aggressive emphasis (`CRITICAL:` / `YOU MUST`); no persona
("you are a senior X"); no "think step by step"; explicit fallbacks
for partial output (`[broken]`, `# WARNING: N parse errors`,
`[+ N conditional includes]`); no model-name pinning. If you add a
Claude-specific or GPT-specific trick, the snippet is no longer
universal — split it instead.
"""
from __future__ import annotations


AGENT_PROMPT = """## Code exploration — prefer `ast-outline` over full reads

For `.cs`, `.py`, `.pyi`, `.ts`, `.tsx`, `.js`, `.jsx`, `.java`, `.kt`, `.kts`,
`.scala`, `.sc`, `.go`, `.rs`, `.php`, `.phtml`, `.md`, and `.yaml`/`.yml`
files, read structure with `ast-outline` before opening full contents.

Pick the smallest of these that answers your question — they're a
broad-to-narrow menu, not a sequence; skip straight to `show` when
you already know the symbol:

1. **Unfamiliar directory** — `ast-outline digest <paths…>`: one-page map
   of every file's types and public methods. Each file is tagged with a
   size label — `[tiny]` / `[medium]` / `[large]` — plus `[broken]`
   when parse errors may have left the outline partial.

2. **File-level shape** — `ast-outline <paths…>`: signatures with line
   ranges, no bodies (5–10× smaller than a full read on non-trivial
   files). A `# WARNING: N parse errors` line in the header means the
   outline is partial — read the source for the affected region.

3. **One method, type, markdown heading, or yaml key** —
   `ast-outline show <file> <Symbol>`. Suffix matching: `TakeDamage`
   for one method; `User` for an entire type — class, struct, interface,
   trait, enum (whole body, useful when a file holds several types);
   `Player.TakeDamage` when ambiguous. Multiple at once:
   `ast-outline show Player.cs TakeDamage Heal Die`.
   For markdown, the symbol is heading text and matching is
   case-insensitive substring — `"installation"` finds
   `"2.1 Installation (macOS / Linux)"`. For yaml, the symbol is a
   dotted key path (`spec.containers[0].image`) — `show` matches keys,
   not values, so for free-text search inside values use `grep`.
   Add `--signature` to any of the above to return header only
   (docs + attrs + signature, no body) — useful after `digest`, when
   you have the name and want the contract, not the implementation.

`outline` and `digest` accept multiple paths in one call (files and
directories, mixed languages OK) — batch instead of looping. Type
headers in both renderers carry inheritance as `: Base, Trait`, so the
shape of class hierarchies is visible without a separate query.

When you need to know **what a file pulls in** or **where a referenced
type / function comes from**, add `--imports` to `outline` or `digest`.
The file header gets an `imports:` line listing every
`import` / `use` / `using` statement verbatim in the language's native
syntax — `from .core import X`, `use foo::Bar`,
`import { X } from './foo'`, `use App\\Foo`, `require_once 'config.php'`.
Read the imports, then call `outline` / `show` on the source file
instead of grepping for the definition. Skip the flag for routine
structure reads — it adds one line per file.

A trailing `[+ N conditional includes]` on the imports line means
N more dependencies live inside `if` / `try` / loop / function bodies
— read the file directly when you need the full dependency picture.

Fall back to a full read only when you need context beyond the body
`show` returned. `ast-outline help` for flags.
"""
