from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import get_runtime_state_path
from ..utils.time import from_iso8601, to_iso8601, utc_now


@dataclass(slots=True)
class RuntimeState:
    running: bool
    pid: int | None
    started_at: datetime | None
    last_updated: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "running": self.running,
            "pid": self.pid,
            "started_at": to_iso8601(self.started_at) if self.started_at else None,
            "last_updated": to_iso8601(self.last_updated),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RuntimeState":
        started_at = payload.get("started_at")
        last_updated = payload.get("last_updated")
        return cls(
            running=bool(payload.get("running", False)),
            pid=payload.get("pid"),
            started_at=from_iso8601(started_at) if started_at else None,
            last_updated=from_iso8601(last_updated) if last_updated else utc_now(),
        )


class RuntimeStateStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or get_runtime_state_path()

    def load(self) -> RuntimeState | None:
        if not self.path.exists():
            return None
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return RuntimeState.from_dict(payload)

    def save(self, state: RuntimeState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")
        tmp_path.replace(self.path)

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()
