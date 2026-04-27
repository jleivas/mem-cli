---
name: run-mcp-serve
description: Use when working on mem serve execution modes, mem status, or duplicate MCP server prevention so the server runs once and status reports the live process state.
---

# Run MCP Serve

Use this skill when changing or debugging `mem serve`, `mem status`, or the MCP server lifecycle.

## Required Behavior

- `mem serve` must show the MCP server in the current terminal, like it does now.
- `mem serve --background` must run hidden in the background and must not show the MCP server UI in the current terminal.
- `mem serve --new-terminal` must open a new terminal and show the MCP server there, like it does now.
- `mem status` must report the MCP server as `running` when any of the three modes is active.
- If the MCP server is already running, every `mem serve` mode must refuse to start another one.

## Required Message

When a server is already running, show this exact English message:

`MCP server is already running. Stop it with \`mem mcp-stop\` before starting a new one.`

## Implementation Notes

- Treat live process state as the source of truth.
- Do not rely only on autostart configuration.
- Preserve the current TTY behavior for normal `mem serve`.
- Keep `--background` silent in the current terminal except for errors.

## Files to Check

- `src/mem/cli.py`
- `src/mem/mcp/server.py`
- `src/mem/storage/runtime_state.py`
- `src/mem/services/process_registry.py`
- `src/mem/services/autostart.py`
- `tests/test_cli.py`

## Tests

- Cover normal `mem serve`, `--background`, and `--new-terminal`.
- Cover `mem status` reporting `running` when the server is active.
- Cover the duplicate-start rejection message.
