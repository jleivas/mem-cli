"""Tests for TokenSnapshotStore."""
from __future__ import annotations

import pytest

from mem.models.agent_status import AgentStatus
from mem.storage.token_snapshot import TokenSnapshotStore


def _make_status(**kwargs) -> AgentStatus:
    defaults = dict(
        agent_name="claude",
        input_tokens=10,
        output_tokens=20,
        total_tokens=30,
        average_tokens_per_minute=5.0,
        last_updated="2024-01-01T00:00:00",
        state="active",
        source="jsonl",
    )
    defaults.update(kwargs)
    return AgentStatus(**defaults)


class TestTokenSnapshotStore:
    def test_load_returns_empty_when_no_file(self, tmp_path):
        store = TokenSnapshotStore(path=tmp_path / "snapshot.json")
        assert store.load() == []

    def test_save_and_load_roundtrip(self, tmp_path):
        store = TokenSnapshotStore(path=tmp_path / "snapshot.json")
        statuses = [_make_status(agent_name="claude"), _make_status(agent_name="codex")]
        store.save(statuses)
        loaded = store.load()
        assert len(loaded) == 2
        assert loaded[0].agent_name == "claude"
        assert loaded[1].agent_name == "codex"

    def test_save_overwrites_previous(self, tmp_path):
        store = TokenSnapshotStore(path=tmp_path / "snapshot.json")
        store.save([_make_status(agent_name="claude", total_tokens=100)])
        store.save([_make_status(agent_name="claude", total_tokens=200)])
        loaded = store.load()
        assert loaded[0].total_tokens == 200

    def test_save_preserves_all_fields(self, tmp_path):
        store = TokenSnapshotStore(path=tmp_path / "snapshot.json")
        s = _make_status(input_tokens=111, output_tokens=222, total_tokens=333,
                         average_tokens_per_minute=7.5, source="jsonl", state="active")
        store.save([s])
        loaded = store.load()[0]
        assert loaded.input_tokens == 111
        assert loaded.output_tokens == 222
        assert loaded.total_tokens == 333
        assert loaded.average_tokens_per_minute == 7.5
        assert loaded.source == "jsonl"
        assert loaded.state == "active"

    def test_clear_removes_file(self, tmp_path):
        path = tmp_path / "snapshot.json"
        store = TokenSnapshotStore(path=path)
        store.save([_make_status()])
        assert path.exists()
        store.clear()
        assert not path.exists()

    def test_clear_is_safe_when_no_file(self, tmp_path):
        store = TokenSnapshotStore(path=tmp_path / "snapshot.json")
        store.clear()  # should not raise

    def test_save_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "nested" / "dir" / "snapshot.json"
        store = TokenSnapshotStore(path=path)
        store.save([_make_status()])
        assert path.exists()
