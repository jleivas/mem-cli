from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from ..models.memory import Memory
from ..storage.memory_store import MemoryStore
from .embedding_service import cosine_similarity, embed, is_available as _embeddings_available


def _resolve_project(cwd: str | None) -> str:
    """Return the canonical project path.

    Uses the provided cwd, the CWD environment variable, or the current
    working directory — in that order.
    """
    if cwd:
        return str(Path(cwd).resolve())
    env_cwd = os.environ.get("PWD") or os.environ.get("CWD")
    if env_cwd:
        return str(Path(env_cwd).resolve())
    return str(Path.cwd().resolve())


class MemoryService:
    def __init__(self, store: MemoryStore | None = None) -> None:
        self._store = store or MemoryStore()

    def remember(
        self,
        content: str,
        *,
        cwd: str | None = None,
        tags: list[str] | None = None,
    ) -> Memory:
        """Store a new memory for the current project and return it."""
        project = _resolve_project(cwd)
        memory = Memory(content=content, project=project, tags=tags or [])
        memory.embedding = embed(content)
        return self._store.save(memory)

    def recall(
        self,
        *,
        cwd: str | None = None,
        query: str | None = None,
        tag: str | None = None,
    ) -> list[Memory]:
        """Return memories for the current project, newest first.

        If *query* is given, only memories whose content matches are returned.
        If *tag* is given, only memories with that tag are returned.
        Both filters can be combined: tag is applied first, then query.
        """
        project = _resolve_project(cwd)
        if tag:
            memories = self._store.filter_by_tag(project, tag)
            if query:
                if _embeddings_available():
                    q_emb = embed(query)
                    if q_emb is not None:
                        with_emb = [(m, cosine_similarity(q_emb, m.embedding))
                                    for m in memories if m.embedding is not None]
                        without_emb = [m for m in memories if m.embedding is None]
                        ranked = [m for m, _ in sorted(with_emb, key=lambda x: x[1], reverse=True)]
                        return ranked + sorted(without_emb, key=lambda m: m.timestamp, reverse=True)
                needle = query.lower()
                memories = [m for m in memories if needle in m.content.lower()]
            return memories
        if query:
            if _embeddings_available():
                q_emb = embed(query)
                if q_emb is not None:
                    return self._store.semantic_search(project, q_emb)
            return self._store.search(project, query)
        return self._store.list(project)

    def auto_remember(
        self,
        content: str,
        *,
        cwd: str | None = None,
        tags: list[str] | None = None,
    ) -> tuple[Memory, bool]:
        """Save memory only if no identical content exists for the project.

        Returns (memory, was_saved). When was_saved is False the returned
        memory is the pre-existing duplicate — nothing was written.
        Always appends the 'auto-captured' tag.
        """
        project = _resolve_project(cwd)
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        for existing in self._store.list(project):
            if hashlib.sha256(existing.content.encode()).hexdigest() == content_hash:
                return existing, False
        all_tags = list(tags or []) + ["auto-captured"]
        memory = Memory(content=content, project=project, tags=all_tags)
        memory.embedding = embed(content)
        return self._store.save(memory), True

    def forget(self, memory_id: str, *, cwd: str | None = None) -> bool:
        """Delete a memory by id. Returns True if found and deleted."""
        project = _resolve_project(cwd)
        return self._store.delete(project, memory_id)

    def projects(self) -> list[dict[str, Any]]:
        """Return metadata for all projects that have memories."""
        return self._store.list_projects()
