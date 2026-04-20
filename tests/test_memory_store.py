import json

import pytest

from mem.models.memory import Memory
from mem.storage.memory_store import MemoryStore, _project_slug


PROJECT = "/projects/mem-cli"
OTHER_PROJECT = "/projects/s-stock"


# ---------------------------------------------------------------------------
# _project_slug helper
# ---------------------------------------------------------------------------

def test_project_slug_is_stable() -> None:
    assert _project_slug(PROJECT) == _project_slug(PROJECT)


def test_project_slug_differs_for_different_projects() -> None:
    assert _project_slug(PROJECT) != _project_slug(OTHER_PROJECT)


def test_project_slug_contains_project_name() -> None:
    slug = _project_slug("/projects/my-app")
    assert slug.startswith("my-app-")


# ---------------------------------------------------------------------------
# save / list
# ---------------------------------------------------------------------------

def test_save_creates_file(tmp_path) -> None:
    store = MemoryStore(root=tmp_path)
    m = store.save(Memory("hello", PROJECT))

    files = list(tmp_path.rglob("memories.jsonl"))
    assert len(files) == 1
    assert m.id in files[0].read_text()


def test_list_returns_newest_first(tmp_path) -> None:
    store = MemoryStore(root=tmp_path)
    m1 = store.save(Memory("first", PROJECT))
    m2 = store.save(Memory("second", PROJECT))
    m3 = store.save(Memory("third", PROJECT))

    memories = store.list(PROJECT)

    assert len(memories) == 3
    assert memories[0].id == m3.id
    assert memories[-1].id == m1.id


def test_list_empty_project_returns_empty(tmp_path) -> None:
    store = MemoryStore(root=tmp_path)
    assert store.list("/nonexistent/project") == []


def test_list_isolates_projects(tmp_path) -> None:
    store = MemoryStore(root=tmp_path)
    store.save(Memory("for mem-cli", PROJECT))
    store.save(Memory("for s-stock", OTHER_PROJECT))

    assert len(store.list(PROJECT)) == 1
    assert len(store.list(OTHER_PROJECT)) == 1


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------

def test_get_returns_memory_by_id(tmp_path) -> None:
    store = MemoryStore(root=tmp_path)
    saved = store.save(Memory("hello", PROJECT))

    found = store.get(PROJECT, saved.id)

    assert found is not None
    assert found.id == saved.id
    assert found.content == "hello"


def test_get_returns_none_for_missing_id(tmp_path) -> None:
    store = MemoryStore(root=tmp_path)
    store.save(Memory("hello", PROJECT))

    assert store.get(PROJECT, "ffffffff") is None


def test_get_on_empty_project_returns_none(tmp_path) -> None:
    store = MemoryStore(root=tmp_path)
    assert store.get(PROJECT, "anything") is None


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------

def test_delete_removes_memory(tmp_path) -> None:
    store = MemoryStore(root=tmp_path)
    m = store.save(Memory("to delete", PROJECT))
    store.save(Memory("keep this", PROJECT))

    result = store.delete(PROJECT, m.id)

    assert result is True
    remaining = store.list(PROJECT)
    assert len(remaining) == 1
    assert remaining[0].content == "keep this"


def test_delete_returns_false_when_not_found(tmp_path) -> None:
    store = MemoryStore(root=tmp_path)
    store.save(Memory("x", PROJECT))

    assert store.delete(PROJECT, "ffffffff") is False


def test_delete_on_empty_project_returns_false(tmp_path) -> None:
    store = MemoryStore(root=tmp_path)
    assert store.delete(PROJECT, "anything") is False


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

def test_search_finds_case_insensitive_match(tmp_path) -> None:
    store = MemoryStore(root=tmp_path)
    store.save(Memory("Use Typer for the CLI", PROJECT))
    store.save(Memory("python 3.11+ required", PROJECT))

    results = store.search(PROJECT, "typer")

    assert len(results) == 1
    assert "Typer" in results[0].content


def test_search_returns_empty_when_no_match(tmp_path) -> None:
    store = MemoryStore(root=tmp_path)
    store.save(Memory("use ruff", PROJECT))

    assert store.search(PROJECT, "black") == []


def test_search_returns_newest_first(tmp_path) -> None:
    store = MemoryStore(root=tmp_path)
    m1 = store.save(Memory("ruff rule A", PROJECT))
    m2 = store.save(Memory("ruff rule B", PROJECT))

    results = store.search(PROJECT, "ruff")

    assert results[0].id == m2.id
    assert results[1].id == m1.id


# ---------------------------------------------------------------------------
# list_projects
# ---------------------------------------------------------------------------

def test_list_projects_returns_all(tmp_path) -> None:
    store = MemoryStore(root=tmp_path)
    store.save(Memory("x", PROJECT))
    store.save(Memory("y", OTHER_PROJECT))

    projects = store.list_projects()

    names = [p["project_name"] for p in projects]
    assert "mem-cli" in names
    assert "s-stock" in names


def test_list_projects_memory_count(tmp_path) -> None:
    store = MemoryStore(root=tmp_path)
    store.save(Memory("a", PROJECT))
    store.save(Memory("b", PROJECT))
    store.save(Memory("c", OTHER_PROJECT))

    projects = {p["project_name"]: p["memory_count"] for p in store.list_projects()}

    assert projects["mem-cli"] == 2
    assert projects["s-stock"] == 1


def test_list_projects_empty_store(tmp_path) -> None:
    store = MemoryStore(root=tmp_path)
    assert store.list_projects() == []


def test_list_projects_sorted_by_name(tmp_path) -> None:
    store = MemoryStore(root=tmp_path)
    store.save(Memory("x", "/projects/zebra"))
    store.save(Memory("y", "/projects/alpha"))

    names = [p["project_name"] for p in store.list_projects()]
    assert names == sorted(names, key=str.lower)


# ---------------------------------------------------------------------------
# Roundtrip — tags and timestamp survive serialization
# ---------------------------------------------------------------------------

def test_roundtrip_preserves_tags_and_timestamp(tmp_path) -> None:
    store = MemoryStore(root=tmp_path)
    original = Memory("check deps", PROJECT, tags=["deps", "ci"])
    store.save(original)

    loaded = store.get(PROJECT, original.id)

    assert loaded is not None
    assert loaded.tags == ["deps", "ci"]
    assert loaded.timestamp.isoformat() == original.timestamp.isoformat()


# ---------------------------------------------------------------------------
# Resilience — corrupt lines are skipped
# ---------------------------------------------------------------------------

def test_corrupt_line_is_skipped(tmp_path) -> None:
    store = MemoryStore(root=tmp_path)
    m = store.save(Memory("good memory", PROJECT))

    # inject a corrupt line
    memories_file = list(tmp_path.rglob("memories.jsonl"))[0]
    memories_file.write_text("not-valid-json\n" + memories_file.read_text())

    memories = store.list(PROJECT)
    assert len(memories) == 1
    assert memories[0].content == "good memory"
