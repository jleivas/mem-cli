# mem-cli

`mem-cli` is a local, open source, cross-platform CLI for token observability and agent memory.

- **Local monitor** — tracks token events from Claude and Codex
- **Live dashboard** — real-time terminal view of token usage
- **Project memory** — per-project memory with tagging and search
- **MCP server** — exposes memory and observability as tools for any MCP-compatible agent

---

## Installation

Requires Python 3.11+.

```bash
pip install -e .
```

Development dependencies:

```bash
pip install -e ".[dev]"
```

---

## Quick Start

```bash
# Launch the interactive menu
mem

# Or use commands directly
mem start        # start the background monitor
mem dashboard    # open the live token dashboard
mem status       # check monitor runtime state
mem stop         # stop the monitor
```

---

## Memory Commands

Store and retrieve project-scoped memories from any terminal.

```bash
# Store a memory (scoped to the current directory)
mem remember "use postgres for all new services" --tag architecture

# List all memories for this project
mem recall

# Search by content
mem recall "postgres"

# Filter by tag
mem recall --tag architecture

# Delete a memory
mem forget <id>

# List all projects that have memories
mem projects

# Initialize memories from an AI agent (Claude or Codex)
mem init
mem init --agent claude
```

---

## MCP Server

`mem serve` starts a local MCP server over stdio. It exposes all memory and
observability operations as tools so agents can read and write project memories
and inspect token usage without running shell commands.

### Available tools

| Tool | Description |
|---|---|
| `memory_remember` | Store a memory for a project |
| `memory_recall` | List memories with optional query and tag filters |
| `memory_forget` | Delete a memory by ID |
| `memory_projects` | List all projects that have memories |
| `monitor_snapshot` | Current token usage snapshot for all tracked agents |
| `monitor_status` | Runtime state of the background monitor process |
| `monitor_start` | Start the background monitor |
| `monitor_stop` | Stop the background monitor |

### Registering with Claude Code

Add the following to your Claude Code `settings.json`
(`~/.claude/settings.json` or the workspace-level `.claude/settings.json`):

```json
{
  "mcpServers": {
    "mem": {
      "command": "mem",
      "args": ["serve"]
    }
  }
}
```

Then restart Claude Code. The `mem` tools will appear automatically when an
agent calls any `mem.*` tool.

### Registering with a custom MCP client

The server speaks the MCP stdio transport, so any MCP-compatible host can
launch it the same way:

```json
{
  "mcpServers": {
    "mem": {
      "command": "mem",
      "args": ["serve"]
    }
  }
}
```

If `mem` is not in `PATH`, use the full path to the executable:

```json
{
  "mcpServers": {
    "mem": {
      "command": "/path/to/mem",
      "args": ["serve"]
    }
  }
}
```

### Running the server manually (for debugging)

```bash
mem serve
```

