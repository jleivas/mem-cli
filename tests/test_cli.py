from typer.testing import CliRunner

from agent_recall import APP_VERSION
from agent_recall.cli import app


def test_version_command() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert APP_VERSION in result.output


def test_start_and_stop_commands(monkeypatch) -> None:
    class FakeState:
        pid = 123
        running = True
        started_at = None
        last_updated = None

    class FakeRegistry:
        def start(self):
            return FakeState()

        def stop(self):
            return FakeState()

        def load_state(self):
            return None

    monkeypatch.setattr("agent_recall.cli._registry", lambda: FakeRegistry())

    runner = CliRunner()
    start_result = runner.invoke(app, ["start"])
    stop_result = runner.invoke(app, ["stop"])

    assert start_result.exit_code == 0
    assert stop_result.exit_code == 0


def test_status_command(monkeypatch) -> None:
    class FakeState:
        running = True
        pid = 999
        started_at = None
        last_updated = type("DT", (), {"isoformat": lambda self: "2026-04-15T00:00:00+00:00"})()

    class FakeRegistry:
        def load_state(self):
            return FakeState()

    monkeypatch.setattr("agent_recall.cli._registry", lambda: FakeRegistry())

    runner = CliRunner()
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "running" in result.output
