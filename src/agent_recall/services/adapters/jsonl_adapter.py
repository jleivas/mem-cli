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

        with path.open("rb") as handle:
            handle.seek(cursor.position)
            raw_bytes = handle.read()

        if not raw_bytes:
            cursor.size = stat_result.st_size
            return ()

        raw_text = raw_bytes.decode("utf-8", errors="ignore")
        events, consumed_chars = self._parse_buffer(raw_text, configured_agent, path)
        cursor.position += len(raw_text[:consumed_chars].encode("utf-8"))
        cursor.size = stat_result.st_size
        return events

    def _parse_buffer(self, raw_text: str, configured_agent: str, path: Path) -> tuple[list[TokenEvent], int]:
        decoder = json.JSONDecoder()
        index = self._skip_whitespace(raw_text, 0)
        events: list[TokenEvent] = []

        while index < len(raw_text):
            try:
                payload, next_index = decoder.raw_decode(raw_text, index)
            except json.JSONDecodeError:
                if index == 0:
                    logger.warning("Skipping invalid JSON/JSONL content in %s", path)
                break

            events.extend(self._events_from_payload(payload, configured_agent, path))
            index = self._skip_whitespace(raw_text, next_index)

        return events, index

    @staticmethod
    def _skip_whitespace(raw_text: str, index: int) -> int:
        while index < len(raw_text) and raw_text[index].isspace():
            index += 1
        return index

    def _events_from_payload(self, payload: Any, configured_agent: str, path: Path) -> list[TokenEvent]:
        if isinstance(payload, list):
            events: list[TokenEvent] = []
            for item in payload:
                events.extend(self._events_from_payload(item, configured_agent, path))
            return events

        if not isinstance(payload, dict):
            return []

        return [self._event_from_payload(payload, configured_agent, path)]

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
        nested_counts = self._search_token_counts(payload)
        if nested_counts is not None:
            return nested_counts

        return 0, 0, None

    def _search_token_counts(self, value: Any) -> tuple[int, int, int | None] | None:
        if isinstance(value, dict):
            for key in ("usage", "last_token_usage", "token_usage", "total_token_usage"):
                nested_value = value.get(key)
                if nested_value is not None:
                    found = self._search_token_counts(nested_value)
                    if found is not None:
                        return found

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
