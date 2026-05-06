"""Canonical setup-prompt for the ast-outline installer flow.

This module holds the text that steers a coding agent (Claude, Codex,
Gemini, Cursor, …) to wire ast-outline into the current repo: append
the canonical agent snippet to AGENTS.md, optionally check for a newer
release, and optionally patch existing exploration-oriented subagent
files. It is the single source of truth for the
`ast-outline setup-prompt` CLI subcommand.

Distinction vs ``_prompt.AGENT_PROMPT``:

- ``AGENT_PROMPT`` runs **at use-time** — it lives in AGENTS.md /
  CLAUDE.md and tells the agent how to *use* ast-outline whenever it
  reads code.
- ``SETUP_PROMPT`` (this file) runs **once at install-time** — the
  user invokes a coding agent which then performs the integration
  steps (file writes, idempotent updates, optional patches of
  existing subagents) on the user's behalf.

Cross-vendor constraints when editing — keep all of these intact, the
prompt is intentionally calibrated to work across Claude Opus 4.7 /
Sonnet 4.6 / Haiku 4.5, OpenAI GPT-5.x (5.3-codex / 5.4 / 5.5), and
Google Gemini 3.x (Pro / Flash / Flash-Lite):

- Outcome-first phrasing, structured by markdown ``###`` headings —
  numbered steps inside each section are tolerated by Claude /
  Gemini and read as workflow rather than rigid prescription on
  GPT-5.5 because the heading already anchors the outcome.
- No persona ("you are a senior engineer") — hurts GPT-5.5, neutral
  on Claude, Gemini gains 5% from identity prompting only when the
  identity is functional ("a planner") which is too narrow here.
- No "think step by step" — hurts Gemini 3 (CoT scaffolding now
  superseded by ``thinking_level``) and reads as noise on GPT-5.5.
- No aggressive emphasis (no ``CRITICAL:`` / ``YOU MUST``) — causes
  overtriggering on Claude 4.5+ and is inert noise on GPT-5.x.
- Marker-based idempotency — every block we insert into the user's
  files is wrapped in ``<!-- ast-outline:start -->`` /
  ``<!-- ast-outline:end -->`` so re-runs replace in place rather
  than duplicating. The agent must respect this contract.
- Explicit headless behaviour — in non-interactive harnesses
  (``codex exec``, scheduled CI) the agent has no human to ask, so
  the prompt restricts execution to the safe-by-default Step 1 and
  lists skipped optional steps in the confirmation. Never silently
  assume consent.
- No model-name pinning — keeps the prompt valid as new model
  versions ship without an edit cycle.

If you add a Claude-specific or GPT-specific tweak, the snippet stops
being universal — split it into a vendor-specific sibling instead of
inflating the canonical text.
"""
from __future__ import annotations


