from pathlib import Path

from typer.testing import CliRunner

from mem import APP_NAME
from mem import APP_VERSION
from mem.cli import app
from mem.cli import _run_menu
from mem.cli import _render_home_screen
from mem.cli import _render_footer
from mem.cli import _render_submenu_screen
from mem.cli import MENU_MONITORING
from mem.cli import MENU_MEMORY
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


def test_serve_help_lists_launch_options() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["serve", "--help"])
    assert result.exit_code == 0
    assert "--background" in result.output
    assert "--new-terminal" in result.output
    assert "--autostart" in result.output


def test_serve_autostart_option_invokes_installer(monkeypatch) -> None:
    called = {"install": False}

    def fake_install_launch_agent():
        called["install"] = True
        return "/tmp/com.mem.cli.mcp.plist"

    monkeypatch.setattr("mem.cli.install_launch_agent", fake_install_launch_agent)

    runner = CliRunner()
    result = runner.invoke(app, ["serve", "--autostart"])

    assert result.exit_code == 0
    assert called["install"] is True
    assert "MCP autostart enabled" in result.output


def test_serve_disable_autostart_option_invokes_remover(monkeypatch) -> None:
    called = {"remove": False}

    def fake_remove_launch_agent():
        called["remove"] = True
        return True

    monkeypatch.setattr("mem.cli.remove_launch_agent", fake_remove_launch_agent)

    runner = CliRunner()
    result = runner.invoke(app, ["serve", "--disable-autostart"])

    assert result.exit_code == 0
    assert called["remove"] is True
    assert "MCP autostart disabled" in result.output


def test_serve_background_option_invokes_detached_launcher(monkeypatch) -> None:
    called = {"start": False}

    def fake_start_hidden_mcp_server(program=None, platform_name=None, stderr_log_path=None):
        called["start"] = True
        class FakeProcess:
            def poll(self):
                return None
        return FakeProcess()

    monkeypatch.setattr("mem.cli.start_hidden_mcp_server", fake_start_hidden_mcp_server)
    monkeypatch.setattr("mem.cli._mcp_serve_log_path", lambda: Path("/tmp/mem-serve.stderr.log"))
    monkeypatch.setattr("mem.cli._wait_for_mcp_server_running", lambda timeout=10.0, interval=0.2: True)

    runner = CliRunner()
    result = runner.invoke(app, ["serve", "--background"])

    assert result.exit_code == 0
    assert called["start"] is True
    assert "MCP server started in background" in result.output


def test_serve_new_terminal_option_invokes_terminal_launcher(monkeypatch) -> None:
    called = {"start": False}

    def fake_start_new_terminal(program=None, platform_name=None):
        called["start"] = True
        return object()

    monkeypatch.setattr("mem.cli.start_new_terminal", fake_start_new_terminal)
    monkeypatch.setattr("mem.cli._wait_for_mcp_server_running", lambda timeout=10.0, interval=0.2: True)

    runner = CliRunner()
    result = runner.invoke(app, ["serve", "--new-terminal"])

    assert result.exit_code == 0
    assert called["start"] is True
    assert "MCP server opened in a new terminal" in result.output


def test_serve_rejects_conflicting_modes() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["serve", "--background", "--new-terminal"])

    assert result.exit_code != 0
    assert "serve --help" in result.output


def test_serve_refuses_to_start_when_mcp_is_already_running(monkeypatch) -> None:
    class FakeState:
        running = True

    monkeypatch.setattr("mem.cli._mcp_registry", lambda: type("R", (), {"load_state": lambda self: FakeState()})())

    runner = CliRunner()
    result = runner.invoke(app, ["serve"])

    assert result.exit_code != 0
    assert "already running" in result.output


def test_setup_command_invokes_installer(monkeypatch) -> None:
    called = {"install": False}

    def fake_install_launch_agent():
        called["install"] = True
        return "/tmp/com.mem.cli.mcp.plist"

    monkeypatch.setattr("mem.cli.install_launch_agent", fake_install_launch_agent)

    runner = CliRunner()
    result = runner.invoke(app, ["setup"])

    assert result.exit_code == 0
    assert called["install"] is True
    assert "MCP setup complete" in result.output


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
    monkeypatch.setattr("mem.cli._mcp_registry", lambda: FakeRegistry())

    runner = CliRunner()
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "Runtime Status" in result.output
    assert "Monitor" in result.output


def test_status_shows_running_mcp_server(monkeypatch) -> None:
    class FakeState:
        running = True
        pid = 4242
        started_at = None
        last_updated = None

    class FakeRegistry:
        def load_state(self):
            return FakeState()

    monkeypatch.setattr("mem.cli._registry", lambda: FakeRegistry())
    monkeypatch.setattr("mem.cli._mcp_registry", lambda: FakeRegistry())

    runner = CliRunner()
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0


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


def test_submenu_renders_horizontal_cards() -> None:
    console = Console(record=True, width=120)
    console.print(_render_submenu_screen("Monitoring", "#E93A7D", MENU_MONITORING, []))
    console.print(_render_submenu_screen("Memory", "#F98C2B", MENU_MEMORY, []))
    output = console.export_text()

    assert "Monitoring" in output
    assert "Launch the monitor" in output
    assert "Memory" in output
    assert "Generate project" in output
    assert "Start the MCP" in output


def test_init_runs_config_before_agent_work(monkeypatch, tmp_path) -> None:
    calls: list[str] = []

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
    assert calls[0] == "agent:claude"
    assert calls[1] == "remember:remembered fact"


def test_config_command_handles_agent_files(monkeypatch, tmp_path) -> None:
    calls: list[str] = []

    def fake_detect_available_agents():
        return ["claude"]

    def fake_config_mode():
        return "mcp-only"

    def fake_write_text(path, content):
        calls.append(f"write:{path.name}")
        return True

    def fake_is_claude_synced_to_agents(claude_path, agents_path):
        return False

    monkeypatch.setattr("mem.cli.detect_available_agents", fake_detect_available_agents)
    monkeypatch.setattr("mem.cli._select_config_mode", fake_config_mode)
    monkeypatch.setattr("mem.cli._write_text", fake_write_text)
    monkeypatch.setattr("mem.cli._is_claude_synced_to_agents", fake_is_claude_synced_to_agents)
    monkeypatch.setattr("mem.cli._sync_claude_symlink", lambda claude_path, agents_path: calls.append("sync"))

    runner = CliRunner()
    result = runner.invoke(app, ["config", "--agent", "claude", "--cwd", str(tmp_path)])

    assert result.exit_code == 0
    assert any(call.startswith("write:") for call in calls)
