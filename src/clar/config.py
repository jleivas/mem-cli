from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "mem-cli"
APP_VERSION = "0.1.0"
HOME_ENV_VAR = "MEM_HOME"
LEGACY_HOME_ENV_VAR = "CLAR_HOME"
CODEX_JSONL_ENV_VAR = "MEM_CODEX_JSONL"
LEGACY_CODEX_JSONL_ENV_VAR = "CLAR_CODEX_JSONL"
CLAUDE_JSONL_ENV_VAR = "MEM_CLAUDE_JSONL"
LEGACY_CLAUDE_JSONL_ENV_VAR = "CLAR_CLAUDE_JSONL"
JSONL_PATHS_ENV_VAR = "MEM_JSONL_PATHS"
LEGACY_JSONL_PATHS_ENV_VAR = "CLAR_JSONL_PATHS"


def get_app_home() -> Path:
    custom_home = os.environ.get(HOME_ENV_VAR) or os.environ.get(LEGACY_HOME_ENV_VAR)
    if custom_home:
        return Path(custom_home).expanduser()
    return Path.home() / ".mem-cli"


def ensure_app_home() -> Path:
    app_home = get_app_home()
    app_home.mkdir(parents=True, exist_ok=True)
    return app_home


def get_history_dir() -> Path:
    return get_app_home() / "history"


def ensure_history_dir() -> Path:
    history_dir = get_history_dir()
    history_dir.mkdir(parents=True, exist_ok=True)
    return history_dir


def get_runtime_dir() -> Path:
    return get_app_home() / "runtime"


def get_runtime_state_path() -> Path:
    return get_runtime_dir() / "state.json"


def get_codex_jsonl_path() -> Path | None:
    value = os.environ.get(CODEX_JSONL_ENV_VAR) or os.environ.get(LEGACY_CODEX_JSONL_ENV_VAR)
    return Path(value).expanduser() if value else None


def get_claude_jsonl_path() -> Path | None:
    value = os.environ.get(CLAUDE_JSONL_ENV_VAR) or os.environ.get(LEGACY_CLAUDE_JSONL_ENV_VAR)
    return Path(value).expanduser() if value else None


def get_jsonl_paths() -> str | None:
    return os.environ.get(JSONL_PATHS_ENV_VAR) or os.environ.get(LEGACY_JSONL_PATHS_ENV_VAR)


def get_default_codex_jsonl_path() -> Path:
    return ensure_app_home() / "codex.jsonl"


def get_default_claude_jsonl_path() -> Path:
    return ensure_app_home() / "claude.jsonl"


def iter_configured_jsonl_paths() -> list[Path]:
    paths: list[Path] = []

    codex_path = get_codex_jsonl_path()
    if codex_path is not None:
        paths.append(codex_path)

    claude_path = get_claude_jsonl_path()
    if claude_path is not None:
        paths.append(claude_path)

    extra_paths = get_jsonl_paths()
    if extra_paths:
        for raw_path in extra_paths.split(","):
            cleaned = raw_path.strip()
            if cleaned:
                paths.append(Path(cleaned).expanduser())

    return paths


def get_codex_watcher_state_path() -> Path:
    return get_runtime_dir() / "codex-processed.json"


def clear_configured_jsonl_files() -> None:
    for path in iter_configured_jsonl_paths():
        if path.exists():
            path.write_text("", encoding="utf-8")

    watcher_state = get_codex_watcher_state_path()
    if watcher_state.exists():
        watcher_state.unlink()
