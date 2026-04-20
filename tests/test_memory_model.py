from datetime import timezone

import pytest

from clar.models.memory import Memory, _project_name


# ---------------------------------------------------------------------------
# _project_name helper
# ---------------------------------------------------------------------------

def test_project_name_returns_last_component() -> None:
    assert _project_name("/Users/acidlabs/projects/mem-cli") == "mem-cli"


def test_project_name_handles_trailing_slash() -> None:
    assert _project_name("/projects/my-app/") == "my-app"


def test_project_name_fallback_on_root() -> None:
    result = _project_name("/")
    # pathlib.Path("/").name == "" — falls back to the original string
    assert result == "/"


# ---------------------------------------------------------------------------
# Memory construction
# ---------------------------------------------------------------------------

def test_memory_defaults() -> None:
    m = Memory(content="hello", project="/projects/foo")

    assert m.content == "hello"
    assert m.project == "/projects/foo"
    assert m.project_name == "foo"
    assert len(m.id) == 8
    assert m.tags == []
    assert m.timestamp.tzinfo is not None


def test_memory_project_name_derived_from_project() -> None:
    m = Memory(content="x", project="/a/b/my-project")
    assert m.project_name == "my-project"


def test_memory_tags_stored() -> None:
    m = Memory(content="x", project="/p", tags=["style", "deps"])
    assert m.tags == ["style", "deps"]


def test_memory_unique_ids() -> None:
    ids = {Memory(content="x", project="/p").id for _ in range(20)}
    assert len(ids) == 20


def test_memory_timestamp_is_utc() -> None:
    m = Memory(content="x", project="/p")
    assert m.timestamp.tzinfo == timezone.utc


def test_memory_negative_content_empty_string() -> None:
    m = Memory(content="", project="/p")
    assert m.content == ""
