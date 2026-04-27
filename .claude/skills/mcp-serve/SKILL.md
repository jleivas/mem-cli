---
name: mcp-serve
description: Use when working on mem serve, MCP autostart, or mem status behavior so the MCP server starts only once and status reflects the real running state.
---

# MCP Serve

Use this skill when changing `mem serve`, `mem status`, or the MCP autostart flow.

## Goal

The MCP server must behave like a singleton:

- `mem serve` must start only once, regardless of launch mode.
- The rule applies to normal, `--background`, and `--new-terminal` launches.
- If a server is already running, stop and do not start a second one.
- Show the user an English message like: `MCP server is already running.`

## Required Behavior

- Check whether the MCP server is already running before launching.
- Reuse the real MCP runtime state, not only the autostart flag.
- `mem status` must report whether the MCP server is actually running.
- Do not infer `running` from autostart alone.

## Implementation Targets

When editing the code, focus on:

- `src/mem/cli.py`
- `src/mem/mcp/server.py`
- `src/mem/storage/runtime_state.py`
- `src/mem/services/process_registry.py`
- `tests/test_cli.py`

## Testing Expectations

- Add or update tests for:
  - duplicate `mem serve` launches
  - `--background`
  - `--new-terminal`
  - `mem status` reporting the real MCP state
- Keep the expected error message in English.
- Verify that `mem serve` exits instead of spawning a second process when already running.

## Practical Rule

If there is any ambiguity between autostart configuration and live process state, trust the live process state first.
