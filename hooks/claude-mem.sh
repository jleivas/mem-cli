#!/usr/bin/env bash
# claude-mem.sh — Claude Code Stop hook for mem
#
# Reads the Stop hook payload from stdin, extracts token usage,
# and appends a JSONL event to the file watched by mem.
#
# Install:
#   1. Copy or symlink this script to a stable path, e.g. ~/.mem-cli/hooks/claude-mem.sh
#   2. Make it executable: chmod +x ~/.mem-cli/hooks/claude-mem.sh
#   3. Add the Stop hook to ~/.claude/settings.json (see README for the exact stanza)
#   4. Set MEM_CLAUDE_JSONL in your shell profile (or let it default below)

set -euo pipefail

JSONL_FILE="${MEM_CLAUDE_JSONL:-$HOME/.mem-cli/claude.jsonl}"
mkdir -p "$(dirname "$JSONL_FILE")"

python3 - "$JSONL_FILE" <<'PYEOF'
import sys, json, datetime, os

jsonl_file = sys.argv[1]
try:
    payload = json.load(sys.stdin)
except (json.JSONDecodeError, ValueError):
    sys.exit(0)

# Usage may sit at the top level or nested inside a "usage" key.
usage = payload if "input_tokens" in payload else payload.get("usage") or {}
input_tokens = int(usage.get("input_tokens") or 0)
output_tokens = int(usage.get("output_tokens") or 0)
cache_creation = int(usage.get("cache_creation_input_tokens") or 0)
cache_read = int(usage.get("cache_read_input_tokens") or 0)

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

with open(jsonl_file, "a") as fh:
    fh.write(json.dumps(event) + "\n")
PYEOF