The server blocks and communicates over stdin/stdout. You can use the
[MCP Inspector](https://github.com/modelcontextprotocol/inspector) to test it:

```bash
npx @modelcontextprotocol/inspector mem serve
```

### Tool reference

#### `memory_remember`

```
memory_remember(content, tags?, cwd?)
```

- `content` — text to store
- `tags` — optional list of strings
- `cwd` — absolute project path; defaults to the caller's working directory

Returns the saved memory with `id`, `project`, `content`, `tags`, `timestamp`.

#### `memory_recall`

```
memory_recall(query?, tag?, cwd?)
```

- `query` — substring filter on content
- `tag` — filter by a single tag
- `cwd` — absolute project path

Returns a list of memory objects, newest first.

#### `memory_forget`

```
memory_forget(memory_id, cwd?)
```

Returns `{ "deleted": true|false, "id": "..." }`.

#### `memory_projects`

```
memory_projects()
```

Returns a list of `{ "project", "project_name", "memory_count" }` objects.

#### `monitor_snapshot`

```
monitor_snapshot()
```

Returns a list of agent usage objects:

```json
[
  {
    "agent_name": "claude",
    "input_tokens": 1200,
    "output_tokens": 4800,
    "total_tokens": 6000,
    "average_tokens_per_minute": 120.0,
    "last_updated": "2026-04-21T10:00:00",
    "state": "active",
    "source": "jsonl"
  }
]
```

#### `monitor_status`

```
monitor_status()
```

Returns `{ "running", "pid", "started_at", "last_updated" }`.

#### `monitor_start` / `monitor_stop`

```
monitor_start()
monitor_stop()
```

Both return `{ "ok": true|false, "pid"?, "started_at"?, "error"? }`.

---

## Agent Hooks

Hook scripts for token capture live in the `hooks/` directory.

| Script | Agent | Purpose |
|---|---|---|
| `claude-mem.sh` | Claude Code | Capture token usage at session end |
| `codex-mem.py` | Codex CLI | Capture token usage (background watcher) |

Memory management for Claude Code is handled entirely through the MCP server — no hooks needed.

---

## Claude Code — Memory via MCP

Claude Code reads and writes project memories through the `mem` MCP server. No shell hooks or
scripts are needed for memory management — the MCP tools are the single interface.

### How it works

```
Claude Code starts
  └─ Launches mem serve over stdio (registered in mcpServers)
  └─ mem.* tools available from turn one

First turn in a project
  └─ Claude calls memory_recall(cwd="$PWD") to load stored context

During the session
  └─ Claude calls memory_remember(...) when it learns something worth keeping
  └─ Claude calls memory_forget(id) when a memory is stale or wrong

No hooks, no scripts, no injected context — MCP handles everything.
```

### 1. Register the MCP server in `~/.claude/settings.json`

```json
{
  "mcpServers": {
    "mem": {
      "command": "mem",
      "args": ["serve"]
    }
  }
}
```

If `mem` is not in `PATH`, use the full executable path:

```json
{
  "mcpServers": {
    "mem": {
      "command": "/path/to/mem",
      "args": ["serve"]
    }
  }
}
```

Restart Claude Code after editing the file.

### 2. Generate AGENTS.md and sync CLAUDE.md

Run `mem config` inside your project:

```bash
# Generate the synced project pair: AGENTS.md + CLAUDE.md
mem config

# Generate the sync pair using Claude as the authoring agent
mem config --agent claude

# Generate the sync pair using Codex as the authoring agent
mem config --agent codex

```

`mem config` asks the selected agent to generate or update `AGENTS.md` dynamically from the
current repository context. `AGENTS.md` is the canonical file, and `CLAUDE.md` is created as a
symlink to it. The generated content keeps shared instructions plus Claude-only and Codex-only
sections when needed, and includes the `mem` MCP workflow: `memory_recall`, `memory_remember`,
and `memory_forget`.

### 3. Token capture hook (optional)

The only hook needed is for token tracking. Install `claude-mem.sh` as a `Stop` hook:

```bash
mkdir -p ~/.mem-cli/hooks
cp hooks/claude-mem.sh ~/.mem-cli/hooks/claude-mem.sh
chmod +x ~/.mem-cli/hooks/claude-mem.sh
```

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "~/.mem-cli/hooks/claude-mem.sh"
          }
        ]
      }
    ]
  }
}
```

> **Token capture for Codex:** use `hooks/codex-mem.py` as a background
> watcher. It polls `~/.codex/sessions/` and writes token events to
> `~/.mem-cli/codex.jsonl`. See [`tokens-tracker.md`](tokens-tracker.md)
> for setup instructions.

---

## Token Data Sources

Set environment variables to point `mem-cli` at local JSONL files written by
your agent CLIs:

| Variable | Description |
|---|---|
| `MEM_CLAUDE_JSONL` | JSONL file for Claude token events |
| `MEM_CODEX_JSONL` | JSONL file for Codex token events |
| `MEM_JSONL_PATHS` | Extra comma-separated JSONL paths |

Example:

```bash
mkdir -p "$HOME/.mem-cli"
export MEM_CLAUDE_JSONL="$HOME/.mem-cli/claude.jsonl"
export MEM_CODEX_JSONL="$HOME/.mem-cli/codex.jsonl"
mem dashboard --view both
```

To capture Claude Code output into the expected file:

```bash
claude -p "hello" --verbose --output-format stream-json \
  | tee -a "$HOME/.mem-cli/claude.jsonl"
```

For full capture setup, see [`tokens-tracker.md`](tokens-tracker.md).

---

## Runtime State

`mem` stores minimal runtime state in `~/.mem-cli/` by default. The directory
is small and safe to delete when the monitor is stopped.

---

## Project Layout

```
src/mem/
  cli.py           # CLI entrypoint (typer)
  app.py           # monitor service factory
  config.py        # path resolution helpers
  mcp/
    server.py      # FastMCP server with all tools
  models/          # data models (TokenEvent, Memory, AgentStatus)
  services/        # business logic (MemoryService, MonitorService, …)
  storage/         # persistence (MemoryStore, RuntimeStateStore, …)
  ui/              # live dashboard
  utils/           # logging, time helpers
tests/             # pytest suite
```

---

## Roadmap

See [`docs/roadmap.md`](docs/roadmap.md).
