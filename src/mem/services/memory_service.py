from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ..models.memory import Memory
from ..storage.memory_store import MemoryStore


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
        return self._store.save(memory)

    def recall(
        self,
        *,
        cwd: str | None = None,
        query: str | None = None,
    ) -> list[Memory]:
        """Return memories for the current project, newest first.

        If *query* is given, only memories whose content matches are returned.
        """
        project = _resolve_project(cwd)
        if query:
            return self._store.search(project, query)
        return self._store.list(project)

    def forget(self, memory_id: str, *, cwd: str | None = None) -> bool:
        """Delete a memory by id. Returns True if found and deleted."""
        project = _resolve_project(cwd)
        return self._store.delete(project, memory_id)

    def projects(self) -> list[dict[str, Any]]:
        """Return metadata for all projects that have memories."""
        return self._store.list_projects()
