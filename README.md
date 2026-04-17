# mem-cli

`mem-cli` is a local, open source, cross-platform CLI for token observability and agent memory.

It starts as a lightweight MVP focused on:

- a portable CLI
- lifecycle commands for a local monitor
- a real-time terminal dashboard
- a modular architecture ready for project memory and a local MCP server later

## Vision

The long-term goal is to help tools like Codex, Claude, and other agents keep useful project memory locally, expose token usage, and provide a clean path toward a local MCP backend.

The project is intentionally starting small. This first release is only the foundation.

## MVP Scope

What this MVP does:

- installs as a `mem` command
- starts a local monitor process
- stops the monitor process
- reports current runtime status
- shows a live terminal dashboard with real token usage from local JSONL events
- keeps the codebase modular for future growth

What it does not do yet:

- persistent project memory
- embeddings
- vector databases
- semantic search
- real integrations with Claude or Codex APIs
- a full MCP server
- cloud services

## Quick Start with Real Token Data

The fastest path to seeing real data in the dashboard:

```bash
# 1. Install
pip install -e .

# 2. Start the dashboard
mem dashboard

# In another terminal — send a Claude Code command and capture it
claude -p "hello" --verbose --output-format stream-json | tee -a "$HOME/.mem-cli/claude.jsonl"
```

The dashboard polls both files every second. Token counts appear within two seconds of each captured event.

---

## Local JSONL Adapters

`mem-cli` reads token events from local JSON or JSONL files written by the CLIs you already use.

Use these environment variables:

- `MEM_CODEX_JSONL` for a JSONL file that represents Codex token events
- `MEM_CLAUDE_JSONL` for a JSONL file that represents Claude token events
- `MEM_JSONL_PATHS` for extra comma-separated JSONL paths

The adapter accepts one JSON object per line, a pretty-printed JSON document, or a JSON array of events. Example:

```jsonl
{"agent_name":"codex","input_tokens":18,"output_tokens":42,"timestamp":"2026-04-15T15:10:00+00:00","source":"codex-local"}
{"agent_name":"claude","input_tokens":12,"output_tokens":21,"timestamp":"2026-04-15T15:10:05+00:00","source":"claude-local"}
```

If `agent_name` is omitted, the configured agent label is used.

Example configuration:

```bash
mkdir -p "$HOME/.mem-cli"
export MEM_CODEX_JSONL="$HOME/.mem-cli/codex.jsonl"
export MEM_CLAUDE_JSONL="$HOME/.mem-cli/claude.jsonl"
mem dashboard --view both
```

If the files are empty or not configured, the dashboard will stay idle instead of fabricating token data.

For Claude and Codex capture setup, see [`tokens-tracker.md`](tokens-tracker.md).

## Installation

Requires Python 3.11+.

```bash
pip install -e .
```

If you want development dependencies:

```bash
pip install -e ".[dev]"
```

## Usage

Start the local monitor:

```bash
mem start
```

Check status:

```bash
mem status
```

Open the live dashboard:

```bash
mem dashboard
```

Stop the monitor:

```bash
mem stop
```

Show the version:

```bash
mem version
```

## Runtime State

`mem` stores minimal runtime state locally in the user home directory by default (`~/.mem-cli/`). The state is intentionally small and easy to clean up.

## Roadmap

1. Real token tracking adapters
2. Persistent memory per project
3. Local MCP server
4. Plugins and agent adapters

## Project Layout

The repository is organized to keep the CLI, services, UI, storage, models, and utilities separate so each layer can evolve independently.
