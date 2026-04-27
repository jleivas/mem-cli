It appears write access to this repository is requiring per-file approval each time. The permission dialog is appearing but not being confirmed. Please approve the write when prompted — either for `AGENTS.md` (new file) or `Agent.md` (existing canonical file that both `CLAUDE.md` and `Claude.md` symlink to).

Here is the complete content ready to write. Once you approve the permission, I'll write it to `Agent.md` (which already exists and is the symlink target), then create `AGENTS.md` as a symlink to it:

---

**Content for `Agent.md` (canonical source):**

```markdown
# Agent Instructions

This repository is `mem-cli` — a local CLI for token observability and agent memory, distributed as a Python package.

## Shared Project Overview

- Package name: `mem-cli` (PyPI: `mem-cli`)
- Python 3.11+; built with `setuptools`
- CLI entrypoint: `mem` → `src/mem/cli.py` → `mem.cli:main`
- MCP server entrypoint: `mem serve` → `src/mem/mcp/server.py`
- Tests: `tests/`
- Distribution artifacts: `dist/`

## Project Type Summary

This is a **backend service / CLI tool**. There is no frontend. Relevant sections: backend, files/directories (for storage layout), and MCP.

## MCP Usage for Mem

The MCP server (`mem serve`) exposes the following tools. Call them from any MCP-capable agent:

| Tool | Purpose |
|---|---|
| `memory_remember` | Persist a fact scoped to the current project (`cwd`) |
| `memory_recall` | Retrieve memories for the current project |
| `memory_forget` | Delete a memory by ID |
| `memory_projects` | List all projects with stored memories |
| `monitor_snapshot` | Read the latest token usage snapshot |
| `monitor_status` | Check monitor daemon status |
| `monitor_start` | Start the token monitor daemon |
| `monitor_stop` | Stop the token monitor daemon |

Workflow: call `memory_recall` before edits to load prior context; call `memory_remember` after confirming stable facts; call `memory_forget` when a fact is renamed, removed, or wrong.

## Shared Memory Conventions and Commands

**Useful commands:**

```
mem                        # interactive menu
mem serve                  # start MCP server
mem monitor start|stop     # daemon lifecycle
mem config                 # show/edit config
pytest tests/              # run all tests
pytest tests/test_<file>.py  # run targeted tests
python -m build            # build distribution
python scripts/release_build.py  # release helper
```

**Memory rules:**
- Store stable facts only: entrypoints, routes, model names, env keys, adapter names.
- Do not store secrets, tokens, volatile state, or customer data.
- One fact per entry; keep entries short.
- Refresh after renames of modules, commands, or storage paths.

## Backend-Specific Block

**Package layout:**

```
src/mem/
  cli.py              # Typer CLI app; all top-level commands
  app.py              # service wiring (build_monitor_service)
  config.py           # paths: JSONL logs, MCP state, runtime state
  version.py          # single source of version
  models/
    memory.py         # Memory dataclass
    token_event.py    # TokenEvent — normalized usage record
    agent_status.py   # AgentStatus
  services/
    adapters/
      jsonl_adapter.py   # parses Claude/Codex JSONL -> TokenEvent
      registry.py        # adapter discovery
    memory_service.py    # CRUD for Memory objects
    token_tracker.py     # aggregates TokenEvent streams
    monitor_service.py   # background monitor lifecycle
    autostart.py         # cross-platform MCP autostart
    macos_launchd.py     # macOS LaunchAgent install/remove
    process_registry.py  # track running daemon PIDs
    embedding_service.py # sentence-transformers embeddings
    prompt_service.py    # run agent prompts; detect available agents
  mcp/
    server.py         # FastMCP server; all @mcp.tool definitions
  storage/
    memory_store.py      # persist/load Memory objects
    token_snapshot.py    # persist/load TokenSnapshot
    runtime_state.py     # persist/load RuntimeState
    dashboard_history.py # rolling history for dashboard
  ui/
    dashboard.py      # Rich live dashboard; DashboardViewMode
  utils/
    logging.py
    time.py
  prompts/            # bundled .md prompt templates
hooks/
  claude-mem.sh       # Claude Code hook script
  codex-mem.py        # Codex hook script
scripts/
  release_build.py
  release_utils.py
  sync_version.py
```

**Key conventions:**
- `TokenEvent` is the canonical normalized token record; adapters must produce it.
- JSONL adapter must tolerate: JSONL (one object per line), JSON arrays, and pretty-printed JSON documents.
- Parse nested usage fields; do not assume a flat schema.
- Storage paths come from `config.py`; do not hardcode `~/.mem` or similar.
- Version is in `version.py`; `sync_version.py` keeps `pyproject.toml` in sync.

**Autostart / daemon:**
- Cross-platform autostart: `services/autostart.py`.
- macOS LaunchAgent: `services/macos_launchd.py`.
- Daemon PID tracking: `services/process_registry.py` + `storage/runtime_state.py`.

## Files/Directories-Specific Block

- `src/mem/prompts/` — bundled markdown prompt templates; included in wheel via `package-data`.
- `hooks/` — integration scripts for Claude Code (`claude-mem.sh`) and Codex (`codex-mem.py`); do not delete.
- `dist/` — build artifacts; do not commit generated wheels/tarballs.
- `tests/` — one test file per module; name pattern `test_<module>.py`.

## Claude-Specific Block

- Call `memory_recall` via MCP before editing to load prior stable context.
- Call `memory_remember` after confirming facts that should persist across sessions.
- Call `memory_forget` when a stored fact is stale, renamed, or removed.
- Keep `CLAUDE.md` as a symlink to `AGENTS.md`; edit `AGENTS.md` only.
- Do not create divergent instructions in `CLAUDE.md`.
- Use `apply_patch` for file edits; prefer small, focused diffs.
- Run targeted tests (`pytest tests/test_<changed_module>.py`) before reporting done.
- If the local virtualenv is broken, report it clearly rather than guessing.

## Codex-Specific Block

- Use `apply_patch` for all edits; do not overwrite unrelated user changes.
- Prefer `rg` and `sed` for read-only inspection before editing.
- Keep diffs small and local; update adjacent tests only when behavior changes.
- Do not remove hook scripts (`hooks/`), prompt templates (`prompts/`), or release scripts.
- When working in parallel with other agents, avoid touching files another agent owns.

## Sync Note

`CLAUDE.md` is a symlink to `AGENTS.md`. There is one canonical source. Edit `AGENTS.md` only.
```

---

**After writing, the symlink plan:**
- `AGENTS.md` → new canonical file (or `Agent.md` renamed/updated to this content)
- `CLAUDE.md` → symlink to `AGENTS.md`
- `Claude.md` → symlink to `AGENTS.md`

Please grant write permission for either `Agent.md` or `AGENTS.md` and I'll complete the operation.

## MCP Usage for mem
- Use mem MCP for durable project context.
- `memory_recall`: check this first when repo history, conventions, or prior decisions matter.
- `memory_remember`: store stable repo facts, validated conventions, and repeatable fixes.
- `memory_forget`: remove stale or incorrect memory when behavior or decisions change.

## Shared Memory Conventions and Commands
- Keep memories short, factual, and project-scoped.
- Do not store secrets, credentials, or one-off debugging noise.
- Prefer file names, endpoints, commands, and accepted conventions over narrative notes.
- Use `rg` for search and `apply_patch` for manual edits.
- Preserve existing user changes and avoid unrelated churn.
