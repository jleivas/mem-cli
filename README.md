# mem-cli

**mem-cli** is a local, open-source CLI tool that gives AI coding agents (Claude Code, Codex) two things they normally lack between sessions: **token usage visibility** and **persistent project memory**.

Without mem-cli, every agent session starts blind — no memory of past decisions, no way to see how many tokens you've spent. mem-cli fixes both.

---

## What it does

| Capability | What you get |
|---|---|
| **Project memory** | Store and retrieve facts scoped to a project directory. Works from the terminal or via MCP tools called directly by an agent. |
| **Token monitor** | Background process that captures token events from Claude and Codex sessions as they happen. |
| **Live dashboard** | Real-time terminal view of token usage per agent, updated as events arrive. |
| **MCP server** | Exposes all memory and observability operations as MCP tools so any compatible agent can call them without running shell commands. |

### How agent memory works

```
You open a project
  └─ mem serve launches over stdio (registered as an MCP server)
  └─ Agent calls memory_recall(cwd) → loads prior context

During the session
  └─ Agent calls memory_remember(...) → stores a fact
  └─ Agent calls memory_forget(id) → removes a stale fact

Next session, same project
  └─ memory_recall returns everything that was stored — no manual copying needed
```

Memory is scoped to the project directory, stored locally under the mem app home
directory, and never sent anywhere. By default this is `~/.mem-cli/` on Unix-like
systems and `%LOCALAPPDATA%\\mem-cli\\` on Windows unless `MEM_HOME` is set.

---

## Requirements

- Python 3.11 or later
- pip

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-org/mem-cli.git
cd mem-cli
```

### 2. Install the package

For local development:

```bash
pip install -e .
```

This installs the `mem` command globally (within your Python environment).

To also install development dependencies (pytest, etc.):

```bash
pip install -e ".[dev]"
```

To install the release tooling (needed to run `scripts/release_build.py`):

```bash
pip install -e ".[release]"
```

The release helpers live under `scripts/` and are not part of the installed
`mem` runtime package.

For an isolated end-user install, `pipx` is the preferred path:

```bash
pipx install .
```

You can also install a released wheel artifact directly:

```bash
pipx install dist/mem_cli-0.1.0-py3-none-any.whl
```

### 3. Verify the install

```bash
mem --version
```

---

## Build And Release

The release flow is intentionally simple:

```bash
python scripts/sync_version.py
python scripts/release_build.py
```

This produces both:

- `dist/*.tar.gz` source distributions
- `dist/*.whl` wheel distributions

The build script clears old artifacts first, then rebuilds both formats from the
current checkout. These scripts are release-only helpers; they are not shipped
inside the `mem` package.

For multiplatform verification, the repository also includes a release workflow
that builds on Linux, macOS, and Windows, then installs the generated wheel and
checks `mem --version` on each platform.

---

## Adapters And Plugins

`mem` discovers external token source adapters through Python entry points in
the `mem.token_sources` group.

To inspect the available adapters for the current installation, run:

```bash
mem adapters
```

Built-in adapters include:

- `jsonl` for local JSON/JSONL token files
- `simulated` for demo and dashboard usage

External plugins should expose a zero-argument factory that returns a
`TokenSource`. The monitor will compose built-in and discovered sources.

---

## MCP Autostart

If you want `mem serve` to start automatically when you log in, install the
startup item once:

```bash
mem serve --autostart
```

This creates an OS-specific startup item:

- macOS: `~/Library/LaunchAgents/com.mem.cli.mcp.plist`
- Linux: `~/.config/systemd/user/mem-cli-mcp.service`
- Windows: `%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\mem-cli-mcp.cmd`

To stop the server and disable autostart:

```bash
mem mcp-stop
```

You can re-enable it later with `mem serve --autostart`.

---

## Quick Start

```bash
# Open the interactive menu (recommended first time)
mem

# Or run commands directly
mem start        # start the background token monitor
mem dashboard    # open the live token dashboard
mem status       # check whether the monitor is running
mem stop         # stop the monitor
```

---

## Memory Commands

Memories are scoped to the current working directory, so running `mem remember` inside a project stores context for that project only.

```bash
# Store a memory for the current project
mem remember "use postgres for all new services" --tag architecture

# List all memories for this project
mem recall

# Search by content
mem recall "postgres"

# Filter by tag
mem recall --tag architecture

# Delete a memory by ID
mem forget <id>

# List all projects that have memories
mem projects

# Auto-initialize memories from an AI agent (reads the repo and generates context)
mem init
mem init --agent claude
mem init --agent codex
```

---

## MCP Server

`mem serve` starts a local MCP server over stdio. Agents registered with it can call memory and observability operations as tools — no shell access required.

### Register with Claude Code

Add the following to `~/.claude/settings.json` (or a workspace-level `.claude/settings.json`):

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

If `mem` is not in your `PATH` (e.g. inside a virtualenv), use the full path:

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

Restart Claude Code after editing the file. The `mem.*` tools will be available automatically.

### Register with any MCP-compatible client

The server speaks the MCP stdio transport. Use the same JSON block above with any host that supports it.

### Run the server manually (debugging)

```bash
mem serve
```

The server blocks and communicates over stdin/stdout. To test it interactively:

```bash
npx @modelcontextprotocol/inspector mem serve
```

### Available MCP tools

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

## Token Capture Setup

### Claude Code

The background monitor picks up token events automatically when the hook is installed.

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

### Codex

Use `hooks/codex-mem.py` as a background watcher. It polls `~/.codex/sessions/` and writes token events to `~/.mem-cli/codex.jsonl`. See [`tokens-tracker.md`](tokens-tracker.md) for full setup instructions.

### Manual / environment variables

You can point mem-cli at any JSONL file written by your agent:

| Variable | Description |
|---|---|
| `MEM_CLAUDE_JSONL` | JSONL file for Claude token events |
| `MEM_CODEX_JSONL` | JSONL file for Codex token events |
| `MEM_JSONL_PATHS` | Extra comma-separated JSONL paths |

Example:

```bash
export MEM_CLAUDE_JSONL="$HOME/.mem-cli/claude.jsonl"
export MEM_CODEX_JSONL="$HOME/.mem-cli/codex.jsonl"
mem dashboard --view both
```

To pipe Claude output directly into the expected file:

```bash
claude -p "hello" --verbose --output-format stream-json \
  | tee -a "$HOME/.mem-cli/claude.jsonl"
```

---

## Project Setup for an Agent (AGENTS.md / CLAUDE.md)

Run `mem config` inside a project to generate `AGENTS.md` and a `CLAUDE.md` symlink. These files instruct the agent on how to use mem-cli tools within that project.

```bash
mem config                 # auto-detect agent
mem config --agent claude  # use Claude as the authoring agent
mem config --agent codex   # use Codex as the authoring agent
```

---

## Runtime State

mem-cli stores minimal runtime state in the mem app home directory. The
directory is safe to delete when the monitor is stopped.

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
hooks/             # shell/Python hook scripts for Claude and Codex
docs/              # architecture notes, roadmap, ASCII logo
```

---

## Roadmap

See [`docs/roadmap.md`](docs/roadmap.md).

## Changelog

See [`CHANGELOG.md`](CHANGELOG.md).
