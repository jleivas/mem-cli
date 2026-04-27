---
name: mcp-autostart-configuration
description: Use when working on MCP stop/autostart behavior so mem serve stop only stops the running MCP server and mem serve --disable-autostart is the only command that disables MCP autostart.
---

# MCP Autostart Configuration

Use this skill when changing the MCP stop flow or autostart lifecycle.

## Required Behavior

- `mem serve stop` must only stop the running MCP server process.
- `mem serve stop` must not disable MCP autostart.
- `mem serve --disable-autostart` is the only command that disables MCP autostart.
- `mem serve --autostart` enables MCP autostart.
- Keep process stop and autostart configuration separate.

## Required Message

If the user stops the MCP server, do not mention autostart being disabled unless they explicitly ran `mem serve --disable-autostart`.

## Implementation Notes

- Preserve live process state as the source of truth for stopping.
- Treat autostart configuration as a separate concern from process lifecycle.
- If `mem serve stop` removes or rewrites autostart config, that is a bug.

## Files to Check

- `src/mem/cli.py`
- `src/mem/services/autostart.py`
- `src/mem/services/process_registry.py`
- `src/mem/mcp/server.py`
- `tests/test_cli.py`

## Tests

- Cover `mem serve stop` stopping the running server without changing autostart.
- Cover `mem serve --disable-autostart` as the only autostart-off path.
- Cover `mem serve --autostart` enabling autostart.
