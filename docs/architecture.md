# Architecture

`mem-cli` is designed as a small local runtime that can grow into a project-aware memory and observability layer.

## Modular Layout

- `cli/` exposes the user-facing commands
- `services/` contains orchestration logic and token tracking behavior
- `services/adapters/` contains pluggable token sources, such as local JSONL readers
- `ui/` contains terminal rendering and live dashboard code
- `storage/` handles local JSON state and future persistence concerns
- `models/` defines data structures shared across the application
- `utils/` holds reusable helpers such as timestamps and logging

## Why This Split Exists

The MVP should stay easy to understand, test, and replace.

- CLI code stays thin and focused on user actions
- service code owns behavior and orchestration
- adapter code isolates data ingestion from any particular agent or file format
- JSONL ingestion is intentionally generic so Codex and Claude CLI outputs can both be normalized into the same token event model
- UI code only renders state
- storage code isolates local filesystem details
- models keep data contracts stable as adapters are added later

This makes it possible to add future adapters without rewriting the whole tool.

## Evolution Path

The current codebase is intentionally structured for these later stages:

1. token tracking from real agent hooks or logs
2. project-scoped memory read/write
3. local MCP server
4. multiple adapters for different agents
5. local file and stream adapters for different agent runtimes

## Near-Term Design Constraints

The MVP avoids premature complexity:

- no database
- no semantic search
- no embeddings
- no remote services
- no full MCP implementation yet

The first release should prove the local runtime and dashboard experience before adding durable memory or integrations.
