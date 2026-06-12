# Changelog

All notable changes to mem-cli are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---
## [0.1.16] — 2026-06-12

### Added

- `mem serve` now enters a persistent **daemon mode** when stdin is `/dev/null` (spawned by LaunchAgent or `start_hidden_mcp_server`): writes its PID to the MCP state file and stays alive instead of exiting on stdio EOF.

### Fixed

- `mem setup` no longer spawns a redundant background process on top of the LaunchAgent; it waits for the LaunchAgent-started daemon to register and shows a warning on timeout without rolling back the autostart configuration.

### Changed

- Removed `KeepAlive` from the macOS LaunchAgent plist — the daemon now stays running, so automatic restarts are unnecessary.
- MCP client pipe connections (`stdin` is a real pipe, e.g. from Claude Code) bypass the "already running" guard and never overwrite daemon state in the MCP state file.

---
## [0.1.15] — 2026-06-12

### Fixed

- Fixed `mem setup` on Homebrew-installed binaries: when running as a PyInstaller frozen binary (`sys.frozen=True`), `sys.executable` points to the `mem` binary itself and does not accept `-c`. The Python supervisor is now skipped and stderr is redirected directly to the log file instead.

---
## [0.1.14] — 2026-06-12

### Fixed

- Build Intel Mac (x86_64) binary on the ARM runner via Rosetta 2 using python.org universal2 Python, eliminating the `bad CPU type in executable` error on Intel Macs.

---
## [0.1.13] — 2026-06-12

### Fixed

- Use a single ARM64 macOS binary for all Macs (Intel + Apple Silicon via Rosetta 2), eliminating the unavailable `macos-13` CI runner dependency.

---
## [0.1.12] — 2026-06-12

### Fixed

- Added Intel Mac (`macos-13`) binary to the CI release matrix so `brew install` no longer attempts to compile from source on Intel Macs.
- Simplified Homebrew formula to use pre-built binaries for all platforms, removing `Language::Python::Virtualenv` and resource blocks.

---
## [0.1.11] — 2026-06-12

### Fixed

- Made `mem version` and `mem --version` skip runtime environment bootstrap so Homebrew sandbox checks can run without creating `MEM_HOME`.

---
## [0.1.10] — 2026-06-12

### Fixed

- Fixed Homebrew formula generation by escaping Ruby block braces inside the Python template.

---
## [0.1.9] — 2026-06-12

### Changed

- Updated the Homebrew formula generator to use `virtualenv_install_with_resources` for Intel macOS source installs.
- Hardened Homebrew binary installs by locating the `mem` executable inside release artifacts, ensuring it is executable, and setting `MEM_HOME` during formula tests.

### Fixed

- `mem version` and `mem --version` now return version output without configuring logging.

---

## [0.1.8] — 2026-06-12

### Changed

- Reused the same background MCP startup flow for `mem serve --background` and `mem setup`.
- `mem setup` now renders the standard status action after enabling autostart and starting the MCP server.

### Fixed

- `mem setup` now rolls back autostart consistently when background server startup fails.

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
