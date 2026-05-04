# ast-outline

**English** · [Русский](./README.ru.md) · [简体中文](./README.zh-CN.md)

> Fast, AST-based **structural outline** for source files — classes, methods,
> signatures with line numbers, but **no method bodies**. Built for LLM coding
> agents that should read the *shape* of a file before reading the whole thing.
>
> Sibling to [ast-grep](https://github.com/ast-grep/ast-grep) in the `ast-*`
> family: **`ast-grep` searches** code structurally, **`ast-outline` overviews** it.

[![Code: Apache 2.0](https://img.shields.io/badge/code-Apache%202.0-blue.svg)](./LICENSE)
[![Docs: CC BY 4.0](https://img.shields.io/badge/docs-CC%20BY%204.0-lightgrey.svg)](./LICENSE-DOCS)
[![PyPI](https://img.shields.io/pypi/v/ast-outline.svg)](https://pypi.org/project/ast-outline/)
![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
![Status: beta](https://img.shields.io/badge/status-beta-orange.svg)

📖 **Documentation:** <https://ast-outline.github.io/> · **Site source:** [ast-outline/ast-outline.github.io](https://github.com/ast-outline/ast-outline.github.io)

> **ast-outline™** by Dmitrii Zaitsev (dim-s) — original project at
> <https://github.com/ast-outline/ast-outline> (created 2026-04-22). Code under
> **Apache 2.0** (v0.6.0+; v0.5.x and earlier remain available under MIT),
> documentation under **CC BY 4.0** — reuse of this README's prose requires
> visible attribution. See [Licensing & attribution](#licensing--attribution) below.

---

## Purpose

**`ast-outline` exists to make LLM coding agents faster, cheaper, and smarter
when navigating unfamiliar code.**

Modern agentic coding tools (Claude Code, Cursor's agent mode, Aider,
Copilot Chat, custom CLI agents) explore codebases by reading files directly
— not via embeddings or vector search. That approach is reliable but has a
cost: on a 1000-line file, the agent pays for 1000 lines of tokens just to
answer *"what methods exist here?"*.

`ast-outline` closes that gap. It's a **pre-reading layer** for agents:

1. **Token savings — typically 5–10×.** An outline replaces a full file
   read when the agent only needs structural understanding.
2. **Faster exploration.** A whole module's public API fits on one screen.
3. **Precise navigation.** Every declaration has a line range (`L42-58`).
   The agent goes straight to the method body it needs.
4. **AST accuracy, not fuzzy match.** `show` and inheritance rendering
   understand real syntax — no false positives from comments or strings.
5. **Zero infrastructure.** No index, no cache, no embeddings, no network.
   Live, always fresh, invisible to your repo.

### The typical agent workflow

**Before `ast-outline`:**

```
Agent: Read Player.cs            # 1200 lines of tokens
Agent: Read Enemy.cs             # 800 lines of tokens
Agent: Read DamageSystem.cs      # 400 lines of tokens
...
```

**With `ast-outline`:**

```
Agent: ast-outline digest src/Combat         # ~100 lines, whole module
Agent: ast-outline Player.cs                 # signatures only, 5–10× smaller
Agent: ast-outline show Player.cs TakeDamage # just the method body
```

Result: **same understanding, a fraction of the tokens, a fraction of
the round-trips.**

---

## Design philosophy

> **Stateless. No index, no cache, no embeddings, no network.**
> Parse on demand, print, exit.

Opposite of RAG-style codebase indexers (Cursor, Bloop, Continue, the
embedding-MCP crowd). Modern LLM agents are sharp enough to chain
`ast-outline` with `grep`, `find`, `ast-grep` and other unix tools and
navigate real code fast — without reading whole files, and without a
local index earning its complexity.

And no MCP server for `ast-outline` itself — for a stateless CLI, agents
get more leverage piping and parallelising it in `bash` than through an
MCP shim wrapping the same calls.

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
| PHP        | `.php`, `.phtml`, `.phps`, `.php8` |
| Markdown   | `.md`, `.markdown`, `.mdx`, `.mdown` |
| YAML       | `.yaml`, `.yml` |

<details>
<summary>What each adapter recognises</summary>

- **Java** — classes, interfaces, `@interface`, enums, records, sealed hierarchies, generics, throws, Javadoc.
- **Kotlin** — classes, interfaces, `fun interface`, `object` / `companion object`, `data` / `sealed` / `enum` / `annotation` classes, extension functions, `suspend` / `inline` / `const` / `lateinit`, generics with `where` constraints, `typealias`, KDoc.
- **Scala** — Scala 2 + Scala 3: classes, traits, `object` / `case object`, `case class`, `sealed` hierarchies, Scala 3 `enum` / `given` / `using` / `extension`, indentation-based bodies, higher-kinded types, context bounds, `opaque type`, `type` aliases, Scaladoc.
- **Go** — packages, structs (with method-grouping under receiver), interfaces, struct/interface embedding as inheritance, generics (Go 1.18+), `type` aliases + defined types, `iota` enum-blocks, doc-comment chains.
- **Rust** — modules (recursive), structs (regular / tuple / unit), unions, enums with all variant shapes, traits with supertraits as bases, **`impl` block regrouping under the target type** (inherent + `impl Trait for Foo` adds Trait to bases), `extern "C"` blocks, `macro_rules!`, type aliases, generics + lifetimes + `where` clauses, `pub` / `pub(crate)` visibility, outer doc comments (`///`, `/** */`) and `#[...]` attributes.
- **PHP** — modern PHP 8.x and the still-deployed 7.4 LTS line: namespaces (file-scoped + bracketed), classes (`abstract` / `final` / `readonly` and combinations), interfaces, traits, PHP 8.1 enums (pure + backed), methods, magic ctor / dtor (`__construct` → ctor, `__destruct` → dtor), PHP 8.0 constructor property promotion (promoted parameters surface as fields), single + multi-variable properties, PHP 8.3 typed class constants, PHP 8.0 `#[Attr]` attributes, top-level `use` / `use function` / `use const` / grouped `use Foo\{A, B}`, plus top-level `include` / `include_once` / `require` / `require_once` for pre-Composer / WordPress / Drupal-7 codebases. Tested on real WordPress core (no parse errors on files up to 291 KB).
- **Markdown** — heading TOC + fenced code blocks.
- **YAML** — key hierarchy with line ranges, `[i]` sequence paths, multi-document separators, format-detect for Kubernetes / OpenAPI / GitHub Actions in the header.

</details>

Adding another language is a single new adapter file. See
[`src/ast_outline/adapters/`](src/ast_outline/adapters/).

#### YAML caveats

Real-world YAML files routinely surface a `# WARNING: N parse errors`
header — `tree-sitter-yaml`'s strict parser flags fairly innocuous
inconsistencies (like a sequence item nested inside an unexpected
mapping context) and the error region can spread well beyond the
actual broken line. The adapter's recovery walk salvages most useful
structure around such regions; treat the outline as best-effort and
fall back to `Read` for the affected region when the answer is
load-bearing.

`show` for YAML matches **keys**, not value text. `show file.yaml
"some phrase"` will not find a phrase that lives inside a string
value — for free-text searches inside values, use `grep`/`rg`.
`ast-outline` is structural; it complements text search rather than
replacing it.

---

## Install

```bash
uv tool install ast-outline
```

Installs the `ast-outline` CLI globally into `~/.local/bin` (macOS / Linux)
or `%USERPROFILE%\.local\bin` (Windows). Don't have [`uv`](https://docs.astral.sh/uv/)?

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh                                          # macOS / Linux
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"       # Windows
```

Update / uninstall: `uv tool upgrade ast-outline` / `uv tool uninstall ast-outline`.

<details>
<summary>Other install options (pipx, pip, from source, bundled script)</summary>

```bash
pipx install ast-outline
pip  install ast-outline                                          # into an active venv

# Latest main instead of the PyPI release:
uv tool install git+https://github.com/ast-outline/ast-outline.git

# Bundled one-shot installer (also installs uv if missing):
curl -LsSf https://raw.githubusercontent.com/ast-outline/ast-outline/main/scripts/install.sh | bash    # macOS / Linux
iwr -useb https://raw.githubusercontent.com/ast-outline/ast-outline/main/scripts/install.ps1 | iex     # Windows
```

</details>

---

## Quick start

```bash
# Structural outline of one file
ast-outline path/to/Player.cs
ast-outline path/to/user_service.py

# Outline a whole directory (recurses supported extensions)
ast-outline src/

# Print the source of one specific method
ast-outline show Player.cs TakeDamage

# Several methods at once
ast-outline show Player.cs TakeDamage Heal Die

# Compact public-API map of a whole module
ast-outline digest src/Services

# Built-in guide
ast-outline help
ast-outline help show
```

---

## Using with LLM coding agents

This is the main use case. Add the snippet below to your `CLAUDE.md`,
`AGENTS.md`, subagent file, or any system prompt that steers a coding
agent. It will then prefer `ast-outline` over reading full files.

The same snippet ships with the tool — `ast-outline prompt` prints it
verbatim, so you can append it to a project's agent config without
copy-pasting:

```bash
ast-outline prompt >> AGENTS.md
ast-outline prompt >> .claude/CLAUDE.md
ast-outline prompt | pbcopy   # macOS clipboard
```

### Prompt snippet (copy-paste)

```markdown
## Code exploration — prefer `ast-outline` over full reads

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
`import { X } from './foo'`, `use App\Foo`, `require_once 'config.php'`.
Read the imports, then call `outline` / `show` on the source file
instead of grepping for the definition. Skip the flag for routine
structure reads — it adds one line per file.

A trailing `[+ N conditional includes]` on the imports line means
N more dependencies live inside `if` / `try` / loop / function bodies
— read the file directly when you need the full dependency picture.

Fall back to a full read only when you need context beyond the body
`show` returned. `ast-outline help` for flags.
```

### Heads up: subagents

`CLAUDE.md` / `AGENTS.md` reach only the **main agent**. Claude Code's
isolated subagents (built-in `Explore`, anything in `.claude/agents/*.md`)
see only their own system prompt. To make `Explore` use `ast-outline`,
shadow it with `.claude/agents/Explore.md` (or `~/.claude/agents/Explore.md`)
and put the `ast-outline prompt` output in the body.

Cursor, Aider, and direct API clients have no isolated subagents —
`CLAUDE.md` / system prompt is enough there.

### Why this helps

- **Fresh subagents with shallow context** (like Claude Code's `Explore`
  agent) can scan a whole module in one call instead of 10–20 `Read`/`grep`
  rounds.
- **"Where is X defined?"** becomes one `show` call once the agent has
  spotted the symbol in `digest` or `outline`.
- **Line ranges** (`L42-58`) turn the outline into a precise navigator —
  the agent reads only the lines it needs.
- **AST-based** type headers carry real `: Base, Trait` inheritance with
  no false positives from string literals, comments, or unrelated name
  mentions — unlike `grep`.

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
ast-outline path/to/File.cs
ast-outline path/to/module.py --no-private --no-fields
```

Flags:

- `--no-private` — hide private members (Python: names starting with `_`)
- `--no-fields` — hide field declarations
- `--no-docs` — hide `///` XML-doc / docstrings
- `--no-attrs` — hide `[Attributes]` / `@decorators`
- `--no-lines` — hide line-number suffixes
- `--imports` — show file's imports (see below)
- `--glob PATTERN` — restrict directory mode to a pattern

#### `--imports` — see what each file depends on

`outline` and `digest` both accept `--imports`. When set, each file's
header is followed by an `imports:` line listing its
`import` / `use` / `using` statements verbatim, in the language's own
syntax — no synthetic format for the agent to learn:

```
$ ast-outline service.py --imports
# src/services/user_service.py (140 lines, ~1,200 tokens, 1 types, 5 methods)
# imports: from .core import UserBase; from .utils import parse_id; from typing import Optional
class UserService(UserBase):  L8-138
    ...
```

Multi-line and grouped forms are flattened: Go's `import (...)` block
becomes individual `import "fmt"` lines; multi-line TypeScript
`import { X, Y } from './long'` collapses to one line. Imports inside
function or class bodies are omitted — only file-level dependencies
are shown.

Useful when the agent needs to know where a referenced type lives, or
what a file pulls in, before deciding which file to read next.

### `show` — extract source of a symbol

```bash
ast-outline show File.cs TakeDamage
ast-outline show File.cs PlayerController.TakeDamage   # disambiguate overloads
ast-outline show service.py UserService.get
ast-outline show File.cs TakeDamage Heal Die           # several at once
```

For code, matching is **suffix-based**: `Foo.Bar` matches any `*.Foo.Bar`. If
multiple declarations match, all are printed with a summary.

For markdown, matching is **case-insensitive substring** per dotted part.
LLM agents rarely remember the exact decoration of a heading (number prefixes
like `1.`, trailing `(Feb 2026)`, `(Confidence: 70%)`), so a fuzzy core works:

```bash
ast-outline show forecast.md "current analysis"
# → matches `## 1. CURRENT ANALYSIS (Feb 2026)`

ast-outline show forecast.md "scenario.transit"
# → matches `### SCENARIO A: "MANAGED TRANSIT"` under any parent
#   heading containing "scenario"
```

If the substring matches several headings, all are printed and the
disambiguation summary lands on stderr — tighten the query to narrow.

### `digest` — one-page module map

```bash
ast-outline digest src/
```

Sample output:

```
# legend: name()=callable, name [kind]=non-callable, marker name()=method modifier (async/static/override/…), [N overloads]=N callables share name, [deprecated]=obsolete, L<a>-<b>=line range, : Base, …=inheritance
src/services/
  __init__.py [tiny] (8 lines, ~74 tokens, 1 fields)
  user_service.py [medium] (140 lines, ~1,200 tokens, 1 types, 5 methods)
    @Service abstract class UserService [deprecated] : IUserService  L8-138
      async get(), async search(), abstract create(), delete(), update_v1() [deprecated]

  auth_service.py [medium] (95 lines, ~840 tokens, 1 types, 4 methods)
    [ApiController] sealed class AuthService  L10-95
      async login(), logout(), refresh(), override verify_token()

  legacy_repo.py [large] [broken] (5234 lines, ~52,000 tokens, ...)
```

The first line is a self-describing legend so an LLM can read the
output cold without `ast-outline prompt` loaded. Tokens follow the
universal programming-doc convention — `name()` for a callable,
`name [kind]` for a property/field/event/etc., method markers
(`async`, `static`, `abstract`, `override`, `virtual`, plus
language-native forms: Kotlin `open` / `suspend`, Python
`@staticmethod` / `@classmethod` / `@abstractmethod`, Java
`@Override`) prefix the name source-true so each language reads in
its own idiom. `[N overloads]` flags when several callables share a
name; `[deprecated]` whenever a type or member carries
`@Deprecated` / `[Obsolete]` / `#[deprecated]`. Type headers also
carry inline decorators / attributes (`@dataclass`, `[ApiController]`,
`#[derive(Debug)]`) and semantic modifiers (`abstract`, `sealed`,
`static`, `final`, `open`, `partial`) so runtime contracts and
instantiation rules read off at a glance. Members are joined with
`, `; types that have a body get a trailing blank line as a
paragraph break, empty types stack tightly so digest stays compact.
Source-language keywords (Rust `trait`, Scala `object`, Kotlin
`data class`) are preserved in the type header instead of the
canonical kind.

Each filename gets a descriptive size label — `[tiny]` (under ~500 tokens),
`[medium]` (500–5000), `[large]` (5000+). A `[broken]` marker appears next
to the size label when the parse hit syntax errors and the outline may be
partial. The labels describe the file; they don't prescribe an action.
An LLM agent reads them, weighs its task (does it need the whole file? a
single section? just structure?) and picks Read / outline / show accordingly
— the tool informs, the agent decides.

The label conventions live in the canonical agent prompt (`ast-outline prompt`)
so they're paid for once per session, not on every digest call. Size class is
calibrated against an approximate token count (`len(chars)/4`, ±15-20% vs
real BPE tokenizers — fine for the heuristic). The same `~N tokens` count
appears in every `outline` header too.

### `prompt` — print the agent prompt snippet

```bash
ast-outline prompt
ast-outline prompt >> AGENTS.md
```

Prints the canonical copy-paste snippet used to steer LLM coding agents
to prefer `ast-outline` over full reads. English, universal across
Claude Opus 4.7 / Sonnet 4.6 / Haiku 4.5. Running it ensures you always
get the current recommended version.

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

`ast-outline show <file> <Symbol>` prints a `# in: ...` breadcrumb
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
git clone https://github.com/ast-outline/ast-outline.git
cd ast-outline

# Create a venv and install in editable mode
uv venv
uv pip install -e .

# Run against the included samples
.venv/bin/ast-outline tests/sample.cs
.venv/bin/ast-outline tests/sample.py
.venv/bin/ast-outline digest tests/
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

The suite (800+ tests) covers every adapter (C#, Python, TypeScript/JS,
Java, Kotlin, Scala, Go, Rust, PHP, Markdown, YAML), the language-agnostic
renderers, symbol search, and the CLI end-to-end. Fixtures live under `tests/fixtures/`;
tests never reach outside that directory.
New behaviour should come with a test; new languages should ship with a
dedicated fixture directory and a `tests/unit/test_<lang>_adapter.py` file.

### Adding a new language

Create `src/ast_outline/adapters/<lang>.py` implementing the
`LanguageAdapter` protocol (see `adapters/base.py`). Then register it in
`adapters/__init__.py`. The core renderers and CLI pick it up automatically
— no further wiring needed.

---

## Roadmap

- [x] TypeScript / JavaScript adapter (`.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs`)
- [x] Java adapter (`.java`) — classes, interfaces, `@interface`, enums, records, sealed hierarchies, generics, throws, Javadoc
- [x] Kotlin adapter (`.kt`, `.kts`) — classes, interfaces, `fun interface`, `object` / `companion object`, `data` / `sealed` / `enum` / `annotation` classes, extension functions, `suspend` / `inline` / `const` / `lateinit`, generics with `where` constraints, `typealias`, KDoc
- [x] Scala adapter (`.scala`, `.sc`) — Scala 2 + Scala 3: classes, traits, `object` / `case object`, `case class`, `sealed` hierarchies, Scala 3 `enum` / `given` / `using` / `extension`, indentation-based bodies, higher-kinded types, context bounds, `opaque type`, `type` aliases, Scaladoc
- [x] Go adapter (`.go`) — packages, structs (with method-grouping under receiver), interfaces, struct/interface embedding as inheritance, generics (Go 1.18+), `type` aliases + defined types, `iota` enum-blocks, doc-comment chains
- [x] Rust adapter (`.rs`) — modules (recursive), structs (regular / tuple / unit), unions, enums with all variant shapes, traits + supertraits as bases, **`impl` block regrouping under the target type** (inherent + `impl Trait for Foo` adds Trait to bases), `extern "C"` blocks, `macro_rules!`, type aliases, generics + lifetimes + `where` clauses, full visibility classifier (`pub` / `pub(crate)` / `pub(super)` / `pub(in path)`), outer doc comments + `#[...]` attributes
- [x] PHP adapter (`.php`, `.phtml`, `.phps`, `.php8`) — modern PHP 8.x + 7.4 LTS: namespaces (file-scoped + bracketed), classes (`abstract` / `final` / `readonly` and combinations), interfaces, traits, PHP 8.1 enums (pure + backed), methods, magic ctor / dtor, PHP 8.0 ctor property promotion, multi-variable properties, PHP 8.3 typed class constants, PHP 8.0 `#[Attr]` attributes, top-level `use` (incl. grouped) + `include` / `require`, robust on real WordPress core
- [x] Markdown adapter (`.md`, `.markdown`, `.mdx`, `.mdown`) — heading TOC + code blocks
- [x] YAML adapter (`.yaml`, `.yml`) — key hierarchy, `[i]` sequence paths, multi-document support, format-detect for Kubernetes / OpenAPI / GitHub Actions
- [ ] `--format json` output mode for programmatic consumers
- [ ] Optional multiprocessing for very large codebases (>500 files)

Contributions welcome.

---

## Project history

- **2026-04-22** — Repository created on GitHub as `dim-s/code-outline`. First public commit, v0.2.0b0.
- **2026-04-22** — Russian and Chinese READMEs added; TypeScript / JavaScript adapter shipped same day.
- **2026-04-23** — Kotlin adapter; `prompt` subcommand.
- **2026-04-24** — Scala adapter. **Renamed `code-outline` → `ast-outline` (v0.3.0).** GitHub repo renamed to `dim-s/ast-outline`.
- **2026-04-25** — Go adapter.
- **2026-04-28** — `# note: …` LLM-friendly error contract on stdout with `rc=0`; substring matching for markdown headings.
- **2026-04-30** — YAML adapter; per-file size labels + token estimate in digest headers; Rust adapter.
- **2026-05-01** — v0.4.0: digest method markers (`[async]` / `[unsafe]` / `[const]` / `[suspend]` / `[static]` / `[abstract]` / `[override]` / `[classmethod]` / `[property]`); type modifiers, attrs, and `[deprecated]` tag. v0.4.1.
- **2026-05-02** — Published to PyPI as [`ast-outline`](https://pypi.org/project/ast-outline/). v0.4.2 / v0.4.3 / v0.5.0 (`code-outline` CLI alias dropped) / v0.5.1 (`implements` command dropped — outline/digest already render `: Base`) / v0.5.2 (`--imports` flag) / v0.5.3 (`--version` flag).
- **2026-05-03** — **v0.6.0: relicense from MIT to Apache License 2.0**, with documentation separately licensed under CC BY 4.0. The previous MIT text is retained in `LICENSE-MIT` for compatibility with downstream forks of the 0.5.x tree.
- **2026-05-03** — Repository transferred from `dim-s/ast-outline` to the [`ast-outline`](https://github.com/ast-outline) GitHub Organization. Old `dim-s/ast-outline` URLs continue to redirect. Copyright remains with Dmitrii Zaitsev (dim-s); the GitHub org is hosting infrastructure, not a new copyright holder.
- **2026-05-03** — v0.6.2: PHP adapter (`.php`, `.phtml`, `.phps`, `.php8`) targeting modern PHP 8.x and the still-deployed 7.4 LTS line. Verified on real WordPress core (no parse errors on files up to 291 KB). Introduces `ParseResult.conditional_imports_count` — a common-IR counter for imports skipped because they live outside the file's static top level (e.g. WordPress `wp-load.php` whose every `require` lives in an `if`/`else` chain); renderers append `[+ N conditional includes]` to the imports line so agents see the file has dynamic dependencies. v0.6.3: counter extended to Python (lazy `import` inside fn / class), Rust (`use` inside `fn` / closures), and Scala (`import` inside method bodies).

For the full record, see `git log` and the [GitHub release page](https://github.com/ast-outline/ast-outline/releases).

---

## Licensing & attribution

Copyright © 2026 **Dmitrii Zaitsev** (GitHub: [dim-s](https://github.com/dim-s)) and ast-outline contributors.

This project uses **two separate licenses** for two different kinds of work:

| What | License | File |
| --- | --- | --- |
| **Source code** (`src/`, tests, build config) — v0.6.0 and later | [Apache 2.0](./LICENSE) | `LICENSE` |
| **Source code** — v0.5.3 and earlier | [MIT](./LICENSE-MIT) | `LICENSE-MIT` |
| **Documentation & prose** (this README, translated READMEs, CLI help text, prompt files, digest legend, design docs) | [CC BY 4.0](./LICENSE-DOCS) | `LICENSE-DOCS` |

All three are permissive — you can fork, use commercially, port to other languages, ship in a product. The split exists so that **attribution requirements are explicit** for each kind of content. Forks of the 0.5.x tree may continue under MIT; new development happens under Apache 2.0.

### If you reuse the code (v0.6.0+)

Keep the `LICENSE` (Apache 2.0) and `NOTICE` files in your distribution. Apache 2.0 §4 requires you to:

- include the `LICENSE` file
- include the `NOTICE` file in any "NOTICE" text file distributed with your work
- carry forward attribution notices (do not strip the copyright header)
- in modified files, add a notice stating that you changed the files

### If you reuse the prose

If your project copies non-trivial portions of this documentation — paragraphs, the workflow snippets, the digest legend, the marker vocabulary, the `# note:` CLI convention's wording — CC BY 4.0 requires **visible attribution**. Use this format (verbatim or equivalent):

> Based on [ast-outline](https://github.com/ast-outline/ast-outline) by Dmitrii Zaitsev (dim-s), licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

Place it where users will see it (typically the README of your derivative work).

### Trademark

**ast-outline™** is an unregistered trademark of Dmitrii Zaitsev (dim-s), used to identify the original project at <https://github.com/ast-outline/ast-outline>. Apache License 2.0 §6 explicitly excludes any grant of trademark rights. **Forks, language ports, and rebranded distributions must use a different name** to avoid user confusion. "Inspired by ast-outline" or "based on ast-outline" wording in your README is fine and encouraged; using `ast-outline` itself as your project / package / binary name is not.

If you maintain a published package called `ast-outline` on any registry (crates.io, npm, PyPI, Homebrew, etc.) that is not the project at the URL above, please rename it.
