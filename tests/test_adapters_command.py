from __future__ import annotations

from typer.testing import CliRunner

from mem.cli import app


def test_adapters_command_lists_builtin_adapters(monkeypatch) -> None:
    monkeypatch.setattr(
        "mem.cli.discover_token_source_plugins",
        lambda: [],
    )

    runner = CliRunner()
    result = runner.invoke(app, ["adapters"])

    assert result.exit_code == 0
    assert "jsonl" in result.output
    assert "simulated" in result.output
    assert "No external token source plugins discovered" in result.output
