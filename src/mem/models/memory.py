from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ..utils.time import utc_now


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


def _project_name(project: str) -> str:
    """Return the last non-empty component of a path as a display name."""
    return Path(project).name or project


@dataclass(slots=True)
class Memory:
    content: str
    project: str
    id: str = field(default_factory=_new_id)
    project_name: str = field(init=False)
    timestamp: datetime = field(default_factory=utc_now)
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.project_name = _project_name(self.project)
