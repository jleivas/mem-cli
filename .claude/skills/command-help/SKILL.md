---
name: command-help
description: Use when adding or changing CLI commands to keep `--help` output accurate and synchronized with the implementation.
---

# Command Help

When you add, rename, remove, or change a command, subcommand, flag, option, or argument:

1. Update the command implementation.
2. Update the matching `--help` output text, examples, and descriptions.
3. Update any CLI registry, command table, or Typer/Click metadata that feeds help text.
4. Update tests that assert help text, usage lines, or command listings.

Do not merge a command change if `--help` is stale or missing the new behavior.

Keep examples in help output short and current.
