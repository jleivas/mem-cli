#!/usr/bin/env bash
# claude-mem.sh — Claude Code Stop hook for mem
#
# Reads the Stop hook payload from stdin, extracts token usage from the
# session transcript, and appends a JSONL event to the file watched by mem.
#
# The Stop hook payload is:
#   { "session_id": "...", "transcript_path": "/path/to/transcript.jsonl" }
#
# Usage totals come from the "type":"result" line in that transcript.
#
# Install:
#   1. Copy or symlink this script to a stable path, e.g. ~/.mem-cli/hooks/claude-mem.sh
#   2. Make it executable: chmod +x ~/.mem-cli/hooks/claude-mem.sh
#   3. Add the Stop hook to ~/.claude/settings.json (see README for the exact stanza)
#   4. Set MEM_CLAUDE_JSONL in your shell profile (or let it default below)

set -euo pipefail

JSONL_FILE="${MEM_CLAUDE_JSONL:-$HOME/.mem-cli/claude.jsonl}"
mkdir -p "$(dirname "$JSONL_FILE")"

payload="$(cat)"

PAYLOAD="$payload" python3 - "$JSONL_FILE" <<'PYEOF'
import datetime
import json
import os
import sys

jsonl_file = sys.argv[1]
raw_payload = os.environ.get("PAYLOAD", "")

try:
    payload = json.loads(raw_payload)
except (json.JSONDecodeError, ValueError):
    sys.exit(0)

if not isinstance(payload, dict):
    sys.exit(0)

# ------------------------------------------------------------------
# Strategy 1: transcript_path — interactive sessions store usage
# inside each "assistant" entry; sum across all turns.
# Non-interactive (-p) sessions also emit a "result" entry with
# cumulative totals — use that if present.
# ------------------------------------------------------------------
input_tokens = output_tokens = cache_creation = cache_read = 0

transcript_path = payload.get("transcript_path")
if transcript_path and os.path.isfile(transcript_path):
    result_usage = None
    try:
        with open(transcript_path, encoding="utf-8") as tf:
            for line in tf:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(entry, dict):
                    continue
                etype = entry.get("type")
                # Cumulative result entry (-p / non-interactive)
                if etype == "result":
                    result_usage = entry.get("usage") or {}
                # Per-turn usage inside interactive assistant messages
                elif etype == "assistant":
                    u = (entry.get("message") or {}).get("usage") or {}
                    input_tokens += int(u.get("input_tokens") or 0)
                    output_tokens += int(u.get("output_tokens") or 0)
                    cache_creation += int(u.get("cache_creation_input_tokens") or 0)
                    cache_read += int(u.get("cache_read_input_tokens") or 0)
    except OSError:
        pass
    # If a result entry was found, prefer its totals (more accurate)
    if result_usage:
        input_tokens = int(result_usage.get("input_tokens") or 0)
        output_tokens = int(result_usage.get("output_tokens") or 0)
        cache_creation = int(result_usage.get("cache_creation_input_tokens") or 0)
        cache_read = int(result_usage.get("cache_read_input_tokens") or 0)

# ------------------------------------------------------------------
# Strategy 2: fallback — payload itself may carry usage directly.
# ------------------------------------------------------------------
if input_tokens == 0 and output_tokens == 0:
    u = payload if "input_tokens" in payload else payload.get("usage") or {}
    input_tokens = int(u.get("input_tokens") or 0)
    output_tokens = int(u.get("output_tokens") or 0)
    cache_creation = int(u.get("cache_creation_input_tokens") or 0)
    cache_read = int(u.get("cache_read_input_tokens") or 0)

if input_tokens == 0 and output_tokens == 0:
    sys.exit(0)

event = {
    "agent_name": "claude",
    "input_tokens": input_tokens,
    "output_tokens": output_tokens,
    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "source": "claude-code-hook",
}
if cache_creation or cache_read:
    event["cache_creation_input_tokens"] = cache_creation
    event["cache_read_input_tokens"] = cache_read

with open(jsonl_file, "a", encoding="utf-8") as fh:
    fh.write(json.dumps(event) + "\n")
PYEOF
