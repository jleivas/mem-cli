---
name: bump-version
description: Use when the user asks to add a new version x.x.x with a list of features or fixes. Updates CHANGELOG.md, pyproject.toml, uv.lock, and any hardcoded version references in README.md. Example triggers: "agrega la versión 0.2.0 con X", "bump version to 0.1.2 with Y".
---

# bump-version

Applies a new version to the project. Follow every step in order.

## Step 1 — Parse the request

Extract from the user's message:
- **version**: the `MAJOR.MINOR.PATCH` string (e.g. `0.1.2`)
- **changes**: group each item into `Added`, `Fixed`, or `Changed` based on its nature.
  - New features → `Added`
  - Bug fixes → `Fixed`
  - Refactors or behaviour changes → `Changed`

## Step 2 — Update CHANGELOG.md

Insert a new section **immediately above** the previous latest released version (i.e. below the `[Unreleased]` divider). Use today's date from the system context (`currentDate`).

```markdown
## [X.Y.Z] — YYYY-MM-DD

### Added
- ...

### Fixed
- ...
```

Include only the headings that have items. Do not add empty sections. Keep the `## [Unreleased]` section at the top untouched.

## Step 3 — Update pyproject.toml

Replace the `version` field value with the new version:

```toml
version = "X.Y.Z"
```

Do **not** run `sync_version.py` — edit the file directly to avoid subprocess issues in the agent environment.

## Step 4 — Update uv.lock

Find the `mem-cli` package entry (it will be the only `source = { editable = "." }` entry) and update its version:

```
[[package]]
name = "mem-cli"
version = "X.Y.Z"
```

## Step 5 — Update README.md

Search for any hardcoded version string in README.md (e.g. in `pipx install dist/mem_cli-A.B.C-py3-none-any.whl` examples) and replace with the new version. Only change exact version strings — do not alter prose or headings.

## Step 6 — Verify

Run a quick grep to confirm no stale version strings remain:

```bash
grep -rn "PREV_VERSION" . --include="*.md" --include="*.toml" --include="*.lock" | grep -v node_modules | grep -v __pycache__
```

Replace `PREV_VERSION` with the version you just replaced. The result should be empty (or only test fixtures, which are acceptable).

## Files touched

| File | What changes |
|---|---|
| `CHANGELOG.md` | New `## [X.Y.Z]` section inserted |
| `pyproject.toml` | `version = "X.Y.Z"` |
| `uv.lock` | `version = "X.Y.Z"` on the `mem-cli` package entry |
| `README.md` | Hardcoded artifact version strings updated |

## What NOT to do

- Do not modify `src/mem/version.py` — it reads the version from CHANGELOG.md at runtime.
- Do not run `scripts/release.sh` — that is the step after the bump; the user triggers it.
- Do not create git commits unless the user explicitly asks.
