#!/usr/bin/env python3
"""
codex-mem — watches ~/.codex/sessions/ for Codex sessions
and appends token usage events to the mem-cli JSONL file.

The watcher emits each new token_count update as it appears in the
session JSONL. For live Codex sessions, this means the dashboard can
update before the session finishes. The parser prefers
last_token_usage so the emitted event represents the incremental delta,
not the cumulative session total.

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
STATE_VERSION = 2


# ---------------------------------------------------------------------------
# State: per-session line cursors
# ---------------------------------------------------------------------------

def _count_complete_lines(path: Path) -> int:
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError:
        return 0

    if not raw_text:
        return 0

    complete_lines = 0
    for chunk in raw_text.splitlines(keepends=True):
        if chunk.endswith(("\n", "\r")):
            complete_lines += 1
    return complete_lines


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            raw_state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        else:
            if isinstance(raw_state, dict):
                files = raw_state.get("files")
                if isinstance(files, dict):
                    normalized: dict[str, dict[str, object]] = {}
                    for raw_path, entry in files.items():
                        if not isinstance(entry, dict):
                            continue
                        normalized[str(raw_path)] = {
                            "lines": max(0, int(entry.get("lines") or 0)),
                            "session_id": str(entry.get("session_id") or ""),
                        }
                    return {"version": STATE_VERSION, "files": normalized}

            if isinstance(raw_state, list):
                migrated: dict[str, dict[str, object]] = {}
                for raw_path in raw_state:
                    path = Path(str(raw_path))
                    migrated[str(path)] = {
                        "lines": _count_complete_lines(path),
                        "session_id": "",
                    }
                return {"version": STATE_VERSION, "files": migrated}

    return {"version": STATE_VERSION, "files": {}}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


# ---------------------------------------------------------------------------
# Session parsing
# ---------------------------------------------------------------------------

def parse_session_line(raw: str, session_id: str) -> tuple[str, dict | None] | None:
    raw = raw.strip()
    if not raw:
        return None

    try:
        entry = json.loads(raw)
    except json.JSONDecodeError:
        return None

    if not isinstance(entry, dict):
        return None

    etype = entry.get("type")
    payload = entry.get("payload") if isinstance(entry.get("payload"), dict) else {}
    ptype = payload.get("type")

    if etype == "session_meta":
        session_id = str(payload.get("id") or session_id)
        return session_id, None

    if etype == "event_msg" and ptype == "token_count":
        info = payload.get("info") or {}
        usage = info.get("last_token_usage") or info.get("total_token_usage")
        if isinstance(usage, dict):
            return session_id, usage

    return session_id, None


def read_complete_lines(path: Path) -> list[str]:
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError:
        return []

    if not raw_text:
        return []

    complete_lines: list[str] = []
    for chunk in raw_text.splitlines(keepends=True):
        if chunk.endswith(("\n", "\r")):
            complete_lines.append(chunk.rstrip("\r\n"))

    return complete_lines


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
    state = load_state()
    state_files = state.setdefault("files", {})
    newly_written = 0

    for root, _dirs, filenames in os.walk(SESSIONS_DIR):
        for fname in filenames:
            if not fname.endswith(".jsonl"):
                continue
            path = Path(root) / fname
            path_str = str(path)
            cursor = state_files.setdefault(path_str, {"lines": 0, "session_id": ""})
            if not isinstance(cursor, dict):
                cursor = {"lines": 0, "session_id": ""}
                state_files[path_str] = cursor

            complete_lines = read_complete_lines(path)
            line_count = len(complete_lines)
            seen_lines = max(0, int(cursor.get("lines") or 0))

            if line_count < seen_lines:
                seen_lines = 0
                cursor["session_id"] = ""

            if line_count <= seen_lines:
                cursor["lines"] = line_count
                continue

            session_id = str(cursor.get("session_id") or path.stem)
            for raw in complete_lines[seen_lines:]:
                parsed = parse_session_line(raw, session_id)
                if parsed is None:
                    continue
                session_id, usage = parsed
                cursor["session_id"] = session_id
                if usage is not None:
                    write_event(session_id, usage)
                    newly_written += 1

            cursor["lines"] = line_count

    save_state(state)
    return newly_written


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
