# CLAUDE.md — python-sdk

The Python SDK for the spore.host hosted REST API. Part of the spore.host suite.

## Versioning & changelog (required)

This project follows **[Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html)**
and keeps a **[Keep a Changelog](https://keepachangelog.com/en/1.1.0/)**-format
`CHANGELOG.md` at the repo root. (Spore.host-wide policy — every repo.)

**Every change that affects users updates `CHANGELOG.md`** in the same PR, under
`## [Unreleased]` in the right group (`Added` / `Changed` / `Deprecated` /
`Removed` / `Fixed` / `Security`; `Documentation` for docs-only). Describe the
user-visible effect; reference the issue/PR.

**On release:**

1. Promote `## [Unreleased]` → `## [X.Y.Z] - YYYY-MM-DD`, open a fresh
   `## [Unreleased]`, update the comparison links.
2. Pick `X.Y.Z` by SemVer (MAJOR breaking / MINOR feature / PATCH fix; pre-1.0
   breaking → MINOR).
3. **Bump `version` in `pyproject.toml` to match.**
4. Tag **`python-v X.Y.Z`** (note the `python-v` prefix this repo uses) → the
   publish-python workflow builds and uploads the package.

## Build & test

- `python -m build` — build the sdist/wheel
- `pytest` — run tests
