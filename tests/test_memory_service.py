import pytest

from clar.models.memory import Memory
from clar.services.memory_service import MemoryService, _resolve_project
from clar.storage.memory_store import MemoryStore


PROJECT = "/projects/mem-cli"
OTHER = "/projects/other"


def _svc(tmp_path):
    return MemoryService(store=MemoryStore(root=tmp_path))


# ---------------------------------------------------------------------------
# _resolve_project
# ---------------------------------------------------------------------------

def test_resolve_project_uses_explicit_cwd() -> None:
    result = _resolve_project("/explicit/path")
    assert result.endswith("explicit/path")


def test_resolve_project_uses_env_pwd(monkeypatch) -> None:
    monkeypatch.setenv("PWD", "/from/env")
    monkeypatch.delenv("CWD", raising=False)
    result = _resolve_project(None)
    assert result.endswith("from/env")


def test_resolve_project_falls_back_to_cwd(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("PWD", raising=False)
    monkeypatch.delenv("CWD", raising=False)
    monkeypatch.chdir(tmp_path)
    result = _resolve_project(None)
    assert result == str(tmp_path)


# ---------------------------------------------------------------------------
# remember
# ---------------------------------------------------------------------------

def test_remember_saves_memory(tmp_path) -> None:
    svc = _svc(tmp_path)
    m = svc.remember("use typer", cwd=PROJECT)

    assert m.content == "use typer"
    assert m.project.endswith("projects/mem-cli")
    assert m.id


def test_remember_stores_tags(tmp_path) -> None:
    svc = _svc(tmp_path)
    m = svc.remember("use ruff", cwd=PROJECT, tags=["style"])

    assert m.tags == ["style"]


def test_remember_persists_to_store(tmp_path) -> None:
    svc = _svc(tmp_path)
    m = svc.remember("persisted", cwd=PROJECT)

    recalled = svc.recall(cwd=PROJECT)
    assert any(x.id == m.id for x in recalled)


# ---------------------------------------------------------------------------
# recall
# ---------------------------------------------------------------------------

def test_recall_returns_memories_for_project(tmp_path) -> None:
    svc = _svc(tmp_path)
    svc.remember("a", cwd=PROJECT)
    svc.remember("b", cwd=PROJECT)

    memories = svc.recall(cwd=PROJECT)
    assert len(memories) == 2


def test_recall_with_query_filters(tmp_path) -> None:
    svc = _svc(tmp_path)
    svc.remember("use typer", cwd=PROJECT)
    svc.remember("use ruff", cwd=PROJECT)

    results = svc.recall(cwd=PROJECT, query="typer")
    assert len(results) == 1
    assert "typer" in results[0].content


def test_recall_returns_empty_for_unknown_project(tmp_path) -> None:
    svc = _svc(tmp_path)
    assert svc.recall(cwd="/nonexistent") == []


def test_recall_does_not_leak_across_projects(tmp_path) -> None:
    svc = _svc(tmp_path)
    svc.remember("for mem-cli", cwd=PROJECT)
    svc.remember("for other", cwd=OTHER)

    assert len(svc.recall(cwd=PROJECT)) == 1
    assert len(svc.recall(cwd=OTHER)) == 1


# ---------------------------------------------------------------------------
# forget
# ---------------------------------------------------------------------------

def test_forget_removes_memory(tmp_path) -> None:
    svc = _svc(tmp_path)
    m = svc.remember("to forget", cwd=PROJECT)

    result = svc.forget(m.id, cwd=PROJECT)

    assert result is True
    assert svc.recall(cwd=PROJECT) == []


def test_forget_returns_false_when_not_found(tmp_path) -> None:
    svc = _svc(tmp_path)
    svc.remember("keep", cwd=PROJECT)

    assert svc.forget("ffffffff", cwd=PROJECT) is False


def test_forget_does_not_remove_wrong_project(tmp_path) -> None:
    svc = _svc(tmp_path)
    m = svc.remember("in mem-cli", cwd=PROJECT)
    svc.remember("in other", cwd=OTHER)

    result = svc.forget(m.id, cwd=OTHER)

    assert result is False
    assert len(svc.recall(cwd=PROJECT)) == 1


# ---------------------------------------------------------------------------
# projects
# ---------------------------------------------------------------------------

def test_projects_lists_all(tmp_path) -> None:
    svc = _svc(tmp_path)
    svc.remember("x", cwd=PROJECT)
    svc.remember("y", cwd=OTHER)

    ps = svc.projects()
    names = [p["project_name"] for p in ps]
    assert "mem-cli" in names
    assert "other" in names


def test_projects_returns_empty_when_none(tmp_path) -> None:
    svc = _svc(tmp_path)
    assert svc.projects() == []
