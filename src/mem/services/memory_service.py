from __future__ import annotations

import hashlib
import os
import re
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

    def replace_all(self, memories: list[Memory], *, cwd: str | None = None) -> None:
        """Overwrite all project memories with *memories*, computing embeddings where missing."""
        project = _resolve_project(cwd)
        for m in memories:
            if m.embedding is None:
                m.embedding = embed(m.content)
        self._store.replace_all(project, memories)

    def compress(
        self,
        *,
        cwd: str | None = None,
        agent: str = "claude",
    ) -> tuple[list[Memory], list[tuple[str, list[str]]], str | None]:
        """Call *agent* to merge redundant memories.

        Returns (originals, compressed_pairs, error).
        compressed_pairs is a list of (content, tags) not yet persisted.
        error is None on success.
        """
        from .prompt_service import run_agent_text as _run_agent_text

        project = _resolve_project(cwd)
        originals = self._store.list(project)
        if not originals:
            return originals, [], None

        prompt = _build_compress_prompt(originals)
        result = _run_agent_text(prompt, agent)

        if not result.result.ok or not result.stdout.strip():
            return originals, [], result.result.stderr or "Agent returned no output."

        pairs: list[tuple[str, list[str]]] = []
        for line in result.stdout.splitlines():
            parsed = _parse_compress_line(line)
            if parsed:
                pairs.append(parsed)

        return originals, pairs, None

    def projects(self) -> list[dict[str, Any]]:
        """Return metadata for all projects that have memories."""
        return self._store.list_projects()


# ---------------------------------------------------------------------------
# Compression helpers
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(r"\s*\[tags?:\s*([^\]]+)\]\s*$", re.IGNORECASE)
_LEADING_BULLET = re.compile(r"^[-*•]\s+|^\d+\.\s+")
_CODE_FENCE = re.compile(r"^```")


def _parse_compress_line(line: str) -> tuple[str, list[str]] | None:
    line = line.strip()
    if not line or _CODE_FENCE.match(line):
        return None
    line = _LEADING_BULLET.sub("", line).strip()
    m = _TAG_RE.search(line)
    if m:
        tags = [t.strip() for t in m.group(1).split(",") if t.strip()]
        content = line[: m.start()].strip()
    else:
        tags = []
        content = line
    return (content, tags) if content else None


def _build_compress_prompt(memories: list[Memory]) -> str:
    project_name = memories[0].project_name if memories else "project"
    lines = []
    for m in memories:
        tag_str = f" [tags: {', '.join(m.tags)}]" if m.tags else ""
        lines.append(f"- {m.content}{tag_str}")
    block = "\n".join(lines)
    return (
        f"Compress the following project memories for '{project_name}' "
        f"by merging redundant or overlapping entries.\n\n"
        f"Current memories ({len(memories)} total):\n"
        f"{block}\n\n"
        "Rules:\n"
        "- Merge memories that overlap or repeat the same fact\n"
        "- Keep ALL distinct facts — never discard unique information\n"
        "- For merged memories, combine and deduplicate their tags\n"
        "- Output ONLY the final compressed memories, one per line\n"
        "- Format each line: memory text [tags: tag1, tag2] — omit [tags:] if no tags\n"
        "- No numbering, no headers, no explanations, no extra blank lines\n"
    )
