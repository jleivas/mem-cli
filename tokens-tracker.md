# Token Tracker Setup

This guide covers how to capture token usage from Claude Code and Codex into local JSONL files that `mem` can read in real time.

## Overview

`mem-cli` reads token events from local JSON or JSONL files. The default paths are:

- `MEM_CLAUDE_JSONL` -> Claude events
- `MEM_CODEX_JSONL` -> Codex events

If the variables are not set, `mem` falls back to its local defaults under the app home directory.

## Claude Code Hook

Claude Code writes one JSONL record at the end of each session using a `Stop` hook.
The hook receives a payload with `session_id` and `transcript_path`; the script reads
the session transcript to extract token usage from the `assistant` entries (interactive
sessions) or the `result` entry (non-interactive `-p` invocations).

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

## Codex Session Watcher

Codex does not expose a native hook system. Instead, `codex-mem.py` watches
`~/.codex/sessions/` and streams new `token_count` updates into the mem JSONL file.

Codex writes a session JSONL file per run under `~/.codex/sessions/YYYY/MM/DD/`.
Each `token_count` event includes a `last_token_usage` block with the incremental
usage for that update. The watcher emits those deltas as soon as they appear, so the
dashboard can move before `task_complete` lands.

### 1. Install the watcher script

```bash
mkdir -p "$HOME/.mem-cli/hooks"
cp hooks/codex-mem.py "$HOME/.mem-cli/hooks/codex-mem.py"
chmod +x "$HOME/.mem-cli/hooks/codex-mem.py"
```

### 2. Set the output path

```bash
export MEM_CODEX_JSONL="$HOME/.mem-cli/codex.jsonl"
```

### 3. Register as a launchd agent (macOS)

Create `~/Library/LaunchAgents/com.mem-cli.codex-watch.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.mem-cli.codex-watch</string>

  <key>ProgramArguments</key>
  <array>
    <string>/opt/homebrew/bin/python3</string>
    <string>/Users/YOUR_USER/.mem-cli/hooks/codex-mem.py</string>
    <string>--watch</string>
  </array>

  <key>RunAtLoad</key>
  <true/>

  <key>KeepAlive</key>
  <true/>

  <key>StandardOutPath</key>
  <string>/Users/YOUR_USER/.mem-cli/runtime/codex-mem.log</string>

  <key>StandardErrorPath</key>
  <string>/Users/YOUR_USER/.mem-cli/runtime/codex-mem.log</string>

  <key>EnvironmentVariables</key>
  <dict>
    <key>MEM_CODEX_JSONL</key>
    <string>/Users/YOUR_USER/.mem-cli/codex.jsonl</string>
    <key>MEM_CODEX_POLL</key>
    <string>30</string>
  </dict>
</dict>
</plist>
```

Replace `YOUR_USER` with your macOS username, then load the agent (`load`/`unload` are
deprecated on modern macOS — use `bootstrap`/`bootout` instead):

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.mem-cli.codex-watch.plist
```

To stop or restart:

```bash
launchctl bootout   gui/$(id -u)/com.mem-cli.codex-watch
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.mem-cli.codex-watch.plist
```

To check status:

```bash
launchctl print gui/$(id -u)/com.mem-cli.codex-watch
```

### 4. Verify

Run a one-shot scan to process any existing sessions immediately:

```bash
python3 "$HOME/.mem-cli/hooks/codex-mem.py" --run
```

Then inspect the file:

```bash
tail -5 "$HOME/.mem-cli/codex.jsonl"
```

Example record:

```jsonl
{"agent_name":"codex","input_tokens":11476,"output_tokens":412,"timestamp":"2026-04-17T18:31:40+00:00","source":"codex-session-watch","session_id":"019d9cb6-6af5-7881-b00b-6563bc1fd26a","cache_read_input_tokens":10112,"reasoning_output_tokens":49}
```

Check the watcher log:

```bash
cat "$HOME/.mem-cli/runtime/codex-mem.log"
```

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `MEM_CODEX_JSONL` | `~/.mem-cli/codex.jsonl` | Output JSONL path |
| `MEM_CODEX_POLL` | `30` | Poll interval in seconds |

### State file

Processed sessions are tracked in `~/.mem-cli/runtime/codex-processed.json`
as per-file line cursors so incremental updates are not duplicated across restarts.

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
