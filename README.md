# code-outline

**English** · [Русский](./README.ru.md) · [简体中文](./README.zh-CN.md)

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
Copilot Chat, custom CLI agents) explore codebases by reading files directly
— not via embeddings or vector search. That approach is reliable but has a
cost: on a 1000-line file, the agent pays for 1000 lines of tokens just to
answer *"what methods exist here?"*.

`code-outline` closes that gap. It's a **pre-reading layer** for agents:

1. **Token savings — typically 5–10×.** An outline replaces a full file
   read when the agent only needs structural understanding.
2. **Faster exploration.** A whole module's public API fits on one screen.
3. **Precise navigation.** Every declaration has a line range (`L42-58`).
   The agent goes straight to the method body it needs.
4. **AST accuracy, not fuzzy match.** `implements` and `show` understand
   real syntax — no false positives from comments or strings.
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
Agent: code-outline digest src/Combat         # ~100 lines, whole module
Agent: code-outline implements IDamageable    # precise list, no grep noise
Agent: code-outline show Player.cs TakeDamage # just the method body
```

Result: **same understanding, a fraction of the tokens, a fraction of
the round-trips.**

---

## Supported languages

| Language | Extensions |
| --- | --- |
| C#         | `.cs` |
| Python     | `.py`, `.pyi` |
| TypeScript | `.ts`, `.tsx` |
| JavaScript | `.js`, `.jsx`, `.mjs`, `.cjs` (parsed by the TypeScript grammar) |
| Java       | `.java` — classes, interfaces, `@interface`, enums, records, sealed hierarchies, generics, throws, Javadoc |
| Markdown   | `.md`, `.markdown`, `.mdx`, `.mdown` — heading TOC + fenced code blocks |

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

## Using with LLM coding agents

This is the main use case. Add the snippet below to your `CLAUDE.md`,
`AGENTS.md`, subagent file, or any system prompt that steers a coding
agent. It will then prefer `code-outline` over reading full files.

### Prompt snippet (copy-paste)

```markdown
## Code exploration — prefer `code-outline` over full reads

For `.cs`, `.py`, `.pyi`, `.ts`, `.tsx`, `.js`, `.jsx`, `.java`, and `.md`
files, read structure with `code-outline` before opening full contents.
Pull method bodies only once you know which ones you need.

Stop at the step that answers the question:

1. **Unfamiliar directory** — `code-outline digest <dir>`: one-page map
   of every file's types and public methods.

2. **One file's shape** — `code-outline <file>`: signatures with line
   ranges, no bodies (5–10× smaller than a full read).

3. **One method, class, or markdown section** — `code-outline show <file>
   <Symbol>`. Suffix matching: `TakeDamage`, or `Player.TakeDamage` when
   ambiguous. Multiple at once: `code-outline show Player.cs TakeDamage
   Heal Die`. For markdown, the symbol is the heading text.

4. **Who implements/extends a type** — `code-outline implements <Type>
   <dir>`: AST-accurate (skip `grep`), transitive by default with
   `[via Parent]` tags on indirect matches. Add `--direct` for level-1 only.

Fall back to a full read only when you need context beyond the body
`show` returned.

If the outline header contains `# WARNING: N parse errors`, the outline
for that file is partial — read the source directly for the affected region.

`code-outline help` for flags and rare options.
```

### Why this helps

- **Fresh subagents with shallow context** (like Claude Code's `Explore`
  agent) can scan a whole module in one call instead of 10–20 `Read`/`grep`
  rounds.
- **"Where is X defined?"** becomes one `implements` or `show` call.
- **Line ranges** (`L42-58`) turn the outline into a precise navigator —
  the agent reads only the lines it needs.
- **AST-based** `implements` has no false positives from string literals,
  comments, or unrelated name mentions — unlike `grep`.

### Works with

- Claude Code (+ custom subagents like `Explore`, `codebase-scout`)
- Cursor agent mode
- Aider
- Copilot Chat / Workspace
- Any custom agent on the Claude / OpenAI / Gemini APIs
- Humans (the format is readable; `show` is a nice alternative to `grep -A 20`)

---

## Commands

### `outline` — default

Print the file's classes, methods, properties, fields with line ranges.

```bash
code-outline path/to/File.cs
code-outline path/to/module.py --no-private --no-fields
```

Flags:

- `--no-private` — hide private members (Python: names starting with `_`)
- `--no-fields` — hide field declarations
- `--no-docs` — hide `///` XML-doc / docstrings
- `--no-attrs` — hide `[Attributes]` / `@decorators`
- `--no-lines` — hide line-number suffixes
- `--glob PATTERN` — restrict directory mode to a pattern

