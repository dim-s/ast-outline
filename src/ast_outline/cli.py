"""CLI entry point for ast-outline (legacy name: code-outline)."""
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
    find_implementations,
    find_symbols,
    render_digest,
    render_outline,
)


SUBCOMMANDS = {"outline", "show", "help", "digest", "implements", "prompt"}


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        _print_guide()
        return 0
    if argv[0] not in SUBCOMMANDS and not argv[0].startswith("-"):
        argv = ["outline", *argv]

    parser = argparse.ArgumentParser(
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

    p_impl = sub.add_parser("implements", help="Find types inheriting/implementing a given type")
    p_impl.add_argument("type", help="Target type name, e.g. `IDamageable`")
    p_impl.add_argument("paths", nargs="+", help="Directories or files to search")
    p_impl.add_argument(
        "--direct",
        "-d",
        action="store_true",
        help="Show only direct subclasses / implementations (skip transitive)",
    )

    p_help = sub.add_parser("help", help="Show usage guide with examples")
    p_help.add_argument(
        "topic",
        nargs="?",
        choices=["outline", "show", "digest", "implements", "prompt"],
        help="Topic-specific help",
    )

    sub.add_parser(
        "prompt",
        help="Print the canonical copy-paste agent prompt snippet (English, universal)",
    )

    args = parser.parse_args(argv)

    if args.cmd == "help":
        _print_guide(getattr(args, "topic", None))
        return 0
    if args.cmd == "show":
        return _cmd_show(args)
    if args.cmd == "digest":
        return _cmd_digest(args)
    if args.cmd == "implements":
        return _cmd_implements(args)
    if args.cmd == "prompt":
        return _cmd_prompt(args)
    return _cmd_outline(args)


def _cmd_prompt(_args) -> int:
    """Print the canonical copy-paste LLM-agent prompt snippet verbatim.

    No trailing newline muting — `print` adds one, matching the shape
    expected by shell pipelines like `ast-outline prompt >> AGENTS.md`.
    """
    # AGENT_PROMPT ends with `\n` already; `print` adds another → a
    # single blank separator line, which is what agent-config files want.
    print(AGENT_PROMPT, end="")
    return 0


def _add_outline_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("paths", nargs="+", help="Files or directories to outline")
    p.add_argument("--no-private", action="store_true")
    p.add_argument("--no-fields", action="store_true")
    p.add_argument("--no-docs", action="store_true")
    p.add_argument("--no-attrs", action="store_true")
    p.add_argument("--no-lines", action="store_true")
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
        print("No input files. Try: ast-outline Player.cs", file=sys.stderr)
        return 2

    opts = OutlineOptions(
        include_private=not args.no_private,
        include_fields=not args.no_fields,
        include_xml_doc=not args.no_docs,
        include_attributes=not args.no_attrs,
        include_line_numbers=not args.no_lines,
    )

    results, errors = _parse_paths([Path(p) for p in paths_raw], glob=args.glob)
    if not results and not errors:
        print(
            f"No files found matching supported extensions: {sorted(supported_extensions())}",
            file=sys.stderr,
        )
        return 2

    for i, r in enumerate(results):
        if i > 0:
            print()
        print(render_outline(r, opts))
    for f, e in errors:
        print(f"# ERROR processing {f}: {e}", file=sys.stderr)
    return 0


def _cmd_show(args) -> int:
    path = Path(args.file)
    if not path.is_file():
        print(f"File not found: {path}", file=sys.stderr)
        return 2
    adapter = get_adapter_for(path)
    if adapter is None:
        print(f"No adapter for extension {path.suffix}", file=sys.stderr)
        return 2
    try:
        result = adapter.parse(path)
    except Exception as e:
        print(f"# ERROR parsing {path}: {e}", file=sys.stderr)
        return 2

    any_found = False
    first = True
    for symbol in args.symbols:
        matches = find_symbols(result, symbol)
        if not matches:
            print(f"# Symbol not found: {symbol} in {path}", file=sys.stderr)
            continue
        any_found = True
        if len(matches) > 1:
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
    return 0 if any_found else 1


def _cmd_digest(args) -> int:
    paths = [Path(p) for p in args.paths]
    missing = [p for p in paths if not p.exists()]
    if missing:
        for p in missing:
            print(f"Path not found: {p}", file=sys.stderr)
        return 2
    opts = DigestOptions(
        include_private=args.include_private,
        include_fields=args.include_fields,
        max_members_per_type=args.max_members,
    )
    results, errors = _parse_paths(paths)
    if not results and not errors:
        print("# no supported files found", file=sys.stderr)
        return 2
    print(render_digest(results, opts), end="")
    for f, e in errors:
        print(f"# ERROR processing {f}: {e}", file=sys.stderr)
    return 0


def _cmd_implements(args) -> int:
    paths = [Path(p) for p in args.paths]
    missing = [p for p in paths if not p.exists()]
    if missing:
        for p in missing:
            print(f"Path not found: {p}", file=sys.stderr)
        return 2
    results, errors = _parse_paths(paths)
    for f, e in errors:
        print(f"# WARN parsing {f}: {e}", file=sys.stderr)
    transitive = not args.direct
    matches = find_implementations(results, args.type, transitive=transitive)
    if not matches:
        scope = "direct " if args.direct else ""
        print(
            f"# No {scope}implementations/subclasses of '{args.type}' found.",
            file=sys.stderr,
        )
        return 1
    scope_label = "direct match(es)" if args.direct else "match(es)"
    suffix = "" if args.direct else " (incl. transitive)"
    print(f"# {len(matches)} {scope_label} for '{args.type}'{suffix}:")
    for m in matches:
        bases = ", ".join(m.bases)
        line = f"{m.path}:{m.start_line}  {m.kind} {m.name} : {bases}"
        # Annotate transitive matches with the chain from the target's
        # first direct subclass down to this match's immediate parent.
        if m.via:
            line += f"          [via {' → '.join(m.via)}]"
        print(line)
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

COMMANDS
    ast-outline outline <paths...>          Print outline of files or dirs
    ast-outline show <file> <symbols...>    Print source of one or more symbols
    ast-outline digest <paths...>           Compact public-API map of a dir
    ast-outline implements <type> <paths>   Find subclasses/implementations
    ast-outline prompt                      Print the canonical agent prompt snippet
    ast-outline help [topic]                Show this guide (or topic-specific)

QUICK EXAMPLES
    ast-outline Player.cs
    ast-outline services/user_service.py
    ast-outline Assets/Scripts --no-private --no-fields
    ast-outline show Player.cs TakeDamage Heal
    ast-outline show user_service.py UserService.get_by_id
    ast-outline digest Assets/Scripts
    ast-outline digest scripts/
    ast-outline implements IDamageable Assets/Scripts
    ast-outline implements BaseValidator scripts/

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
    2. Looking for "who implements/extends X?" — use `implements`, not grep.
    3. Symbol matching is suffix-based: `Foo.Bar` matches `*.Foo.Bar`.
    4. Use `--no-private --no-fields` for a pure public-API view.
"""

GUIDE_OUTLINE = """\
ast-outline outline — structural overview of source files

USAGE
    ast-outline outline <paths...> [flags]
    ast-outline <paths...> [flags]

SUPPORTED
    C# (.cs), Python (.py, .pyi), TypeScript/JavaScript (.ts/.tsx/.js/.jsx),
    Java (.java), Kotlin (.kt, .kts), Scala (.scala, .sc), Go (.go),
    Markdown (.md)

FLAGS
    --no-private    Hide private members (Python: names starting with _)
    --no-fields     Hide field / variable declarations
    --no-docs       Hide doc comments (/// XML-doc or docstrings)
    --no-attrs      Hide [Attributes] / @decorators
    --no-lines      Hide line number suffixes
    --glob PATTERN  Custom glob for directory mode (default: all supported)

EXAMPLES
    ast-outline Foo.cs
    ast-outline service.py
    ast-outline src/ --no-private --no-fields --no-attrs
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

MULTIPLE SYMBOLS
    Pass several names in one call:
        ast-outline show Player.cs TakeDamage Heal Die
        ast-outline show user_service.py get_by_id create update

BEHAVIOR
    - One match: prints its source (including preceding doc).
    - Multiple matches for a name (overloads, same name in different classes):
      all are printed, summary on stderr.
    - Exit code 1 only when NONE of the requested symbols matched.

FLAGS
    --no-doc    Strip leading /// or docstring block from output
"""

GUIDE_DIGEST = """\
ast-outline digest — compact public-API map of a directory

USAGE
    ast-outline digest <paths...> [flags]

WHAT IT DOES
    Walks directory, lists every source file as:
      <file>  (N lines)
        <kind> <Name>[ : <bases>]  L<start>-<end>
          +method1  +method2  +property [prop]  ...
    One-page architecture view of a whole module in a single call.

FLAGS
    --include-private   Include private members (Python: `_`-prefixed)
    --include-fields    Include fields / module-level assignments
    --max-members N     Truncate long member lists (default: 50)

EXAMPLES
    ast-outline digest Assets/Scripts
    ast-outline digest scripts/
    ast-outline digest src/Services src/Domain
"""

GUIDE_IMPLEMENTS = """\
ast-outline implements — find subclasses / implementations of a type

USAGE
    ast-outline implements <TypeName> <paths...> [--direct]

WHAT IT DOES
    AST-based search across every parsed file for classes / structs /
    records / interfaces that inherit or implement <TypeName>. Matching
    is done by the last segment with generics stripped — so `IDamageable`
    matches `Game.Combat.IDamageable<T>`.

    Python: works for `class Foo(Bar):` — the argument list is treated
    as the base list.

    Transitive by default: `Puppy extends Dog extends Animal` — searching
    `Animal` returns Dog AND Puppy (the latter tagged `[via Dog]`).
    Add --direct / -d to restrict to first-level subclasses only.

    Search walks across any number of files and nested directories —
    no reliance on filename↔classname convention.

EXAMPLES
    ast-outline implements IDamageable Assets/Scripts
    ast-outline implements MonoBehaviour Assets/Scripts/App/Audio
    ast-outline implements --direct BaseService src/
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
    elif topic == "implements":
        print(GUIDE_IMPLEMENTS)
    elif topic == "prompt":
        print(GUIDE_PROMPT)
    else:
        print(GUIDE_GENERAL)


if __name__ == "__main__":
    raise SystemExit(main())
