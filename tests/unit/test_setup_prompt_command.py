"""Tests for the `ast-outline setup-prompt` subcommand and the
underlying SETUP_PROMPT constant in `ast_outline._setup_prompt`.

This subcommand prints a one-shot checklist that an LLM agent follows
to wire ast-outline into the current repo (version check, AGENTS.md
create/update, optional patch of existing exploration subagents).
Tests cover:

- The CLI command exits 0 and prints the snippet to stdout.
- Output is pure markdown (no ANSI noise) so the agent reading stdout
  receives clean instructions.
- `help setup-prompt` renders a topic-specific guide.
- The constant's content carries the load-bearing structural elements
  (idempotency markers, distinct steps, headless fallback, negative
  scopes). If a future edit accidentally drops one, the test fails.
"""
from __future__ import annotations

from ast_outline._setup_prompt import SETUP_PROMPT
from ast_outline.cli import main


# --- CLI end-to-end ------------------------------------------------------


def test_setup_prompt_command_exits_zero(capsys):
    rc = main(["setup-prompt"])
    assert rc == 0


def test_setup_prompt_command_prints_snippet(capsys):
    rc = main(["setup-prompt"])
    out = capsys.readouterr().out
    assert rc == 0
    assert out == SETUP_PROMPT


def test_setup_prompt_output_is_plain_markdown(capsys):
    """No ANSI escape codes — piping to a file or another agent must
    produce clean markdown."""
    main(["setup-prompt"])
    out = capsys.readouterr().out
    assert "\x1b[" not in out
    assert "\x1b]" not in out


def test_setup_prompt_output_is_idempotent(capsys):
    """Running the command twice produces the same output."""
    main(["setup-prompt"])
    first = capsys.readouterr().out
    main(["setup-prompt"])
    second = capsys.readouterr().out
    assert first == second


# --- help setup-prompt --------------------------------------------------


