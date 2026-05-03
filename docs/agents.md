# LLM agents

This is the primary use case for `ast-outline`. Add the snippet below to
your `CLAUDE.md`, `AGENTS.md`, subagent file, or any system prompt that
steers a coding agent. Once it's there, the agent will reach for
`ast-outline` before reading whole files.

## The prompt snippet

The same snippet ships with the tool — `ast-outline prompt` prints it
verbatim, so you can append it to your project's agent config without
copying by hand:

```bash
ast-outline prompt >> AGENTS.md
ast-outline prompt >> .claude/CLAUDE.md
ast-outline prompt | pbcopy   # macOS clipboard
```

??? quote "Snippet (copy-paste version)"

    ```markdown
    ## Code exploration — prefer `ast-outline` over full reads

    For `.cs`, `.py`, `.pyi`, `.ts`, `.tsx`, `.js`, `.jsx`, `.java`,
    `.kt`, `.kts`, `.scala`, `.sc`, `.go`, `.rs`, `.md`, and
    `.yaml`/`.yml` files, read structure with `ast-outline` before
    opening the full file.

    Stop at the step that answers the question:

    1. **Unfamiliar directory** — `ast-outline digest <paths…>`: a
       one-page map of every file's types and public methods. Each
       file is tagged with a size label — `[tiny]` / `[medium]` /
       `[large]` — plus `[broken]` if parse errors clipped the outline.

    2. **File-level structure** — `ast-outline <paths…>`: signatures
       with line ranges, no bodies (5–10× smaller than a full read on
       non-trivial files). If the header carries `# WARNING: N parse
       errors`, the outline is incomplete — read the affected region
       directly.

    3. **One method / type / markdown heading / yaml key** —
       `ast-outline show <file> <Symbol>`. Suffix matching: `TakeDamage`
       picks one method; `User` returns the full body of a type — class,
       struct, interface, trait, enum (especially useful when a file
       holds several types); disambiguate with `Player.TakeDamage` if
       there's ambiguity. Multiple at once:
       `ast-outline show Player.cs TakeDamage Heal Die`. Markdown
       symbols are heading text, matched case-insensitive substring:
       `"installation"` hits `"2.1 Installation (macOS / Linux)"`.
       YAML symbols are dot-separated key paths
       (`spec.containers[0].image`) — `show` matches **keys**, not
       values; for free-text search inside values use `grep`.

    Both `outline` and `digest` accept multiple paths in a single call
    (mix files and directories, mix languages). Both renderers append
    `: Base, Trait` inheritance to type headers, so you see the
    hierarchy without a separate query.

    When you need to know **what a file pulls in** or **where a
    referenced type lives**, pass `--imports` to `outline` / `digest`.
    Each file gets an extra `imports:` line listing its `import` /
    `use` / `using` statements verbatim — `from .core import X`,
    `use foo::Bar`, `import { X } from './foo'`. Read that line, then
    call `outline` / `show` on the source file directly — no `grep`
    needed to find definitions. Skip `--imports` for routine structural
    reads — it adds one line per file.

    Fall back to a full read only when `show`'s body isn't enough
    context. `ast-outline help` for the full flag list.
    ```

---

## Integration notes per agent

### Claude Code

`CLAUDE.md` (project-level) or `~/.claude/CLAUDE.md` (global) instructs
the **main agent**. To make Claude Code's isolated subagents (the
built-in `Explore`, anything in `.claude/agents/*.md`) use
`ast-outline`, override them: a subagent file at
`.claude/agents/Explore.md` (or `~/.claude/agents/Explore.md`) shadows
the built-in.

Subagents only see their own system prompt, not your `CLAUDE.md` — so
each subagent that should know about `ast-outline` needs the snippet
in its own file.

### Cursor

Add the snippet to `.cursor/rules/ast-outline.mdc` or to your global
"Rules for AI" in Cursor settings.

### Aider

Append to `CONVENTIONS.md` at the repo root, or pass via
`--read CONVENTIONS.md`.

### Codex / Copilot Chat / others

Most agents accept a project-root file named `AGENTS.md` or a system
prompt configurable via the agent's settings UI. The snippet is plain
Markdown — drop it wherever your agent reads instructions.

---

## What's NOT in the snippet (and why)

- **No "always run `ast-outline` before any read"** rule. The snippet
  steers the agent toward structural reads first, but full reads
  remain valid when needed (small files, body-level questions).
- **No examples of failure modes.** The agent learns from the tool's
  `# note: …` output contract on its own — no need to pre-train it.
- **No reference to specific file extensions you don't use.** If your
  project is pure Python, you can shorten the extension list. The
  generic version supports all adapters.

---

## Verifying the integration

Open the agent in a fresh session and ask:

> "What types live in `src/Combat`? Use `ast-outline` if available."

A correctly-wired agent will run `ast-outline digest src/Combat`,
return the structural map, and only then open specific files for
detail. If it goes straight to `Read` instead, the snippet didn't land
— check that the agent loaded the right config file.