### `show` — extract source of a symbol

```bash
code-outline show File.cs TakeDamage
code-outline show File.cs PlayerController.TakeDamage   # disambiguate overloads
code-outline show service.py UserService.get
code-outline show File.cs TakeDamage Heal Die           # several at once
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
**Transitive by default**: if `Puppy extends Dog extends Animal`, then
`implements Animal` returns all three, with an annotation on indirect
matches:

```
# 3 match(es) for 'Animal' (incl. transitive):
src/Animals.cs:5   class Dog : Animal
src/Cats.cs:3      class Cat : Animal
src/Puppies.cs:12  class Puppy : Dog          [via Dog]
```

Add `--direct` / `-d` to restrict to level-1 subclasses only:

```bash
code-outline implements --direct IDamageable src/
```

The search works across any number of files and nested directories —
no reliance on filename↔classname convention. Matching is by the last
segment of the type name (stripping generics and namespace prefixes).

---

## Output format

The format is designed to be **LLM-friendly**: Python-style indentation,
line-number suffixes in `L<start>-<end>` form, doc-comments preserved.
The header summarises scale and flags partial parses.

### C#

```
# Player.cs (142 lines, 3 types, 12 methods, 5 fields)
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
# user_service.py (70 lines, 2 types, 5 methods, 3 fields)
@dataclass class User  L16-29
    def display_name(self) -> str  L26-29
        """Human-friendly label."""

class UserService  L31-58
    def __init__(self, storage: Storage) -> None  L34-35
    def get(self, user_id: int) -> User | None  L37-42
        """Look up a user by id."""
    def save(self, user: User) -> None  L44-46
```

### `show` with ancestor context

`code-outline show <file> <Symbol>` prints a `# in: ...` breadcrumb
between the header and the body so you know what the extracted code is
nested inside, without a second `outline` call:

```
# Player.cs:30-48  Game.Player.PlayerController.TakeDamage  (method)
# in: namespace Game.Player → public class PlayerController : MonoBehaviour, IDamageable
/// <summary>Apply damage.</summary>
public void TakeDamage(int amount) { ... }
```

Top-level symbols (no enclosing namespace/type) have no breadcrumb.

### Partial parses

When tree-sitter recovers from syntax errors, the outline is kept but a
second header line flags the gap:

```
# broken.java (16 lines, 1 types, 3 methods)
# WARNING: 3 parse errors — output may be incomplete
```

Agents should treat these files as partial and read the source directly
for the affected region.

Differences are language-idiomatic:

- C# `///` XML-doc appears **above** the signature.
- Python `"""docstrings"""` appear **below** the signature with one extra
  indent (matching Python semantics).
- C# attributes (`[Attr]`) and Python decorators (`@foo`) are inlined with
  the declaration.
- C# property accessors `{ get; private set; }` are preserved.

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

### Running the tests

Tests are an optional dev dependency — end users don't pull them in. Install
them once and run via `pytest`:

```bash
# Install pytest into the same venv as the editable install
uv pip install -e ".[dev]"

# Run the full suite (takes ~0.1s)
.venv/bin/pytest

# Just one file, verbose
.venv/bin/pytest tests/unit/test_csharp_adapter.py -v

# Match by test name
.venv/bin/pytest -k file_scoped_namespace -v
```

The suite (200+ tests) covers every adapter (C#, Python, TypeScript/JS,
Java, Markdown), the language-agnostic renderers, symbol search, and the
CLI end-to-end. Fixtures live under `tests/fixtures/`; tests never reach
outside that directory.
New behaviour should come with a test; new languages should ship with a
dedicated fixture directory and a `tests/unit/test_<lang>_adapter.py` file.

### Adding a new language

Create `src/code_outline/adapters/<lang>.py` implementing the
`LanguageAdapter` protocol (see `adapters/base.py`). Then register it in
`adapters/__init__.py`. The core renderers and CLI pick it up automatically
— no further wiring needed.

---

## Roadmap

- [x] TypeScript / JavaScript adapter (`.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs`)
- [x] Java adapter (`.java`) — classes, interfaces, `@interface`, enums, records, sealed hierarchies, generics, throws, Javadoc
- [x] Markdown adapter (`.md`, `.markdown`, `.mdx`, `.mdown`) — heading TOC + code blocks
- [ ] Go adapter
- [ ] Rust adapter
- [ ] `--format json` output mode for programmatic consumers
- [ ] Optional multiprocessing for very large codebases (>500 files)

Contributions welcome.

---

## License

[MIT](./LICENSE)
