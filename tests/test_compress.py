"""Tests for mem compress: helpers, MemoryService, MemoryStore.replace_all."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from mem.cli import app
from mem.models.memory import Memory
from mem.services.memory_service import (
    MemoryService,
    _build_compress_prompt,
    _parse_compress_line,
)
from mem.storage.memory_store import MemoryStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _svc(tmp_path: Path) -> MemoryService:
    return MemoryService(store=MemoryStore(root=tmp_path))


def _mem(content: str, project: str = "/proj", tags: list[str] | None = None) -> Memory:
    return Memory(content=content, project=project, tags=tags or [])


def _no_embed():
    return patch("mem.services.memory_service.embed", return_value=None)


# ---------------------------------------------------------------------------
# _parse_compress_line
# ---------------------------------------------------------------------------

def test_parse_plain_line():
    content, tags = _parse_compress_line("use postgres for storage")
    assert content == "use postgres for storage"
    assert tags == []


def test_parse_line_with_tags():
    content, tags = _parse_compress_line("use postgres [tags: db, architecture]")
    assert content == "use postgres"
    assert tags == ["db", "architecture"]


def test_parse_single_tag():
    content, tags = _parse_compress_line("prefer redis [tag: cache]")
    assert content == "prefer redis"
    assert tags == ["cache"]


def test_parse_strips_bullet():
    content, tags = _parse_compress_line("- use postgres")
    assert content == "use postgres"


def test_parse_strips_numbered():
    content, tags = _parse_compress_line("1. use postgres")
    assert content == "use postgres"


def test_parse_skips_code_fence():
    assert _parse_compress_line("```") is None
    assert _parse_compress_line("```python") is None


def test_parse_skips_blank():
    assert _parse_compress_line("") is None
    assert _parse_compress_line("   ") is None


def test_parse_skips_content_only_tags():
    assert _parse_compress_line("[tags: foo]") is None


# ---------------------------------------------------------------------------
# _build_compress_prompt
# ---------------------------------------------------------------------------

def test_build_prompt_includes_all_memories():
    mems = [_mem("use postgres"), _mem("prefer redis", tags=["cache"])]
    prompt = _build_compress_prompt(mems)
    assert "use postgres" in prompt
    assert "prefer redis" in prompt
    assert "[tags: cache]" in prompt


def test_build_prompt_includes_count():
    mems = [_mem("a"), _mem("b"), _mem("c")]
    assert "3 total" in _build_compress_prompt(mems)


def test_build_prompt_includes_project_name():
    m = Memory(content="fact", project="/my-project")
    assert "my-project" in _build_compress_prompt([m])


# ---------------------------------------------------------------------------
# MemoryStore.replace_all
# ---------------------------------------------------------------------------

def test_replace_all_overwrites_existing(tmp_path):
    store = MemoryStore(root=tmp_path)
    project = "/proj"
    store.save(_mem("old memory a", project))
    store.save(_mem("old memory b", project))

    new_mems = [_mem("compressed fact", project)]
    store.replace_all(project, new_mems)

    loaded = store.list(project)
    assert len(loaded) == 1
    assert loaded[0].content == "compressed fact"


def test_replace_all_creates_project_dir(tmp_path):
    store = MemoryStore(root=tmp_path)
    project = "/brand-new"
    store.replace_all(project, [_mem("fact", project)])
    assert len(store.list(project)) == 1


def test_replace_all_with_empty_list_clears_project(tmp_path):
    store = MemoryStore(root=tmp_path)
    project = "/proj"
    store.save(_mem("something", project))
    store.replace_all(project, [])
    assert store.list(project) == []


# ---------------------------------------------------------------------------
# MemoryService.replace_all
# ---------------------------------------------------------------------------

def test_service_replace_all_persists(tmp_path):
    svc = _svc(tmp_path)
    with _no_embed():
        svc.remember("old fact", cwd="/proj")

    new = [Memory(content="new fact", project="/proj")]
    with _no_embed():
        svc.replace_all(new, cwd="/proj")

    stored = svc.recall(cwd="/proj")
    assert len(stored) == 1
    assert stored[0].content == "new fact"


# ---------------------------------------------------------------------------
# MemoryService.compress — mocked agent
# ---------------------------------------------------------------------------

def _mock_agent_text(stdout: str, ok: bool = True):
    from mem.services.prompt_service import AgentResult, AgentTextResult
    result = AgentResult(exit_code=0 if ok else 1, stderr="" if ok else "boom")
    return MagicMock(return_value=AgentTextResult(stdout=stdout, result=result))


def test_compress_returns_parsed_pairs(tmp_path):
    svc = _svc(tmp_path)
    with _no_embed():
        svc.remember("use postgres for storage", cwd="/proj", tags=["db"])
        svc.remember("prefer postgres", cwd="/proj")

    agent_output = "use postgres for all storage needs [tags: db]"

    with patch("mem.services.prompt_service.run_agent_text") as mock_run, _no_embed():
        mock_run.return_value = _mock_agent_text(agent_output).return_value
        originals, pairs, error = svc.compress(cwd="/proj", agent="claude")

    assert error is None
    assert len(originals) == 2
    assert len(pairs) == 1
    assert pairs[0][0] == "use postgres for all storage needs"
    assert "db" in pairs[0][1]


def test_compress_returns_error_on_agent_failure(tmp_path):
    svc = _svc(tmp_path)
    with _no_embed():
        svc.remember("fact", cwd="/proj")
        svc.remember("another fact", cwd="/proj")

    with patch("mem.services.prompt_service.run_agent_text") as mock_run, _no_embed():
        mock_run.return_value = _mock_agent_text("", ok=False).return_value
        _, pairs, error = svc.compress(cwd="/proj", agent="claude")

    assert error is not None
    assert pairs == []


def test_compress_returns_empty_on_no_memories(tmp_path):
    svc = _svc(tmp_path)
    with patch("mem.services.prompt_service.run_agent_text") as mock_run:
        originals, pairs, error = svc.compress(cwd="/proj", agent="claude")

    assert originals == []
    assert pairs == []
    assert error is None
    mock_run.assert_not_called()


def test_compress_skips_blank_lines_in_output(tmp_path):
    svc = _svc(tmp_path)
    with _no_embed():
        svc.remember("fact a", cwd="/proj")
        svc.remember("fact b", cwd="/proj")

    agent_output = "\nfact a merged with b\n\n"
    with patch("mem.services.prompt_service.run_agent_text") as mock_run, _no_embed():
        mock_run.return_value = _mock_agent_text(agent_output).return_value
        _, pairs, error = svc.compress(cwd="/proj", agent="claude")

    assert len(pairs) == 1
    assert error is None


# ---------------------------------------------------------------------------
# CLI compress command — requires confirmation
# ---------------------------------------------------------------------------

def _patch_svc(monkeypatch, svc: MemoryService) -> None:
    monkeypatch.setattr("mem.cli._memory_service", lambda: svc)


def _patch_agents(monkeypatch, agents: list[str]) -> None:
    monkeypatch.setattr("mem.cli.detect_available_agents", lambda: agents)


def test_cli_compress_no_memories(tmp_path, monkeypatch):
    svc = _svc(tmp_path)
    _patch_svc(monkeypatch, svc)
    _patch_agents(monkeypatch, ["claude"])
    result = CliRunner().invoke(app, ["compress", "--cwd", "/empty"])
    assert result.exit_code == 0
    assert "No memories" in result.output


def test_cli_compress_single_memory(tmp_path, monkeypatch):
    svc = _svc(tmp_path)
    with _no_embed():
        svc.remember("only one", cwd="/proj")
    _patch_svc(monkeypatch, svc)
    _patch_agents(monkeypatch, ["claude"])
    result = CliRunner().invoke(app, ["compress", "--cwd", "/proj"])
    assert result.exit_code == 0
    assert "nothing to compress" in result.output.lower()


def test_cli_compress_confirm_replaces(tmp_path, monkeypatch):
    svc = _svc(tmp_path)
    with _no_embed():
        svc.remember("fact a", cwd="/proj")
        svc.remember("fact b", cwd="/proj")

    _patch_svc(monkeypatch, svc)
    _patch_agents(monkeypatch, ["claude"])

    agent_output = "merged fact"

    def _fake_compress(**kwargs):
        originals = svc._store.list("/proj")
        pairs = [("merged fact", [])]
        return originals, pairs, None

    monkeypatch.setattr(svc, "compress", _fake_compress)

    with _no_embed():
        result = CliRunner().invoke(app, ["compress", "--cwd", "/proj"], input="y\n")

    assert result.exit_code == 0
    stored = svc.recall(cwd="/proj")
    assert len(stored) == 1
    assert stored[0].content == "merged fact"


def test_cli_compress_cancel_keeps_originals(tmp_path, monkeypatch):
    svc = _svc(tmp_path)
    with _no_embed():
        svc.remember("fact a", cwd="/proj")
        svc.remember("fact b", cwd="/proj")

    _patch_svc(monkeypatch, svc)
    _patch_agents(monkeypatch, ["claude"])

    def _fake_compress(**kwargs):
        originals = svc._store.list("/proj")
        return originals, [("merged", [])], None

    monkeypatch.setattr(svc, "compress", _fake_compress)

    result = CliRunner().invoke(app, ["compress", "--cwd", "/proj"], input="n\n")

    assert result.exit_code == 0
    assert len(svc.recall(cwd="/proj")) == 2
