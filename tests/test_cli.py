from typer.testing import CliRunner

from mem import APP_NAME
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
    assert APP_NAME in result.output
    assert APP_VERSION in result.output


def test_root_version_option() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert APP_NAME in result.output
    assert APP_VERSION in result.output


def test_help_lists_version_command() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "version" in result.output
    assert "Print the installed mem-cli version and exit." in result.output


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
    assert "Monitoring" in output
    assert "Memory" in output


def test_footer_renders_hotkeys() -> None:
    console = Console(record=True, width=120)
    console.print(_render_footer())
    output = console.export_text()

    assert "Monitoring" in output
    assert "Memory" in output
    assert "Quit" in output


def test_init_runs_config_before_agent_work(monkeypatch, tmp_path) -> None:
    calls: list[str] = []

    def fake_config(agent: str, cwd: str = "") -> None:
        calls.append(f"config:{agent}:{cwd}")

    def fake_run_agent(prompt: str, agent: str, on_line=None):
        calls.append(f"agent:{agent}")
        if on_line is not None:
            on_line('mem remember "remembered fact" --tag conventions')
        class Result:
            ok = True
            partial = False
            stderr = ""
            exit_code = 0
        return Result()

    class FakeMemoryService:
        def recall(self, cwd=None, query=None, tag=None):
            return []

        def remember(self, content, cwd=None, tags=None):
            calls.append(f"remember:{content}")
            return None

    monkeypatch.setattr("mem.cli.config", fake_config)
    monkeypatch.setattr("mem.cli.run_agent", fake_run_agent)
    monkeypatch.setattr("mem.services.memory_service.MemoryService", lambda: FakeMemoryService())
    monkeypatch.setattr("mem.cli.detect_available_agents", lambda: ["claude"])

    class DummyLive:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def update(self, *args, **kwargs):
            return None

    monkeypatch.setattr("rich.live.Live", DummyLive)

    from mem.cli import init as run_init

    run_init(agent="claude", cwd=str(tmp_path))
    assert calls[0].startswith("config:claude:")
    assert calls[1] == "agent:claude"
    assert calls[2] == "remember:remembered fact"
