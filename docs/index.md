---
hide:
  - navigation
  - toc
---

# ast-outline

> **Fast, AST-based structural outline for source files** — classes, methods,
> signatures with line numbers, but **no method bodies**. Built for LLM coding
> agents that should read the *shape* of a file before reading the whole thing.

[![Code: Apache 2.0](https://img.shields.io/badge/code-Apache%202.0-blue.svg)](https://github.com/ast-outline/ast-outline/blob/main/LICENSE)
[![Docs: CC BY 4.0](https://img.shields.io/badge/docs-CC%20BY%204.0-lightgrey.svg)](https://github.com/ast-outline/ast-outline/blob/main/LICENSE-DOCS)
[![PyPI](https://img.shields.io/pypi/v/ast-outline.svg)](https://pypi.org/project/ast-outline/)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://pypi.org/project/ast-outline/)

---

## Install

```bash
uv tool install ast-outline
```

??? note "Other install options (pipx, pip, from source)"

    ```bash
    pipx install ast-outline
    pip  install ast-outline                                                # into an active venv

    # Latest main:
    uv tool install git+https://github.com/ast-outline/ast-outline.git
    ```

---

## Why

**`ast-outline` exists to make LLM coding agents faster, cheaper, and smarter
when navigating unfamiliar code.**

Modern agentic tools (Claude Code, Cursor's agent mode, Aider, Copilot Chat,
custom CLI agents) explore codebases by reading files directly — not via
embeddings or vector search. That approach is reliable but has a cost: on a
1000-line file, the agent pays for 1000 lines of tokens just to answer
*"what methods exist here?"*.

`ast-outline` closes that gap. It's a **pre-reading layer** for agents:

- :material-database-arrow-down: **Token savings — typically 5–10×.** An outline replaces a full file read when the agent only needs structural understanding.
- :material-map-search: **Faster exploration.** A whole module's public API fits on one screen.
- :material-target: **Precise navigation.** Every declaration has a line range (`L42-58`). The agent goes straight to the method body it needs.
- :material-tree-outline: **AST accuracy, not fuzzy match.** `show` and inheritance rendering understand real syntax — no false positives from comments or strings.
- :material-cloud-off-outline: **Zero infrastructure.** No index, no cache, no embeddings, no network. Live, always fresh, invisible to your repo.

---

## The typical agent workflow

=== "Before `ast-outline`"

    ```
    Agent: Read Player.cs            # 1200 lines of tokens
    Agent: Read Enemy.cs             # 800 lines of tokens
    Agent: Read DamageSystem.cs      # 400 lines of tokens
    ...
    ```

=== "With `ast-outline`"

    ```
    Agent: ast-outline digest src/Combat         # ~100 lines, whole module
    Agent: ast-outline Player.cs                 # signatures only, 5–10× smaller
    Agent: ast-outline show Player.cs TakeDamage # just the method body
    ```

**Same understanding, a fraction of the tokens, a fraction of the round-trips.**

---

## Design philosophy

> **Stateless. No index, no cache, no embeddings, no network.**
> Parse on demand, print, exit.

Opposite of RAG-style codebase indexers (Cursor, Bloop, Continue, the
embedding-MCP crowd). Modern LLM agents are sharp enough to chain
`ast-outline` with `grep`, `find`, `ast-grep` and other unix tools and navigate
real code fast — without reading whole files, and without a local index
earning its complexity.

---

## Supported languages

| Language   | Extensions |
| ---        | --- |
| C#         | `.cs` |
| Python     | `.py`, `.pyi` |
| TypeScript | `.ts`, `.tsx` |
| JavaScript | `.js`, `.jsx`, `.mjs`, `.cjs` *(parsed by the TypeScript grammar)* |
| Java       | `.java` |
| Kotlin     | `.kt`, `.kts` |
| Scala      | `.scala`, `.sc` |
| Go         | `.go` |
| Rust       | `.rs` |
| Markdown   | `.md`, `.markdown`, `.mdx`, `.mdown` |
| YAML       | `.yaml`, `.yml` |

Adding another language is a single new adapter file. See
[`src/ast_outline/adapters/`](https://github.com/ast-outline/ast-outline/tree/main/src/ast_outline/adapters).

---

## Next steps

<div class="grid cards" markdown>

- :material-console: **[Commands](commands.md)**
  Outline, digest, show, prompt — full CLI reference with examples.

- :material-robot: **[LLM agents](agents.md)**
  How to wire `ast-outline` into Claude Code, Cursor, Aider, and custom agents.

- :material-format-list-bulleted: **[Output format](output-format.md)**
  Digest legend, marker tags, size labels.

- :material-source-branch: **[GitHub](https://github.com/ast-outline/ast-outline)**
  Source, issues, releases.

</div>
