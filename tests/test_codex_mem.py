from __future__ import annotations

import json
import importlib.util
from pathlib import Path
from types import ModuleType


def _load_codex_mem() -> ModuleType:
    script_path = Path(__file__).resolve().parents[1] / "hooks" / "codex-mem.py"
    spec = importlib.util.spec_from_file_location("codex_mem_hook", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_codex_watcher_emits_incremental_token_updates(tmp_path) -> None:
    module = _load_codex_mem()

    sessions_dir = tmp_path / ".codex" / "sessions"
    session_dir = sessions_dir / "2026" / "04" / "20"
    session_dir.mkdir(parents=True)

    output_file = tmp_path / ".mem-cli" / "codex.jsonl"
    state_file = tmp_path / ".mem-cli" / "runtime" / "codex-processed.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.parent.mkdir(parents=True, exist_ok=True)

    session_file = session_dir / "rollout-2026-04-20T10-00-00-019test.jsonl"
    session_file.write_text(
        "\n".join(
            [
                '{"timestamp":"2026-04-20T10:00:00.000Z","type":"session_meta","payload":{"id":"session-1"}}',
                '{"timestamp":"2026-04-20T10:00:01.000Z","type":"event_msg","payload":{"type":"token_count","info":{"total_token_usage":{"input_tokens":100,"output_tokens":20},"last_token_usage":{"input_tokens":10,"output_tokens":2}}}}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    module.SESSIONS_DIR = sessions_dir
    module.JSONL_FILE = output_file
    module.STATE_FILE = state_file

    first_written = module.scan_once()
    assert first_written == 1

    first_batch = output_file.read_text(encoding="utf-8").splitlines()
    assert len(first_batch) == 1

    first_event = json.loads(first_batch[0])
    assert first_event["session_id"] == "session-1"
    assert first_event["input_tokens"] == 10
    assert first_event["output_tokens"] == 2

    session_file.write_text(
        "\n".join(
            [
                '{"timestamp":"2026-04-20T10:00:00.000Z","type":"session_meta","payload":{"id":"session-1"}}',
                '{"timestamp":"2026-04-20T10:00:01.000Z","type":"event_msg","payload":{"type":"token_count","info":{"total_token_usage":{"input_tokens":100,"output_tokens":20},"last_token_usage":{"input_tokens":10,"output_tokens":2}}}}',
                '{"timestamp":"2026-04-20T10:00:02.000Z","type":"event_msg","payload":{"type":"token_count","info":{"total_token_usage":{"input_tokens":130,"output_tokens":28},"last_token_usage":{"input_tokens":30,"output_tokens":8}}}}',
                '{"timestamp":"2026-04-20T10:00:03.000Z","type":"event_msg","payload":{"type":"task_complete"}}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    second_written = module.scan_once()
    assert second_written == 1

    second_batch = output_file.read_text(encoding="utf-8").splitlines()
    assert len(second_batch) == 2

    second_event = json.loads(second_batch[1])
    assert second_event["session_id"] == "session-1"
    assert second_event["input_tokens"] == 30
    assert second_event["output_tokens"] == 8
