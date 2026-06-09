# Changelog

All notable changes to mem-cli are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.1.7] — 2026-06-09

### Fixed

- `mem --version` now returns the correct version in the PyInstaller macOS ARM64 binary instead of `0.0.0`.
- Added `--copy-metadata mem-cli` to the PyInstaller invocation so `importlib.metadata.version()` resolves correctly inside frozen binaries.
- Added a baked-version fallback: `build_binary.py` writes `_baked_version.py` before bundling as a compile-time constant, eliminating any dependency on metadata or filesystem lookups at runtime.
- Version resolution chain updated: `importlib.metadata` → baked constant → CHANGELOG.md walk (now also checks `sys._MEIPASS` for frozen bundles).
- Strengthened `test_version_contract.py`: version must now match `^\d+\.\d+\.\d+$` and must not equal `"0.0.0"`.

---

## [0.1.6] — 2026-06-08

### Changed

- Replaced `sentence-transformers` (PyTorch, ~1.5 GB) with a pure-Python TF + character-bigram implementation in `embedding_service.py`. Semantic search now uses feature hashing over word tokens and character bigrams — no external ML dependencies, always available, binary size drops to ~80 MB.
- Removed `sentence-transformers` from required dependencies in `pyproject.toml`.
- Cleaned up `build_binary.py`: removed `--collect-submodules` and `--exclude-module` flags that were added to work around the ML library size.

---

## [0.1.5] — 2026-06-08

### Changed

- Removed `mem-linux-arm64` from the CI release matrix. The Linux binary now targets only `amd64`, eliminating the `mem-linux-arm64.tar.gz` artifact that exceeded GitHub's 2 GB release asset limit.

---

## [0.1.4] — 2026-06-08

### Changed

- Intel Mac (`brew install mem-cli`) now installs from source via `pip` into an isolated virtualenv instead of a pre-built binary. This eliminates the dependency on scarce GitHub-hosted `macos-12`/`macos-13` Intel runners, which caused releases to stall indefinitely waiting for a runner.

### Fixed

- Removed `mem-darwin-amd64` from the CI release matrix. All three remaining platforms (macOS ARM64, Linux amd64, Linux arm64) use consistently available runners and are unaffected.

---

## [0.1.3] — 2026-06-08

### Fixed

- Fixed GitHub Actions release workflow: PyInstaller was targeting `src/mem/cli.py` directly, which runs as `__main__` and cannot resolve relative imports. Added `scripts/mem_entry.py` as a thin entry point that imports `mem.cli` with absolute imports so the compiled binary runs correctly on Linux and macOS.

---

## [0.1.2] — 2026-06-08

### Fixed

- Fixed GitHub Actions release workflow: added `scripts/mem_entry.py` as a thin PyInstaller entry point using absolute imports, replacing the direct `src/mem/cli.py` target that caused `ImportError: attempted relative import with no known parent package` when running `mem --version` on the compiled binary.

---

## [0.1.1] — 2026-06-08

### Fixed

- Fixed release binary compilation for Linux and macOS: added `scripts/mem_entry.py` as a thin PyInstaller entry point that uses absolute imports, replacing the direct `src/mem/cli.py` target that caused `ImportError: attempted relative import with no known parent package` at startup.

---

## [0.1.0] — 2026-04-21

### Added

- Semantic search via sentence-transformers
- Auto-capture via Claude Code Stop hook
- `mem compress` command for AI-powered memory compression
- sentence-transformers is now a required dependency
- `mem` CLI entrypoint with interactive menu (`mem` with no arguments)
- `mem start` / `mem stop` / `mem status` — background token monitor lifecycle
- `mem dashboard` — live terminal token-usage dashboard with per-agent views
- `mem remember` / `mem recall` / `mem forget` / `mem projects` — project-scoped memory commands
- `mem init` — auto-initialize project memories from Claude or Codex
- `mem config` — generate `AGENTS.md` and `CLAUDE.md` symlink for a project
- `mem serve` — local MCP server (stdio transport) exposing all memory and observability tools
- MCP tools: `memory_remember`, `memory_recall`, `memory_forget`, `memory_projects`, `monitor_snapshot`, `monitor_status`, `monitor_start`, `monitor_stop`
- JSONL adapter that normalizes Claude and Codex token events into `TokenEvent`
- `claude-mem.sh` hook for capturing Claude Code token events at session end
- `codex-mem.py` background watcher for Codex session token capture
- Environment variable overrides: `MEM_CLAUDE_JSONL`, `MEM_CODEX_JSONL`, `MEM_JSONL_PATHS`
- Runtime state stored in `~/.mem-cli/`
- MIT license

### Fixed

- `mem serve --autostart` no longer prints `Boot-out failed: 5: Input/output error` on macOS when the LaunchAgent was not previously loaded. `launchctl bootout` stderr is now suppressed because errors are expected on a first install.
- `mem config` no longer writes `"I need permission to write the file…"` into `AGENTS.md`. The prompt now explicitly instructs the agent to output markdown to stdout only and not touch any files. As a belt-and-suspenders measure, the Claude command now passes `--allowedTools ""` so tool use is disabled at the CLI level too.
