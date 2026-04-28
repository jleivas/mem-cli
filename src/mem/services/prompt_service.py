from __future__ import annotations

import importlib.resources
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..config import get_app_home
from ..services.memory_service import _resolve_project

# Matches:  mem remember "content" --tag foo
#           mem remember "content" -t foo
#           mem remember "content"
REMEMBER_RE = re.compile(
    r'\bmem\s+remember\s+"([^"]+)"'
    r'(?:\s+(?:--tag|-t)\s+(\S+))?'
)

BUILTIN_PROMPT = "project_memory.md"
USER_PROMPT_FILENAME = "project-memory.md"

# Base command for each agent. Prompt is appended as the last positional arg
# for agents that accept it that way (see _AGENT_USES_STDIN below).
AGENT_COMMANDS: dict[str, list[str]] = {
    # --disallowedTools blocks write operations so no permission prompt leaks
    # into the captured stdout. The prompt is delivered via stdin (see below)
    # to avoid argument-parsing conflicts with variadic --tools / --disallowedTools.
    "claude": ["claude", "-p", "--output-format", "text", "--disallowedTools", "Write,Edit,MultiEdit,Bash"],
    "codex": ["codex", "exec"],
}

# Agents that read the prompt from stdin instead of a positional argument.
# claude -p accepts stdin when no positional prompt is given, and using stdin
# avoids the variadic-flag parsing bug where --disallowedTools <tools...>
# consumes the prompt string as an extra tool name.
_AGENT_USES_STDIN: frozenset[str] = frozenset({"claude"})

AGENT_INSTALL_HINTS: dict[str, str] = {
    "claude": "npm install -g @anthropic-ai/claude-code",
    "codex": "npm install -g @openai/codex",
}


def detect_available_agents() -> list[str]:
    """Return the names of agents whose CLI is present in PATH."""
    return [name for name in AGENT_COMMANDS if shutil.which(name) is not None]


def _user_prompt_path() -> Path:
    return get_app_home() / "prompts" / USER_PROMPT_FILENAME


def _load_template() -> str:
    """Load prompt template — user override takes precedence over built-in."""
    user_path = _user_prompt_path()
    if user_path.exists():
        return user_path.read_text(encoding="utf-8")

    ref = importlib.resources.files("mem.prompts").joinpath(BUILTIN_PROMPT)
    return ref.read_text(encoding="utf-8")


def build_prompt(cwd: str | None = None) -> str:
    """Return the filled prompt for the resolved project."""
    project = _resolve_project(cwd)
    project_name = Path(project).name or project
    template = _load_template()
    return template.replace("{cwd}", project).replace("{project_name}", project_name)


class AgentResult:
    """Outcome of a streamed agent run."""

    def __init__(self, exit_code: int, stderr: str) -> None:
        self.exit_code = exit_code
        self.stderr = stderr.strip()

    @property
    def ok(self) -> bool:
        return self.exit_code == 0

    @property
    def partial(self) -> bool:
        """True when the agent produced some output but exited with an error."""
        return not self.ok and self.exit_code not in (127, 1)


@dataclass(slots=True)
class AgentTextResult:
    stdout: str
    result: AgentResult


def parse_remember(line: str) -> tuple[str, str] | None:
    """
    If *line* contains a mem remember command, return (content, tag).
    Tag is an empty string when absent.
    Returns None if the line is not a remember command.
    """
    match = REMEMBER_RE.search(line)
    if match:
        return match.group(1), match.group(2) or ""
    return None


def run_agent(
    prompt: str,
    agent: str,
    on_line: Callable[[str], None] | None = None,
) -> AgentResult:
    """
    Run *agent* with *prompt*, streaming stdout line-by-line.

    *on_line* is called for every non-empty stdout line so the caller can
    render progress. Stderr is captured and returned in the result.
    """
    import threading

    cmd = AGENT_COMMANDS.get(agent)
    if cmd is None:
        return AgentResult(exit_code=1, stderr=f"Unknown agent: {agent!r}.")

    use_stdin = agent in _AGENT_USES_STDIN
    full_cmd = cmd if use_stdin else cmd + [prompt]

    try:
        proc = subprocess.Popen(
            full_cmd,
            stdin=subprocess.PIPE if use_stdin else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        return AgentResult(
            exit_code=127,
            stderr=f"Agent '{agent}' not found in PATH. Make sure it is installed.",
        )

    if use_stdin:
        assert proc.stdin is not None
        proc.stdin.write(prompt)
        proc.stdin.close()

    stderr_lines: list[str] = []

    def _drain_stderr() -> None:
        assert proc.stderr is not None
        for line in proc.stderr:
            stderr_lines.append(line)

    stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
    stderr_thread.start()

    assert proc.stdout is not None
    for raw in proc.stdout:
        line = raw.rstrip()
        if line and on_line is not None:
            on_line(line)

    proc.wait()
    stderr_thread.join(timeout=5.0)

    return AgentResult(exit_code=proc.returncode, stderr="".join(stderr_lines))


def run_agent_text(prompt: str, agent: str) -> AgentTextResult:
    """Run *agent* with *prompt* and capture the full stdout text."""
    cmd = AGENT_COMMANDS.get(agent)
    if cmd is None:
        return AgentTextResult(
            stdout="",
            result=AgentResult(exit_code=1, stderr=f"Unknown agent: {agent!r}."),
        )

    use_stdin = agent in _AGENT_USES_STDIN
    full_cmd = cmd if use_stdin else cmd + [prompt]

    try:
        completed = subprocess.run(
            full_cmd,
            input=prompt if use_stdin else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except FileNotFoundError:
        return AgentTextResult(
            stdout="",
            result=AgentResult(
                exit_code=127,
                stderr=f"Agent '{agent}' not found in PATH. Make sure it is installed.",
            ),
        )

    return AgentTextResult(
        stdout=completed.stdout,
        result=AgentResult(exit_code=completed.returncode, stderr=completed.stderr),
    )
