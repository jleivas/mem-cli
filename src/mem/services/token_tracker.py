from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

from ..models import AgentStatus, TokenEvent


@dataclass(slots=True)
class _AgentTotals:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    record_count: int = 0
    last_updated: str = ""
    source: str = "simulated"
    state: str = "active"


class TokenTracker:
    def __init__(self) -> None:
        self._lock = Lock()
        self._agents: dict[str, _AgentTotals] = {}

    def register_event(self, event: TokenEvent) -> None:
        with self._lock:
            totals = self._agents.setdefault(event.agent_name, _AgentTotals())
            totals.input_tokens += event.input_tokens
            totals.output_tokens += event.output_tokens
            totals.total_tokens += event.total_tokens
            totals.record_count += 1
            totals.last_updated = event.timestamp.isoformat()
            totals.source = event.source

    def snapshot(self) -> list[AgentStatus]:
        with self._lock:
            items = [
                AgentStatus(
                    agent_name=name,
                    input_tokens=totals.input_tokens,
                    output_tokens=totals.output_tokens,
                    total_tokens=totals.total_tokens,
                    average_tokens_per_minute=totals.total_tokens / totals.record_count if totals.record_count else 0.0,
                    last_updated=totals.last_updated,
                    state=totals.state,
                    source=totals.source,
                )
                for name, totals in self._agents.items()
            ]
        return sorted(items, key=lambda item: item.agent_name)

    def reset(self) -> None:
        with self._lock:
            self._agents.clear()
