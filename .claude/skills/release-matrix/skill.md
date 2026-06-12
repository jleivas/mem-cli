---
name: release-matrix
description: Use when modifying .github/workflows/release.yml or adding CI build targets. Enforces the approved runner matrix and prevents re-adding macos-13 (Intel) which hangs indefinitely waiting for a runner. Example triggers: "agrega un runner", "modifica el CI", "nuevo target de build", any edit to release.yml.
---

# release-matrix

Enforces the approved GitHub Actions runner matrix for the release workflow.

## Approved matrix (never deviate from this)

```yaml
matrix:
  include:
    - os: macos-latest       # macOS ARM64 (Apple Silicon)
      asset: mem-darwin-arm64
    - os: ubuntu-latest      # Linux x86_64
      asset: mem-linux-amd64
```

This binary set covers all supported platforms:

| Platform | Binary used | How |
|---|---|---|
| macOS Apple Silicon (M1/M2/M3/M4) | `mem-darwin-arm64` | Native |
| macOS Intel | `mem-darwin-amd64` | Native x86_64 (built on ARM runner via Rosetta 2) |
| Linux x86_64 | `mem-linux-amd64` | Native |

> **IMPORTANTE:** Rosetta 2 solo va en una dirección — permite a Macs ARM correr binarios x86_64, NO al revés. Un Mac Intel NO puede ejecutar el binario ARM64 (`bad CPU type in executable`). Se requieren binarios separados para cada arquitectura.

## Banned runners

| Runner | Reason |
|---|---|
| `macos-13` | Waits 20+ minutes for a runner that never arrives — GitHub's Intel Mac runner pool is too small. Tried in v0.1.12, removed in v0.1.13. |
| `macos-12` | Deprecated by GitHub Actions in August 2024. |
| `macos-13-large` | Same pool problem as `macos-13`. |
| `ubuntu-24.04-arm` | Linux ARM binary is currently not required by any target user. Add only if explicitly requested. |

## What to do if asked to add Intel Mac support

**Do not** add `macos-13` or any Intel Mac runner.

Instead, explain that the ARM64 binary already covers Intel Macs via Rosetta 2 and no changes are needed.

## What to do if the binary exceeds 2 GB

GitHub Release assets have a 2 GB limit. If a binary exceeds this:

1. Check `build_binary.py` — avoid `--collect-all` for large packages (torch, transformers). Use `--collect-submodules` or `--hidden-import` instead.
2. Do **not** solve this by adding an Intel runner to avoid building a full binary.

## Verification step

After any edit to `.github/workflows/release.yml`, run:

```bash
grep "macos-13\|macos-12\|macos-13-large" .github/workflows/release.yml
```

The result must be empty. If it is not, remove the offending entry before proceeding.
