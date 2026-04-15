from __future__ import annotations

import signal
import threading

from pathlib import Path

from .config import (
    get_claude_jsonl_path,
    get_codex_jsonl_path,
    get_jsonl_paths,
    use_simulated_source,
)
from .services.adapters import JsonlTokenSource, JsonlTokenSourceConfig
from .services.monitor_service import CompositeTokenSource, MonitorService, SimulatedTokenSource
from .utils.logging import configure_logging


def build_monitor_service() -> MonitorService:
    sources = []

    jsonl_paths = _build_jsonl_source()
    if jsonl_paths is not None:
        sources.append(jsonl_paths)

    if use_simulated_source():
        sources.append(SimulatedTokenSource())

    token_source = sources[0] if len(sources) == 1 else CompositeTokenSource(tuple(sources))
    return MonitorService(token_source=token_source)


def _build_jsonl_source() -> JsonlTokenSource | None:
    paths_by_agent: dict[str, Path] = {}

    codex_path = get_codex_jsonl_path()
    if codex_path is not None:
        paths_by_agent["codex"] = codex_path

    claude_path = get_claude_jsonl_path()
    if claude_path is not None:
        paths_by_agent["claude"] = claude_path

    extra_paths = get_jsonl_paths()
    if extra_paths:
        for index, raw_path in enumerate(extra_paths.split(","), start=1):
            cleaned = raw_path.strip()
            if not cleaned:
                continue
            paths_by_agent[f"jsonl-{index}"] = Path(cleaned).expanduser()

    if not paths_by_agent:
        return None

    return JsonlTokenSource(JsonlTokenSourceConfig(paths_by_agent=paths_by_agent))


def run_daemon() -> None:
    configure_logging()
    service = build_monitor_service()
    service.start()

    stop_event = threading.Event()

    def handle_signal(signum, frame):  # noqa: ARG001
        stop_event.set()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    try:
        while not stop_event.wait(0.5):
            pass
    finally:
        service.stop()
