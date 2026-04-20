from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ..utils.time import utc_now


@dataclass(slots=True)
class TokenEvent:
    agent_name: str
    input_tokens: int
    output_tokens: int
    total_tokens: int = field(init=False)
    timestamp: datetime = field(default_factory=utc_now)
    source: str = "simulated"

    def __post_init__(self) -> None:
        if self.input_tokens < 0 or self.output_tokens < 0:
            raise ValueError("Token counts must be non-negative.")
        self.total_tokens = self.input_tokens + self.output_tokens
