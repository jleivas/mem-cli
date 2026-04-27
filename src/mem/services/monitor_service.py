from __future__ import annotations

import threading
import time
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from ..models import TokenEvent
from .token_tracker import TokenTracker


class TokenSource(Protocol):
    def poll(self) -> Iterable[TokenEvent]:
        """Return a batch of token events."""


@dataclass(slots=True)
class NullTokenSource:
    def poll(self) -> Iterable[TokenEvent]:
        return ()


@dataclass(slots=True)
class CompositeTokenSource:
    sources: tuple[TokenSource, ...]

    def poll(self) -> Iterable[TokenEvent]:
        for source in self.sources:
            yield from source.poll()


class MonitorService:
    def __init__(
        self,
        tracker: TokenTracker | None = None,
        token_source: TokenSource | None = None,
        interval_seconds: float = 1.0,
    ) -> None:
        self.tracker = tracker or TokenTracker()
        self.token_source = token_source or NullTokenSource()
        self.interval_seconds = interval_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name="mem-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def tick(self) -> None:
        for event in self.token_source.poll():
            self.tracker.register_event(event)

    def snapshot(self):
        return self.tracker.snapshot()

    def reset(self) -> None:
        self.tracker.reset()

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            self.tick()
            time.sleep(self.interval_seconds)


__all__ = [
    "CompositeTokenSource",
    "MonitorService",
    "NullTokenSource",
    "TokenSource",
]
