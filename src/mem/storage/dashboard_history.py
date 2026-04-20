from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import ensure_history_dir
from ..models import AgentStatus
from ..utils.time import from_iso8601, to_iso8601, utc_now


@dataclass(slots=True)
class DashboardSnapshotMeta:
    created_at: datetime
    source: str
    rows: int
    path: Path


class DashboardSnapshotStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or ensure_history_dir()
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, snapshot: list[AgentStatus], source: str = "live") -> Path:
        created_at = utc_now()
        filename = f"snapshot-{created_at.strftime('%Y%m%d-%H%M%S-%f')}.json"
        path = self.root / filename
        payload = {
            "created_at": to_iso8601(created_at),
            "source": source,
            "rows": [asdict(item) for item in snapshot],
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    def list(self) -> list[DashboardSnapshotMeta]:
        metas: list[DashboardSnapshotMeta] = []
        for path in sorted(self.root.glob("snapshot-*.json"), reverse=True):
            payload = self._read_payload(path)
            created_at = from_iso8601(payload.get("created_at")) if payload.get("created_at") else utc_now()
            rows = payload.get("rows") or []
            metas.append(
                DashboardSnapshotMeta(
                    created_at=created_at,
                    source=str(payload.get("source") or "live"),
                    rows=len(rows),
                    path=path,
                )
            )
        return metas

    def load(self, path: Path) -> list[AgentStatus]:
        payload = self._read_payload(path)
        rows = payload.get("rows") or []
        return [self._agent_status_from_payload(item) for item in rows]

    def delete(self, path: Path) -> None:
        if path.exists():
            path.unlink()

    def _read_payload(self, path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _agent_status_from_payload(payload: dict[str, Any]) -> AgentStatus:
        return AgentStatus(
            agent_name=str(payload.get("agent_name", "-")),
            input_tokens=int(payload.get("input_tokens", 0)),
            output_tokens=int(payload.get("output_tokens", 0)),
            total_tokens=int(payload.get("total_tokens", 0)),
            average_tokens_per_minute=float(payload.get("average_tokens_per_minute", 0.0)),
            last_updated=str(payload.get("last_updated", "-")),
            state=str(payload.get("state", "waiting")),
            source=str(payload.get("source", "-")),
        )
