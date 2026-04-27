"""Tests for auto-capture: MemoryService.auto_remember() and --auto CLI flag."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from mem.cli import app
from mem.services.memory_service import MemoryService
from mem.storage.memory_store import MemoryStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _svc(tmp_path: Path) -> MemoryService:
    return MemoryService(store=MemoryStore(root=tmp_path))


def _no_embed():
    return patch("mem.services.memory_service.embed", return_value=None)


# ---------------------------------------------------------------------------
# MemoryService.auto_remember()
# ---------------------------------------------------------------------------

def test_auto_remember_saves_with_auto_captured_tag(tmp_path):
    svc = _svc(tmp_path)
    with _no_embed():
        memory, saved = svc.auto_remember("use postgres", cwd="/proj")
    assert saved is True
    assert "auto-captured" in memory.tags


def test_auto_remember_deduplicates_identical_content(tmp_path):
    svc = _svc(tmp_path)
    with _no_embed():
        _, first_saved = svc.auto_remember("use postgres", cwd="/proj")
        _, second_saved = svc.auto_remember("use postgres", cwd="/proj")
    assert first_saved is True
    assert second_saved is False
    assert len(svc.recall(cwd="/proj")) == 1


def test_auto_remember_saves_different_content(tmp_path):
    svc = _svc(tmp_path)
    with _no_embed():
        _, s1 = svc.auto_remember("use postgres", cwd="/proj")
        _, s2 = svc.auto_remember("use redis for cache", cwd="/proj")
    assert s1 is True
    assert s2 is True
    assert len(svc.recall(cwd="/proj")) == 2


def test_auto_remember_returns_existing_on_duplicate(tmp_path):
    svc = _svc(tmp_path)
    with _no_embed():
        original, _ = svc.auto_remember("use postgres", cwd="/proj")
        duplicate, saved = svc.auto_remember("use postgres", cwd="/proj")
    assert saved is False
    assert duplicate.id == original.id


def test_auto_remember_does_not_leak_across_projects(tmp_path):
    svc = _svc(tmp_path)
    with _no_embed():
        _, s1 = svc.auto_remember("shared content", cwd="/proj-a")
        _, s2 = svc.auto_remember("shared content", cwd="/proj-b")
    assert s1 is True
    assert s2 is True


def test_auto_remember_extra_tags_preserved(tmp_path):
    svc = _svc(tmp_path)
    with _no_embed():
        memory, _ = svc.auto_remember("use postgres", cwd="/proj", tags=["db"])
    assert "db" in memory.tags
    assert "auto-captured" in memory.tags


def test_auto_remember_dedup_is_content_hash_not_whitespace(tmp_path):
    """Trailing whitespace differences do NOT bypass deduplication."""
    svc = _svc(tmp_path)
    with _no_embed():
        _, s1 = svc.auto_remember("use postgres", cwd="/proj")
        _, s2 = svc.auto_remember("use postgres", cwd="/proj")
    assert s1 is True
    assert s2 is False


# ---------------------------------------------------------------------------
# CLI --auto flag
# ---------------------------------------------------------------------------

def _patch_service(monkeypatch, svc: MemoryService) -> None:
    monkeypatch.setattr("mem.cli._memory_service", lambda: svc)


def test_cli_auto_flag_saves_memory(tmp_path, monkeypatch):
    svc = _svc(tmp_path)
    _patch_service(monkeypatch, svc)
    runner = CliRunner()
    with _no_embed():
        result = runner.invoke(app, ["remember", "--auto", "use postgres", "--cwd", "/proj"])
    assert result.exit_code == 0
    memories = svc.recall(cwd="/proj")
    assert len(memories) == 1
    assert "auto-captured" in memories[0].tags


def test_cli_auto_flag_silent_on_duplicate(tmp_path, monkeypatch):
    svc = _svc(tmp_path)
    _patch_service(monkeypatch, svc)
    runner = CliRunner()
    with _no_embed():
        runner.invoke(app, ["remember", "--auto", "use postgres", "--cwd", "/proj"])
        result = runner.invoke(app, ["remember", "--auto", "use postgres", "--cwd", "/proj"])
    assert result.exit_code == 0
    assert len(svc.recall(cwd="/proj")) == 1


def test_cli_remember_without_auto_unchanged(tmp_path, monkeypatch):
    """Normal remember still works and does NOT add auto-captured tag."""
    svc = _svc(tmp_path)
    _patch_service(monkeypatch, svc)
    runner = CliRunner()
    with _no_embed():
        result = runner.invoke(app, ["remember", "use postgres", "--cwd", "/proj"])
    assert result.exit_code == 0
    memories = svc.recall(cwd="/proj")
    assert len(memories) == 1
    assert "auto-captured" not in memories[0].tags
