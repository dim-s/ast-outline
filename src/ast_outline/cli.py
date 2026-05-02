"""CLI entry point for ast-outline.

Error-handling philosophy
-------------------------
This CLI is consumed primarily by LLM agents (Claude Code, Cursor, etc.).
In those harnesses, a non-zero exit code from one tool call can fail the
whole parallel batch of bash invocations. So we deliberately do NOT use
exit codes to signal "no match" or "file not found" — instead we print a
short ``# note: ...`` line on stdout (the channel the agent reads as the
answer) and return 0. Real internal crashes still propagate normally.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ._prompt import AGENT_PROMPT
from .adapters import collect_files, get_adapter_for, supported_extensions
from .core import (
    DigestOptions,
    OutlineOptions,
    ParseResult,
    find_symbols,
    render_digest,
    render_outline,
)


SUBCOMMANDS = {"outline", "show", "help", "digest", "prompt"}


class _LLMArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that doesn't ``sys.exit`` on bad args.

    Default ``argparse`` behavior on bad arguments is to print to stderr
    and call ``sys.exit(2)``. For an LLM-facing CLI that breaks parallel
    bash chains in Claude Code. Instead we raise a sentinel exception
    that ``main()`` turns into a short ``# note:`` line on stdout +
    ``return 0``.
    """

    def error(self, message: str) -> None:  # type: ignore[override]
        raise _ArgParseFail(message)

    def exit(self, status: int = 0, message: str | None = None) -> None:  # type: ignore[override]
        # ``--help`` flows through ``exit(0, None)`` after print_help — let
        # those through. Anything else (status != 0) is an arg failure.
        if status == 0:
            raise SystemExit(0)
        raise _ArgParseFail(message or f"argument error (status={status})")


