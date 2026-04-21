# Changelog

All notable changes to mem-cli are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.1.0] — 2026-04-21

### Added

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
