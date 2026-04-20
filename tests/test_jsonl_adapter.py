from pathlib import Path

from mem.services.adapters.jsonl_adapter import JsonlTokenSource, JsonlTokenSourceConfig


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


def test_jsonl_source_reads_pretty_printed_json_documents(tmp_path) -> None:
    path = tmp_path / "claude.json"
    path.write_text(
        """[
  {
    "result": "done",
    "usage": {
      "input_tokens": 18,
      "output_tokens": 27,
      "total_tokens": 45
    },
    "session_id": "abc"
  }
]
""",
        encoding="utf-8",
    )

    source = JsonlTokenSource(JsonlTokenSourceConfig(paths_by_agent={"claude": path}))
    events = list(source.poll())

    assert len(events) == 1
    assert events[0].agent_name == "claude"
    assert events[0].input_tokens == 18
    assert events[0].output_tokens == 27
    assert events[0].total_tokens == 45


def test_jsonl_source_subtracts_cached_input_tokens_codex(tmp_path) -> None:
    """codex exec --json reports cached_input_tokens inside usage; only net new tokens should be counted."""
    path = tmp_path / "codex.jsonl"
    path.write_text(
        '{"type":"turn.completed","usage":{"input_tokens":11568,"cached_input_tokens":10112,"output_tokens":21}}\n',
        encoding="utf-8",
    )

    source = JsonlTokenSource(JsonlTokenSourceConfig(paths_by_agent={"codex": path}))
    events = list(source.poll())

    assert len(events) == 1
    assert events[0].input_tokens == 11568 - 10112  # 1456 net new tokens
    assert events[0].output_tokens == 21


def test_jsonl_source_subtracts_cache_read_input_tokens_claude(tmp_path) -> None:
    """Claude Code Stop hook may report cache_read_input_tokens; subtract them from input_tokens."""
    path = tmp_path / "claude.jsonl"
    path.write_text(
        '{"agent_name":"claude","usage":{"input_tokens":5000,"cache_read_input_tokens":4800,"output_tokens":60}}\n',
        encoding="utf-8",
    )

    source = JsonlTokenSource(JsonlTokenSourceConfig(paths_by_agent={"claude": path}))
    events = list(source.poll())

    assert len(events) == 1
    assert events[0].input_tokens == 5000 - 4800  # 200 net new tokens
    assert events[0].output_tokens == 60


def test_jsonl_source_prefers_last_token_usage_for_codex(tmp_path) -> None:
    path = tmp_path / "codex.json"
    path.write_text(
        """{
  "type": "event_msg",
  "payload": {
    "type": "token_count",
    "info": {
      "total_token_usage": {
        "input_tokens": 100,
        "output_tokens": 20
      },
      "last_token_usage": {
        "input_tokens": 7,
        "output_tokens": 3
      }
    }
  }
}
""",
        encoding="utf-8",
    )

    source = JsonlTokenSource(JsonlTokenSourceConfig(paths_by_agent={"codex": path}))
    events = list(source.poll())

    assert len(events) == 1
    assert events[0].input_tokens == 7
    assert events[0].output_tokens == 3


def test_jsonl_source_skips_records_without_token_counts(tmp_path) -> None:
    path = tmp_path / "claude.jsonl"
    path.write_text(
        "\n".join(
            [
                '{"event":"heartbeat","message":"still running"}',
                '{"usage":{"input_tokens":8,"output_tokens":12}}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    source = JsonlTokenSource(JsonlTokenSourceConfig(paths_by_agent={"claude": path}))
    events = list(source.poll())

    assert len(events) == 1
    assert events[0].input_tokens == 8
    assert events[0].output_tokens == 12
