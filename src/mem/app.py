from __future__ import annotations

import signal
import threading

from pathlib import Path

from .config import (
    get_claude_jsonl_path,
    get_codex_jsonl_path,
    get_jsonl_paths,
)
from .services.adapters import JsonlTokenSource, JsonlTokenSourceConfig
from .services.monitor_service import MonitorService
from .storage.token_snapshot import TokenSnapshotStore
from .utils.logging import configure_logging


def build_monitor_service() -> MonitorService:
    jsonl_paths = _build_jsonl_source()
    if jsonl_paths is None:
        return MonitorService()
    return MonitorService(token_source=jsonl_paths)


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
    snapshot_store = TokenSnapshotStore()
    service.start()

    stop_event = threading.Event()

    def handle_signal(signum, frame):  # noqa: ARG001
        stop_event.set()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    try:
        while not stop_event.wait(0.5):
            snapshot_store.save(service.snapshot())
    finally:
        service.stop()
        snapshot_store.clear()
