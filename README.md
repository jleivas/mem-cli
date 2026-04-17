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

### Capture from Codex CLI — manual one-shot

The non-interactive subcommand is `codex exec`. Use `--json` to emit JSONL and tee it into the watched file:

```bash
codex exec --json "review this project" | tee -a "$HOME/.mem-cli/codex.jsonl"
```

The JSONL reader extracts token counts from top-level fields or nested `usage` objects.

### Capture from Codex CLI — automatic wrapper (recommended)

Codex CLI does not have a native hook system, so the recommended approach is a shell function wrapper that transparently tees JSONL output on every `codex exec` run.

#### 1. Set the environment variable

Add to your `~/.zshrc` or `~/.bashrc`:

```bash
export MEM_CODEX_JSONL="$HOME/.mem-cli/codex.jsonl"
```

#### 2. Add the wrapper function

In the same file, define a function that wraps `codex exec`:

```bash
codex-track() {
  mkdir -p "$(dirname "${MEM_CODEX_JSONL:-$HOME/.mem-cli/codex.jsonl}")"
  command codex exec --json "$@" \
    | tee -a "${MEM_CODEX_JSONL:-$HOME/.mem-cli/codex.jsonl}"
}
```

Reload your shell (`source ~/.zshrc`). Use `codex-track` instead of `codex exec` for runs you want monitored. Your normal `codex` invocations are unaffected.

#### 3. Verify the wrapper is working

Run a short Codex task and inspect the file:

```bash
tail -5 "${MEM_CODEX_JSONL:-$HOME/.mem-cli/codex.jsonl}"
```

You should see JSONL lines that include a `usage` block. `mem` normalises this automatically.

### Capture from Claude Code — manual one-shot

Claude Code supports structured JSON output for print mode with `-p` and `--output-format json`:

```bash
claude -p "review this project" --output-format json | tee -a "$HOME/.mem-cli/claude.jsonl"
```

For a line-oriented stream, `--output-format stream-json` combined with `--verbose` is usually a better fit. `mem` reads token fields from `usage`, `last_token_usage`, and similar nested blocks when present.

```bash
claude -p "review this project" --verbose --output-format stream-json | tee -a "$HOME/.mem-cli/claude.jsonl"
```

### Capture from Claude Code — automatic Stop hook (recommended)

Claude Code supports shell hooks that fire automatically at the end of every session. Use the **Stop** hook to append token usage to the JSONL file without changing your normal workflow.

#### 1. Install the hook script

Copy the script from the `hooks/` directory to a stable location and make it executable:

```bash
mkdir -p "$HOME/.mem-cli/hooks"
cp hooks/claude-mem.sh "$HOME/.mem-cli/hooks/claude-mem.sh"
chmod +x "$HOME/.mem-cli/hooks/claude-mem.sh"
```

#### 2. Register the hook in Claude Code settings

Open (or create) `~/.claude/settings.json` and add the `Stop` hook:

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

If `settings.json` already exists and contains other keys, merge the `"hooks"` block into the existing JSON — do not replace the whole file.

#### 3. Set the environment variable

Add this line to your `~/.zshrc` or `~/.bashrc`:

```bash
export MEM_CLAUDE_JSONL="$HOME/.mem-cli/claude.jsonl"
```

Reload your shell (`source ~/.zshrc`) and then start `mem` as usual.

#### How it works

After each Claude Code session the Stop hook fires. Claude Code passes a JSON payload — including the `usage` block with `input_tokens` and `output_tokens` — to the script via stdin. The script writes one JSONL line to the watched file, and the dashboard picks it up on the next poll cycle.

#### Verify the hook is working

Run a short Claude Code command, then inspect the file:

```bash
tail -5 "$HOME/.mem-cli/claude.jsonl"
```

You should see a new line similar to:

```jsonl
{"agent_name": "claude", "input_tokens": 312, "output_tokens": 87, "timestamp": "2026-04-17T14:00:00+00:00", "source": "claude-code-hook"}
```

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
