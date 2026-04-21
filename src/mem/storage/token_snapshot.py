"""Persists the latest token snapshot from the daemon to a shared file.

The daemon writes here on every tick; any other process (MCP server, CLI)
reads from here to get the current token state without joining the daemon.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..config import get_token_snapshot_path
from ..models import AgentStatus
from ..utils.time import from_iso8601, to_iso8601, utc_now


class TokenSnapshotStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or get_token_snapshot_path()

    def save(self, snapshot: list[AgentStatus]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "updated_at": to_iso8601(utc_now()),
            "agents": [asdict(s) for s in snapshot],
        }
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def load(self) -> list[AgentStatus]:
        if not self.path.exists():
            return []
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return [self._from_dict(item) for item in payload.get("agents", [])]

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()

    @staticmethod
    def _from_dict(item: dict[str, Any]) -> AgentStatus:
        return AgentStatus(
            agent_name=str(item.get("agent_name", "-")),
            input_tokens=int(item.get("input_tokens", 0)),
            output_tokens=int(item.get("output_tokens", 0)),
            total_tokens=int(item.get("total_tokens", 0)),
            average_tokens_per_minute=float(item.get("average_tokens_per_minute", 0.0)),
            last_updated=str(item.get("last_updated", "-")),
            state=str(item.get("state", "waiting")),
            source=str(item.get("source", "-")),
        )
