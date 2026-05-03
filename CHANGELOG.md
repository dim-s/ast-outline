# Changelog

All notable changes to this project are documented here. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

For the complete history before v0.6.0, see `git log` and the
[GitHub release page](https://github.com/dim-s/ast-outline/releases).

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

[0.6.0]: https://github.com/dim-s/ast-outline/releases/tag/v0.6.0
