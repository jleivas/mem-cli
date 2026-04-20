from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ..config import ensure_projects_dir
from ..models.memory import Memory
from ..utils.time import from_iso8601, to_iso8601


def _project_slug(project: str) -> str:
    """Stable, filesystem-safe directory name for a project path."""
    digest = hashlib.sha256(project.encode()).hexdigest()[:12]
    name = Path(project).name or "root"
    return f"{name}-{digest}"


def _memory_to_dict(memory: Memory) -> dict[str, Any]:
    return {
        "id": memory.id,
        "content": memory.content,
        "project": memory.project,
        "project_name": memory.project_name,
        "timestamp": to_iso8601(memory.timestamp),
        "tags": memory.tags,
    }


def _memory_from_dict(payload: dict[str, Any]) -> Memory:
    memory = Memory(
        content=str(payload["content"]),
        project=str(payload["project"]),
        tags=list(payload.get("tags") or []),
    )
    memory.id = str(payload["id"])
    ts = payload.get("timestamp")
    if ts:
        memory.timestamp = from_iso8601(ts)
    return memory


class MemoryStore:
    def __init__(self, root: Path | None = None) -> None:
        self._root = root or ensure_projects_dir()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _project_dir(self, project: str) -> Path:
        return self._root / _project_slug(project)

    def _memories_file(self, project: str) -> Path:
        return self._project_dir(project) / "memories.jsonl"

    def _meta_file(self, project: str) -> Path:
        return self._project_dir(project) / "meta.json"

    def _ensure_project_dir(self, project: str) -> None:
        d = self._project_dir(project)
        d.mkdir(parents=True, exist_ok=True)
        meta = self._meta_file(project)
        if not meta.exists():
            meta.write_text(
                json.dumps({"project": project, "project_name": Path(project).name or project}),
                encoding="utf-8",
            )

    def _read_all(self, project: str) -> list[Memory]:
        path = self._memories_file(project)
        if not path.exists():
            return []
        memories: list[Memory] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
                memories.append(_memory_from_dict(payload))
            except (json.JSONDecodeError, KeyError):
                continue
        return memories

    def _write_all(self, project: str, memories: list[Memory]) -> None:
        path = self._memories_file(project)
        lines = [json.dumps(_memory_to_dict(m)) for m in memories]
        path.write_text("\n".join(lines) + "\n" if lines else "", encoding="utf-8")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(self, memory: Memory) -> Memory:
        """Append a memory to the project store. Returns the saved memory."""
        self._ensure_project_dir(memory.project)
        path = self._memories_file(memory.project)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(_memory_to_dict(memory)) + "\n")
        return memory

    def list(self, project: str) -> list[Memory]:
        """Return all memories for a project, newest first."""
        memories = self._read_all(project)
        return sorted(memories, key=lambda m: m.timestamp, reverse=True)

    def get(self, project: str, memory_id: str) -> Memory | None:
        """Return a single memory by id, or None if not found."""
        for memory in self._read_all(project):
            if memory.id == memory_id:
                return memory
        return None

    def delete(self, project: str, memory_id: str) -> bool:
        """Remove a memory by id. Returns True if it was found and deleted."""
        memories = self._read_all(project)
        remaining = [m for m in memories if m.id != memory_id]
        if len(remaining) == len(memories):
            return False
        self._write_all(project, remaining)
        return True

    def search(self, project: str, query: str) -> list[Memory]:
        """Return memories whose content contains query (case-insensitive), newest first."""
        needle = query.lower()
        matches = [m for m in self._read_all(project) if needle in m.content.lower()]
        return sorted(matches, key=lambda m: m.timestamp, reverse=True)

    def list_projects(self) -> list[dict[str, Any]]:
        """Return metadata for all projects that have memories, sorted by name."""
        results: list[dict[str, Any]] = []
        for meta_file in sorted(self._root.glob("*/meta.json")):
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                memories_file = meta_file.parent / "memories.jsonl"
                count = 0
                if memories_file.exists():
                    count = sum(
                        1 for line in memories_file.read_text(encoding="utf-8").splitlines()
                        if line.strip()
                    )
                results.append({
                    "project": meta.get("project", ""),
                    "project_name": meta.get("project_name", ""),
                    "memory_count": count,
                })
            except (json.JSONDecodeError, OSError):
                continue
        return sorted(results, key=lambda r: r["project_name"].lower())