SETUP_PROMPT = """## Integrating ast-outline into this project

You are wiring ast-outline into the current repo's agent context at the
user's request. The user has not specified which agentic CLI they use —
Claude Code, Codex CLI, Gemini CLI, or a combination — so do not assume.

Reply to the user in whichever human language the surrounding
conversation has been using (Russian, English, Chinese, etc.). Apply
the same rule to any free-form prose you write into AGENTS.md or
CLAUDE.md when creating those files from scratch — top headings,
brief comments, section labels around the marker block — the user's
own project notes should read in their own language.

Two exceptions stay in English regardless of the conversation's
language. Translating these breaks the architecture, so insert them
verbatim:

1. The content inside the `<!-- ast-outline:start --> ... <!-- ast-outline:end -->`
   block in AGENTS.md (and the markers themselves). It comes from
   `ast-outline prompt`, calibrated for cross-vendor LLM reliability.
2. Subagent files entirely (`.claude/agents/*.md`,
   `.codex/agents/*.md`, `.gemini/agents/*.md`) — both any existing
   content and the patch block you insert in Step 3. Subagent system
   prompts steer LLM behaviour, English is the working language on
   that surface.

The checklist below also stays in English for cross-vendor model
reliability — you read it, the user does not.

This setup is safe to re-run. Every inserted block is wrapped in
`<!-- ast-outline:start -->` / `<!-- ast-outline:end -->` markers so
re-runs find the existing block instead of duplicating. When the
existing content differs from the fresh canonical (the user may have
edited it manually), the prompt flips into a diff-aware mode in
Step 2 / Step 3 — the user is shown what changed and decides whether
to overwrite, keep, or merge. Never replace a customized block
silently.

### How to talk to the user

- Keep questions short — one sentence, one decision. Avoid stacking
  multiple questions in a single turn.
- Use plain language; assume the reader is new to LLM coding tooling.
  Skip jargon, or define it inline in three or four words.
- Before running any command on the user's behalf, show the exact
  command on its own line so they see what is about to happen.
- You may run install / upgrade / file-edit commands yourself only
  when the user explicitly asks ("install it", "upgrade now",
  "обнови", "поставь"). Never run them silently or by inference.

### Cross-OS note

Examples below use Unix-style commands (`which`, `$VIRTUAL_ENV`,
`curl`). Translate to whatever the user's shell needs without
asking:

- Windows `cmd.exe` — `where uv`, `%VIRTUAL_ENV%`.
- Windows PowerShell — `Get-Command uv`, `$env:VIRTUAL_ENV`.
- macOS / Linux — the examples as written.

If a probe is unavailable on the platform (e.g. no `curl` and no
`jq`), pick a working substitute or skip silently.

### Step 1 — Make sure ast-outline is available

1. Run `ast-outline --version`.

   - **Command found** — note the installed version and continue
     to step 2. Do not probe package managers or venvs at this
     point; they are only relevant if you need to install or
     upgrade.
   - **Command not found** — only now check what install tooling
     is on PATH (`uv`, `pipx`, `pip`) and whether a Python venv is
     active (`VIRTUAL_ENV`, `.venv/` in the repo root). Use the
     result to pick a *default* recommendation, then ask the user
     to confirm or override:

     - `uv tool install ast-outline` — recommended when `uv` is on
       PATH. Single venv per tool, available globally, fast.
     - `pipx install ast-outline` — fallback when `uv` is missing
       but `pipx` is present.
     - `pip install ast-outline` — only when the user explicitly
       wants the package pinned inside the active project venv.

     The user can run the chosen command themselves, or ask you to
     run it for them. After install, run `ast-outline --version`
     again to verify. If the binary is not yet on PATH (common
     with a fresh `uv tool install`), tell the user to start a new
     shell or use the suggested launcher, then continue.

   Do not proceed with the rest of the checklist until
   `ast-outline --version` succeeds.

2. Best-effort: check whether a newer version exists on PyPI.
   Reasonable probes include `pip index versions ast-outline`,
   `uv tool list --outdated`, or
   `curl -s https://pypi.org/pypi/ast-outline/json` parsed for
   `info.version`. Skip silently if the probe fails — it is
   informational, not load-bearing.

3. If a newer version is available, tell the user the new version
   number and the upgrade command appropriate to how they
   installed:

   - `uv tool upgrade ast-outline` — for `uv`-installed tools
   - `pipx upgrade ast-outline` — for `pipx`-installed tools
   - `pip install -U ast-outline` — inside the active venv otherwise

   If you cannot tell which install method was used, list all three
   and let the user pick. Frame it as an explicit offer ("you can
   run it yourself, or ask me to upgrade"), not a default. If the
   user asks you to upgrade, run the chosen command, verify with
   `ast-outline --version`, and re-capture the snippet via
   `ast-outline prompt` before Step 2 so AGENTS.md picks up the
   fresher version. The bundled snippet evolves with the package,
   so upgrading first is usually preferable.

### Step 2 — Persistent-context file (diff-aware, idempotent)

AGENTS.md is the cross-tool default — read natively by Codex CLI,
by Claude Code via `@AGENTS.md` import from CLAUDE.md, by Gemini
CLI when `~/.gemini/settings.json` configures
`context.fileName: ["AGENTS.md", "GEMINI.md"]`, and by Cursor in
recent versions. One file usually covers every frontier coding-
agent CLI the user might have. Three system-aware adjustments make
this universal across the harnesses the user might actually have:

**Filename selection.** Default to `./AGENTS.md`. If the user has
only **one** frontier agentic CLI installed, prefer that tool's
native file — no extra config needed:

- Claude Code only (`~/.claude/` exists, `~/.codex/` and
  `~/.gemini/` do not) → `./CLAUDE.md`
- Codex CLI only → `./AGENTS.md`
- Gemini CLI only → `./GEMINI.md`

Detect by checking which `~/.<tool>/` directories exist on the
user's machine, or ask explicitly. When in doubt, default to
AGENTS.md — the safest cross-tool option.

**Codex override pattern.** Before writing, check for a
`AGENTS.override.md` next to the target `AGENTS.md`
(`./AGENTS.override.md` repo-level, or `~/.codex/AGENTS.override.md`
if you are touching the global Codex file). If an override exists,
Codex CLI loads it **instead of** the regular `AGENTS.md` — writing
to `AGENTS.md` would be silently shadowed. Either write the marker
block to the override, or ask the user which file they want updated.
Don't write to both; that creates drift.

**Scope.** Ask once, before writing: project-local (default,
`./AGENTS.md` / `./CLAUDE.md` / `./GEMINI.md` per the filename rule
above) or global, applying across all the user's projects:

- Claude Code → `~/.claude/CLAUDE.md`
- Codex CLI → `~/.codex/AGENTS.md` (or `~/.codex/AGENTS.override.md`)
- Gemini CLI → `~/.gemini/GEMINI.md`

Pick the global file matching the agentic CLI(s) the user has.
Default to project-local — it's the less invasive choice. The user
can re-run with global scope later if they decide they want
cross-project awareness.

1. Run `ast-outline prompt` and capture stdout — call this the
   *fresh canonical*. It is the agent snippet for the installed CLI
   version, regenerated every run so it stays in sync with `pip
   install -U`.
2. Open the chosen target file and pick the matching branch:

   - **File missing** — create it containing only the marker-wrapped
     fresh canonical. No question needed.
   - **File exists** — scan for any mention of `ast-outline`,
     `## Code exploration` (the snippet's heading), or the markers
     themselves. The scan governs which sub-branch applies:

     - **No mention anywhere** — append the marker-wrapped fresh
       canonical at the end of the file with one blank line above
       the opening marker. No question needed.
     - **Markers present** — read the content between them and
       compare to the fresh canonical:
       - **Identical** — already up to date. Tell the user,
         continue.
       - **Different** — the user may have either an older bundled
         version (regular case) or a manual customization (their
         project-specific tweaks). Do not replace silently. Show
         a short diff summary — what changed in a sentence or two
         — and ask which path they want:
         1. **Replace with the fresh canonical** — overwrite.
            Recommended when the diff looks like a version bump
            (added language extensions, new fallback markers).
         2. **Keep the existing block** — skip the write. Note
            this in Step 4 so the user knows the snippet is now
            lagging.
         3. **Show full diff first** — print the diff, then ask
            again with the same three options.

         Default to **ask**, never to overwrite. The user's
         manual edits are load-bearing until proven otherwise.
     - **`ast-outline` mentioned outside markers** — the user has
       hand-written content (perhaps from an old `ast-outline
       prompt >> AGENTS.md` run that they then edited, or notes in
       their own words). Do not append a second block silently —
       that would leave two competing references in the same file.
       Show the user the offending lines (file, line range, brief
       excerpt) and ask which path they want:

       1. **Wrap their existing content in markers** — leave the
          text exactly as written, just add
          `<!-- ast-outline:start -->` above and
          `<!-- ast-outline:end -->` below. Future re-runs then
          fall under the diff-aware branch. Recommended when the
          user's version is intentional and they want to keep it.
       2. **Replace it with the fresh canonical** — remove the
          old hand-written block and write the marker-wrapped
          fresh canonical in its place. Recommended when the old
          content was a stale `ast-outline prompt` paste and the
          user wants the current version.
       3. **Append the fresh canonical anyway, in addition** —
          accept the duplication. Use only when the user
          explicitly wants both (rare; usually a sign of
          confusion).
       4. **Skip Step 2 entirely** — leave AGENTS.md untouched.
          Note in Step 4 that the snippet was not written.

       Default to **ask**. Never silently append on top of
       existing user content.

3. Cross-tool wiring (only when relevant): if you wrote to
   `./AGENTS.md` AND `./CLAUDE.md` also exists AND CLAUDE.md does
   not already reference `@AGENTS.md`, ask the user whether to
   prepend `@AGENTS.md` at the top of CLAUDE.md so Claude Code
   picks up the shared block. Skip this when you wrote directly to
   `./CLAUDE.md` or `./GEMINI.md` — there is nothing to import in
   that case.

### Step 3 — Patch existing exploration subagents (ask first, per agent)

Look for user-defined subagent files in:

- `./.claude/agents/*.md` and `~/.claude/agents/*.md`
- `./.codex/agents/*.md` and `~/.codex/agents/*.md`
- `./.gemini/agents/*.md` and `~/.gemini/agents/*.md`

For each agent whose `description` or role text mentions code
exploration, codebase research, structure mapping, file-graph
analysis, or similar — show the user the agent's name and path, then
ask whether to patch it.

If approved, insert this block at the end of the agent's body, just
before any closing sections, wrapped in markers:

    <!-- ast-outline:start -->
    ## Tooling — ast-outline

    Before reading source files to understand structure, prefer
    `ast-outline outline / digest / show` over full file reads —
    5-10x lower context cost on supported languages.

    Run `ast-outline prompt` once per session to load the canonical
    usage snippet (commands, flags, supported extensions, fallback
    markers).

    Falls back to native Read when `ast-outline` is unavailable
    (`command not found`).
    <!-- ast-outline:end -->

Re-run handling: if existing markers are present, compare the
content between them to the canonical block above.

- Identical — no-op, move on.
- Different — same diff-aware flow as Step 2: tell the user the
  block has drifted, offer replace / keep / show-diff. Do not
  silently overwrite a customized subagent block.

Do not patch built-in subagents (Claude Code's `Explore`,
`codebase-scout`, `general-purpose`, and similar) — they are not
file-based and not user-modifiable.

**Claude-Code-only sub-step: shadow the built-in `Explore` agent.**
Claude Code lets you override a built-in subagent by creating a
file with the same name in `.claude/agents/`. This is useful
because Claude Code's `Explore` runs in an isolated context — it
does not inherit `CLAUDE.md` / `AGENTS.md`, so the snippet you just
wrote in Step 2 does not reach `Explore` invocations on its own.

If — and only if — the user has Claude Code (`~/.claude/` exists)
AND no `.claude/agents/Explore.md` (or `~/.claude/agents/Explore.md`)
exists yet, ask once:

> Claude Code's built-in `Explore` subagent runs in an isolated
> context — it won't see the snippet from Step 2. Create a shadow
> at `.claude/agents/Explore.md` (project) or
> `~/.claude/agents/Explore.md` (global) so `Explore` learns to use
> ast-outline too?

If approved, create the file with this body (project-local default,
ask which scope the user wants). The shadow file embeds the **full
fresh canonical** from Step 2.1 — not a short pointer — because the
shadow is a brand-new file, the canonical is the entire reason the
shadow exists, and embedding avoids forcing every `Explore`
invocation to re-run `ast-outline prompt`. Future `setup-prompt`
re-runs will pick up the shadow under the diff-aware branch (Step 3
patch flow) and offer to refresh it when `ast-outline` upgrades:

    ---
    name: Explore
    description: Explore the codebase to find files and code relevant to a task. Returns a focused summary with file paths, key symbols, and relationships — not full file contents.
    ---

    You are an exploration subagent for the current codebase. Return
    a focused summary: file paths, key symbols, relationships — not
    full file contents. The parent agent will read specific files
    itself.

    <!-- ast-outline:start -->
    {paste the fresh canonical captured in Step 2.1 verbatim here}
    <!-- ast-outline:end -->

    Falls back to native Read / Grep / Glob when `ast-outline` is
    unavailable (`command not found`).

Skip this sub-step entirely if the user does not use Claude Code,
or if a shadow already exists (in which case it falls under the
diff-aware patch logic above, not this create-from-scratch flow).

### Step 4 — Confirm

Report:

- Installed ast-outline version, and whether a newer version is
  available (with the upgrade command if so).
- Path of AGENTS.md written or updated, plus the first heading of the
  inserted block.
- Each patched subagent's path.
- Anything skipped, with the reason.

### Interactive vs headless

If you can ask the user, ask before each patching decision in Step 3,
the optional `@AGENTS.md` import in Step 2, the filename / scope
choice in Step 2, and the install / upgrade decisions in Step 1.

If you cannot ask (headless / batch mode — `codex exec`,
`claude -p`, Gemini CLI's non-interactive mode, scheduled CI),
execute Steps 1 and 2 only:

- Step 1: read-only version check; only proceed if `ast-outline` is
  already installed. If missing, exit and report — do not auto-install.
- Step 2: write to `./AGENTS.md` at project-local scope (least
  surprise across vendors, no per-tool detection needed). Skip the
  filename / scope / `@AGENTS.md` import questions.

Skip Step 3 entirely. List every skipped optional decision in Step 4
so a later interactive run can apply them.

Never assume "yes" on a patching, install, or scope decision when the
user cannot be asked.

### Do not

- Modify source files, run tests, or trigger builds.
- Patch agents the user did not approve, or built-in subagents.
- Auto-upgrade the package without explicit user consent.
"""
