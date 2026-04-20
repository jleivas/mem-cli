#!/usr/bin/env python3
"""
codex-mem — watches ~/.codex/sessions/ for completed Codex sessions
and appends token usage events to the mem-cli JSONL file.

A session is considered complete when it contains a
  { "type": "event_msg", "payload": { "type": "task_complete" } }
entry. The last preceding token_count entry carries the cumulative
total_token_usage for the whole session.

Usage:
  python3 codex-mem.py --watch   # poll loop (default, for launchd/background)
  python3 codex-mem.py --run     # one-shot scan, then exit

Environment:
  MEM_CODEX_JSONL   output JSONL path  (default: ~/.mem-cli/codex.jsonl)
  MEM_CODEX_POLL    poll interval in seconds (default: 30)
"""

import datetime
import json
import os
import sys
import time
from pathlib import Path

SESSIONS_DIR = Path.home() / ".codex" / "sessions"
JSONL_FILE = Path(
    os.environ.get("MEM_CODEX_JSONL", str(Path.home() / ".mem-cli" / "codex.jsonl"))
)
STATE_FILE = Path.home() / ".mem-cli" / "runtime" / "codex-processed.json"
POLL_INTERVAL = int(os.environ.get("MEM_CODEX_POLL", "30"))


# ---------------------------------------------------------------------------
# State: set of already-processed session file paths
# ---------------------------------------------------------------------------

def load_processed() -> set:
    if STATE_FILE.exists():
        try:
            return set(json.loads(STATE_FILE.read_text(encoding="utf-8")))
        except Exception:
            pass
    return set()


def save_processed(processed: set) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(sorted(processed), indent=2), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Session parsing
# ---------------------------------------------------------------------------

def parse_session(path: Path):
    """
    Parse a Codex session JSONL file.

    Returns (session_id, usage_dict) if the session is complete and has
    token data, or None if the session is still in progress or empty.
    """
    session_id = str(path)
    last_token_usage = None
    is_complete = False

    try:
        with open(path, encoding="utf-8") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    entry = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if not isinstance(entry, dict):
                    continue

                etype = entry.get("type")
                payload = entry.get("payload") if isinstance(entry.get("payload"), dict) else {}
                ptype = payload.get("type")

                # Extract stable session id
                if etype == "session_meta":
                    session_id = payload.get("id") or session_id

                # Track the latest cumulative token count
                if etype == "event_msg" and ptype == "token_count":
                    info = payload.get("info") or {}
                    total = info.get("total_token_usage")
                    if total:
                        last_token_usage = total

                # Detect end of session
                if etype == "event_msg" and ptype == "task_complete":
                    is_complete = True

    except OSError:
        return None

    if not is_complete or not last_token_usage:
        return None

    return session_id, last_token_usage


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_event(session_id: str, usage: dict) -> None:
    JSONL_FILE.parent.mkdir(parents=True, exist_ok=True)

    event = {
        "agent_name": "codex",
        "input_tokens": int(usage.get("input_tokens") or 0),
        "output_tokens": int(usage.get("output_tokens") or 0),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source": "codex-session-watch",
        "session_id": session_id,
    }

    cached = int(usage.get("cached_input_tokens") or 0)
    if cached:
        event["cache_read_input_tokens"] = cached

    reasoning = int(usage.get("reasoning_output_tokens") or 0)
    if reasoning:
        event["reasoning_output_tokens"] = reasoning

    with open(JSONL_FILE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(event) + "\n")


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------

def scan_once() -> int:
    processed = load_processed()
    newly_processed: set = set()

    for root, _dirs, files in os.walk(SESSIONS_DIR):
        for fname in files:
            if not fname.endswith(".jsonl"):
                continue
            path = Path(root) / fname
            path_str = str(path)
            if path_str in processed:
                continue
            result = parse_session(path)
            if result is None:
                continue
            session_id, usage = result
            write_event(session_id, usage)
            newly_processed.add(path_str)

    if newly_processed:
        save_processed(processed | newly_processed)

    return len(newly_processed)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "--watch"

    if mode == "--run":
        n = scan_once()
        if n:
            print(f"codex-mem: wrote {n} new event(s) to {JSONL_FILE}")
        sys.exit(0)

    # --watch: continuous poll loop
    print(
        f"codex-mem: watching {SESSIONS_DIR} every {POLL_INTERVAL}s → {JSONL_FILE}",
        flush=True,
    )
    while True:
        try:
            scan_once()
        except Exception as exc:
            print(f"codex-mem: error during scan: {exc}", file=sys.stderr, flush=True)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
