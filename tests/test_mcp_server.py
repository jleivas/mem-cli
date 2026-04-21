"""Tests for the MCP server tools (mem.mcp.server)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from mem.mcp.server import (
    memory_forget,
    memory_projects,
    memory_recall,
    memory_remember,
    monitor_snapshot,
    monitor_start,
    monitor_status,
    monitor_stop,
)
from mem.models.memory import Memory
from mem.models.agent_status import AgentStatus
from mem.storage.runtime_state import RuntimeState
from mem.utils.time import utc_now


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_memory(**kwargs) -> Memory:
    defaults = dict(content="test memory", project="/tmp/proj")
    defaults.update(kwargs)
    return Memory(**defaults)


def _make_state(**kwargs) -> RuntimeState:
    defaults = dict(running=True, pid=1234, started_at=utc_now(), last_updated=utc_now())
    defaults.update(kwargs)
    return RuntimeState(**defaults)


# ---------------------------------------------------------------------------
# memory_remember
# ---------------------------------------------------------------------------

class TestMemoryRemember:
    def test_returns_saved_memory_dict(self):
        m = _make_memory(content="hello world")
        svc = MagicMock()
        svc.remember.return_value = m
        with patch("mem.mcp.server._mem", return_value=svc):
            result = memory_remember("hello world")
        assert result["content"] == "hello world"
        assert "id" in result
        assert "timestamp" in result

    def test_passes_tags_and_cwd(self):
        m = _make_memory()
        svc = MagicMock()
        svc.remember.return_value = m
        with patch("mem.mcp.server._mem", return_value=svc):
            memory_remember("x", tags=["tag1"], cwd="/some/path")
        svc.remember.assert_called_once_with("x", cwd="/some/path", tags=["tag1"])

    def test_empty_cwd_passes_none(self):
        m = _make_memory()
        svc = MagicMock()
        svc.remember.return_value = m
        with patch("mem.mcp.server._mem", return_value=svc):
            memory_remember("x")
        svc.remember.assert_called_once_with("x", cwd=None, tags=[])


# ---------------------------------------------------------------------------
# memory_recall
# ---------------------------------------------------------------------------

class TestMemoryRecall:
    def test_returns_list_of_dicts(self):
        memories = [_make_memory(content="a"), _make_memory(content="b")]
        svc = MagicMock()
        svc.recall.return_value = memories
        with patch("mem.mcp.server._mem", return_value=svc):
            result = memory_recall()
        assert len(result) == 2
        assert result[0]["content"] == "a"

    def test_passes_filters(self):
        svc = MagicMock()
        svc.recall.return_value = []
        with patch("mem.mcp.server._mem", return_value=svc):
            memory_recall(query="foo", tag="bar", cwd="/p")
        svc.recall.assert_called_once_with(cwd="/p", query="foo", tag="bar")

    def test_empty_strings_become_none(self):
        svc = MagicMock()
        svc.recall.return_value = []
        with patch("mem.mcp.server._mem", return_value=svc):
            memory_recall()
        svc.recall.assert_called_once_with(cwd=None, query=None, tag=None)


# ---------------------------------------------------------------------------
# memory_forget
# ---------------------------------------------------------------------------

class TestMemoryForget:
    def test_returns_deleted_true(self):
        svc = MagicMock()
        svc.forget.return_value = True
        with patch("mem.mcp.server._mem", return_value=svc):
            result = memory_forget("abc123")
        assert result == {"deleted": True, "id": "abc123"}

    def test_returns_deleted_false_when_not_found(self):
        svc = MagicMock()
        svc.forget.return_value = False
        with patch("mem.mcp.server._mem", return_value=svc):
            result = memory_forget("nope")
        assert result["deleted"] is False


# ---------------------------------------------------------------------------
# memory_projects
# ---------------------------------------------------------------------------

class TestMemoryProjects:
    def test_delegates_to_service(self):
        projects = [{"project": "/a", "project_name": "a", "memory_count": 2}]
        svc = MagicMock()
        svc.projects.return_value = projects
        with patch("mem.mcp.server._mem", return_value=svc):
            result = memory_projects()
        assert result == projects


# ---------------------------------------------------------------------------
# monitor_snapshot
# ---------------------------------------------------------------------------

class TestMonitorSnapshot:
    def test_returns_agent_dicts(self):
        status = AgentStatus(
            agent_name="claude",
            input_tokens=10,
            output_tokens=20,
            total_tokens=30,
            average_tokens_per_minute=5.0,
            last_updated="2024-01-01T00:00:00",
            state="active",
            source="jsonl",
        )
        store = MagicMock()
        store.load.return_value = [status]
        with patch("mem.mcp.server._snapshot_store", return_value=store):
            result = monitor_snapshot()
        assert len(result) == 1
        assert result[0]["agent_name"] == "claude"
        assert result[0]["total_tokens"] == 30

    def test_returns_empty_when_daemon_not_running(self):
        store = MagicMock()
        store.load.return_value = []
        with patch("mem.mcp.server._snapshot_store", return_value=store):
            result = monitor_snapshot()
        assert result == []


# ---------------------------------------------------------------------------
# monitor_status
# ---------------------------------------------------------------------------

class TestMonitorStatus:
    def test_running_state(self):
        state = _make_state()
        reg = MagicMock()
        reg.load_state.return_value = state
        with patch("mem.mcp.server._registry", return_value=reg):
            result = monitor_status()
        assert result["running"] is True
        assert result["pid"] == 1234

    def test_no_state_returns_stopped(self):
        reg = MagicMock()
        reg.load_state.return_value = None
        with patch("mem.mcp.server._registry", return_value=reg):
            result = monitor_status()
        assert result["running"] is False
        assert result["pid"] is None


# ---------------------------------------------------------------------------
# monitor_start / monitor_stop
# ---------------------------------------------------------------------------

class TestMonitorStart:
    def test_success(self):
        state = _make_state()
        reg = MagicMock()
        reg.start.return_value = state
        with patch("mem.mcp.server._registry", return_value=reg):
            result = monitor_start()
        assert result["ok"] is True
        assert result["pid"] == 1234

    def test_already_running(self):
        reg = MagicMock()
        reg.start.side_effect = RuntimeError("already running")
        with patch("mem.mcp.server._registry", return_value=reg):
            result = monitor_start()
        assert result["ok"] is False
        assert "already running" in result["error"]


class TestMonitorStop:
    def test_success(self):
        state = _make_state(running=False)
        reg = MagicMock()
        reg.stop.return_value = state
        with patch("mem.mcp.server._registry", return_value=reg):
            result = monitor_stop()
        assert result["ok"] is True

    def test_nothing_running(self):
        reg = MagicMock()
        reg.stop.return_value = None
        with patch("mem.mcp.server._registry", return_value=reg):
            result = monitor_stop()
        assert result["ok"] is False
        assert "No running monitor" in result["error"]
