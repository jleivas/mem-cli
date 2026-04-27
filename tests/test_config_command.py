from __future__ import annotations

from typer.testing import CliRunner

from mem.cli import app
from mem.services.prompt_service import AgentResult
from mem.services.prompt_service import AgentTextResult


def test_config_command_writes_synced_pair(monkeypatch, tmp_path) -> None:
    prompts: list[str] = []

    def fake_run_agent_text(prompt: str, agent: str) -> AgentTextResult:
        prompts.append(prompt)
        return AgentTextResult(
            stdout=(
                "# AGENTS.md\n\n"
                "Shared guidance.\n\n"
                "## Claude\n"
                "Claude-specific guidance.\n\n"
                "## Codex\n"
                "Codex-specific guidance.\n"
            ),
            result=AgentResult(exit_code=0, stderr=""),
        )

    monkeypatch.setattr("mem.cli.detect_available_agents", lambda: ["claude"])
    monkeypatch.setattr("mem.cli.run_agent_text", fake_run_agent_text)

    runner = CliRunner()
    result = runner.invoke(app, ["config", "--cwd", str(tmp_path)], input="1\n")

    assert result.exit_code == 0

    agents_path = tmp_path / "AGENTS.md"
    claude_path = tmp_path / "CLAUDE.md"

    assert agents_path.exists()
    assert claude_path.is_symlink()
    assert claude_path.resolve() == agents_path.resolve()

    agents_text = agents_path.read_text(encoding="utf-8")
    claude_text = claude_path.read_text(encoding="utf-8")

    assert "Shared guidance." in agents_text
    assert claude_text == agents_text
    assert "AGENTS.md" in prompts[0]
    assert "CLAUDE.md is a symlink to AGENTS.md" in prompts[0]
    assert "Do not create any extra markdown files." in prompts[0]
    assert "Only touch AGENTS.md and CLAUDE.md." in prompts[0]
    assert "memory_recall" in prompts[0]
    assert "backend service" in prompts[0]
    assert "frontend app" in prompts[0]
    assert "repository of files/directories" in prompts[0]


def test_config_command_prompts_before_overwriting_synced_pair(monkeypatch, tmp_path) -> None:
    agents_path = tmp_path / "AGENTS.md"
    agents_path.write_text("Existing AGENTS content.\n", encoding="utf-8")
    claude_path = tmp_path / "CLAUDE.md"
    claude_path.symlink_to(agents_path.name)

    called = False

    def fake_run_agent_text(prompt: str, agent: str) -> AgentTextResult:
        nonlocal called
        called = True
        return AgentTextResult(
            stdout="# AGENTS.md\n",
            result=AgentResult(exit_code=0, stderr=""),
        )

    monkeypatch.setattr("mem.cli.detect_available_agents", lambda: ["claude"])
    monkeypatch.setattr("mem.cli.run_agent_text", fake_run_agent_text)

    runner = CliRunner()
    result = runner.invoke(app, ["config", "--cwd", str(tmp_path)], input="1\nn\n")

    assert result.exit_code == 0
    assert "The project already seems to have been configured." in result.output
    assert "Do you want to continue anyway?" in result.output
    assert called is False


def test_config_command_adds_only_mcp_instructions(monkeypatch, tmp_path) -> None:
    agents_path = tmp_path / "AGENTS.md"
    agents_path.write_text(
        "# Project\n\nExisting guidance.\n",
        encoding="utf-8",
    )
    claude_path = tmp_path / "CLAUDE.md"
    claude_path.symlink_to(agents_path.name)

    called = False

    def fake_run_agent_text(prompt: str, agent: str) -> AgentTextResult:
        nonlocal called
        called = True
        return AgentTextResult(
            stdout="# AGENTS.md\n",
            result=AgentResult(exit_code=0, stderr=""),
        )

    monkeypatch.setattr("mem.cli.detect_available_agents", lambda: ["claude"])
    monkeypatch.setattr("mem.cli.run_agent_text", fake_run_agent_text)

    runner = CliRunner()
    result = runner.invoke(app, ["config", "--cwd", str(tmp_path)], input="2\n")

    assert result.exit_code == 0
    assert "configure a new AGENTS.md" in result.output
    assert "only add mem MCP instructions" in result.output
    assert called is False

    agents_text = agents_path.read_text(encoding="utf-8")
    assert "Existing guidance." in agents_text
    assert "## MCP Usage for mem" in agents_text
    assert "memory_recall" in agents_text
    assert claude_path.is_symlink()
    assert claude_path.resolve() == agents_path.resolve()
