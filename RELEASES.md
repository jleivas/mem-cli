# Release Guide

This document covers how to cut a release of mem-cli. The CI pipeline handles building, publishing, and updating the Homebrew tap automatically — the developer's job is to update the changelog, tag, and push.

---

## What CI Does Automatically

When a tag matching `v*` is pushed, `.github/workflows/release.yml`:

1. Builds standalone binaries for four platforms via PyInstaller (`scripts/build_binary.py`):
   - `mem-darwin-arm64` (macOS Apple Silicon)
   - `mem-darwin-amd64` (macOS Intel)
   - `mem-linux-amd64`
   - `mem-linux-arm64`
2. Smoke-tests each binary (`mem --version`).
3. Creates a GitHub Release with all four `.tar.gz` artifacts.
4. Regenerates `Formula/mem-cli.rb` via `scripts/update_formula.py` and pushes it to the `homebrew-mem-cli` tap.

---

## Prerequisites

- Write access to the `mem-cli` GitHub repository
- `gh` CLI authenticated (`gh auth login`)
- `HOMEBREW_TAP_TOKEN` repository secret set (see [Repository Secrets](#repository-secrets))
- Python 3.11+ with release tooling for local testing: `pip install -e ".[release]"`

---

## Cutting a Release

### Step 1 — Add the new version to CHANGELOG.md

Add a new version section at the top of the released entries:

```markdown
## [0.2.0] — 2026-06-08

### Added
- ...

### Fixed
- ...
```

Follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) conventions. The `[Unreleased]` section stays at the top for ongoing work. The version must follow `MAJOR.MINOR.PATCH` — see [Version Conventions](#version-conventions).

### Step 2 — Run the release script

```bash
bash scripts/release.sh
```

The script:
1. Reads the latest version from `CHANGELOG.md`.
2. Checks whether a git tag for that version already exists.
   - **Tag exists** → exits and prompts you to add a new version to `CHANGELOG.md` first.
   - **Tag does not exist** → syncs `pyproject.toml`, commits, creates the tag, and pushes.
3. Pushing the tag triggers the CI release workflow.

### Step 3 — Monitor CI

Watch the run at `https://github.com/jleivas/mem-cli/actions`. The workflow:

1. Builds and smoke-tests all four platform binaries in parallel.
2. Creates the GitHub Release once all binaries pass.
3. Updates and pushes the Homebrew formula.

If any binary job fails, the `release` job is skipped and no release or formula update is published.

---

## Local Build (optional — test before tagging)

To verify the binary builds cleanly on your machine before pushing a tag:

```bash
pip install -e ".[release]"
python scripts/build_binary.py
dist/mem/mem --version
```

`build_binary.py` outputs the binary to `dist/mem/`. The `dist/` directory is gitignored.

---

## Repository Secrets

The workflow requires one secret configured in the GitHub repository settings:

| Secret | Purpose |
|---|---|
| `HOMEBREW_TAP_TOKEN` | PAT with `Contents: write` access to the `jleivas/homebrew-mem-cli` repository |

To create the token: GitHub → Settings → Developer Settings → Personal access tokens → Fine-grained → set scope to `jleivas/homebrew-mem-cli`, permission `Contents: read and write`.

---

## Installing mem-cli

### From Homebrew (macOS and Linux — recommended)

```bash
brew tap jleivas/mem-cli
brew install mem-cli
```

### Direct binary download

Download the tarball for your platform from the [GitHub Releases](https://github.com/jleivas/mem-cli/releases) page, extract, and place the `mem` binary on your `PATH`:

```bash
# Example for macOS Apple Silicon
curl -L https://github.com/jleivas/mem-cli/releases/download/v<version>/mem-darwin-arm64.tar.gz | tar -xz
sudo mv mem /usr/local/bin/
mem --version
```

### From source (development)

```bash
git clone https://github.com/jleivas/mem-cli.git
cd mem-cli
pip install -e ".[dev]"
```

### Verify the install

```bash
mem --version
```

---

## MCP Registration (post-install)

After installing, register `mem serve` as an MCP server so agents can call memory and observability tools directly:

```bash
# Claude Code
cat >> ~/.claude/settings.json <<'EOF'
{
  "mcpServers": {
    "mem": {
      "command": "mem",
      "args": ["serve"]
    }
  }
}
EOF
```

For the full setup including Claude Code hooks and Codex watcher, see the [README](README.md).

---

## Version Conventions

| Pattern | Meaning |
|---|---|
| `0.x.0` | Minor release — new features, backward compatible |
| `0.x.y` | Patch release — bug fixes only |
| `1.0.0` | First stable public API |

Versions are sourced from `CHANGELOG.md` — never edit `pyproject.toml` directly; use `python scripts/sync_version.py` instead.
