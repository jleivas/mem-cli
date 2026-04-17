from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

from ..models import AgentStatus, TokenEvent
from ..utils.time import utc_now


@dataclass(slots=True)
class _AgentTotals:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    last_updated: str = ""
    source: str = "simulated"
    state: str = "active"


class TokenTracker:
    def __init__(self) -> None:
        self._lock = Lock()
        self._agents: dict[str, _AgentTotals] = {}
        self._started_at = utc_now()

    def register_event(self, event: TokenEvent) -> None:
        with self._lock:
            totals = self._agents.setdefault(event.agent_name, _AgentTotals())
            totals.input_tokens += event.input_tokens
            totals.output_tokens += event.output_tokens
            totals.total_tokens += event.total_tokens
            totals.last_updated = event.timestamp.isoformat()
            totals.source = event.source

    def snapshot(self) -> list[AgentStatus]:
        with self._lock:
            now = utc_now()
            elapsed_minutes = max((now - self._started_at).total_seconds() / 60, 1 / 60)
            items = [
                AgentStatus(
                    agent_name=name,
                    input_tokens=totals.input_tokens,
                    output_tokens=totals.output_tokens,
                    total_tokens=totals.total_tokens,
                    average_tokens_per_minute=totals.total_tokens / elapsed_minutes,
                    last_updated=totals.last_updated,
                    state=totals.state,
                    source=totals.source,
                )
                for name, totals in self._agents.items()
            ]
        return sorted(items, key=lambda item: item.agent_name)
