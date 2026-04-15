from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "agent-recall"
APP_VERSION = "0.1.0"
HOME_ENV_VAR = "AGENT_RECALL_HOME"
CODEX_JSONL_ENV_VAR = "AGENT_RECALL_CODEX_JSONL"
CLAUDE_JSONL_ENV_VAR = "AGENT_RECALL_CLAUDE_JSONL"
JSONL_PATHS_ENV_VAR = "AGENT_RECALL_JSONL_PATHS"
USE_SIMULATED_ENV_VAR = "AGENT_RECALL_USE_SIMULATED"


def get_app_home() -> Path:
    custom_home = os.environ.get(HOME_ENV_VAR)
    if custom_home:
        return Path(custom_home).expanduser()
    return Path.home() / ".agent-recall"


def get_runtime_dir() -> Path:
    return get_app_home() / "runtime"


def get_runtime_state_path() -> Path:
    return get_runtime_dir() / "state.json"


def get_codex_jsonl_path() -> Path | None:
    value = os.environ.get(CODEX_JSONL_ENV_VAR)
    return Path(value).expanduser() if value else None


def get_claude_jsonl_path() -> Path | None:
    value = os.environ.get(CLAUDE_JSONL_ENV_VAR)
    return Path(value).expanduser() if value else None


def get_jsonl_paths() -> str | None:
    return os.environ.get(JSONL_PATHS_ENV_VAR)


def use_simulated_source() -> bool:
    value = os.environ.get(USE_SIMULATED_ENV_VAR, "1").strip().lower()
    return value not in {"0", "false", "no", "off"}
