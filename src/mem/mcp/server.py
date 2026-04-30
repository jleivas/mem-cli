"""MCP server for mem-cli.

Exposes memory and observability operations as MCP tools so that agents
can read and write project memories and inspect token usage without
running shell commands.

Run via:
    mem serve
"""
from __future__ import annotations

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..config import get_runtime_state_path
from ..services.memory_service import MemoryService
from ..services.process_registry import ProcessRegistry
from ..storage.runtime_state import RuntimeStateStore
from ..storage.token_snapshot import TokenSnapshotStore
from ..utils.logging import configure_logging

logger = logging.getLogger(__name__)

mcp = FastMCP(
    "mem",
    instructions=(
        "mem-cli MCP server. Use the memory_* tools to store and retrieve "
        "project-scoped memories. Use the monitor_* tools to inspect or "
        "control the local token monitor."
    ),
)

# ---------------------------------------------------------------------------
# Internal helpers — instantiated lazily so the server can start without a
# running daemon or any project context.
# ---------------------------------------------------------------------------

_memory_svc: MemoryService | None = None


def _mem() -> MemoryService:
    global _memory_svc
    if _memory_svc is None:
        _memory_svc = MemoryService()
    return _memory_svc


def _registry() -> ProcessRegistry:
    return ProcessRegistry(RuntimeStateStore(get_runtime_state_path()))


def _snapshot_store() -> TokenSnapshotStore:
    return TokenSnapshotStore()


# ---------------------------------------------------------------------------
# Memory tools
# ---------------------------------------------------------------------------

@mcp.tool()
def memory_remember(
    content: str,
    tags: list[str] | None = None,
    cwd: str = "",
) -> dict[str, Any]:
    """Store a memory for the current project.

    Args:
        content: Text to remember.
        tags: Optional list of tag strings.
        cwd: Absolute project path. Defaults to the caller's working directory.
    """
    memory = _mem().remember(content, cwd=cwd or None, tags=tags or [])
    return {
        "id": memory.id,
        "project": memory.project,
        "project_name": memory.project_name,
        "content": memory.content,
        "tags": memory.tags,
        "timestamp": memory.timestamp.isoformat(),
    }


@mcp.tool()
def memory_recall(
    query: str = "",
    tag: str = "",
    cwd: str = "",
) -> list[dict[str, Any]]:
    """Retrieve memories for the current project.

    Args:
        query: Optional substring to filter memories by content.
        tag: Optional tag to filter memories.
        cwd: Absolute project path. Defaults to the caller's working directory.
    """
    memories = _mem().recall(
        cwd=cwd or None,
        query=query or None,
        tag=tag or None,
    )
    return [
        {
            "id": m.id,
            "project": m.project,
            "project_name": m.project_name,
            "content": m.content,
            "tags": m.tags,
            "timestamp": m.timestamp.isoformat(),
        }
        for m in memories
    ]


@mcp.tool()
def memory_forget(memory_id: str, cwd: str = "") -> dict[str, bool]:
    """Delete a memory by ID.

    Args:
        memory_id: The ID returned by memory_remember or memory_recall.
        cwd: Absolute project path. Defaults to the caller's working directory.
    """
    deleted = _mem().forget(memory_id, cwd=cwd or None)
    return {"deleted": deleted, "id": memory_id}


@mcp.tool()
def memory_projects() -> list[dict[str, Any]]:
    """List all projects that have stored memories."""
    return _mem().projects()


# ---------------------------------------------------------------------------
# Observability tools
# ---------------------------------------------------------------------------

@mcp.tool()
def monitor_snapshot() -> list[dict[str, Any]]:
    """Return the current token usage snapshot for all tracked agents.

    Reads the snapshot written by the daemon (started with `mem start`).
    Returns an empty list if the daemon is not running.
    """
    statuses = _snapshot_store().load()
    return [
        {
            "agent_name": s.agent_name,
            "input_tokens": s.input_tokens,
            "output_tokens": s.output_tokens,
            "total_tokens": s.total_tokens,
            "average_tokens_per_minute": s.average_tokens_per_minute,
            "last_updated": s.last_updated,
            "state": s.state,
            "source": s.source,
        }
        for s in statuses
    ]


@mcp.tool()
def monitor_status() -> dict[str, Any]:
    """Return the runtime status of the local background monitor process."""
    state = _registry().load_state()
    if not state:
        return {"running": False, "pid": None, "started_at": None, "last_updated": None}
    return {
        "running": state.running,
        "pid": state.pid,
        "started_at": state.started_at.isoformat() if state.started_at else None,
        "last_updated": state.last_updated.isoformat() if state.last_updated else None,
    }


# ---------------------------------------------------------------------------
# Lifecycle tools
# ---------------------------------------------------------------------------

@mcp.tool()
def monitor_start() -> dict[str, Any]:
    """Start the local background monitor process.

    Returns the new runtime state. Raises if a monitor is already running.
    """
    try:
        state = _registry().start()
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}
    return {
        "ok": True,
        "pid": state.pid,
        "started_at": state.started_at.isoformat() if state.started_at else None,
    }


@mcp.tool()
def monitor_stop() -> dict[str, Any]:
    """Stop the local background monitor process.

    Returns the final runtime state, or a message if no monitor was running.
    """
    state = _registry().stop()
    if state is None:
        return {"ok": False, "error": "No running monitor found."}
    return {
        "ok": True,
        "pid": state.pid,
        "started_at": state.started_at.isoformat() if state.started_at else None,
    }


def run() -> None:
    """Entry point: start the MCP server over stdio.

    Registers the process PID in the MCP state file so that `mem status`
    and `mem serve stop` can inspect and terminate it.
    """
    import os

    from ..config import get_mcp_state_path
    from ..storage.runtime_state import RuntimeState, RuntimeStateStore
    from ..utils.time import utc_now

    configure_logging()
    state_store = RuntimeStateStore(get_mcp_state_path())
    state = RuntimeState(
        running=True,
        pid=os.getpid(),
        started_at=utc_now(),
        last_updated=utc_now(),
    )
    try:
        state_store.save(state)
    except OSError:
        logger.exception(
            "mem MCP server could not write runtime state to %s; continuing without status tracking.",
            state_store.path,
        )
    try:
        logger.info("mem MCP server ready")
        mcp.run()
    finally:
        try:
            state_store.clear()
        except OSError:
            logger.debug("Could not clear MCP runtime state", exc_info=True)