def test_help_setup_prompt_topic(capsys):
    rc = main(["help", "setup-prompt"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "ast-outline setup-prompt" in out
    assert "USAGE" in out
    assert "EXAMPLES" in out


def test_general_help_mentions_setup_prompt_command(capsys):
    main(["help"])
    out = capsys.readouterr().out
    assert "ast-outline setup-prompt" in out


# --- Snippet structural checks -----------------------------------------


def test_snippet_starts_with_markdown_h2():
    """Setup-prompt must open with an `## ...` heading so it slots
    cleanly into whatever wrapper the agent uses."""
    first_line = SETUP_PROMPT.splitlines()[0]
    assert first_line.startswith("## ")


def test_snippet_carries_idempotency_markers():
    """Every block we instruct the agent to insert is wrapped in these
    markers so re-runs replace in place. Drop them and re-runs would
    duplicate user content."""
    assert "<!-- ast-outline:start -->" in SETUP_PROMPT
    assert "<!-- ast-outline:end -->" in SETUP_PROMPT


def test_snippet_covers_version_check_step():
    """Step 1 is a version + update check — load-bearing because it's
    the only signal a user gets that their bundled snippet may be
    stale."""
    assert "ast-outline --version" in SETUP_PROMPT
    assert "PyPI" in SETUP_PROMPT
    assert "pip install -U ast-outline" in SETUP_PROMPT


def test_snippet_offers_install_method_choice():
    """When the CLI is missing, the prompt must present both install
    paths (global isolated vs project venv) — picking the wrong one
    silently is a real foot-gun for a CLI tool. uv is the recommended
    primary; pipx and project-venv pip are real alternatives."""
    assert "uv tool install ast-outline" in SETUP_PROMPT
    assert "pip install ast-outline" in SETUP_PROMPT
    assert "pipx install ast-outline" in SETUP_PROMPT
    # Per-install upgrade commands present so step 1.3 can tailor.
    assert "uv tool upgrade ast-outline" in SETUP_PROMPT
    assert "pipx upgrade ast-outline" in SETUP_PROMPT


def test_snippet_carries_environment_sensing_logic():
    """Environment detection (package manager + venv) must be present
    so the agent can default to the user's actual setup instead of
    asking blindly. The probes themselves are gated by relevance —
    only run when the CLI is missing or upgrade is requested — so we
    assert the *concepts* rather than verbatim `which uv` strings
    (the cross-OS note tells the agent to translate to whatever the
    user's shell needs)."""
    assert "uv" in SETUP_PROMPT
    assert "pipx" in SETUP_PROMPT
    # Venv detection signals.
    assert "VIRTUAL_ENV" in SETUP_PROMPT
    assert ".venv" in SETUP_PROMPT
    # Cross-OS guidance — the agent must adapt probe commands.
    lowered = SETUP_PROMPT.lower()
    assert "windows" in lowered or "powershell" in lowered or "cross-os" in lowered


def test_snippet_allows_agent_to_run_install_with_consent():
    """The agent may execute install / upgrade commands on the user's
    behalf, but only with explicit consent. Both flows must be named
    so a literal model picks the right one. Silent / inferred
    upgrades remain forbidden."""
    lowered = SETUP_PROMPT.lower()
    # Explicit-consent gate: the agent MAY run, only when asked.
    assert "explicitly" in lowered or "explicit" in lowered
    # The two flows are both named.
    assert "themselves" in lowered  # user runs it
    assert "for them" in lowered or "on their behalf" in lowered  # agent runs it
    # Silent upgrades remain forbidden.
    assert "silently" in lowered or "silent" in lowered


def test_snippet_carries_question_style_guidance():
    """User-facing questions should be short, plain, one-decision-at-
    a-time. Without explicit guidance, agents on dense models pile
    up multi-clause questions that confuse beginners. Show-the-
    command-before-running is the safety primitive that lets the
    user veto destructive runs at the last moment."""
    lowered = SETUP_PROMPT.lower()
    # Concise, beginner-friendly questions.
    assert "short" in lowered or "concise" in lowered or "plain" in lowered
    # Show command before running — the consent UX hook.
    assert "show" in lowered and "command" in lowered


def test_snippet_carries_language_adaptation_directive():
    """The agent must mirror the user's conversation language for both
    spoken replies AND any free-form prose it writes into
    AGENTS.md / CLAUDE.md (top headings, brief comments around the
    marker block). Without this, a Russian/Chinese/etc. user ends up
    with English wrapper text in their own project notes."""
    lowered = SETUP_PROMPT.lower()
    assert "language" in lowered
    assert "agents.md" in lowered
    assert "claude.md" in lowered


def test_snippet_pins_subagents_and_markers_to_english():
    """Two exceptions to the language-adaptation rule: (a) the marker-
    wrapped snippet block (from `ast-outline prompt`, calibrated for
    cross-vendor LLM reliability — translating breaks that), and (b)
    subagent files entirely, since their contents are LLM system
    prompts where English is the working surface. The directive must
    name both exceptions explicitly so a literal model (Opus 4.7,
    GPT-5.5) doesn't translate them by extension."""
    lowered = SETUP_PROMPT.lower()
    assert "verbatim" in lowered
    assert "subagent" in lowered
    # The snippet exception must reference the marker block, not just
    # generic "file contents", so the agent doesn't over-generalise.
    assert "ast-outline:start" in SETUP_PROMPT


def test_snippet_covers_agents_md_step():
    """The AGENTS.md install/update is the primary outcome — must be
    present along with the path-handling branches (missing / markers
    present / no markers)."""
    assert "AGENTS.md" in SETUP_PROMPT
    assert "ast-outline prompt" in SETUP_PROMPT


def test_snippet_covers_per_vendor_filename_logic():
    """The agent must know that AGENTS.md is the cross-tool default,
    but each frontier vendor has a native single-tool file:
    `./CLAUDE.md` (Claude Code), `./AGENTS.md` (Codex CLI),
    `./GEMINI.md` (Gemini CLI). Without this, single-vendor users
    end up with the wrong file or with a Gemini config caveat that
    leaves the snippet silently unloaded."""
    # All three native project-local files are named.
    assert "./CLAUDE.md" in SETUP_PROMPT
    assert "./AGENTS.md" in SETUP_PROMPT
    assert "./GEMINI.md" in SETUP_PROMPT
    # Gemini's settings.json caveat — without it, AGENTS.md is
    # invisible to Gemini CLI, the prompt must explain that.
    assert "settings.json" in SETUP_PROMPT
    assert "context.fileName" in SETUP_PROMPT or "fileName" in SETUP_PROMPT


def test_snippet_handles_codex_override_pattern():
    """Codex's `AGENTS.override.md` takes precedence over `AGENTS.md`.
    Writing to AGENTS.md when an override exists silently shadows the
    write. The prompt must check for the override and ask the user
    which file to update."""
    assert "AGENTS.override.md" in SETUP_PROMPT
    lowered = SETUP_PROMPT.lower()
    assert "shadow" in lowered or "precedence" in lowered or "override" in lowered


def test_snippet_offers_project_vs_global_scope():
    """Setup-prompt should let the user pick project-local (default)
    vs global scope. Without the choice, solo developers wanting
    cross-project ast-outline awareness either don't get it (we
    default to project-local) or are surprised when their global
    `~/.claude/CLAUDE.md` is overwritten silently."""
    lowered = SETUP_PROMPT.lower()
    assert "global" in lowered
    assert "project-local" in lowered
    # All three vendors' global files mentioned.
    assert "~/.claude/CLAUDE.md" in SETUP_PROMPT
    assert "~/.codex/AGENTS.md" in SETUP_PROMPT
    assert "~/.gemini/GEMINI.md" in SETUP_PROMPT


def test_snippet_headless_covers_all_vendors():
    """Headless example must not fixate one vendor — all three
    frontier CLIs have non-interactive modes (`codex exec`,
    `claude -p`, Gemini CLI's headless). Without naming each, users
    in CI on the other two vendors might think the rule does not
    apply to them."""
    assert "codex exec" in SETUP_PROMPT
    assert "claude -p" in SETUP_PROMPT
    assert "Gemini CLI" in SETUP_PROMPT


def test_snippet_offers_claude_code_explore_shadow():
    """Claude Code's built-in `Explore` subagent runs in an isolated
    context — it doesn't inherit CLAUDE.md / AGENTS.md. Without a
    shadow file at `.claude/agents/Explore.md`, the snippet written
    in Step 2 never reaches Explore. The setup-prompt should offer
    this opt-in shadow creation. This is Claude-Code-only — Codex
    and Gemini subagents are user-defined files only, no built-in
    to shadow."""
    # Shadow concept named.
    assert "shadow" in SETUP_PROMPT.lower()
    # Built-in Explore mentioned.
    assert "Explore" in SETUP_PROMPT
    # Claude Code is the gating condition.
    assert "Claude-Code-only" in SETUP_PROMPT or "Claude Code" in SETUP_PROMPT
    # Both project-local and global shadow paths must be mentioned.
    assert ".claude/agents/Explore.md" in SETUP_PROMPT
    assert "~/.claude/agents/Explore.md" in SETUP_PROMPT


def test_snippet_lists_cursor_in_cross_tool_coverage():
    """Cursor reads AGENTS.md in recent versions. The cross-tool
    preamble in Step 2 must mention Cursor alongside Codex CLI,
    Claude Code, and Gemini CLI so the agent doesn't tell the user
    that Cursor needs a separate file. Positive framing — we don't
    need a `### Do not` rule against Cursor-specific files when the
    same AGENTS.md covers Cursor too."""
    assert "Cursor" in SETUP_PROMPT


def test_snippet_handles_user_written_content_outside_markers():
    """If a user has hand-written ast-outline content in AGENTS.md
    (perhaps from an old `ast-outline prompt >> AGENTS.md` run that
    they then edited, or notes in their own words), Step 2 must not
    silently append a second marker block on top — that would leave
    two competing references in the file. The agent must scan for
    `ast-outline` mentions outside markers and ask the user how to
    handle them: wrap-as-is, replace, append-anyway, or skip."""
    lowered = SETUP_PROMPT.lower()
    # Scan logic explicit.
    assert "outside markers" in lowered or "outside the markers" in lowered or "outside" in lowered
    # The four options the user gets.
    assert "wrap" in lowered  # wrap-existing-content option
    # And the negative invariant — no silent append on top of user content.
    assert "silently append" in lowered or "silently" in lowered


def test_snippet_carries_diff_aware_re_run_logic():
    """On re-run, if the existing marker-wrapped block differs from
    the fresh `ast-outline prompt` output, the agent must NOT silently
    overwrite — the user may have hand-edited it. Three choices must
    be present: replace / keep / show diff. This protects user
    customizations across CLI upgrades."""
    lowered = SETUP_PROMPT.lower()
    # Diff awareness named.
    assert "diff" in lowered
    # The three choices the user gets when content has drifted.
    assert "replace" in lowered
    assert "keep" in lowered
    # Silent overwrite of customized blocks must be explicitly
    # forbidden.
    assert "silently" in lowered
    # Comparing existing content to the fresh canonical is the gate.
    assert "fresh canonical" in lowered or "canonical" in lowered


def test_snippet_covers_subagent_patching():
    """Optional Step 3 — ask permission, search the three known
    agent-folder layouts."""
    assert ".claude/agents/" in SETUP_PROMPT
    assert ".codex/agents/" in SETUP_PROMPT
    assert ".gemini/agents/" in SETUP_PROMPT


def test_snippet_has_headless_fallback():
    """Headless harnesses (`codex exec`) cannot ask the user. Without
    an explicit fallback, the agent either hangs or silently assumes
    consent — both bad."""
    assert "headless" in SETUP_PROMPT.lower()
    assert "codex exec" in SETUP_PROMPT


def test_snippet_excludes_builtin_subagents():
    """Built-in subagents (Explore / codebase-scout / general-purpose)
    are not file-based; patching them is impossible. The negative
    scope must be explicit."""
    lowered = SETUP_PROMPT.lower()
    assert "built-in" in lowered
    assert "explore" in lowered


def test_snippet_avoids_emphasis_overuse():
    """Universal prompts should avoid CRITICAL / YOU MUST stacks —
    overtriggers on Claude 4.5+, inert noise on GPT-5.x. Acronyms
    (CLI, README, PyPI) are fine — only the recognised emphasis
    tokens are forbidden."""
    forbidden = ["CRITICAL", "YOU MUST", "IMPORTANT:", "NEVER ", "ALWAYS "]
    hits = [tok for tok in forbidden if tok in SETUP_PROMPT]
    assert hits == [], f"emphasis-overuse tokens present: {hits}"


def test_snippet_ends_with_newline():
    """Trailing newline matters for any pipeline that concatenates
    further text after the snippet."""
    assert SETUP_PROMPT.endswith("\n")


def test_snippet_does_not_overlap_with_use_time_prompt():
    """The setup-prompt and the use-time AGENT_PROMPT cover different
    concerns. They're allowed to share a few obvious tokens
    (`ast-outline`, language extensions in the patch block) but
    setup-prompt should not contain the AGENT_PROMPT verbatim — that
    would defeat the architecture (agent already runs `ast-outline
    prompt` to capture the canonical snippet)."""
    from ast_outline._prompt import AGENT_PROMPT

    # AGENT_PROMPT first line is the heading — if it appears verbatim,
    # the setup-prompt is duplicating content that should be fetched
    # at runtime.
    agent_prompt_heading = AGENT_PROMPT.splitlines()[0]
    assert agent_prompt_heading not in SETUP_PROMPT
