# Changelog

All notable changes to this project are documented here. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

For the complete history before v0.6.0, see `git log` and the
[GitHub release page](https://github.com/ast-outline/ast-outline/releases).

## [0.6.5] — 2026-05-03

### Changed

- Agent-prompt snippet (`ast-outline prompt`, README copy, localized
  READMEs) is now explicitly cross-vendor — Claude Opus 4.7 / Sonnet
  4.6 / Haiku 4.5 **and** OpenAI GPT-5.x (5.3-codex / 5.4 / 5.5).
  Reworded the lead-in of the broad-to-narrow command list from
  "Stop at the step that answers the question" to "Pick the smallest
  of these that answers your question — they're a menu, not a
  sequence; skip straight to `show` when you already know the
  symbol." OpenAI's GPT-5.5 prompt-guide flags numbered step lists
  as interference; the new wording keeps the same meaning while
  reading as a decision tree on both vendors. Module docstring of
  `_prompt.py` now lists the cross-vendor invariants future edits
  must keep intact (no aggressive emphasis, no persona, no "think
  step by step", explicit fallbacks, no model-name pinning).

## [0.6.4] — 2026-05-03

### Fixed

- `outline` and `digest` no longer produce empty stdout when **every**
  file in a batch fails to parse. Previously per-file `# WARN`
  diagnostics went only to stderr, so an LLM agent (which reads
  stdout) saw `(no output)` and had no idea what happened. The CLI
  now prints one `# note: parse error in <path>: <err>` line per
  failed file on stdout — matching the existing convention for
  user-facing failures (path-not-found, no-adapter, etc.) — while
  the detailed `# WARN` lines still go to stderr for humans.
  Partial-failure batches (some files succeed) keep the existing
  behavior: clean outline on stdout, warnings on stderr.

## [0.6.3] — 2026-05-03

### Added

- `conditional_imports_count` is now populated by the **Python**,
  **Rust**, and **Scala** adapters in addition to PHP. The counter
  surfaces imports the adapter intentionally skipped because they
  live outside the file's static top level:
  - **Python**: `import` / `from ... import` inside a
    `function_definition` / `async_function_definition` /
    `class_definition` body. Lazy imports for circular-deps
    avoidance and class-namespace-scoped imports both count.
    Top-level `if TYPE_CHECKING:` and `try/except` import-fallbacks
    are still surfaced as static (unchanged).
  - **Rust**: `use` and `extern crate` inside `fn` bodies and
    closures. Nested `mod foo { use ... }` is NOT counted — that
    `use` belongs to the inner module's surface, not the parent
    file's.
  - **Scala**: `import` inside `function_definition` bodies (the
    concrete `def m = ...` variant; abstract `def m: T` has no body
    and can't host an `import`). Imports inside `object` / `class`
    / `trait` bodies are NOT counted — they're scoped but eager
    (load-time), not runtime.
- Java, Go, Kotlin, C#, and TypeScript leave the counter at `0` —
  their import grammars allow only top-level imports (or, for
  TypeScript ES modules, top-level only by spec; CommonJS
  `require()` is a separate concern not yet handled).

## [0.6.2] — 2026-05-03

### Added

- **PHP language adapter** (`tree-sitter-php`). Targets modern PHP 8.x
  and the still-widely-deployed 7.4 line. Recognised constructs:
  - `namespace Foo;` (file-scoped) and `namespace Foo { ... }`
    (bracketed, including the unnamed global block);
  - `class` / `abstract class` / `final class` / `readonly class` /
    `final readonly class` / `abstract readonly class`;
  - `interface` (with multi-`extends`), `trait` (mapped to
    `KIND_INTERFACE` with `native_kind="trait"` for cross-language
    search uniformity, mirroring Scala / Rust);
  - PHP 8.1 `enum` — both pure (`enum Color`) and backed
    (`enum Status: string`);
  - methods, abstract methods, `__construct` → `KIND_CTOR`,
    `__destruct` → `KIND_DTOR`;
  - PHP 8.0 constructor property promotion — promoted parameters are
    surfaced as implicit `KIND_FIELD` entries on the enclosing type
    (mirrors Kotlin's primary-ctor `val`/`var` promotion);
  - properties (single + multi-variable: `public $a, $b;`);
  - PHP 7.1+ class constants with explicit visibility, PHP 8.3 typed
    class constants (`public const string FOO = "bar"`);
  - top-level `function` and `const` declarations;
  - PHP 8.0 attributes (`#[Attr]` / `#[Attr(args)]`) collected into
    `attrs` and stripped from rendered signatures.
- File extensions handled: `.php`, `.phtml`, `.phps`, `.php8`.
- Imports: `use App\Foo`, `use App\Foo as Bar`, `use function f`,
  `use const C`, and grouped imports `use App\{A, B as Bb}` —
  group form is expanded so each `imports` entry is a single
  source-true `use ...` statement. `use` declarations inside
  bracketed namespaces are also collected.
- Pre-Composer / WordPress / Drupal-7-style legacy code uses
  `require[_once]` / `include[_once]` as the only dependency
  mechanism, so top-level `include` / `include_once` / `require` /
  `require_once` statements are also emitted as imports — preserving
  source-true expression text including computed paths
  (`require_once ABSPATH . 'wp-config.php'`). Collection is
  deliberately limited to **direct top-level statements** (children
  of `program` plus the body of bracketed namespaces). Conditional
  includes inside `if` / `try` / `switch` / `match` / loop bodies are
  out of scope, matching how every other adapter handles conditional
  imports (Python `try/except` fallbacks, `if TYPE_CHECKING`, etc.).
  `use` and `require` entries appear in source order.

### Added — common IR

- `ParseResult.conditional_imports_count: int` (default `0`) — count
  of imports the adapter intentionally skipped because they live
  outside the file's static top level. Renderers append
  `[+ 1 conditional include]` (singular) or
  `[+ N conditional includes]` (plural) to the `imports:` line when
  this is non-zero, so an agent reading a WordPress `wp-load.php`
  (whose every `require` lives in an `if`/`else` chain) sees
  `imports: [+ 6 conditional includes]` instead of an empty imports
  list — clear signal that more dependencies exist but require
  reading the file directly. Currently populated only by the PHP
  adapter; other adapters leave it at `0` (their imports are
  top-level by spec — Java, Go, C#, Kotlin, Scala — or already
  collect conditional cases like Python's `try/except` fallback).

## [0.6.1] — 2026-05-03

### Changed

- **Repository transferred** from `dim-s/ast-outline` to the
  [`ast-outline`](https://github.com/ast-outline) GitHub Organization.
  Old `dim-s/ast-outline` URLs continue to redirect.
- All canonical project URLs in `pyproject.toml`, CLI `--version`
  output, install scripts, README × 3 attribution templates, NOTICE,
  and LICENSE-DOCS updated to the new home.
- No code or behavior changes. This release exists solely to refresh
  PyPI metadata (which is frozen per-version on upload).

### Unchanged

- **Copyright** remains with Dmitrii Zaitsev (dim-s) and ast-outline
  contributors. The GitHub Organization is hosting infrastructure,
  not a new copyright holder.
- **Trademark** `ast-outline™` continues to be held by Dmitrii Zaitsev.
- Priority date for the project (2026-04-22, first public commit at
  `dim-s/ast-outline`) is unaffected and recorded in `NOTICE`.

## [0.6.0] — 2026-05-03

### License change

This release **relicenses the project from MIT to Apache License,
Version 2.0**. Documentation is separately licensed under CC BY 4.0.

| What | License | File |
| --- | --- | --- |
| Source code (v0.6.0+) | [Apache 2.0](./LICENSE) | `LICENSE` |
| Source code (v0.5.3 and earlier) | [MIT](./LICENSE-MIT) | `LICENSE-MIT` |
| Documentation & prose | [CC BY 4.0](./LICENSE-DOCS) | `LICENSE-DOCS` |

The previous MIT text is retained in `LICENSE-MIT` for compatibility
with downstream forks of the 0.5.x tree. Versions 0.5.3 and earlier
remain available on PyPI under their original MIT terms.

### Why

Apache License 2.0 provides three protections that MIT does not:

- **§4(b)** — modified files must carry a notice that they were changed,
  which makes ports and derivative works traceable;
- **§4(c)** — redistributions must include the `NOTICE` file, which
  carries forward original attribution;
- **§6** — explicit exclusion of any trademark grant. The project name
  *ast-outline* is now an unregistered trademark (™) of Dmitrii Zaitsev
  (dim-s); forks, language ports, and rebranded distributions must use a
  different name.

The change also adds an explicit patent grant (§3) which auto-terminates
on patent litigation against the project.

### Impact on existing users

- **End users running `ast-outline` from PyPI / brew:** none. CLI
  behavior is unchanged.
- **Forks / packagers:** the 0.5.x tree remains under MIT and is fully
  forkable; v0.6.0+ requires Apache 2.0 compliance (carry `LICENSE` and
  `NOTICE`).
- **Downstream projects copying code:** Apache 2.0 is compatible with
  most permissive workflows (MIT, BSD, ISC); upstreaming Apache code into
  GPLv2-only projects is not allowed by FSF, but GPLv3 is fine.

### Other changes

- Added `LICENSE-MIT` (preserves prior MIT text).
- Added `LICENSE-DOCS` (CC BY 4.0 for prose).
- Added `NOTICE` (Apache-style attribution + trademark statement).
- `pyproject.toml`: `license = { text = "Apache-2.0" }`,
  `License :: OSI Approved :: Apache Software License` classifier,
  Dmitrii Zaitsev added to `authors`, sdist now ships `LICENSE-MIT`,
  `LICENSE-DOCS`, `NOTICE`, `CHANGELOG.md`.
- README (en/ru/zh-CN): added "Project history" section, "Licensing &
  attribution" section with the three-license matrix, trademark notice.

[0.6.0]: https://github.com/ast-outline/ast-outline/releases/tag/v0.6.0
[0.6.1]: https://github.com/ast-outline/ast-outline/releases/tag/v0.6.1
