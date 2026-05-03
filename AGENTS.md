# AGENTS.md — ast-outline (code repo)

Notes for Claude Code / Cursor / other coding agents working in this
repo. The user (Dmitrii Zaitsev / dim-s) maintains **two related
repositories** locally — keep both in mind.

## The two repos

| Role | GitHub | Local path |
| --- | --- | --- |
| **This repo — CLI tool source** | [ast-outline/ast-outline](https://github.com/ast-outline/ast-outline) | `/Users/dmitrijzajcev/dev/tools/code-outline/` *(historical folder name; renamed project, kept path)* |
| **Documentation website source** | [ast-outline/ast-outline.github.io](https://github.com/ast-outline/ast-outline.github.io) | `/Users/dmitrijzajcev/dev/tools/ast-outline.github.io/` |

Site is published at <https://ast-outline.github.io/> (org-level Pages
convention — repo name must match `<orgname>.github.io` exactly).

## When to also update the docs site

Whenever a change in this repo is **user-visible**, the corresponding
page in `../ast-outline.github.io/docs/` likely needs an update:

| Change here | Page to update there |
| --- | --- |
| New CLI subcommand or flag | `docs/commands.md` |
| New / changed digest marker, size label, legend, output structure | `docs/output-format.md` |
| New language adapter | `docs/index.md` (supported-languages table) + `docs/output-format.md` (any adapter-specific format quirks) |
| Change to the LLM-agent prompt snippet (`src/ast_outline/_prompt.py` or `cli.py prompt` command) | `docs/agents.md` (the `??? quote` block) |
| New release | `docs/history.md` (timeline) |
| License / trademark changes | `docs/about.md` + `LICENSE-DOCS` / `NOTICE` here + `LICENSE` / `NOTICE` in the site repo |

The docs site does **not** auto-pull from this repo. Edits must be
made in `../ast-outline.github.io/` and committed/pushed there
separately. Site rebuilds on push to `main`.

## Local site preview

```bash
cd ../ast-outline.github.io
uvx --with mkdocs-material mkdocs serve   # http://127.0.0.1:8000
```

## License & ownership

- **Code (this repo, v0.6.0+)**: Apache License 2.0 (`LICENSE`).
- **Older code (≤0.5.3)**: MIT, preserved in `LICENSE-MIT`.
- **Documentation prose** (this README, CHANGELOG, prompt files,
  digest legend, CLI help text): CC BY 4.0 (`LICENSE-DOCS`).
- **Docs site repo**: same CC BY 4.0 — see that repo's `LICENSE`.

Copyright held by **Dmitrii Zaitsev** (GitHub: `dim-s`). The
`ast-outline` GitHub Organization is hosting infrastructure, not a
new copyright holder.

`ast-outline™` is an unregistered trademark of Dmitrii Zaitsev. Apache
2.0 §6 explicitly excludes any trademark grant. Forks and language
ports must use a different name.

## Release flow (this repo)

```bash
# Bump version in pyproject.toml AND src/ast_outline/__init__.py
# (test_digest_format.test_version_string_matches_pyproject enforces this)

# Add CHANGELOG entry under a new ## [X.Y.Z] heading

git commit -m "vX.Y.Z: <one-line summary>"
git tag -a vX.Y.Z -m "vX.Y.Z: <details>"
git push origin main --follow-tags

uv build
uvx twine upload dist/ast_outline-X.Y.Z*

# Then update the docs site if anything user-visible changed.
```

## Tests

```bash
.venv/bin/pytest             # full suite, ~0.5s, 753+ tests
```

The CI gate is `pytest --strict` style (no warnings tolerated for new
adapters); fixtures live under `tests/fixtures/<lang>/`.

## Don't do

- Don't restore `docs/`, `mkdocs.yml`, `.github/workflows/docs.yml`
  here — they were split out **on purpose** in commit `8b41e08`. The
  site lives in the sibling repo.
- Don't change `LICENSE` to non-Apache without an explicit
  relicensing decision; prior MIT versions are preserved in
  `LICENSE-MIT` and that file should not be removed.
- Don't include `ast-outline` as an `extras` install name in
  downstream packages — that's the project's binary/distribution
  name, reserved.
