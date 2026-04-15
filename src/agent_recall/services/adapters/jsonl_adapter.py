from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from ...models import TokenEvent
from ...utils.time import utc_now

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class JsonlTokenSourceConfig:
    paths_by_agent: dict[str, Path]
    source_name: str = "jsonl"


@dataclass(slots=True)
class _FileCursor:
    position: int = 0
    size: int = 0


@dataclass(slots=True)
class JsonlTokenSource:
    config: JsonlTokenSourceConfig
    _cursors: dict[str, _FileCursor] = field(default_factory=dict, init=False, repr=False)

    def poll(self) -> Iterable[TokenEvent]:
        for configured_agent, path in self.config.paths_by_agent.items():
            yield from self._poll_file(configured_agent, path)

    def _poll_file(self, configured_agent: str, path: Path) -> Iterable[TokenEvent]:
        if not path.exists():
            return ()

        cursor = self._cursors.setdefault(str(path), _FileCursor())
        stat_result = path.stat()
        if stat_result.st_size < cursor.size:
            cursor.position = 0

        events: list[TokenEvent] = []
        with path.open("r", encoding="utf-8") as handle:
            handle.seek(cursor.position)
            while line := handle.readline():
                cursor.position = handle.tell()
                cursor.size = max(cursor.size, cursor.position)
                raw = line.strip()
                if not raw:
                    continue
                event = self._parse_event(raw, configured_agent, path)
                if event is not None:
                    events.append(event)
        cursor.size = stat_result.st_size
        return events

    def _parse_event(self, raw: str, configured_agent: str, path: Path) -> TokenEvent | None:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Skipping invalid JSONL line in %s", path)
            return None

        if not isinstance(payload, dict):
            logger.warning("Skipping non-object JSONL line in %s", path)
            return None

        return self._event_from_payload(payload, configured_agent, path)

    def _event_from_payload(self, payload: dict[str, Any], configured_agent: str, path: Path) -> TokenEvent:
        agent_name = str(payload.get("agent_name") or configured_agent)
        input_tokens, output_tokens, total_tokens = self._extract_token_counts(payload)
        if total_tokens is not None and input_tokens == 0 and output_tokens == 0:
            output_tokens = total_tokens

        timestamp = self._parse_timestamp(payload.get("timestamp"))
        source = str(payload.get("source") or f"{self.config.source_name}:{path.name}")
        return TokenEvent(
            agent_name=agent_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            timestamp=timestamp,
            source=source,
        )

    @staticmethod
    def _coerce_int(value: Any) -> int:
        if value is None:
            return 0
        return int(value)

    def _extract_token_counts(self, payload: dict[str, Any]) -> tuple[int, int, int | None]:
        direct_input = self._coerce_int(payload.get("input_tokens"))
        direct_output = self._coerce_int(payload.get("output_tokens"))
        direct_total = payload.get("total_tokens")

        if direct_input or direct_output or direct_total is not None:
            return direct_input, direct_output, self._coerce_int(direct_total) if direct_total is not None else None

        nested_counts = self._search_token_counts(payload)
        if nested_counts is not None:
            return nested_counts

        return 0, 0, None

    def _search_token_counts(self, value: Any) -> tuple[int, int, int | None] | None:
        if isinstance(value, dict):
            input_tokens = self._coerce_int(value.get("input_tokens"))
            output_tokens = self._coerce_int(value.get("output_tokens"))
            total_tokens = value.get("total_tokens")
            if input_tokens or output_tokens or total_tokens is not None:
                return (
                    input_tokens,
                    output_tokens,
                    self._coerce_int(total_tokens) if total_tokens is not None else None,
                )
            for child in value.values():
                found = self._search_token_counts(child)
                if found is not None:
                    return found
        elif isinstance(value, list):
            for child in value:
                found = self._search_token_counts(child)
                if found is not None:
                    return found
        return None

    @staticmethod
    def _parse_timestamp(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str) and value:
            normalized = value.replace("Z", "+00:00")
            try:
                return datetime.fromisoformat(normalized)
            except ValueError:
                logger.warning("Invalid timestamp in JSONL event; using current UTC time")
        return utc_now()
