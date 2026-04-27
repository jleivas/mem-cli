# Release Guide

This document covers how to cut a GitHub release, publish a Homebrew tap, and install mem-cli from each source.

---

## Prerequisites

- Write access to the `mem-cli` GitHub repository
- Python 3.11+ with the release tooling installed (`pip install -e ".[release]"`)
- `gh` CLI authenticated (`gh auth login`)
- (For the tap) write access to a `homebrew-mem-cli` GitHub repository under the same org/user

---

## 1. Cutting a GitHub Release

### Step 1 — Update CHANGELOG.md

Add a new version section at the top of the released entries. The version is read automatically from here.

```markdown
## [0.2.0] — 2026-05-01

### Added
- Semantic search via sentence-transformers
- Auto-capture via Claude Code Stop hook
- `mem compress` command for AI-powered memory compression

### Changed
- sentence-transformers is now a required dependency
```

Follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) conventions. Use `[Unreleased]` for work not yet tagged.

### Step 2 — Build the distributions

```bash
python scripts/release_build.py
```

This script:
1. Reads the latest version from `CHANGELOG.md`
2. Syncs it into `pyproject.toml`
3. Clears `dist/` and `build/`
4. Produces `dist/mem_cli-<version>-py3-none-any.whl` and `dist/mem_cli-<version>.tar.gz`

### Step 3 — Verify locally

```bash
pipx install dist/mem_cli-<version>-py3-none-any.whl --force
mem --version
```

### Step 4 — Commit the version bump

```bash
git add CHANGELOG.md pyproject.toml
git commit -m "release: v<version>"
```

### Step 5 — Tag and push

```bash
git tag v<version>
git push origin master --tags
```

Pushing the tag triggers the `release` workflow in `.github/workflows/release.yml`, which builds and verifies the wheel on Linux, macOS, and Windows.

### Step 6 — Create the GitHub Release

Wait for the workflow to pass, then:

```bash
gh release create v<version> dist/* \
  --title "mem-cli v<version>" \
  --notes-file <(awk '/^## \[<version>\]/,/^## \[/' CHANGELOG.md | head -n -1)
```

Or create it manually on GitHub with the contents of the corresponding `CHANGELOG.md` section as release notes.

The `.whl` and `.tar.gz` files attached to the release are what the Homebrew formula will reference.

---

## 2. Publishing a Homebrew Tap

A Homebrew tap is a separate GitHub repository named `homebrew-mem-cli`. The convention `user/homebrew-mem-cli` lets users install with `brew install user/mem-cli/mem-cli`.

### Step 1 — Create the tap repository

```bash
gh repo create homebrew-mem-cli --public --description "Homebrew tap for mem-cli"
git clone https://github.com/jleivas/homebrew-mem-cli
cd homebrew-mem-cli
mkdir Formula
```

### Step 2 — Get the SHA256 of the release tarball

```bash
curl -sL https://github.com/jleivas/mem-cli/archive/refs/tags/v<version>.tar.gz \
  | shasum -a 256
```

### Step 3 — Write the formula

Create `Formula/mem-cli.rb`:

```ruby
class MemCli < Formula
  include Language::Python::Virtualenv

  desc "Local token observability and agent memory for Claude and Codex"
  homepage "https://memcli.ai"
  url "https://github.com/jleivas/mem-cli/archive/refs/tags/v<version>.tar.gz"
  sha256 "<sha256-from-step-2>"
  license "MIT"

  depends_on "python@3.11"

  resource "sentence-transformers" do
    url "https://files.pythonhosted.org/packages/.../sentence_transformers-<ver>.tar.gz"
    sha256 "<sha256>"
  end

  # Add one `resource` block per transitive dependency that Homebrew
  # cannot resolve automatically. Use `poet mem-cli` from homebrew-pypi-poet
  # to generate them:
  #   pip install homebrew-pypi-poet
  #   poet mem-cli

  def install
    virtualenv_install_with_resources
  end

  test do
    system "#{bin}/mem", "--version"
  end
end
```

> **Tip**: run `poet mem-cli` after installing `homebrew-pypi-poet` to auto-generate all `resource` blocks with correct URLs and hashes.

### Step 4 — Commit and push the formula

```bash
cd homebrew-mem-cli
git add Formula/mem-cli.rb
git commit -m "mem-cli v<version>"
git push
```

### Step 5 — Test the tap locally

```bash
brew tap jleivas/mem-cli
brew install mem-cli
mem --version
```

### Updating the tap for future releases

Repeat Steps 2–4 with the new version and new SHA256. The URL and hash are the only fields that change between releases.

---

## 3. Installing mem-cli

### From Homebrew (recommended for macOS/Linux)

```bash
brew tap jleivas/mem-cli
brew install mem-cli
```

### From pip

```bash
pip install mem-cli
```

### From pipx (isolated environment, recommended for CLI tools)

```bash
pipx install mem-cli
```

### From a specific GitHub Release (wheel)

```bash
pipx install https://github.com/jleivas/mem-cli/releases/download/v<version>/mem_cli-<version>-py3-none-any.whl
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

## 4. MCP Registration (post-install)

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

## 5. Version Conventions

| Pattern | Meaning |
|---|---|
| `0.x.0` | Minor release — new features, backward compatible |
| `0.x.y` | Patch release — bug fixes only |
| `1.0.0` | First stable public API |

Versions are sourced from `CHANGELOG.md` — never edit `pyproject.toml` directly.