class _ArgParseFail(Exception):
    """Raised by _LLMArgumentParser instead of sys.exit on bad args."""


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        _print_guide()
        return 0
    # Standalone `--version` / `-V` follows the universal CLI convention
    # (`git --version`, `python --version`, `rg --version`). We handle it
    # before argparse subcommand dispatch so the user doesn't need to
    # spell out a subcommand for a one-line capability check.
    if argv[0] in ("--version", "-V"):
        return _cmd_version(None)
    if argv[0] not in SUBCOMMANDS and not argv[0].startswith("-"):
        argv = ["outline", *argv]

    parser = _LLMArgumentParser(
        # `prog` is intentionally left unset so argparse picks up the actual
        # invoked binary name from sys.argv[0]. That way `ast-outline foo.py`
        # surfaces `ast-outline: error: ...` and the backward-compat
        # `ast-outline foo.py` alias still shows its own name — zero
        # confusion for existing users during the rebrand window.
        description="AST-based structural outline for source files. Signatures with line numbers — no method bodies.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_outline = sub.add_parser("outline", help="Print structural outline (default)")
    _add_outline_args(p_outline)

    p_show = sub.add_parser("show", help="Print source of one or more symbols")
    p_show.add_argument("file", help="Source file")
    p_show.add_argument("symbols", nargs="+", help="Symbol name(s), e.g. `TakeDamage Heal`")
    p_show.add_argument("--no-doc", action="store_true", help="Strip leading doc comments from output")

    p_digest = sub.add_parser("digest", help="Compact public-API map of a directory")
    p_digest.add_argument("paths", nargs="+", help="Directories or files")
    p_digest.add_argument("--include-private", action="store_true")
    p_digest.add_argument("--include-fields", action="store_true")
    p_digest.add_argument("--max-members", type=int, default=50)
    p_digest.add_argument(
        "--imports",
        action="store_true",
        help="Show each file's import / use / using statements as a header line",
    )

    p_help = sub.add_parser("help", help="Show usage guide with examples")
    p_help.add_argument(
        "topic",
        nargs="?",
        choices=["outline", "show", "digest", "prompt"],
        help="Topic-specific help",
    )

    sub.add_parser(
        "prompt",
        help="Print the canonical copy-paste agent prompt snippet (English, universal)",
    )

    try:
        args = parser.parse_args(argv)
    except _ArgParseFail as e:
        # Bad CLI usage. Surface it as the LLM's response on stdout and
        # exit cleanly so a parallel batch isn't aborted by exit code 2.
        print(f"# note: {e}")
        return 0

    if args.cmd == "help":
        _print_guide(getattr(args, "topic", None))
        return 0
    if args.cmd == "show":
        return _cmd_show(args)
    if args.cmd == "digest":
        return _cmd_digest(args)
    if args.cmd == "prompt":
        return _cmd_prompt(args)
    return _cmd_outline(args)


def _cmd_version(_args) -> int:
    """Print version + authorship in the standard `tool x.y.z` form
    plus a one-line author / project-URL block. Matches the convention
    used by `git --version`, `python --version`, `rg --version`, etc.,
    so an LLM (or human) can grep `ast-outline version` for the same
    fields without parsing prose."""
    from . import __version__
    print(f"ast-outline {__version__}")
    print("author: Dmitrii Zaitsev <zayceffdev@gmail.com>")
    print("homepage: https://github.com/dim-s/ast-outline")
    print("license: MIT")
    return 0


def _cmd_prompt(_args) -> int:
    """Print the canonical copy-paste LLM-agent prompt snippet verbatim."""
    # AGENT_PROMPT already terminates with `\n`. `end=""` suppresses
    # `print`'s extra newline, so stdout receives exactly the snippet
    # text + a single trailing `\n`. Matches the shape expected by
    # shell pipelines (`ast-outline prompt >> AGENTS.md` appends one
    # newline; the user inserts a blank separator line by hand if they
    # want one between existing content and the snippet).
    print(AGENT_PROMPT, end="")
    return 0


def _add_outline_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("paths", nargs="+", help="Files or directories to outline")
    p.add_argument("--no-private", action="store_true")
    p.add_argument("--no-fields", action="store_true")
    p.add_argument("--no-docs", action="store_true")
    p.add_argument("--no-attrs", action="store_true")
    p.add_argument("--no-lines", action="store_true")
    p.add_argument(
        "--imports",
        action="store_true",
        help="Show each file's import / use / using statements as a header line",
    )
    p.add_argument("--glob", default=None, help="Custom glob for directory mode (default: all supported extensions)")


def _parse_paths(paths: list[Path], glob: str | None = None) -> tuple[list[ParseResult], list[tuple[Path, Exception]]]:
    """Parse every supported file under the given paths."""
    files = collect_files(paths, glob=glob)
    results: list[ParseResult] = []
    errors: list[tuple[Path, Exception]] = []
    for f in files:
        adapter = get_adapter_for(f)
        if adapter is None:
            continue  # silently skip unsupported extensions
        try:
            results.append(adapter.parse(f))
        except Exception as e:
            errors.append((f, e))
    return results, errors


def _cmd_outline(args) -> int:
    paths_raw = getattr(args, "paths", None) or []
    if not paths_raw:
        # `# note:` lines go on stdout because they ARE the response to the
        # agent — there's no successful outline to keep clean of warnings.
        print("# note: no input files. try: ast-outline Player.cs")
        return 0

    paths = [Path(p) for p in paths_raw]
    missing = [p for p in paths if not p.exists()]
    if missing:
        for p in missing:
            print(f"# note: path not found: {p}")
        return 0

    opts = OutlineOptions(
        include_private=not args.no_private,
        include_fields=not args.no_fields,
        include_xml_doc=not args.no_docs,
        include_attributes=not args.no_attrs,
        include_line_numbers=not args.no_lines,
        show_imports=args.imports,
    )

    results, errors = _parse_paths(paths, glob=args.glob)
    if not results and not errors:
        exts = sorted(supported_extensions())
        print(
            f"# note: no files found matching supported extensions: {exts}"
        )
        return 0

    for i, r in enumerate(results):
        if i > 0:
            print()
        print(render_outline(r, opts))
    # Per-file parse errors are warnings inside a successful batch — we
    # keep them on stderr so stdout (the LLM's primary channel) holds
    # only the actual outline content.
    for f, e in errors:
        print(f"# WARN processing {f}: {e}", file=sys.stderr)
    return 0


def _cmd_show(args) -> int:
    path = Path(args.file)
    if not path.is_file():
        print(f"# note: file not found: {path}")
        return 0
    adapter = get_adapter_for(path)
    if adapter is None:
        print(f"# note: no adapter for extension {path.suffix}")
        return 0
    try:
        result = adapter.parse(path)
    except Exception as e:
        print(f"# note: parse error in {path}: {e}")
        return 0

    first = True
    for symbol in args.symbols:
        matches = find_symbols(result, symbol)
        if not matches:
            # Each requested symbol gets its own line. We use stdout — the
            # LLM is iterating over these to assemble its answer; it should
            # see "not found" inline next to the matches that did succeed.
            print(f"# note: symbol not found: {symbol} in {path}")
            continue
        if len(matches) > 1:
            # Disambiguation summary — informational, but still useful for
            # the agent to see alongside the bodies it's about to read.
            print(f"# {len(matches)} matches for '{symbol}' in {path}:", file=sys.stderr)
            for m in matches:
                print(f"#   {m.qualified_name}  L{m.start_line}-{m.end_line}  ({m.kind})", file=sys.stderr)
            print(file=sys.stderr)
        for m in matches:
            if not first:
                print()
            first = False
            src = m.source
            if args.no_doc:
                src = _strip_leading_doc(src)
            print(f"# {path}:{m.start_line}-{m.end_line}  {m.qualified_name}  ({m.kind})")
            # Breadcrumb: show the enclosing namespace/class chain so the agent
            # knows what the extracted body is nested inside — without having
            # to call `outline` separately. Skipped for top-level symbols.
            if m.ancestor_signatures:
                chain = " → ".join(m.ancestor_signatures)
                print(f"# in: {chain}")
            print(src)
    return 0


def _cmd_digest(args) -> int:
    paths = [Path(p) for p in args.paths]
    missing = [p for p in paths if not p.exists()]
    if missing:
        for p in missing:
            print(f"# note: path not found: {p}")
        return 0
    opts = DigestOptions(
        include_private=args.include_private,
        include_fields=args.include_fields,
        max_members_per_type=args.max_members,
        show_imports=args.imports,
    )
    results, errors = _parse_paths(paths)
    if not results and not errors:
        print("# note: no supported files found")
        return 0
    print(render_digest(results, opts), end="")
    # Per-file parse errors are warnings on a successful batch — stderr.
    for f, e in errors:
        print(f"# WARN processing {f}: {e}", file=sys.stderr)
    return 0


def _strip_leading_doc(src: str) -> str:
    """Strip the doc block from a `show` source slice.

    Two shapes we handle:
    - C# style: one or more ``///`` lines at the top of the slice.
    - Python style: a ``def`` / ``class`` / decorator header followed by a
      triple-quoted docstring as the first body statement.
    """
    lines = src.splitlines()

    # C#: strip any leading /// comment lines.
    i = 0
    while i < len(lines) and lines[i].lstrip().startswith("///"):
        i += 1
    if i > 0:
        return "\n".join(lines[i:])

    # Python: skip decorators + def/class header, then drop the docstring if
    # it's the first body statement.
    j = 0
    while j < len(lines) and lines[j].lstrip().startswith("@"):
        j += 1
    if j < len(lines):
        header = lines[j].lstrip()
        if header.startswith(("def ", "async def ", "class ")):
            k = j + 1
            while k < len(lines) and not lines[k].strip():
                k += 1
            if k < len(lines):
                doc_line = lines[k].lstrip()
                for delim in ('"""', "'''"):
                    if doc_line.startswith(delim):
                        rest = doc_line[3:]
                        if delim in rest:
                            # Single-line docstring
                            return "\n".join(lines[:k] + lines[k + 1 :])
                        # Multi-line: find closing delim
                        end = k + 1
                        while end < len(lines) and delim not in lines[end]:
                            end += 1
                        return "\n".join(lines[:k] + lines[end + 1 :])
    return src


GUIDE_GENERAL = """\
ast-outline — structural outline for source files

WHAT IT DOES
    Prints class/method/function/field signatures with line numbers,
    WITHOUT method bodies. Typical output is 5–10× smaller than the source.
    Designed for LLM agents that need to understand a file's shape before
    reading (or editing) specific parts.

SUPPORTED LANGUAGES
    C#          .cs
    Python      .py, .pyi
    TypeScript  .ts, .tsx, .js, .jsx
    Java        .java
    Kotlin      .kt, .kts
    Scala       .scala, .sc
    Go          .go
    Markdown    .md
    YAML        .yaml, .yml

COMMANDS
    ast-outline outline <paths...>          Print outline of files or dirs
    ast-outline show <file> <symbols...>    Print source of one or more symbols
    ast-outline digest <paths...>           Compact public-API map of a dir
    ast-outline prompt                      Print the canonical agent prompt snippet
    ast-outline --version                   Print version + author
    ast-outline help [topic]                Show this guide (or topic-specific)

QUICK EXAMPLES
    ast-outline Player.cs
    ast-outline services/user_service.py
    ast-outline Assets/Scripts --no-private --no-fields
    ast-outline show Player.cs TakeDamage Heal
    ast-outline show user_service.py UserService.get_by_id
    ast-outline digest Assets/Scripts
    ast-outline digest scripts/

OUTPUT FORMAT
    # path/to/File.cs (N lines)
    namespace X.Y
        public class Foo : IBar  L10-120
            public int Count { get; private set; }  L15
            public void Do(int x)  L30-48

    For Python:
    # path/to/service.py (N lines)
    class UserService:  L8-120
        <docstring: "Handles user CRUD and auth flows.">
        def __init__(self, repo)  L12-14
        async def get_by_id(self, id: UUID) -> User  L18-28

    Each declaration shows: signature + line range `L<start>-<end>` (or `L<n>`
    for single-line items).

TIPS FOR LLM AGENTS
    1. Start broad → narrow:
         ast-outline digest <dir>        # architecture map of the module
         ast-outline <file>              # one file in detail
         ast-outline show <file> <Name>  # body of a specific symbol
    2. Symbol matching is suffix-based: `Foo.Bar` matches `*.Foo.Bar`.
    3. Use `--no-private --no-fields` for a pure public-API view.
"""

GUIDE_OUTLINE = """\
ast-outline outline — structural overview of source files

USAGE
    ast-outline outline <paths...> [flags]
    ast-outline <paths...> [flags]

SUPPORTED
    C# (.cs), Python (.py, .pyi), TypeScript/JavaScript (.ts/.tsx/.js/.jsx),
    Java (.java), Kotlin (.kt, .kts), Scala (.scala, .sc), Go (.go),
    Markdown (.md), YAML (.yaml, .yml)

FLAGS
    --no-private    Hide private members (Python: names starting with _)
    --no-fields     Hide field / variable declarations
    --no-docs       Hide doc comments (/// XML-doc or docstrings)
    --no-attrs      Hide [Attributes] / @decorators
    --no-lines      Hide line number suffixes
    --imports       Show file's imports (source-true, language-native)
    --glob PATTERN  Custom glob for directory mode (default: all supported)

EXAMPLES
    ast-outline Foo.cs
    ast-outline service.py
    ast-outline src/ --no-private --no-fields --no-attrs
    ast-outline service.py --imports     # add `# imports: ...` header
    ast-outline Foo.cs Bar.py   # mixed languages at once
"""

GUIDE_SHOW = """\
ast-outline show — extract source of one or more symbols

USAGE
    ast-outline show <file> <symbols...> [--no-doc]

SYMBOL SYNTAX
    Short name:      TakeDamage        get_by_id
    Class-scoped:    PlayerController.TakeDamage      UserService.get_by_id
    Fully-qualified: Game.Player.PlayerController.TakeDamage
    Matching is suffix-based — short name works unless ambiguous.

MARKDOWN HEADINGS — substring matching
    For .md files, headings match by case-insensitive substring of every
    dotted part. So `"current analysis"` finds
    `"1. CURRENT ANALYSIS (Feb 2026)"`, and `"intro.usage"` finds the
    nested heading `"Usage"` under any parent containing "intro".
    If the substring matches multiple headings, all are printed and a
    disambiguation summary lands on stderr — tighten the query to narrow.

MULTIPLE SYMBOLS
    Pass several names in one call:
        ast-outline show Player.cs TakeDamage Heal Die
        ast-outline show user_service.py get_by_id create update

BEHAVIOR
    - One match: prints its source (including preceding doc).
    - Multiple matches for a name (overloads, same name in different classes,
      or a markdown substring spanning several headings): all are printed,
      summary on stderr.
    - Always exits 0 — "not found" is printed as `# note: ...` on stdout
      so the LLM agent's parallel batch isn't aborted by an exit code.

FLAGS
    --no-doc    Strip leading /// or docstring block from output
"""

GUIDE_DIGEST = """\
ast-outline digest — compact public-API map of a directory

USAGE
    ast-outline digest <paths...> [flags]

WHAT IT DOES
    Walks directory, lists every source file as:
      # legend: name()=callable, name [kind]=non-callable, ...
      <file>  (N lines, ~tokens)
        [Attr] <modifiers> <kind> <Name> [deprecated][ : <bases>]  L<start>-<end>
          <marker> method1(), method2(), property [property], ...
    Output starts with a one-line legend so it is parseable cold.
    Callable names carry `()`; properties / fields / events show
    `[kind]`. Method markers (`async`, `static`, `abstract`,
    `override`, `virtual`, Kotlin `open` / `suspend`, Python
    `@staticmethod` / `@classmethod` / `@abstractmethod`, Java
    `@Override`) prefix the name source-true so each language reads
    in its own idiom. Same-name overloads collapse to
    `name() [N overloads]`. Type headers carry their decorators /
    attributes verbatim (`@dataclass`, `[Serializable]`,
    `#[derive(Debug)]`) plus semantic modifiers (`abstract`,
    `sealed`, `static`, `final`, `open`, `partial`). Anything
    marked deprecated / obsolete gets a trailing `[deprecated]` tag.
    Members are joined by `, `. Types with bodies get a trailing
    blank line; empty types stack tight.

FLAGS
    --include-private   Include private members (Python: `_`-prefixed)
    --include-fields    Include fields / module-level assignments
    --max-members N     Truncate long member lists (default: 50)
    --imports           Show each file's imports (source-true, language-native)

EXAMPLES
    ast-outline digest Assets/Scripts
    ast-outline digest scripts/
    ast-outline digest src/Services src/Domain
    ast-outline digest src/ --imports        # see what each file depends on
"""

GUIDE_PROMPT = """\
ast-outline prompt — print the canonical agent prompt snippet

USAGE
    ast-outline prompt

WHAT IT DOES
    Prints the copy-paste-ready markdown snippet that steers an LLM
    coding agent (Claude, Cursor, etc.) to prefer `ast-outline` over
    full-file reads. English, universal — calibrated to work across
    Claude Opus 4.7 / Sonnet 4.6 / Haiku 4.5 out of the box.

    The snippet ships with the tool so `ast-outline prompt` always
    emits the current recommended version, not a stale copy someone
    saved a year ago.

EXAMPLES
    # Append straight into a project's agent config
    ast-outline prompt >> AGENTS.md
    ast-outline prompt >> .claude/CLAUDE.md

    # Pipe into clipboard
    ast-outline prompt | pbcopy          # macOS
    ast-outline prompt | xclip -sel c    # Linux
"""

def _print_guide(topic: str | None = None) -> None:
    if topic == "outline":
        print(GUIDE_OUTLINE)
    elif topic == "show":
        print(GUIDE_SHOW)
    elif topic == "digest":
        print(GUIDE_DIGEST)
    elif topic == "prompt":
        print(GUIDE_PROMPT)
    else:
        print(GUIDE_GENERAL)


if __name__ == "__main__":
    raise SystemExit(main())
