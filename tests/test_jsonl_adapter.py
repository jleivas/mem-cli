from pathlib import Path

from agent_recall.services.adapters.jsonl_adapter import JsonlTokenSource, JsonlTokenSourceConfig


def test_jsonl_source_reads_appended_events(tmp_path) -> None:
    path = tmp_path / "codex.jsonl"
    path.write_text(
        "\n".join(
            [
                '{"agent_name":"codex","input_tokens":10,"output_tokens":20,"timestamp":"2026-04-15T15:00:00Z"}',
                '{"output_tokens":7,"total_tokens":7,"source":"codex-local"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    source = JsonlTokenSource(JsonlTokenSourceConfig(paths_by_agent={"codex": path}))
    first_batch = list(source.poll())

    assert len(first_batch) == 2
    assert first_batch[0].agent_name == "codex"
    assert first_batch[0].total_tokens == 30
    assert first_batch[1].agent_name == "codex"
    assert first_batch[1].source == "codex-local"

    path.write_text(
        "\n".join(
            [
                '{"agent_name":"codex","input_tokens":10,"output_tokens":20,"timestamp":"2026-04-15T15:00:00Z"}',
                '{"output_tokens":7,"total_tokens":7,"source":"codex-local"}',
                '{"agent_name":"codex","input_tokens":3,"output_tokens":9,"source":"codex-local"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    second_batch = list(source.poll())

    assert len(second_batch) == 1
    assert second_batch[0].input_tokens == 3
    assert second_batch[0].output_tokens == 9


def test_jsonl_source_extracts_nested_usage_fields(tmp_path) -> None:
    path = tmp_path / "claude.jsonl"
    path.write_text(
        "\n".join(
            [
                '{"result":"done","usage":{"input_tokens":15,"output_tokens":25,"total_tokens":40},"session_id":"abc"}',
                '{"type":"event","event":{"usage":{"input_tokens":4,"output_tokens":6}},"agent_name":"codex"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    source = JsonlTokenSource(JsonlTokenSourceConfig(paths_by_agent={"claude": path}))
    events = list(source.poll())

    assert len(events) == 2
    assert events[0].input_tokens == 15
    assert events[0].output_tokens == 25
    assert events[0].total_tokens == 40
    assert events[1].agent_name == "codex"
    assert events[1].input_tokens == 4
    assert events[1].output_tokens == 6
