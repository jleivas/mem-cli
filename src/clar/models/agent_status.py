from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AgentStatus:
    agent_name: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    last_updated: str
    state: str
    source: str

