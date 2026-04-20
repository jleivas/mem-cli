from typer.testing import CliRunner

from mem import APP_VERSION
from mem.cli import app
from mem.cli import _run_menu
from mem.cli import _render_home_screen
from mem.cli import _render_footer
from rich.console import Console


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

    monkeypatch.setattr("mem.cli._registry", lambda: FakeRegistry())

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

    monkeypatch.setattr("mem.cli._registry", lambda: FakeRegistry())

    runner = CliRunner()
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "running" in result.output


def test_menu_quit_returns_cleanly(monkeypatch) -> None:
    monkeypatch.setattr("mem.cli.console.input", lambda prompt: "0")

    _run_menu()


def test_home_screen_renders_menu_entries() -> None:
    console = Console(record=True, width=120)
    console.print(_render_home_screen())
    output = console.export_text()

    assert "mem" in output
    assert "Start monitor" in output
    assert "Dashboard" in output


def test_footer_renders_hotkeys() -> None:
    console = Console(record=True, width=120)
    console.print(_render_footer())
    output = console.export_text()

    assert "Start" in output
    assert "Dashboard" in output
    assert "Quit" in output
