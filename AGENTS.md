# mem-cli Agent Instructions

This repository is `mem-cli`, a Python 3.11+ CLI for local token observability and project memory.

## Project Overview

- Package name: `mem-cli`
- CLI entrypoint: `mem`
- Main package: `src/mem`
- Tests: `tests/`
- Build artifacts: `dist/`

## Working Rules

- Keep changes small and focused.
- Preserve existing behavior unless the task explicitly changes it.
- Add or update tests when behavior changes.
- Use `apply_patch` for file edits.
- Do not revert user changes outside the current task.

## Core Commands

```bash
mem                # interactive menu
mem serve          # start the MCP server
mem setup          # enable autostart and start MCP now
mem config         # generate AGENTS.md and sync CLAUDE.md
pytest tests/      # run the test suite
python -m build    # build distribution artifacts
```

## Memory Conventions

- Store stable facts only: entrypoints, routes, env keys, adapter names, and repeatable fixes.
- Do not store secrets, tokens, volatile state, or one-off debugging noise.
- Keep entries short and project-scoped.
- Refresh memory when commands, modules, or paths are renamed.

## Repository Layout

```text
src/mem/
  cli.py              # Typer CLI app
  app.py              # monitor service wiring
  config.py           # path resolution helpers
  version.py          # single source of version
  services/
    adapters/         # token source adapters and discovery
    memory_service.py # memory CRUD
    autostart.py      # cross-platform MCP autostart
    process_registry.py
    prompt_service.py
    embedding_service.py
  mcp/server.py      # FastMCP server
  storage/           # memory/runtime/token persistence
  ui/                # Rich dashboard
hooks/               # Claude/Codex integration scripts
scripts/             # release helpers
```

## MCP Usage

- Use `memory_recall` before edits when prior project context matters.
- Use `memory_remember` after confirming stable facts worth keeping.
- Use `memory_forget` when a fact is stale, renamed, or wrong.

## AGENTS and CLAUDE Files

- `mem config` generates `AGENTS.md` and keeps `CLAUDE.md` as a symlink to it.
- Do not create backup copies or extra markdown variants.
- Keep `CLAUDE.md` synchronized through `AGENTS.md` only.

## Notes for Agents

- Prefer `rg` for search and `sed` for inspection.
- Run targeted tests for the files you change.
- If the virtualenv is broken, report it clearly instead of guessing.
