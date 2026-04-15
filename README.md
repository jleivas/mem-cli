# agent-recall

`agent-recall` is a local, open source, cross-platform CLI for agent memory and usage observability.

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

- installs as an `agent-recall` command
- starts a local monitor process
- stops the monitor process
- reports current runtime status
- shows a live terminal dashboard with simulated token usage
- keeps the codebase modular for future growth

What it does not do yet:

- persistent project memory
- embeddings
- vector databases
- semantic search
- real integrations with Claude or Codex APIs
- a full MCP server
- cloud services

## Local JSONL Adapters

`agent-recall` can read token events from local JSONL files before real adapters exist.

Use these environment variables:

- `AGENT_RECALL_CODEX_JSONL` for a JSONL file that represents Codex token events
- `AGENT_RECALL_CLAUDE_JSONL` for a JSONL file that represents Claude token events
- `AGENT_RECALL_JSONL_PATHS` for extra comma-separated JSONL paths
- `AGENT_RECALL_USE_SIMULATED` to keep simulated events on by default

The adapter expects one JSON object per line. Example:

```jsonl
{"agent_name":"codex","input_tokens":18,"output_tokens":42,"timestamp":"2026-04-15T15:10:00+00:00","source":"codex-local"}
{"agent_name":"claude","input_tokens":12,"output_tokens":21,"timestamp":"2026-04-15T15:10:05+00:00","source":"claude-local"}
```

If `agent_name` is omitted, the configured agent label is used.

Example configuration:

```bash
export AGENT_RECALL_CODEX_JSONL="$HOME/.agent-recall/codex.jsonl"
export AGENT_RECALL_CLAUDE_JSONL="$HOME/.agent-recall/claude.jsonl"
export AGENT_RECALL_USE_SIMULATED=0
agent-recall dashboard --view both
```

If you want the demo to stay alive even when those files are empty, leave simulated events enabled or omit the JSONL paths.

### Capture from Codex CLI

Codex CLI supports newline-delimited JSON with `--json`, which is the right format for `agent-recall` to tail locally:

```bash
codex --json "review this project" | tee -a "$HOME/.agent-recall/codex.jsonl"
```

If the emitted JSON event includes token usage metadata, `agent-recall` will pick it up automatically.

### Capture from Claude CLI

Claude Code supports structured JSON output for print mode:

```bash
claude -p "review this project" --bare --output-format json | tee "$HOME/.agent-recall/claude.jsonl"
```

Anthropic documents that the JSON output includes metadata such as usage. `agent-recall` will read that metadata when present.

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
agent-recall start
```

Check status:

```bash
agent-recall status
```

Open the live dashboard:

```bash
agent-recall dashboard
```

Stop the monitor:

```bash
agent-recall stop
```

Show the version:

```bash
agent-recall version
```

## Runtime State

`agent-recall` stores minimal runtime state locally in the user home directory by default. The state is intentionally small and easy to clean up.

## Roadmap

1. Real token tracking adapters
2. Persistent memory per project
3. Local MCP server
4. Plugins and agent adapters

## Project Layout

The repository is organized to keep the CLI, services, UI, storage, models, and utilities separate so each layer can evolve independently.
