import pytest
from typer.testing import CliRunner

from mem.cli import app
from mem.models.memory import Memory
from mem.services.memory_service import MemoryService
from mem.storage.memory_store import MemoryStore


PROJECT = "/projects/mem-cli"


def _make_service(tmp_path):
    return MemoryService(store=MemoryStore(root=tmp_path))


def _patch_service(monkeypatch, tmp_path):
    svc = _make_service(tmp_path)
    monkeypatch.setattr("mem.cli._memory_service", lambda: svc)
    return svc


# ---------------------------------------------------------------------------
# remember
# ---------------------------------------------------------------------------

def test_remember_exits_zero(monkeypatch, tmp_path) -> None:
    _patch_service(monkeypatch, tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["remember", "hello world", "--cwd", PROJECT])
    assert result.exit_code == 0


def test_remember_shows_id_and_project(monkeypatch, tmp_path) -> None:
    _patch_service(monkeypatch, tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["remember", "use typer", "--cwd", PROJECT])
    assert "mem-cli" in result.output
    assert "use typer" in result.output


def test_remember_with_tags(monkeypatch, tmp_path) -> None:
    svc = _patch_service(monkeypatch, tmp_path)
    runner = CliRunner()
    runner.invoke(app, ["remember", "use ruff", "--tag", "style", "--cwd", PROJECT])
    memories = svc.recall(cwd=PROJECT)
    assert memories[0].tags == ["style"]


def test_remember_persists(monkeypatch, tmp_path) -> None:
    svc = _patch_service(monkeypatch, tmp_path)
    runner = CliRunner()
    runner.invoke(app, ["remember", "persisted fact", "--cwd", PROJECT])
    assert len(svc.recall(cwd=PROJECT)) == 1


# ---------------------------------------------------------------------------
# recall
# ---------------------------------------------------------------------------

def test_recall_shows_memories(monkeypatch, tmp_path) -> None:
    svc = _patch_service(monkeypatch, tmp_path)
    svc.remember("use typer", cwd=PROJECT)
    runner = CliRunner()
    result = runner.invoke(app, ["recall", "--cwd", PROJECT])
    assert result.exit_code == 0
    assert "use typer" in result.output


def test_recall_with_query(monkeypatch, tmp_path) -> None:
    svc = _patch_service(monkeypatch, tmp_path)
    svc.remember("use typer", cwd=PROJECT)
    svc.remember("use ruff", cwd=PROJECT)
    runner = CliRunner()
    result = runner.invoke(app, ["recall", "typer", "--cwd", PROJECT])
    assert "typer" in result.output
    assert "ruff" not in result.output


def test_recall_empty_project(monkeypatch, tmp_path) -> None:
    _patch_service(monkeypatch, tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["recall", "--cwd", PROJECT])
    assert result.exit_code == 0
    assert "No memories" in result.output


def test_recall_no_match_query(monkeypatch, tmp_path) -> None:
    svc = _patch_service(monkeypatch, tmp_path)
    svc.remember("use ruff", cwd=PROJECT)
    runner = CliRunner()
    result = runner.invoke(app, ["recall", "typer", "--cwd", PROJECT])
    assert result.exit_code == 0
    assert "No memories" in result.output


# ---------------------------------------------------------------------------
# forget
# ---------------------------------------------------------------------------

def test_forget_deletes_memory(monkeypatch, tmp_path) -> None:
    svc = _patch_service(monkeypatch, tmp_path)
    m = svc.remember("to delete", cwd=PROJECT)
    runner = CliRunner()
    result = runner.invoke(app, ["forget", m.id, "--cwd", PROJECT])
    assert result.exit_code == 0
    assert "deleted" in result.output
    assert svc.recall(cwd=PROJECT) == []


def test_forget_not_found_exits_one(monkeypatch, tmp_path) -> None:
    _patch_service(monkeypatch, tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["forget", "ffffffff", "--cwd", PROJECT])
    assert result.exit_code == 1
    assert "Not found" in result.output


# ---------------------------------------------------------------------------
# projects
# ---------------------------------------------------------------------------

def test_projects_lists_projects(monkeypatch, tmp_path) -> None:
    svc = _patch_service(monkeypatch, tmp_path)
    svc.remember("x", cwd=PROJECT)
    runner = CliRunner()
    result = runner.invoke(app, ["projects"])
    assert result.exit_code == 0
    assert "mem-cli" in result.output


def test_projects_empty(monkeypatch, tmp_path) -> None:
    _patch_service(monkeypatch, tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["projects"])
    assert result.exit_code == 0
    assert "No projects" in result.output
