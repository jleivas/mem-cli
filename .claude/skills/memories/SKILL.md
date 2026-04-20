---
name: memories
description: Use when recording or updating project memory so information stays compressed into a fixed taxonomy and minimizes token usage per project.
---

# Memories

Use the `mem` CLI to store, retrieve, and manage project-scoped memories. Each memory
is a short, concrete fact tied to the current working directory.

## CLI commands

| Command | Usage | Description |
|---|---|---|
| `mem remember "<fact>" --tag <category>` | `mem remember "uses Typer for CLI" --tag architecture` | Store a new memory for the current project. Use `-t` to add multiple tags. |
| `mem recall` | `mem recall` / `mem recall "typer"` | List memories for the current project, newest first. Pass a query to filter by substring. |
| `mem forget <id>` | `mem forget e52d0eef` | Delete a memory by its 8-character ID. Exits with code 1 if not found. |
| `mem projects` | `mem projects` | List all projects that have stored memories with their memory count. |
| `mem init --agent <claude\|codex>` | `mem init --agent claude` | Analyze the current project with an AI agent and auto-generate memories by category. Asks for confirmation if the project already has memories. |

## How `mem init` works

### Execution flow

1. **Agent detection** — checks which agents are installed in `PATH` (`claude`, `codex`). If none found, prints install instructions and exits.
2. **Agent selection** — if `--agent` is not provided and more than one agent is available, shows an interactive picker. If only one is installed, selects it automatically.
3. **Existing memory guard** — if the current project already has stored memories, warns the user and asks `Replace all memories? (y/N)`. Answering `y` deletes all existing memories before proceeding. Anything else cancels with exit code 0.
4. **Prompt rendering** — loads the base prompt template (see below), replaces `{cwd}` and `{project_name}` placeholders with the current project path and folder name.
5. **Agent execution** — runs the agent as a subprocess, streaming its stdout line by line in real time. A live spinner shows progress. Each `mem remember` command parsed from the output is executed immediately and displayed with a ✓ checkmark.
6. **Outcome** — on success, shows a summary table of all saved memories grouped by tag. On partial failure (agent exited early but some commands ran), shows the summary plus a warning. On full failure (agent never started or produced no output), shows the error cause.

### Base prompt

The prompt template lives at:

```
src/mem/prompts/project_memory.md   ← built-in, ships with the package
~/.mem-cli/prompts/project-memory.md  ← user override, takes precedence if present
```

The template instructs the agent to read project files in a defined order (README, manifest, config, entry points, up to 5 source files — max 20 files total), then output only `mem remember` commands, one per line, with no commentary.

### How commands are parsed and executed

The CLI scans each output line with this pattern:

```
mem remember "<content>" --tag <tag>
```

When a match is found it calls `MemoryService.remember()` directly — no subprocess, no shell. The memory is written to `~/.mem-cli/projects/<project-slug>/memories.jsonl` immediately.

Lines that do not match the pattern are shown as a dim progress hint and discarded.

## Categories

Use only these tags when storing memories:

- `decisions`: architectural or product choices that should not be re-litigated.
- `conventions`: naming, style, folder layout, or process rules.
- `architecture`: system structure, module boundaries, data flow.
- `bugs`: known failures or risky behavior.
- `fixes`: the resolution that addressed a bug.
- `pending`: open follow-ups or unfinished work.
- `commands`: useful local commands for build, test, run, or deploy.
- `key-files`: files that matter most for orientation in the codebase.

## Rules

1. Do not create new memory categories.
2. Prefer the smallest useful entry for each item — under 120 characters.
3. Keep each note project-scoped and concrete.
4. Record commands only when they are reusable or diagnose an important workflow.
5. Record key files only when they are central to understanding the project.
6. If a fact fits multiple categories, place it in the most specific one only — never repeat it.
7. Use this taxonomy to reduce duplicate context and optimize token consumption for agents working on the same project.

