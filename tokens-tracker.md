# Token Tracker Setup

This guide covers how to capture token usage from Claude Code and Codex into local JSONL files that `mem` can read in real time.

## Overview

`mem-cli` reads token events from local JSON or JSONL files. The default paths are:

- `MEM_CLAUDE_JSONL` -> Claude events
- `MEM_CODEX_JSONL` -> Codex events

If the variables are not set, `mem` falls back to its local defaults under the app home directory.

## Claude Code Hook

Claude Code can write one JSONL record at the end of each session using a `Stop` hook.

### 1. Install the hook script

```bash
mkdir -p "$HOME/.mem-cli/hooks"
cp hooks/claude-mem.sh "$HOME/.mem-cli/hooks/claude-mem.sh"
chmod +x "$HOME/.mem-cli/hooks/claude-mem.sh"
```

### 2. Register the hook

Add the hook to `~/.claude/settings.json`:

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

If the file already exists, merge this block into it.

### 3. Set the output path

```bash
export MEM_CLAUDE_JSONL="$HOME/.mem-cli/claude.jsonl"
```

### 4. Verify

Run a short Claude Code session, then inspect the file:

```bash
tail -5 "$HOME/.mem-cli/claude.jsonl"
```

Example record:

```jsonl
{"agent_name":"claude","input_tokens":312,"output_tokens":87,"timestamp":"2026-04-17T14:00:00+00:00","source":"claude-code-hook"}
```

## Codex Wrapper

Codex does not expose a native hook system, so the recommended setup is a shell wrapper that tees `codex exec --json` output into the tracked JSONL file.

### 1. Set the output path

```bash
export MEM_CODEX_JSONL="$HOME/.mem-cli/codex.jsonl"
```

### 2. Add the wrapper

Add this function to your shell profile:

```bash
codex-track() {
  mkdir -p "$(dirname "${MEM_CODEX_JSONL:-$HOME/.mem-cli/codex.jsonl}")"
  command codex exec --json "$@" \
    | tee -a "${MEM_CODEX_JSONL:-$HOME/.mem-cli/codex.jsonl}"
}
```

### 3. Use it for tracked requests

```bash
codex-track "what does this project do?"
```

### 4. Verify

Inspect the file after a run:

```bash
tail -5 "${MEM_CODEX_JSONL:-$HOME/.mem-cli/codex.jsonl}"
```

## Local JSONL Format

`mem` accepts:

- one JSON object per line
- a pretty-printed JSON document
- a JSON array of events

Each record should include token counts in either top-level fields or nested `usage` blocks.

Example:

```jsonl
{"agent_name":"codex","input_tokens":18,"output_tokens":42,"timestamp":"2026-04-15T15:10:00+00:00","source":"codex-local"}
{"agent_name":"claude","input_tokens":12,"output_tokens":21,"timestamp":"2026-04-15T15:10:05+00:00","source":"claude-local"}
```

## Dashboard

Start the dashboard after configuring the capture paths:

```bash
mem dashboard
```

If the files are empty or not configured, the dashboard stays idle instead of fabricating data.
