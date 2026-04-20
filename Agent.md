# Agent Instructions

This repository is `mem-cli` — a local CLI for token observability and agent memory.

## Working Rules

- Prefer small, focused changes.
- Keep the CLI, services, adapters, UI, storage, models, and utilities separated.
- Preserve existing behavior unless the task explicitly changes it.
- Add or update tests when behavior changes.
- Use `apply_patch` for file edits.
- Do not revert user changes outside the current task.

## Project Facts

- Python 3.11+
- CLI entrypoint: `mem`
- Main package: `src/mem`
- Tests: `tests/`

## Token Tracking Notes

- The JSONL adapter normalizes Codex and Claude outputs into `TokenEvent`.
- Prefer parsing nested usage fields instead of assuming a fixed schema.
- Keep the parser tolerant of JSONL, JSON arrays, and pretty-printed JSON documents.

## Verification

- Run targeted tests for the files you change.
- If the local virtualenv is broken, report that clearly rather than guessing.
