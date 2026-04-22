# code-outline

> Fast, AST-based **structural outline** for source files — classes, methods,
> signatures with line numbers, but **no method bodies**. Built for LLM coding
> agents that should read the *shape* of a file before reading the whole thing.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
![Status: beta](https://img.shields.io/badge/status-beta-orange.svg)

---

## Purpose

**`code-outline` exists to make LLM coding agents faster, cheaper, and smarter
when navigating unfamiliar code.**

Modern agentic coding tools (Claude Code, Cursor's agent mode, Aider,
Copilot Chat, in-house CLI agents) explore codebases by reading files
directly — not via embeddings or vector search. That approach is reliable
but has a cost: on a 1000-line file, the agent pays for 1000 lines of
tokens just to answer *"what methods exist here?"*.

This tool closes that gap. It's a **pre-reading layer** for agents:

1. **Token savings — typically 5–10×.** An outline replaces a full file
   read when the agent only needs structural understanding.
2. **Faster exploration.** A whole module's public API fits on one screen,
   so the agent reaches understanding in one call instead of 10–20
   `Read`/`grep` rounds.
3. **Precise navigation.** Every declaration has a line range
   (`L42-58`). The agent goes straight to the method body it needs,
   via `code-outline show` or a targeted `Read` with offset+limit.
4. **AST accuracy, not fuzzy match.** Unlike grep, `implements` and `show`
   understand real syntax — no false positives from comments or strings.
5. **Zero infrastructure.** No index, no cache, no embeddings, no network.
   Live, always fresh, invisible to your repo.

### The typical agent workflow

**Before `code-outline`:**

```
Agent: Read Player.cs            # 1200 lines of tokens
Agent: Read Enemy.cs             # 800 lines of tokens
Agent: Read DamageSystem.cs      # 400 lines of tokens
Agent: grep "IDamageable" src/   # noisy, lots of false matches
...
```

**With `code-outline`:**

```
Agent: code-outline digest src/Combat       # ~100 lines, whole module in one view
Agent: code-outline implements IDamageable  # precise list, no grep noise
Agent: code-outline show Player.cs TakeDamage  # just the method body
```

Result: **same understanding, a fraction of the tokens, a fraction of
the round-trips.**

### Designed for (but not limited to)

- Claude Code subagents like `Explore` / `codebase-scout`
- Custom agents built on the Claude / OpenAI / Gemini APIs that need to
  navigate code
- `CLAUDE.md` / `AGENTS.md` prompts that tell an agent "prefer this over
  full reads"
- Humans too — the outline format is readable, the `show` command is
  a nice alternative to `grep -A 20`

See the [Using with LLM coding agents](#using-with-llm-coding-agents)
section for a copy-pasteable prompt snippet.

---

## Why (the long version)

Tools like Claude Code and similar coding agents do **not** use vector/RAG
indexing — they read files directly with `grep` / `cat`-style tools. On a
1200-line `.cs` file that means 1200 lines of tokens just to learn "which
methods exist here".

`code-outline` gives the agent a **~8× smaller** view of the same file:

```
# CustomerController.cs (1202 lines)
namespace App.Customers
    public class CustomerController : MonoBehaviour  L77-1200
        public void SpawnCustomers()  L887-891
        public void TakeDamage(int amount)  L930-948
        ...
```

Each declaration has an **exact line range**. The agent can then fetch the
body of just one method with `code-outline show <file> <Method>` instead of
re-reading the whole file.

## Supported languages

| Language | Extensions |
| --- | --- |
| C#     | `.cs` |
| Python | `.py`, `.pyi` |

Adding another language is a single new adapter file. See
[`src/code_outline/adapters/`](src/code_outline/adapters/).

---

## Install

### One-liner (recommended — macOS / Linux / Windows)

Requires [`uv`](https://docs.astral.sh/uv/) (a fast Python package manager):

```bash
uv tool install git+https://github.com/dim-s/code-outline.git
```

This installs the `code-outline` CLI globally into `~/.local/bin` (Mac / Linux)
or `%USERPROFILE%\.local\bin` (Windows) — make sure that's on your `PATH`.

Don't have `uv` yet?

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Using the install scripts in this repo

```bash
# macOS / Linux
curl -LsSf https://raw.githubusercontent.com/dim-s/code-outline/main/scripts/install.sh | bash

# Windows (PowerShell)
iwr -useb https://raw.githubusercontent.com/dim-s/code-outline/main/scripts/install.ps1 | iex
```

### Alternative: `pipx`

```bash
pipx install git+https://github.com/dim-s/code-outline.git
```

### Alternative: `pip` (into an active venv)

```bash
pip install git+https://github.com/dim-s/code-outline.git
```

### Update / uninstall

```bash
uv tool upgrade code-outline
uv tool uninstall code-outline
```

---

## Quick start

```bash
# Structural outline of one file
code-outline path/to/Player.cs
code-outline path/to/user_service.py

# Outline a whole directory (recurses supported extensions)
code-outline src/

# Print the source of one specific method
code-outline show Player.cs TakeDamage

# Several methods at once
code-outline show Player.cs TakeDamage Heal Die

# Compact public-API map of a whole module
code-outline digest src/Services

# Every class that inherits/implements a given type
code-outline implements IDamageable src/

# Built-in guide
code-outline help
code-outline help show
```

---

## Commands

### `outline` — default

Print the file's classes, methods, properties, fields with line ranges.
Use when you want to read *one file's* structure before diving in.

```bash
code-outline path/to/File.cs
code-outline path/to/module.py --no-private --no-fields
```

Flags:

- `--no-private` — hide private members (Python: names starting with `_`)
- `--no-fields` — hide field declarations
- `--no-docs` — hide `///` XML-doc / `"""docstrings"""`
- `--no-attrs` — hide `[Attributes]` / `@decorators`
- `--no-lines` — hide line-number suffixes
- `--glob PATTERN` — restrict directory mode to a pattern

### `show` — extract source of a symbol

```bash
code-outline show File.cs TakeDamage
code-outline show File.cs PlayerController.TakeDamage    # disambiguate overloads
code-outline show service.py UserService.get
code-outline show File.cs TakeDamage Heal Die            # several at once
```

Matching is **suffix-based**: `Foo.Bar` matches any `*.Foo.Bar`. If multiple
declarations match, all are printed with a summary.

### `digest` — one-page module map

```bash
code-outline digest src/
```

Sample output:

```
src/services/
  user_service.py (140 lines)
    class UserService : IUserService  L8-138
      +get  +search  +create  +delete  +update
  auth_service.py (95 lines)
    class AuthService  L10-95
      +login  +logout  +refresh  +verify_token
```

### `implements` — find subclasses / implementations

```bash
code-outline implements IDamageable src/
```

AST-based — no false positives from comments or unrelated mentions.

---

## Output format

The format is designed to be **LLM-friendly**: Python-style indentation,
line-number suffixes in `L<start>-<end>` form, doc-comments preserved.

### C#

```
# Player.cs (142 lines)
namespace Game.Player
    [RequireComponent(typeof(Rigidbody2D))] public class PlayerController : MonoBehaviour, IDamageable  L10-120
        [SerializeField] private float speed = 5f  L12
        public int CurrentHealth { get; private set; }  L15
        /// <summary>Apply damage.</summary>
        public void TakeDamage(int amount)  L30-48
        private void Die()  L50-55
```

### Python

```
# user_service.py (70 lines)
@dataclass class User  L16-29
    def display_name(self) -> str  L26-28
        """Human-friendly label."""

class UserService  L31-58
    def __init__(self, storage: Storage) -> None  L34-35
    def get(self, user_id: int) -> User | None  L37-42
        """Look up a user by id."""
    def save(self, user: User) -> None  L44-46
```

Differences are language-idiomatic:

- C# `///` XML-doc appears **above** the signature.
- Python `"""docstrings"""` appear **below** the signature with one extra
  indent (matching Python semantics).
- C# attributes (`[Attr]`) and Python decorators (`@foo`) are inlined with
  the declaration.
- C# property accessors `{ get; private set; }` are preserved.

---

## Using with LLM coding agents

Add this to your `CLAUDE.md`, `AGENTS.md`, or a subagent file to make the
agent prefer `code-outline` over reading full files:

```markdown
## Code exploration

For C# and Python source files, prefer `code-outline` over full-file reads:

- `code-outline <file>` — structural outline with line ranges (≈8× less
  tokens than reading the full file)
- `code-outline show <file> <Symbol>` — fetch just one method/class body
- `code-outline digest <dir>` — one-page architecture overview of a module
- `code-outline implements <BaseType> <dir>` — find all subclasses/implementations

Read full files only when the outline does not give enough context — e.g.
when you actually need the logic inside a specific method you've already
identified via outline.

Run `code-outline help` for full usage.
```

Why this helps:

- Agents with shallow context (fresh subagents) can scan a whole module in
  one shot.
- "Where is X defined?" becomes one `implements` or `show` call instead of
  multiple `grep` + `read` rounds.
- Line ranges (`L42-58`) turn the outline into a precise navigator — the
  agent can read just the lines it needs.

---

## How it works (briefly)

- Parses source with [tree-sitter](https://tree-sitter.github.io/) —
  real AST, not regex.
- Language-specific adapters convert the AST to a uniform
  `Declaration` intermediate representation.
- Language-agnostic renderers produce outline / digest / search output.
- Purely local, no network, no indexing, no cache — just reads and parses
  the files you ask about.

No vector database, no embedding, no RAG. This is deliberate — the philosophy
matches how agentic coding tools like Claude Code actually work.

---

## Development

```bash
git clone https://github.com/dim-s/code-outline.git
cd code-outline

# Create a venv and install in editable mode
uv venv
uv pip install -e .

# Run against the included samples
.venv/bin/code-outline tests/sample.cs
.venv/bin/code-outline tests/sample.py
.venv/bin/code-outline digest tests/
```

### Adding a new language

Create `src/code_outline/adapters/<lang>.py` implementing the
`LanguageAdapter` protocol (see `adapters/base.py`). Then register it in
`adapters/__init__.py`. The core renderers and CLI pick it up automatically
— no further wiring needed.

---

## Roadmap

- [ ] TypeScript / JavaScript adapter
- [ ] Go adapter
- [ ] Rust adapter
- [ ] `--format json` output mode for programmatic consumers
- [ ] Optional multiprocessing for very large codebases (>500 files)

Contributions welcome.

---

## License

[MIT](./LICENSE)
