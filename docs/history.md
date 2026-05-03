# Project history

A timeline of releases and notable events. The full record lives in
[`git log`](https://github.com/ast-outline/ast-outline/commits/main) and
the [GitHub release page](https://github.com/ast-outline/ast-outline/releases).

## 2026

### May

| Date | Event |
| --- | --- |
| **2026-05-03** | **v0.6.1**: PyPI metadata refresh after the GitHub Organization transfer (no code changes). |
| **2026-05-03** | **Repository transferred** from `dim-s/ast-outline` to the [`ast-outline`](https://github.com/ast-outline) GitHub Organization. Old `dim-s/ast-outline` URLs continue to redirect. Copyright remains with Dmitrii Zaitsev (dim-s); the org is hosting infrastructure, not a new copyright holder. |
| **2026-05-03** | **v0.6.0**: relicense from MIT to **Apache License 2.0**. Documentation separately licensed under **CC BY 4.0**. The previous MIT text is retained in `LICENSE-MIT` for compatibility with downstream forks of the 0.5.x tree. |
| **2026-05-02** | First publish to **PyPI** as [`ast-outline`](https://pypi.org/project/ast-outline/). v0.4.2 / v0.4.3 / v0.5.0 (`code-outline` CLI alias dropped) / v0.5.1 (`implements` command dropped — outline/digest already render `: Base`) / v0.5.2 (`--imports` flag) / v0.5.3 (`--version` flag). |
| **2026-05-01** | **v0.4.0**: digest method markers (`[async]` / `[unsafe]` / `[const]` / `[suspend]` / `[static]` / `[abstract]` / `[override]` / `[classmethod]` / `[property]`); type modifiers, attrs, and `[deprecated]` tag. |

### April

| Date | Event |
| --- | --- |
| **2026-04-30** | YAML adapter; per-file size labels + token estimate in digest headers; **Rust adapter**. |
| **2026-04-28** | `# note: …` LLM-friendly error contract on stdout with `rc=0`; substring matching for Markdown headings. |
| **2026-04-25** | Go adapter. |
| **2026-04-24** | Scala adapter. **Renamed `code-outline` → `ast-outline` (v0.3.0).** GitHub repo renamed to `dim-s/ast-outline`. |
| **2026-04-23** | Kotlin adapter; `prompt` subcommand. |
| **2026-04-22** | **Repository created** on GitHub as `dim-s/code-outline`. First public commit, v0.2.0b0. Russian and Chinese READMEs added; TypeScript / JavaScript adapter shipped same day. |

---

## Priority date

The **2026-04-22** date matters: it's the first public commit and the
anchor for trademark priority. It's recorded in
[`NOTICE`](https://github.com/ast-outline/ast-outline/blob/main/NOTICE)
and frozen in PyPI release metadata, so it can't be backdated by
downstream forks or copies.
