from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from importlib import metadata
from typing import Protocol, cast

from ..monitor_service import CompositeTokenSource
from ..monitor_service import TokenSource

logger = logging.getLogger(__name__)

ENTRY_POINT_GROUP = "mem.token_sources"


class TokenSourceFactory(Protocol):
    def __call__(self) -> TokenSource:
        """Return a token source ready to be polled."""


@dataclass(slots=True)
class DiscoveredTokenSourcePlugin:
    name: str
    entry_point: str
    source: TokenSource


def _iter_entry_points(group: str) -> Iterable[metadata.EntryPoint]:
    entry_points = metadata.entry_points()
    if hasattr(entry_points, "select"):
        return entry_points.select(group=group)
    return entry_points.get(group, ())  # type: ignore[return-value]


def discover_token_source_plugins() -> list[DiscoveredTokenSourcePlugin]:
    plugins: list[DiscoveredTokenSourcePlugin] = []
    for entry_point in _iter_entry_points(ENTRY_POINT_GROUP):
        try:
            factory = cast(Callable[[], TokenSource] | TokenSource, entry_point.load())
            source = factory() if callable(factory) else factory
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Skipping token source plugin %s: %s", entry_point.name, exc)
            continue

        if not hasattr(source, "poll"):
            logger.warning("Skipping token source plugin %s: missing poll()", entry_point.name)
            continue

        plugins.append(
            DiscoveredTokenSourcePlugin(
                name=entry_point.name,
                entry_point=entry_point.value,
                source=cast(TokenSource, source),
            )
        )
    return plugins


def build_token_source_pipeline(*sources: TokenSource | None) -> TokenSource | None:
    active_sources = tuple(source for source in sources if source is not None)
    if not active_sources:
        return None
    if len(active_sources) == 1:
        return active_sources[0]
    return CompositeTokenSource(active_sources)
