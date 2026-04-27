"""Tests for semantic search: embedding_service, MemoryStore.semantic_search,
and MemoryService.recall() with semantic ranking."""
from __future__ import annotations

import math
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mem.models.memory import Memory
from mem.services.embedding_service import cosine_similarity
from mem.storage.memory_store import MemoryStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unit_vec(values: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in values))
    return [x / norm for x in values] if norm else values


def _make_memory(content: str, project: str = "/proj", embedding: list[float] | None = None) -> Memory:
    m = Memory(content=content, project=project)
    m.embedding = embedding
    return m


def _store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(root=tmp_path)


# ---------------------------------------------------------------------------
# cosine_similarity
# ---------------------------------------------------------------------------

def test_cosine_identical_vectors():
    v = _unit_vec([1.0, 2.0, 3.0])
    assert cosine_similarity(v, v) == pytest.approx(1.0)


def test_cosine_orthogonal_vectors():
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert cosine_similarity(a, b) == pytest.approx(0.0)


def test_cosine_opposite_vectors():
    a = [1.0, 0.0]
    b = [-1.0, 0.0]
    assert cosine_similarity(a, b) == pytest.approx(-1.0)


def test_cosine_zero_vector_returns_zero():
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


# ---------------------------------------------------------------------------
# MemoryStore.semantic_search
# ---------------------------------------------------------------------------

def test_semantic_search_ranks_by_similarity(tmp_path):
    store = _store(tmp_path)
    project = "/proj"

    close = _make_memory("use postgres", project, embedding=_unit_vec([1.0, 0.1]))
    far = _make_memory("prefer redis", project, embedding=_unit_vec([0.1, 1.0]))

    store.save(close)
    store.save(far)

    query_emb = _unit_vec([1.0, 0.0])
    results = store.semantic_search(project, query_emb)

    assert results[0].content == "use postgres"
    assert results[1].content == "prefer redis"


def test_semantic_search_appends_memories_without_embedding(tmp_path):
    store = _store(tmp_path)
    project = "/proj"

    with_emb = _make_memory("has embedding", project, embedding=_unit_vec([0.5, 0.5]))
    without_emb = _make_memory("no embedding", project, embedding=None)

    store.save(with_emb)
    store.save(without_emb)

    results = store.semantic_search(project, _unit_vec([1.0, 0.0]))

    assert results[0].content == "has embedding"
    assert results[1].content == "no embedding"


def test_semantic_search_empty_project(tmp_path):
    store = _store(tmp_path)
    assert store.semantic_search("/empty", _unit_vec([1.0, 0.0])) == []


# ---------------------------------------------------------------------------
# Memory model: embedding field round-trips through JSONL
# ---------------------------------------------------------------------------

def test_embedding_survives_jsonl_roundtrip(tmp_path):
    store = _store(tmp_path)
    project = "/proj"
    emb = _unit_vec([0.3, 0.4, 0.5])

    m = _make_memory("roundtrip test", project, embedding=emb)
    store.save(m)

    loaded = store.list(project)
    assert len(loaded) == 1
    assert loaded[0].embedding == pytest.approx(emb)


def test_memory_without_embedding_loads_as_none(tmp_path):
    store = _store(tmp_path)
    project = "/proj"
    store.save(_make_memory("no embedding", project, embedding=None))

    loaded = store.list(project)
    assert loaded[0].embedding is None


# ---------------------------------------------------------------------------
# MemoryService.recall() — semantic path via mock
# ---------------------------------------------------------------------------

def _patch_embed(return_value: list[float] | None):
    return patch("mem.services.memory_service.embed", return_value=return_value)


def _patch_available(available: bool):
    return patch("mem.services.memory_service._embeddings_available", return_value=available)


def test_recall_uses_semantic_search_when_available(tmp_path):
    from mem.services.memory_service import MemoryService

    store = MemoryStore(root=tmp_path)
    project = "/proj"

    close_emb = _unit_vec([1.0, 0.1])
    far_emb = _unit_vec([0.1, 1.0])
    query_emb = _unit_vec([1.0, 0.0])

    store.save(_make_memory("close match", project, embedding=close_emb))
    store.save(_make_memory("far match", project, embedding=far_emb))

    svc = MemoryService(store=store)

    with _patch_available(True), _patch_embed(query_emb):
        results = svc.recall(cwd=project, query="anything")

    assert results[0].content == "close match"
    assert results[1].content == "far match"


def test_recall_falls_back_to_substring_when_unavailable(tmp_path):
    from mem.services.memory_service import MemoryService

    store = MemoryStore(root=tmp_path)
    project = "/proj"

    store.save(_make_memory("use postgres for storage", project))
    store.save(_make_memory("prefer redis cache", project))

    svc = MemoryService(store=store)

    with _patch_available(False):
        results = svc.recall(cwd=project, query="postgres")

    assert len(results) == 1
    assert "postgres" in results[0].content


def test_recall_falls_back_when_embed_returns_none(tmp_path):
    from mem.services.memory_service import MemoryService

    store = MemoryStore(root=tmp_path)
    project = "/proj"
    store.save(_make_memory("use postgres", project))

    svc = MemoryService(store=store)

    with _patch_available(True), _patch_embed(None):
        results = svc.recall(cwd=project, query="postgres")

    assert len(results) == 1


# ---------------------------------------------------------------------------
# MemoryService.remember() — embedding attached at save time
# ---------------------------------------------------------------------------

def test_remember_attaches_embedding(tmp_path):
    from mem.services.memory_service import MemoryService

    store = MemoryStore(root=tmp_path)
    fake_emb = _unit_vec([0.6, 0.8])

    svc = MemoryService(store=store)

    with patch("mem.services.memory_service.embed", return_value=fake_emb):
        memory = svc.remember("use postgres", cwd="/proj")

    assert memory.embedding == pytest.approx(fake_emb)

    persisted = store.list("/proj")
    assert persisted[0].embedding == pytest.approx(fake_emb)


def test_remember_works_when_embed_returns_none(tmp_path):
    from mem.services.memory_service import MemoryService

    store = MemoryStore(root=tmp_path)
    svc = MemoryService(store=store)

    with patch("mem.services.memory_service.embed", return_value=None):
        memory = svc.remember("use postgres", cwd="/proj")

    assert memory.embedding is None
    assert store.list("/proj")[0].embedding is None
