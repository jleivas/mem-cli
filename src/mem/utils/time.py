from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_iso8601(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def from_iso8601(value: str) -> datetime:
    return datetime.fromisoformat(value)

