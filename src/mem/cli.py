from __future__ import annotations

from dataclasses import dataclass
import os
import shutil
from pathlib import Path
from typing import cast

import typer
from rich.align import Align
from rich.box import ROUNDED
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from . import APP_NAME, APP_VERSION
from .config import get_default_claude_jsonl_path
from .config import get_default_codex_jsonl_path
from .config import get_mcp_state_path
from .config import get_runtime_dir
from .config import get_runtime_state_path
from .app import build_monitor_service
from .models.memory import Memory
from .services.adapters import discover_token_source_plugins
from .services.macos_launchd import is_supported_platform
from .services.macos_launchd import install_launch_agent
from .services.macos_launchd import launch_agent_installed
from .services.macos_launchd import launch_agent_path
from .services.macos_launchd import remove_launch_agent
from .services.autostart import start_hidden_mcp_server
from .services.autostart import start_new_terminal
from .services.memory_service import MemoryService
from .services.prompt_service import (
    AgentResult,
    AgentTextResult,
    build_prompt,
    run_agent,
    run_agent_text,
    parse_remember,
    detect_available_agents,
    AGENT_COMMANDS,
    AGENT_INSTALL_HINTS,
)
from .services.process_registry import ProcessRegistry
from .storage.runtime_state import RuntimeStateStore
from .ui.dashboard import live_dashboard
from .ui.dashboard import DashboardViewMode

app = typer.Typer(
    add_completion=False,
    rich_markup_mode="rich",
    help="[bold #E93A7D]Mem CLI[/] for AI agents — [dim]local token observability & memory.[/dim]",
)
serve_app = typer.Typer(
    add_completion=False,
    rich_markup_mode="rich",
    help="[bold #E93A7D]Start[/] the local [bold #F98C2B]MCP server[/] over stdio.",
)
console = Console()
CLI_NAME = "mem"
ACCENT_PINK = "#E93A7D"
ACCENT_CORAL = "#F25C5C"
ACCENT_ORANGE = "#F98C2B"
ACCENT_YELLOW = "#F7B500"
# Main menu — two category cards + quit
MENU_MAIN = (
    ("1", "Monitoring", "Start · Stop · Dashboard · Status", ACCENT_PINK),
    ("2", "Memory",     "Init · Config · MCP server",        ACCENT_ORANGE),
    ("0", "Quit",       "",                                   ACCENT_YELLOW),
)
# Monitoring submenu
MENU_MONITORING = (
    ("1", "Start",     "Launch the monitor",      ACCENT_PINK),
    ("2", "Stop",      "Stop the monitor",        ACCENT_CORAL),
    ("3", "Dashboard", "Open the live dashboard", ACCENT_ORANGE),
    ("4", "Status",    "Inspect runtime state",   ACCENT_YELLOW),
    ("0", "Back",      "",                        "dim white"),
)
# Memory submenu
MENU_MEMORY = (
    ("1", "Init",      "Generate project memory", ACCENT_PINK),
    ("2", "Config",    "Prepare project config",  ACCENT_CORAL),
    ("3", "Start MCP", "Start the MCP server",    ACCENT_ORANGE),
    ("4", "Stop MCP",  "Stop the MCP server",     ACCENT_CORAL),
    ("0", "Back",      "",                        "dim white"),
)

# Footer shortcut bars
_FOOTER_MAIN = [
    ("1", " Monitoring  ", ACCENT_PINK),
    ("2", " Memory  ",     ACCENT_ORANGE),
    ("0", " Quit",         ACCENT_YELLOW),
]
_FOOTER_MONITORING = [
    ("1", " Start  ",     ACCENT_PINK),
    ("2", " Stop  ",      ACCENT_CORAL),
    ("3", " Dashboard  ", ACCENT_ORANGE),
    ("4", " Status  ",    ACCENT_YELLOW),
    ("0", " Back",        "dim white"),
]
_FOOTER_MEMORY = [
    ("1", " Init  ",      ACCENT_PINK),
    ("2", " Config  ",    ACCENT_CORAL),
    ("3", " Start MCP  ", ACCENT_ORANGE),
    ("4", " Stop MCP  ",  ACCENT_CORAL),
    ("0", " Back",        "dim white"),
]

app.add_typer(serve_app, name="serve", rich_help_panel=f"[bold {ACCENT_ORANGE}]Memory[/]")


@dataclass(slots=True)
class _ActionResult:
    title: str
    body: Panel | Table
    border_style: str


def _bootstrap_env() -> None:
    os.environ.setdefault("MEM_CLAUDE_JSONL", str(get_default_claude_jsonl_path()))
    os.environ.setdefault("MEM_CODEX_JSONL", str(get_default_codex_jsonl_path()))


@app.callback(invoke_without_command=True)
def _bootstrap(
    version: bool = typer.Option(
        False,
        "--version",
        help="Print the installed mem-cli version and exit.",
        is_eager=True,
    ),
) -> None:
    _bootstrap_env()
    if version:
        console.print(_render_version_panel())
        raise typer.Exit()


def _registry() -> ProcessRegistry:
    return ProcessRegistry(RuntimeStateStore(get_runtime_state_path()))


def _mcp_server_is_running() -> bool:
    state = _mcp_registry().load_state()
    return bool(state and state.running)


def _wait_for_mcp_server_running(timeout: float = 10.0, interval: float = 0.2) -> bool:
    import time

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _mcp_server_is_running():
            return True
        time.sleep(interval)
    return False


def _mcp_serve_log_path() -> Path:
    return get_runtime_dir() / "mcp-serve.stderr.log"


def _tail_text(path: Path, max_lines: int = 20) -> str:
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    tail = lines[-max_lines:]
    return "\n".join(tail).strip()


_LOGO_LINES = [
    "                  ░▓▓▓▒░                                        ",
    "                ░▓▓▓▒▒▓▓░        ▒▒▒▒░                          ",
    "              ░▒▓▓░   ░▓▓░     ░▒▒▒▒▒▒▒░                        ",
    "             ░▓▓▓░     ▓▓▒    ▒▓▓░   ░▒▒░                       ",
    "          ░▒▓▓▓▒       ░▓▓   ░▓▓░     ░▒▒▒░░                    ",
    "  ▓▓▓▓▓▓▓▓▓▓▒░         ░▓▓▒ ░▓▓░        ░░▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒░  ",
    "                         ░▓▓▓▓▓░                                ",
    "                           ░░░                                  ",
]
# Positional gradient: Pink → Coral → Orange → Yellow (left to right)
_LOGO_COLORS: list[tuple[int, str]] = [
    (22, "#E93A7D"),   # Pink
    (40, "#F25C5C"),   # Coral
    (53, "#F98C2B"),   # Orange
    (999, "#F7B500"),  # Yellow
]


def _build_logo() -> Text:
    t = Text(no_wrap=True)
    for i, line in enumerate(_LOGO_LINES):
        for col, ch in enumerate(line):
            if ch in ("▓", "▒", "░"):
                color = next(c for limit, c in _LOGO_COLORS if col <= limit)
                t.append(ch, style=f"bold {color}")
            else:
                t.append(ch)
        if i < len(_LOGO_LINES) - 1:
            t.append("\n")
    return t


def _build_brand_line() -> Text:
    t = Text()
    t.append("m", style=f"bold {ACCENT_PINK}")
    t.append("e", style=f"bold {ACCENT_CORAL}")
    t.append("m", style=f"bold {ACCENT_ORANGE}")
    t.append(f"  v{APP_VERSION}", style=f"bold {ACCENT_YELLOW}")
    t.append("  ·  ", style="dim")
    t.append("Token observability & agent memory", style="dim white")
    return t


def _menu_cell(key: str, title: str, accent: str) -> Panel:
    is_back_or_quit = key == "0"
    title_style = f"bold {accent}" if not is_back_or_quit else "dim white"
    border = accent if not is_back_or_quit else "dim"
    label = Text()
    label.append(f" {key} ", style=f"reverse bold {accent}")
    label.append(f" {title}", style=title_style)
    return Panel(Align.center(label), box=ROUNDED, border_style=border, padding=(0, 0))


def _menu_card(key: str, title: str, subtitle: str, accent: str) -> Panel:
    is_quit = key == "0"
    title_style = f"bold {accent}" if not is_quit else "dim white"
    border = accent if not is_quit else "dim"
    label = Text(justify="center")
    label.append(f" {key} ", style=f"reverse bold {accent}")
    label.append(f"  {title}", style=title_style)
    if subtitle:
        label.append(f"\n{subtitle}", style="dim")
    return Panel(Align.center(label), box=ROUNDED, border_style=border, padding=(0, 2))


def _build_main_menu() -> Table:
    inner = Table.grid(padding=(0, 1))
    for _ in MENU_MAIN:
        inner.add_column(ratio=1)
    inner.add_row(*[_menu_card(k, t, s, a) for k, t, s, a in MENU_MAIN])
    return inner


def _build_submenu_options(items: tuple) -> Table:
    inner = Table.grid(padding=(0, 1))
    for _ in items:
        inner.add_column(ratio=1)
    inner.add_row(*[_menu_card(k, t, s, a) for k, t, s, a in items])
    return inner



def _render_footer(pairs: list | None = None) -> Panel:
    if pairs is None:
        pairs = _FOOTER_MAIN
    line = Text()
    for key, label, accent in pairs:
        line.append(key, style=f"bold {accent}")
        line.append(label, style="dim")
    return Panel(
        Align.center(line),
        box=ROUNDED,
        border_style=ACCENT_YELLOW,
        padding=(0, 1),
    )


def _render_prompt_line() -> Text:
    t = Text()
    t.append(" > ", style=f"bold {ACCENT_YELLOW}")
    return t


def _render_home_screen() -> Group:
    return Group(
        Text(""),
        Panel(
            Group(
                Align.center(_build_logo()),
                Text(""),
                Align.center(_build_brand_line()),
            ),
            box=ROUNDED,
            border_style=ACCENT_PINK,
            padding=(0, 1),
        ),
        Text(""),
        Panel(
            _build_main_menu(),
            box=ROUNDED,
            border_style=ACCENT_ORANGE,
            padding=(0, 1),
            title=Text("Main menu", style=f"dim {ACCENT_ORANGE}"),
        ),
        Text(""),
        _render_footer(_FOOTER_MAIN),
        Text(""),
        _render_prompt_line(),
    )


def _render_submenu_screen(title: str, accent: str, items: tuple, footer_pairs: list) -> Group:
    header_text = Text.assemble(
        ("mem", f"bold {ACCENT_PINK}"),
        ("  ·  ", "dim"),
        (title, f"bold {accent}"),
    )
    return Group(
        Text(""),
        Panel(
            header_text,
            box=ROUNDED,
            border_style=accent,
            padding=(0, 1),
        ),
        Text(""),
        Panel(
            _build_submenu_options(items),
            box=ROUNDED,
            border_style=accent,
            padding=(0, 1),
            title=Text(title, style=f"dim {accent}"),
        ),
        Text(""),
        _render_footer(footer_pairs),
        Text(""),
        _render_prompt_line(),
    )


def _render_home_layout() -> Group:
    return _render_home_screen()


def _render_action_screen(result: _ActionResult) -> Panel:
    title = Text(result.title, style=f"bold {ACCENT_PINK}")
    return Panel(
        result.body,
        box=ROUNDED,
        border_style=result.border_style,
        title=title,
        padding=(0, 1),
    )


def _render_version_panel() -> Panel:
    header = Text()
    header.append("m", style=f"bold {ACCENT_PINK}")
    header.append("e", style=f"bold {ACCENT_CORAL}")
    header.append("m", style=f"bold {ACCENT_ORANGE}")
    header.append("  ·  ", style="dim")
    header.append("version", style=f"bold {ACCENT_YELLOW}")

    body = Table.grid(padding=(0, 1))
    body.add_row(Text("Package", style=f"bold {ACCENT_ORANGE}"), Text(APP_NAME, style="white"))
    body.add_row(Text("Version", style=f"bold {ACCENT_ORANGE}"), Text(APP_VERSION, style=f"bold {ACCENT_YELLOW}"))
    body.add_row(Text("Status", style=f"bold {ACCENT_ORANGE}"), Text("installed", style=f"bold {ACCENT_PINK}"))

    return Panel(
        body,
        box=ROUNDED,
        border_style=ACCENT_PINK,
        title=header,
        padding=(0, 1),
    )


def _render_action_layout(result: _ActionResult, footer_pairs: list | None = None) -> Group:
    header = Panel(
        Text.assemble(
            ("mem", f"bold {ACCENT_PINK}"),
            ("  ·  ", "dim"),
            (result.title, f"bold {ACCENT_YELLOW}"),
        ),
        box=ROUNDED,
        border_style=result.border_style,
        padding=(0, 1),
    )
    body = Panel(
        result.body,
        box=ROUNDED,
        border_style=result.border_style,
        padding=(0, 1),
        title=Text(result.title, style=f"bold {ACCENT_PINK}"),
    )
    return Group(header, body, _render_footer(footer_pairs))


def _pause_for_continue() -> None:
    try:
        console.input(f"[bold {ACCENT_YELLOW}]Press Enter to return to the menu...[/bold {ACCENT_YELLOW}]")
    except (EOFError, KeyboardInterrupt):
        return


def _start_monitor_action() -> _ActionResult:
    try:
        state = _registry().start()
    except RuntimeError as exc:
        return _ActionResult(
            title="Start failed",
            body=Panel.fit(str(exc), border_style="red"),
            border_style="red",
        )

    table = Table.grid(padding=(0, 1))
    table.add_row(Text("Started", style=f"bold {ACCENT_YELLOW}"), Text("monitor active", style="green"))
    table.add_row(Text("PID", style=f"bold {ACCENT_ORANGE}"), Text(str(state.pid), style="white"))
    table.add_row(Text("State", style=f"bold {ACCENT_PINK}"), Text(str(get_runtime_state_path()), style="white"))
    return _ActionResult(title="Monitor started", body=table, border_style=ACCENT_PINK)


def _stop_monitor_action() -> _ActionResult:
    state = _registry().stop()
    if state is None:
        return _ActionResult(
            title="Stop monitor",
            body=Panel.fit("No running monitor found.", border_style=ACCENT_YELLOW),
            border_style=ACCENT_YELLOW,
        )

    table = Table.grid(padding=(0, 1))
    table.add_row(Text("Stopped", style=f"bold {ACCENT_YELLOW}"), Text("monitor halted", style="green"))
    table.add_row(Text("PID", style=f"bold {ACCENT_CORAL}"), Text(str(state.pid), style="white"))
    return _ActionResult(title="Monitor stopped", body=table, border_style=ACCENT_CORAL)


def _mcp_registry() -> ProcessRegistry:
    return ProcessRegistry(RuntimeStateStore(get_mcp_state_path()))


def _status_action() -> _ActionResult:
    monitor_state = _registry().load_state()
    mcp_state = _mcp_registry().load_state()
    autostart_enabled = launch_agent_installed()

    table = Table(title="Runtime Status", expand=True)
    table.add_column("Service", style=ACCENT_ORANGE, no_wrap=True)
    table.add_column("State", no_wrap=True)
    table.add_column("PID", style="dim", no_wrap=True)
    table.add_column("Started", style="dim", no_wrap=True)

    def _state_text(running: bool) -> Text:
        return (
            Text("running", style=f"bold {ACCENT_PINK}")
            if running
            else Text("stopped", style="dim")
        )

    # Monitor row
    if monitor_state:
        table.add_row(
            "Monitor",
            _state_text(monitor_state.running),
            str(monitor_state.pid) if monitor_state.pid else "-",
            monitor_state.started_at.isoformat() if monitor_state.started_at else "-",
        )
    else:
        table.add_row("Monitor", _state_text(False), "-", "-")

    # MCP server row
    if mcp_state:
        table.add_row(
            "MCP server",
            _state_text(mcp_state.running),
            str(mcp_state.pid) if mcp_state.pid else "-",
            mcp_state.started_at.isoformat() if mcp_state.started_at else "-",
        )
    else:
        table.add_row("MCP server", _state_text(False), "-", "-")

    table.add_row(
        "MCP autostart",
        Text("enabled", style=f"bold {ACCENT_PINK}") if autostart_enabled else Text("disabled", style="dim"),
        "-",
        str(launch_agent_path()),
    )

    any_running = (monitor_state and monitor_state.running) or (mcp_state and mcp_state.running)
    return _ActionResult(
        title="Status",
        body=table,
        border_style=ACCENT_PINK if any_running else ACCENT_YELLOW,
    )


def _mcp_stop_action() -> _ActionResult:
    state = _mcp_registry().stop()
    if state is None:
        return _ActionResult(
            title="Stop MCP server",
            body=Panel.fit("No running MCP server found.", border_style=ACCENT_YELLOW),
            border_style=ACCENT_YELLOW,
        )
    table = Table.grid(padding=(0, 1))
    table.add_row(Text("Stopped", style=f"bold {ACCENT_YELLOW}"), Text("MCP server halted", style="green"))
    table.add_row(Text("PID", style=f"bold {ACCENT_CORAL}"), Text(str(state.pid), style="white"))
    return _ActionResult(title="MCP server stopped", body=table, border_style=ACCENT_CORAL)


def _run_monitoring_menu() -> None:
    while True:
        console.clear()
        console.print(_render_submenu_screen("Monitoring", ACCENT_PINK, MENU_MONITORING, _FOOTER_MONITORING))
        try:
            choice = console.input("").strip()
        except (EOFError, KeyboardInterrupt):
            return

        if choice == "1":
            console.clear()
            result = _start_monitor_action()
            console.print(_render_action_screen(result))
            _pause_for_continue()
        elif choice == "2":
            console.clear()
            result = _stop_monitor_action()
            console.print(_render_action_screen(result))
            _pause_for_continue()
        elif choice == "3":
            _launch_dashboard()
        elif choice == "4":
            console.clear()
            result = _status_action()
            console.print(_render_action_screen(result))
            _pause_for_continue()
        elif choice == "0" or choice.lower() in {"b", "back"}:
            return
        else:
            console.clear()
            console.print(_render_action_screen(_ActionResult(
                title="Unknown option",
                body=Panel.fit(f"Unknown option: {choice!r}. Enter 1–4 or 0 to go back.", border_style="red"),
                border_style="red",
            )))
            _pause_for_continue()


def _run_memory_menu() -> None:
    while True:
        console.clear()
        console.print(_render_submenu_screen("Memory", ACCENT_ORANGE, MENU_MEMORY, _FOOTER_MEMORY))
        try:
            choice = console.input("").strip()
        except (EOFError, KeyboardInterrupt):
            return

        if choice == "1":
            console.clear()
            _launch_init()
            _pause_for_continue()
        elif choice == "2":
            console.clear()
            import subprocess, sys as _sys
            try:
                subprocess.run([_sys.argv[0], "config"])
            except KeyboardInterrupt:
                console.print(Text("  Cancelled.", style="dim"))
            _pause_for_continue()
        elif choice == "3":
            console.clear()
            console.print(Panel.fit(
                Text.assemble(
                    ("Starting MCP server…\n", f"bold {ACCENT_ORANGE}"),
                    ("Press ", "dim"), ("Ctrl+C", f"bold {ACCENT_YELLOW}"), (" to stop and return to the menu.", "dim"),
                ),
                border_style=ACCENT_ORANGE,
            ))
            _launch_mcp()
        elif choice == "4":
            console.clear()
            result = _mcp_stop_action()
            console.print(_render_action_screen(result))
            _pause_for_continue()
        elif choice == "0" or choice.lower() in {"b", "back"}:
            return
        else:
            console.clear()
            console.print(_render_action_screen(_ActionResult(
                title="Unknown option",
                body=Panel.fit(f"Unknown option: {choice!r}. Enter 1–4 or 0 to go back.", border_style="red"),
                border_style="red",
            )))
            _pause_for_continue()


def _run_menu() -> None:
    while True:
        console.clear()
        console.print(_render_home_screen())
        try:
            choice = console.input("").strip()
        except (EOFError, KeyboardInterrupt):
            return

        if choice == "1":
            _run_monitoring_menu()
        elif choice == "2":
            _run_memory_menu()
        elif choice == "0" or choice.lower() in {"q", "quit", "exit"}:
            console.clear()
            return
        else:
            console.clear()
            console.print(_render_action_screen(_ActionResult(
                title="Unknown option",
                body=Panel.fit(f"Unknown option: {choice!r}. Enter 1, 2, or 0 to quit.", border_style="red"),
                border_style="red",
            )))
            _pause_for_continue()




@app.command(rich_help_panel=f"[bold {ACCENT_PINK}]Monitor[/]")
def start() -> None:
    """[bold #E93A7D]Start[/] the local monitor."""
    result = _start_monitor_action()
    console.print(_render_action_screen(result))
    if result.border_style == "red":
        raise typer.Exit(code=1)


@app.command(rich_help_panel=f"[bold {ACCENT_PINK}]Monitor[/]")
def stop() -> None:
    """[bold #F25C5C]Stop[/] the local monitor."""
    result = _stop_monitor_action()
    console.print(_render_action_screen(result))


@app.command(rich_help_panel=f"[bold {ACCENT_PINK}]Monitor[/]")
def status() -> None:
    """Show monitor [bold #F7B500]status[/]."""
    result = _status_action()
    console.print(_render_action_screen(result))


def _launch_init() -> None:
    import subprocess
    import sys
    subprocess.run([sys.argv[0], "init"])


def _launch_mcp() -> None:
    import subprocess
    import sys
    try:
        subprocess.run([sys.argv[0], "serve"])
    except KeyboardInterrupt:
        pass


def _launch_dashboard(view: str = "both") -> None:
    service = build_monitor_service()
    service.start()

    def snapshot_provider():
        return service.snapshot()

    def running_provider() -> bool:
        return service.is_running()

    try:
        live_dashboard(
            snapshot_provider,
            running_provider,
            reset_provider=service.reset,
            view=cast(DashboardViewMode, view),
        )
    except KeyboardInterrupt:
        pass
    finally:
        service.stop()


@app.command(rich_help_panel=f"[bold {ACCENT_PINK}]Monitor[/]")
def dashboard(
    view: str = typer.Option(
        "both",
        "--view",
        "-v",
        help="Dashboard view mode: summary, detail, or both.",
        case_sensitive=False,
    ),
) -> None:
    """Open a [bold #F98C2B]live token dashboard[/] in the terminal."""
    normalized_view = view.lower()
    if normalized_view not in {"summary", "detail", "both"}:
        raise typer.BadParameter("view must be one of: summary, detail, both")
    _launch_dashboard(normalized_view)


@app.command(
    rich_help_panel=f"[bold {ACCENT_PINK}]Monitor[/]",
    help="Print the installed mem-cli version and exit.",
)
def version() -> None:
    """Print the current [bold #F7B500]version[/]."""
    console.print(_render_version_panel())


# ---------------------------------------------------------------------------
# Memory commands
# ---------------------------------------------------------------------------

def _memory_service() -> MemoryService:
    return MemoryService()


def _render_memory_table(memories: list) -> Table:
    table = Table(expand=True, box=ROUNDED, border_style=ACCENT_PINK)
    table.add_column("ID", style=f"bold {ACCENT_YELLOW}", no_wrap=True, width=10)
    table.add_column("Content", style="white", ratio=3)
    table.add_column("Tags", style=ACCENT_CORAL, ratio=1)
    table.add_column("Saved", style="dim", no_wrap=True)
    for m in memories:
        tags = ", ".join(m.tags) if m.tags else "-"
        ts = m.timestamp.strftime("%Y-%m-%d %H:%M")
        table.add_row(m.id, m.content, tags, ts)
    return table


@app.command(rich_help_panel=f"[bold {ACCENT_ORANGE}]Memory[/]")
def remember(
    content: str = typer.Argument(..., help="The memory to store."),
    tags: list[str] = typer.Option([], "--tag", "-t", help="Optional tags (repeatable)."),
    cwd: str = typer.Option("", "--cwd", hidden=True, help="Project path override."),
    auto: bool = typer.Option(False, "--auto", hidden=True, help="Auto-capture: adds auto-captured tag and skips duplicates."),
) -> None:
    """[bold #E93A7D]Store[/] a [bold #F98C2B]memory[/] for the current project."""
    svc = _memory_service()
    if auto:
        _, was_saved = svc.auto_remember(content, cwd=cwd or None, tags=list(tags))
        if not was_saved:
            raise typer.Exit(code=0)
        return
    memory = svc.remember(content, cwd=cwd or None, tags=tags)

    table = Table.grid(padding=(0, 1))
    table.add_row(Text("ID", style=f"bold {ACCENT_ORANGE}"), Text(memory.id, style=ACCENT_YELLOW))
    table.add_row(Text("Project", style=f"bold {ACCENT_ORANGE}"), Text(memory.project_name, style="white"))
    table.add_row(Text("Content", style=f"bold {ACCENT_ORANGE}"), Text(memory.content, style="white"))
    if memory.tags:
        table.add_row(Text("Tags", style=f"bold {ACCENT_ORANGE}"), Text(", ".join(memory.tags), style="white"))

    console.print(_render_action_screen(_ActionResult(
        title="Memory saved",
        body=table,
        border_style=ACCENT_PINK,
    )))


@app.command(rich_help_panel=f"[bold {ACCENT_ORANGE}]Memory[/]")
def recall(
    query: str = typer.Argument("", help="Optional search query (substring match on content)."),
    tag: str = typer.Option("", "--tag", "-t", help="Filter by tag."),
    cwd: str = typer.Option("", "--cwd", hidden=True, help="Project path override."),
    plain: bool = typer.Option(False, "--plain", "-p", help="Plain text output (no formatting). Useful for scripts and hooks."),
) -> None:
    """[bold #F25C5C]List[/] memories for the current project."""
    svc = _memory_service()
    memories = svc.recall(cwd=cwd or None, query=query or None, tag=tag or None)

    if not memories:
        if plain:
            return
        parts = []
        if tag:
            parts.append(f"tag [bold]{tag}[/bold]")
        if query:
            parts.append(f"query [bold]{query!r}[/bold]")
        filter_desc = " and ".join(parts)
        msg = f"No memories found{f' matching {filter_desc}' if filter_desc else ''}."
        console.print(_render_action_screen(_ActionResult(
            title="Recall",
            body=Panel.fit(msg, border_style=ACCENT_YELLOW),
            border_style=ACCENT_YELLOW,
        )))
        return

    if plain:
        for m in memories:
            tags_str = f"  [{', '.join(m.tags)}]" if m.tags else ""
            print(f"{m.content}{tags_str}")
        return

    title_parts = [f"Memories — {memories[0].project_name}"]
    if tag:
        title_parts.append(f"[dim]#{tag}[/dim]")
    if query:
        title_parts.append(f"[dim]\"{query}\"[/dim]")

    console.print(_render_action_screen(_ActionResult(
        title=" ".join(title_parts),
        body=_render_memory_table(memories),
        border_style=ACCENT_PINK,
    )))


@app.command(rich_help_panel=f"[bold {ACCENT_ORANGE}]Memory[/]")
def forget(
    memory_id: str = typer.Argument(..., help="ID of the memory to delete."),
    cwd: str = typer.Option("", "--cwd", hidden=True, help="Project path override."),
) -> None:
    """[bold #F25C5C]Delete[/] a memory by ID."""
    svc = _memory_service()
    deleted = svc.forget(memory_id, cwd=cwd or None)

    if deleted:
        body = Panel.fit(f"Memory [bold]{memory_id}[/bold] deleted.", border_style=ACCENT_PINK)
        console.print(_render_action_screen(_ActionResult(
            title="Memory deleted",
            body=body,
            border_style=ACCENT_PINK,
        )))
    else:
        body = Panel.fit(f"No memory found with ID [bold]{memory_id}[/bold].", border_style="red")
        console.print(_render_action_screen(_ActionResult(
            title="Not found",
            body=body,
            border_style="red",
        )))
        raise typer.Exit(code=1)


@app.command(rich_help_panel=f"[bold {ACCENT_ORANGE}]Memory[/]")
def projects() -> None:
    """List all [bold #F98C2B]projects[/] that have stored memories."""
    svc = _memory_service()
    all_projects = svc.projects()

    if not all_projects:
        console.print(_render_action_screen(_ActionResult(
            title="Projects",
            body=Panel.fit("No projects with memories yet.", border_style=ACCENT_YELLOW),
            border_style=ACCENT_YELLOW,
        )))
        return

    table = Table(expand=True, box=ROUNDED, border_style=ACCENT_PINK)
    table.add_column("Project", style=f"bold {ACCENT_YELLOW}", ratio=2)
    table.add_column("Path", style="dim", ratio=3)
    table.add_column("Memories", style=ACCENT_ORANGE, justify="right", width=10)
    for p in all_projects:
        table.add_row(p["project_name"], p["project"], str(p["memory_count"]))

    console.print(_render_action_screen(_ActionResult(
        title="Projects",
        body=table,
        border_style=ACCENT_PINK,
    )))


@app.command(rich_help_panel=f"[bold {ACCENT_ORANGE}]Memory[/]")
def compress(
    agent: str = typer.Option(
        "",
        "--agent",
        "-a",
        help="Agent to use: 'claude' or 'codex'. Auto-detects if omitted.",
    ),
    cwd: str = typer.Option("", "--cwd", hidden=True, help="Project path override."),
) -> None:
    """[bold #E93A7D]Compress[/] project memories using an [bold #F98C2B]AI agent[/].

    Merges redundant or overlapping memories into a smaller, denser set.
    Shows a preview and asks for confirmation before replacing anything.

    \b
    Examples:
      mem compress                  # detect agent, pick interactively
      mem compress --agent claude   # use Claude Code
      mem compress --agent codex    # use Codex
    """
    from rich.live import Live
    from rich.spinner import Spinner

    resolved_cwd = cwd or None

    # ------------------------------------------------------------------ #
    # 1. Load existing memories                                           #
    # ------------------------------------------------------------------ #
    svc = _memory_service()
    originals = svc.recall(cwd=resolved_cwd)

    if not originals:
        console.print(_render_action_screen(_ActionResult(
            title="Compress",
            body=Panel.fit("No memories found for this project.", border_style=ACCENT_YELLOW),
            border_style=ACCENT_YELLOW,
        )))
        raise typer.Exit(code=0)

    if len(originals) < 2:
        console.print(_render_action_screen(_ActionResult(
            title="Compress",
            body=Panel.fit(
                f"Only {len(originals)} memory — nothing to compress.",
                border_style=ACCENT_YELLOW,
            ),
            border_style=ACCENT_YELLOW,
        )))
        raise typer.Exit(code=0)

    # ------------------------------------------------------------------ #
    # 2. Detect / resolve agent                                           #
    # ------------------------------------------------------------------ #
    available = detect_available_agents()

    if not available:
        hints = "\n".join(
            f"  {name}: {hint}" for name, hint in AGENT_INSTALL_HINTS.items()
        )
        console.print(_render_action_screen(_ActionResult(
            title="No agent found",
            body=Panel.fit(
                Text.assemble(
                    ("No supported agent is installed.\n\n", "white"),
                    ("Install one of:\n", "dim"),
                    (hints, f"bold {ACCENT_YELLOW}"),
                ),
                border_style="red",
            ),
            border_style="red",
        )))
        raise typer.Exit(code=1)

    chosen = agent.lower() if agent else ""

    if chosen and chosen not in AGENT_COMMANDS:
        agents_str = ", ".join(f"'{a}'" for a in AGENT_COMMANDS)
        console.print(Panel.fit(
            f"Unknown agent {chosen!r}. Choose one of: {agents_str}.",
            border_style="red",
        ))
        raise typer.Exit(code=1)

    if chosen and chosen not in available:
        console.print(Panel.fit(
            Text.assemble(
                (f"Agent '{chosen}' is not installed.\n", "white"),
                (f"Install it with: {AGENT_INSTALL_HINTS.get(chosen, '')}", f"bold {ACCENT_YELLOW}"),
            ),
            border_style="red",
        ))
        raise typer.Exit(code=1)

    if not chosen:
        if len(available) == 1:
            chosen = available[0]
        else:
            chosen = _select_interactive_agent(available)
            if chosen is None:
                console.print(Text("  Cancelled.", style="dim"))
                raise typer.Exit(code=0)

    # ------------------------------------------------------------------ #
    # 3. Run compression with spinner                                     #
    # ------------------------------------------------------------------ #
    result_holder: list[tuple[list, list, str | None]] = []

    def _do_compress() -> None:
        res = svc.compress(cwd=resolved_cwd, agent=chosen)
        result_holder.append(res)

    import threading

    spinner = Spinner("dots", text=Text(
        f"  Compressing {len(originals)} memories with {chosen}…",
        style=f"bold {ACCENT_ORANGE}",
    ))

    worker = threading.Thread(target=_do_compress, daemon=True)
    worker.start()

    with Live(spinner, refresh_per_second=12, console=console):
        worker.join()

    _, pairs, error = result_holder[0]

    if error:
        console.print(_render_action_screen(_ActionResult(
            title="Compress failed",
            body=Panel.fit(
                Text.assemble(
                    ("Agent error:\n", f"bold {ACCENT_CORAL}"),
                    (error, "white"),
                ),
                border_style="red",
            ),
            border_style="red",
        )))
        raise typer.Exit(code=1)

    if not pairs:
        console.print(_render_action_screen(_ActionResult(
            title="Compress",
            body=Panel.fit("Agent returned no memories.", border_style=ACCENT_YELLOW),
            border_style=ACCENT_YELLOW,
        )))
        raise typer.Exit(code=1)

    # ------------------------------------------------------------------ #
    # 4. Preview: before / after                                          #
    # ------------------------------------------------------------------ #
    preview = Table(expand=True, box=ROUNDED, border_style=ACCENT_PINK)
    preview.add_column(
        f"Before ({len(originals)})",
        style="dim white",
        ratio=1,
    )
    preview.add_column(
        f"After ({len(pairs)})",
        style=f"bold {ACCENT_YELLOW}",
        ratio=1,
    )

    max_rows = max(len(originals), len(pairs))
    for i in range(max_rows):
        before = originals[i].content if i < len(originals) else ""
        after_content, after_tags = pairs[i] if i < len(pairs) else ("", [])
        after_cell = after_content
        if after_tags:
            after_cell += f"\n[dim]#{' #'.join(after_tags)}[/dim]"
        preview.add_row(before, after_cell)

    console.print(_render_action_screen(_ActionResult(
        title=f"Compress — {originals[0].project_name}",
        body=preview,
        border_style=ACCENT_PINK,
    )))

    # ------------------------------------------------------------------ #
    # 5. Confirm and save                                                 #
    # ------------------------------------------------------------------ #
    console.print()
    try:
        confirm = console.input(
            f"[bold {ACCENT_YELLOW}]Replace {len(originals)} memories with {len(pairs)}? (y/N): [/]"
        ).strip().lower()
    except (EOFError, KeyboardInterrupt):
        confirm = ""

    if confirm != "y":
        console.print(Text("  Cancelled.", style="dim"))
        raise typer.Exit(code=0)

    new_memories = [
        Memory(content=content, project=originals[0].project, tags=tags)
        for content, tags in pairs
    ]
    svc.replace_all(new_memories, cwd=resolved_cwd)

    console.print(_render_action_screen(_ActionResult(
        title="Compressed",
        body=Panel.fit(
            Text.assemble(
                (f"{len(originals)}", f"bold {ACCENT_CORAL}"),
                (" memories → ", "white"),
                (f"{len(new_memories)}", f"bold {ACCENT_YELLOW}"),
                (" memories saved.", "white"),
            ),
            border_style=ACCENT_PINK,
        ),
        border_style=ACCENT_PINK,
    )))


@app.command(rich_help_panel=f"[bold {ACCENT_ORANGE}]Memory[/]")
def init(
    agent: str = typer.Option(
        "",
        "--agent",
        "-a",
        help="Agent to use: 'claude' or 'codex'. Omit to pick interactively.",
    ),
    cwd: str = typer.Option("", "--cwd", hidden=True, help="Project path override."),
) -> None:
    """[bold #E93A7D]Initialize[/] memories for the current project using an [bold #F98C2B]AI agent[/].

    The agent analyzes the project and generates mem remember commands organized
    by category. If the project already has memories you will be asked to confirm
    before replacing them.

    \b
    Examples:
      mem init                   # detect agents, pick interactively
      mem init --agent claude    # use Claude Code directly
      mem init --agent codex     # use Codex directly
    """
    from .services.memory_service import MemoryService
    from .storage.memory_store import MemoryStore

    resolved_cwd = cwd or None

    # ------------------------------------------------------------------ #
    # 1. Detect installed agents                                          #
    # ------------------------------------------------------------------ #
    available = detect_available_agents()

    if not available:
        hints = "\n".join(
            f"  {name}: {hint}" for name, hint in AGENT_INSTALL_HINTS.items()
        )
        console.print(_render_action_screen(_ActionResult(
            title="No agent found",
            body=Panel.fit(
                Text.assemble(
                    ("No supported agent is installed.\n\n", "white"),
                    ("Install one of:\n", "dim"),
                    (hints, f"bold {ACCENT_YELLOW}"),
                ),
                border_style="red",
            ),
            border_style="red",
        )))
        raise typer.Exit(code=1)

    # ------------------------------------------------------------------ #
    # 2. Resolve which agent to use                                       #
    # ------------------------------------------------------------------ #
    chosen = agent.lower() if agent else ""

    if chosen and chosen not in AGENT_COMMANDS:
        agents = ", ".join(f"'{a}'" for a in AGENT_COMMANDS)
        console.print(Panel.fit(
            f"Unknown agent {chosen!r}. Choose one of: {agents}.",
            border_style="red",
        ))
        raise typer.Exit(code=1)

    if chosen and chosen not in available:
        console.print(Panel.fit(
            Text.assemble(
                (f"Agent '{chosen}' is not installed.\n", "white"),
                (f"Install it with: {AGENT_INSTALL_HINTS.get(chosen, '')}", f"bold {ACCENT_YELLOW}"),
            ),
            border_style="red",
        ))
        raise typer.Exit(code=1)

    if not chosen:
        if len(available) == 1:
            chosen = available[0]
        else:
            chosen = _select_interactive_agent(available)
            if chosen is None:
                console.print(Text("  Cancelled.", style="dim"))
                raise typer.Exit(code=0)

    # ------------------------------------------------------------------ #
    # 3. Check if project already has memories                            #
    # ------------------------------------------------------------------ #
    svc = MemoryService()
    existing = svc.recall(cwd=resolved_cwd)

    if existing:
        project_name = existing[0].project_name
        console.print()
        console.print(Panel.fit(
            Text.assemble(
                ("Project ", "white"),
                (project_name, f"bold {ACCENT_YELLOW}"),
                (f" already has {len(existing)} memory(s).\n", "white"),
                ("This will delete all existing memories and regenerate them.", "dim"),
            ),
            border_style=ACCENT_ORANGE,
            title=Text("Project exists", style=f"bold {ACCENT_ORANGE}"),
        ))
        console.print()
        try:
            confirm = console.input(
                f"[bold {ACCENT_YELLOW}]Replace all memories? (y/N): [/]"
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            confirm = ""

        if confirm != "y":
            console.print(Text("  Cancelled.", style="dim"))
            raise typer.Exit(code=0)

        # Delete all existing memories for this project
        for m in existing:
            svc.forget(m.id, cwd=resolved_cwd)

    # ------------------------------------------------------------------ #
    # 4. Run the agent with live UI                                       #
    # ------------------------------------------------------------------ #
    from rich.live import Live
    from rich.spinner import Spinner

    filled = build_prompt(cwd=resolved_cwd)
    saved: list[tuple[str, str]] = []   # (content, tag)
    last_line: list[str] = [""]         # mutable cell for current output line
    is_running: list[bool] = [True]

    def _make_live() -> Group:
        items: list = []

        # Spinner row
        spinner_text = Text.assemble(
            (" Generating with ", "dim"),
            (chosen, f"bold {ACCENT_YELLOW}"),
            ("…", "dim"),
        )
        items.append(Spinner("dots", text=spinner_text) if is_running[0]
                     else Text(""))

        # Latest raw line from the agent (dim, truncated)
        raw = last_line[0]
        if raw:
            preview = raw if len(raw) <= 80 else raw[:77] + "…"
            items.append(Text(f"  {preview}", style="dim"))

        # Saved memories so far
        if saved:
            t = Table.grid(padding=(0, 1))
            for content, tag in saved:
                label = f"[{tag}]" if tag else ""
                t.add_row(
                    Text("  ✓", style=f"bold {ACCENT_PINK}"),
                    Text(label, style=ACCENT_ORANGE),
                    Text(content, style="white"),
                )
            items.append(t)

        return Group(*items)

    def _on_line(line: str) -> None:
        parsed = parse_remember(line)
        if parsed:
            content, tag = parsed
            svc.remember(content, cwd=resolved_cwd, tags=[tag] if tag else [])
            saved.append((content, tag))
            last_line[0] = ""
        else:
            # Show raw agent output as a progress hint, skip markdown fences
            if not line.startswith("```"):
                last_line[0] = line

    console.print()
    with Live(_make_live(), console=console, refresh_per_second=12) as live:
        result = run_agent(filled, chosen, on_line=lambda ln: (
            _on_line(ln),
            live.update(_make_live()),
        ))
        is_running[0] = False
        last_line[0] = ""
        live.update(_make_live())

    console.print()

    if result.ok or (result.partial and saved):
        # Show summary
        summary_table = Table(expand=True, box=ROUNDED, border_style=ACCENT_PINK)
        summary_table.add_column("Tag", style=ACCENT_ORANGE, no_wrap=True)
        summary_table.add_column("Memory", style="white")
        for content, tag in saved:
            summary_table.add_row(tag or "-", content)

        console.print(_render_action_screen(_ActionResult(
            title=f"{len(saved)} memor{'y' if len(saved) == 1 else 'ies'} saved",
            body=summary_table if saved else Panel.fit("No memories were generated.", border_style=ACCENT_YELLOW),
            border_style=ACCENT_PINK if saved else ACCENT_YELLOW,
        )))

        if result.partial:
            console.print(Panel.fit(
                Text.assemble(
                    ("The agent exited early — some memories may be missing.\n", "white"),
                    (f"Cause: {result.stderr}", "red") if result.stderr else ("", ""),
                ),
                border_style=ACCENT_ORANGE,
                title=Text("Partial completion", style=f"bold {ACCENT_ORANGE}"),
            ))
            raise typer.Exit(code=result.exit_code)
    else:
        body = Text.assemble(
            ("The task did not complete — the agent failed before saving any memory.\n", "white"),
            *([("\nCause:\n", "dim"), (result.stderr, "red")] if result.stderr else []),
        )
        console.print(Panel(
            body,
            title=Text("Task failed", style="bold red"),
            border_style="red",
        ))
        raise typer.Exit(code=result.exit_code)


# ---------------------------------------------------------------------------
# Config command — generate AGENTS.md and sync CLAUDE.md as a symlink
# ---------------------------------------------------------------------------


def _config_prompt(agent: str, existing_agents: str, cwd: Path) -> str:
    priority_agent = "Claude" if agent == "claude" else "Codex"
    other_agent = "Codex" if agent == "claude" else "Claude"
    existing_block = existing_agents.strip()
    existing_text = existing_block or "(AGENTS.md does not exist yet.)"

    return f"""
You are generating the canonical AGENTS.md content for the mem CLI repository.

Output the complete AGENTS.md markdown to stdout — nothing else.
Do not write any files. Do not use any tools. Do not ask for permissions.
The caller will handle saving the output to disk.

Rules:
- Output markdown only. No code fences, no preamble, no trailing explanation.
- Prioritize the selected agent's ordering first: {priority_agent} sections before {other_agent} sections if that improves clarity.
- Preserve compatibility for Claude Code, Codex, and other MCP-capable agents.
- Separate shared guidance from agent-specific guidance.
- Include explicit blocks for Claude-only and Codex-only instructions when needed.
- Add or keep mem MCP instructions: memory_recall, memory_remember, memory_forget.
- Keep content concise, project-scoped, and organized for low token consumption.
- Use the repository context at {cwd}.

Project classification:
- First decide whether this repository is primarily a backend service, a frontend app, a repository of files/directories, or a mixed project.
- Write only the sections that fit the project. Do not force irrelevant sections into the output.
- If the repo is mixed, include the relevant sections from more than one category, but keep the result compact.

When the project is a backend service, prioritize:
- Stack, runtime, entrypoints, deployment targets.
- Routes, controllers, services, auth, middleware, data flow.
- Environment variables, secrets, integrations, persistence boundaries.
- API contracts, request/response conventions, error handling.

When the project is a frontend app, prioritize:
- Framework, rendering model, bootstrapping, routing.
- Component structure, state management, styling system, assets.
- Build/test commands, deployment targets, environment variables.
- Accessibility, responsive behavior, performance constraints, design tokens.

When the project is a repository of files/directories or a content-heavy workspace, prioritize:
- Directory taxonomy, naming conventions, file formats, and ownership rules.
- How files are created, updated, validated, moved, archived, or generated.
- Canonical entry files, templates, indexes, and sync rules.
- Search conventions, indexing rules, and any automation that relies on the layout.

Operational focus:
- Preserve the most useful technical facts for future agents, not long-form prose.
- Prefer command names, file paths, routes, env vars, and rules over narrative descriptions.
- Keep memory-related guidance short enough to minimize token use but specific enough to avoid mistakes.

Current AGENTS.md content:
{existing_text}

Required output structure:
1. Shared project overview.
2. Project type summary and the sections that matter for this repo.
3. MCP usage for mem.
4. Shared memory conventions and commands.
5. Backend-specific block if applicable.
6. Frontend-specific block if applicable.
7. Files/directories-specific block if applicable.
8. Claude-specific block.
9. Codex-specific block.
10. Sync note stating CLAUDE.md is a symlink to AGENTS.md.
"""


def _normalize_markdown_output(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].startswith("```"):
            cleaned = "\n".join(lines[1:-1]).strip()
    return cleaned + ("\n" if cleaned and not cleaned.endswith("\n") else "")


def _write_text(path: Path, content: str) -> bool:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if existing == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def _sync_claude_symlink(claude_path: Path, agents_path: Path) -> None:
    claude_path.parent.mkdir(parents=True, exist_ok=True)
    if claude_path.exists() or claude_path.is_symlink():
        if claude_path.is_dir() and not claude_path.is_symlink():
            shutil.rmtree(claude_path)
        else:
            claude_path.unlink()
    target = agents_path.name if claude_path.parent == agents_path.parent else os.path.relpath(agents_path, claude_path.parent)
    claude_path.symlink_to(target)


def _is_claude_synced_to_agents(claude_path: Path, agents_path: Path) -> bool:
    return claude_path.is_symlink() and claude_path.resolve() == agents_path.resolve()


def _select_config_mode() -> str:
    console.print()
    console.print(Text("Choose a configuration mode:", style=f"bold {ACCENT_ORANGE}"))
    console.print(f"  [1] configure a new AGENTS.md")
    console.print(f"  [2] only add mem MCP instructions in current AGENTS.md or CLAUDE.md")
    console.print(f"  [0] cancel")
    console.print()
    while True:
        try:
            raw = console.input(f"[bold {ACCENT_YELLOW}]Select mode (1-2, 0 to cancel): [/]").strip()
        except (EOFError, KeyboardInterrupt):
            raise typer.Exit(code=0)
        if raw == "1":
            return "new"
        if raw == "2":
            return "mcp-only"
        if raw == "0":
            raise typer.Exit(code=0)
        console.print("  Invalid choice, try again.", style="red")


def _select_interactive_agent(available: list[str], *, prompt_label: str = "Select agent") -> str | None:
    console.print()
    console.print(Text("Available agents:", style=f"bold {ACCENT_ORANGE}"))
    for i, name in enumerate(available, 1):
        console.print(f"  [{i}] {name}")
    console.print("  [0] cancel")
    console.print()
    while True:
        try:
            raw = console.input(
                f"[bold {ACCENT_YELLOW}]{prompt_label} (1-{len(available)}, 0 to cancel): [/]"
            ).strip()
        except (EOFError, KeyboardInterrupt):
            raise typer.Exit(code=0)
        if raw == "0":
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(available):
            return available[int(raw) - 1]
        console.print("  Invalid choice, try again.", style="red")


def _mcp_instructions_block() -> str:
    return """## MCP Usage for mem
- Use mem MCP for durable project context.
- `memory_recall`: check this first when repo history, conventions, or prior decisions matter.
- `memory_remember`: store stable repo facts, validated conventions, and repeatable fixes.
- `memory_forget`: remove stale or incorrect memory when behavior or decisions change.

## Shared Memory Conventions and Commands
- Keep memories short, factual, and project-scoped.
- Do not store secrets, credentials, or one-off debugging noise.
- Prefer file names, endpoints, commands, and accepted conventions over narrative notes.
- Use `rg` for search and `apply_patch` for manual edits.
- Preserve existing user changes and avoid unrelated churn.
"""


def _append_or_replace_mcp_block(content: str) -> str:
    block = _mcp_instructions_block().strip()
    text = content.strip()
    if not text:
        return block + "\n"

    marker = "## MCP Usage for mem"
    if marker in text:
        start = text.index(marker)
        next_markers = [
            idx for idx in (
                text.find("\n## ", start + len(marker)),
                text.find("\n# ", start + len(marker)),
            )
            if idx != -1
        ]
        end = min(next_markers) if next_markers else len(text)
        updated = text[:start].rstrip() + "\n\n" + block + "\n"
        if end < len(text):
            updated += text[end:].lstrip("\n")
        return updated.rstrip() + "\n"

    return text + "\n\n" + block + "\n"


@app.command(rich_help_panel=f"[bold {ACCENT_ORANGE}]Memory[/]")
def config(
    agent: str = typer.Option(
        "all",
        "--agent",
        "-a",
        help="Agent to use when generating AGENTS.md: 'claude', 'codex', or 'all'.",
        case_sensitive=False,
    ),
    cwd: str = typer.Option("", "--cwd", hidden=True, help="Project path override."),
) -> None:
    """[bold #E93A7D]Generate[/] [bold #F98C2B]AGENTS.md[/] and sync [bold #F98C2B]CLAUDE.md[/] as a symlink.

    The selected agent generates the canonical AGENTS.md content dynamically.
    CLAUDE.md is then rewritten as a symlink to AGENTS.md so Claude Code and
    Codex stay aligned. The generated file keeps shared instructions plus
    agent-specific blocks when needed.

    \b
    Examples:
      mem config               # generate AGENTS.md and symlink CLAUDE.md
      mem config --agent claude
      mem config --agent codex
    """
    resolved_cwd = Path(cwd).resolve() if cwd else Path.cwd()
    agent_lower = agent.lower()

    if agent_lower not in {"claude", "codex", "all"}:
        console.print(Panel.fit(
            f"Unknown agent {agent!r}. Choose one of: 'claude', 'codex', 'all'.",
            border_style="red",
        ))
        raise typer.Exit(code=1)

    if agent_lower == "all":
        available = detect_available_agents()
        if not available:
            hints = "\n".join(
                f"  {name}: {hint}" for name, hint in AGENT_INSTALL_HINTS.items()
            )
            console.print(_render_action_screen(_ActionResult(
                title="No agent found",
                body=Panel.fit(
                    Text.assemble(
                        ("No supported agent is installed.\n\n", "white"),
                        ("Install one of:\n", "dim"),
                        (hints, f"bold {ACCENT_YELLOW}"),
                    ),
                    border_style="red",
                ),
                border_style="red",
            )))
            raise typer.Exit(code=1)

        if len(available) == 1:
            chosen = available[0]
        else:
            chosen = _select_interactive_agent(available)
            if chosen is None:
                console.print(Text("  Cancelled.", style="dim"))
                raise typer.Exit(code=0)
    else:
        chosen = agent_lower

    if chosen not in AGENT_COMMANDS:
        agents = ", ".join(f"'{a}'" for a in AGENT_COMMANDS)
        console.print(Panel.fit(
            f"Unknown agent {chosen!r}. Choose one of: {agents}.",
            border_style="red",
        ))
        raise typer.Exit(code=1)

    if chosen not in detect_available_agents():
        console.print(Panel.fit(
            Text.assemble(
                (f"Agent '{chosen}' is not installed.\n", "white"),
                (f"Install it with: {AGENT_INSTALL_HINTS.get(chosen, '')}", f"bold {ACCENT_YELLOW}"),
            ),
            border_style="red",
        ))
        raise typer.Exit(code=1)

    base_dir = resolved_cwd
    agents_path = base_dir / "AGENTS.md"
    claude_path = base_dir / "CLAUDE.md"
    existing_agents = agents_path.read_text(encoding="utf-8") if agents_path.exists() else ""

    config_mode = _select_config_mode()

    if config_mode == "mcp-only":
        target_path = agents_path if agents_path.exists() else claude_path if claude_path.exists() and not claude_path.is_symlink() else agents_path
        source_path = agents_path if agents_path.exists() else claude_path if claude_path.exists() else target_path
        source_text = source_path.read_text(encoding="utf-8") if source_path.exists() else ""
        updated_text = _append_or_replace_mcp_block(source_text)

        if target_path != agents_path and claude_path.exists() and claude_path.is_symlink():
            target_path = agents_path

        changed = _write_text(target_path, updated_text)
        if target_path == agents_path:
            _sync_claude_symlink(claude_path, agents_path)

        table = Table(expand=True, box=ROUNDED, border_style=ACCENT_PINK)
        table.add_column("File", style=f"bold {ACCENT_YELLOW}", no_wrap=True)
        table.add_column("Path", style="dim")
        table.add_column("Result", no_wrap=True)

        table.add_row(
            target_path.name,
            str(target_path),
            Text("updated", style=f"bold {ACCENT_PINK}") if changed else Text("already up to date", style="dim"),
        )
        if target_path == agents_path:
            table.add_row(
                "CLAUDE.md",
                str(claude_path),
                Text("synced", style=f"bold {ACCENT_PINK}") if claude_path.exists() or claude_path.is_symlink() else Text("created", style=f"bold {ACCENT_PINK}"),
            )

        console.print(_render_action_screen(_ActionResult(
            title="Config",
            body=table,
            border_style=ACCENT_PINK,
        )))
        return

    if _is_claude_synced_to_agents(claude_path, agents_path):
        console.print()
        console.print(Panel.fit(
            Text.assemble(
                ("The project already seems to have been configured.\n", "white"),
                ("Do you want to continue anyway?", "bold"),
            ),
            border_style=ACCENT_ORANGE,
            title=Text("Already configured", style=f"bold {ACCENT_ORANGE}"),
        ))
        try:
            confirm = console.input(
                f"[bold {ACCENT_YELLOW}]Continue anyway? (y/N): [/]"
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            confirm = ""
        if confirm != "y":
            console.print(Text("  Cancelled.", style="dim"))
            raise typer.Exit(code=0)

    prompt = _config_prompt(chosen, existing_agents, resolved_cwd)
    console.print()
    from rich.live import Live
    from rich.spinner import Spinner

    def _make_config_live() -> Group:
        spinner_text = Text.assemble(
            (" Generating ", "dim"),
            ("AGENTS.md", f"bold {ACCENT_YELLOW}"),
            (" with ", "dim"),
            (chosen, f"bold {ACCENT_YELLOW}"),
            ("...", "dim"),
        )
        return Group(
            Spinner("dots", text=spinner_text),
            Panel.fit(
                Text.assemble(
                    ("Updating the project memory guide and syncing CLAUDE.md as a symlink.", "dim"),
                ),
                border_style=ACCENT_ORANGE,
            ),
        )

    with Live(_make_config_live(), console=console, refresh_per_second=12) as live:
        agent_output: AgentTextResult = run_agent_text(prompt, chosen)
        live.update(_make_config_live())

    generated_agents = _normalize_markdown_output(agent_output.stdout)

    if not generated_agents:
        console.print(Panel.fit(
            Text.assemble(
                ("The agent did not produce AGENTS.md content.\n", "white"),
                (agent_output.result.stderr, "red") if agent_output.result.stderr else ("", ""),
            ),
            border_style="red",
            title=Text("Config failed", style="bold red"),
        ))
        raise typer.Exit(code=agent_output.result.exit_code or 1)

    agents_changed = _write_text(agents_path, generated_agents)
    _sync_claude_symlink(claude_path, agents_path)

    # ---- Result table -------------------------------------------------------
    table = Table(expand=True, box=ROUNDED, border_style=ACCENT_PINK)
    table.add_column("File", style=f"bold {ACCENT_YELLOW}", no_wrap=True)
    table.add_column("Path", style="dim")
    table.add_column("Result", no_wrap=True)

    for label, path_str, changed in (
        ("AGENTS.md", str(agents_path), agents_changed),
        ("CLAUDE.md", str(claude_path), True),
    ):
        result_text = (
            Text("updated", style=f"bold {ACCENT_PINK}")
            if changed
            else Text("already up to date", style="dim")
        )
        table.add_row(label, path_str, result_text)

    console.print(_render_action_screen(_ActionResult(
        title="Config",
        body=table,
        border_style=ACCENT_PINK,
    )))

    if not agent_output.result.ok:
        console.print(Panel.fit(
            Text.assemble(
                ("The agent exited with a non-zero status after producing AGENTS.md.\n", "white"),
                (agent_output.result.stderr, "red") if agent_output.result.stderr else ("", ""),
            ),
            border_style=ACCENT_ORANGE,
            title=Text("Partial completion", style=f"bold {ACCENT_ORANGE}"),
        ))


def _serve_tty() -> None:
    """Live status display for interactive (TTY) usage of mem serve."""
    import os
    import time

    from rich.live import Live
    from rich.spinner import Spinner

    from .config import get_mcp_state_path
    from .storage.runtime_state import RuntimeState, RuntimeStateStore
    from .utils.time import utc_now

    state_store = RuntimeStateStore(get_mcp_state_path())
    started_at = utc_now()
    state_store.save(RuntimeState(
        running=True,
        pid=os.getpid(),
        started_at=started_at,
        last_updated=started_at,
    ))

    def _elapsed(since) -> str:
        secs = int((utc_now() - since).total_seconds())
        h, rem = divmod(secs, 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _make_display() -> Group:
        status_line = Text()
        status_line.append("● ", style=f"bold {ACCENT_PINK}")
        status_line.append("running", style=f"bold {ACCENT_PINK}")
        status_line.append("  ", style="")
        status_line.append(_elapsed(started_at), style=f"dim {ACCENT_YELLOW}")

        info = Table.grid(padding=(0, 2))
        info.add_column(style=f"dim {ACCENT_ORANGE}")
        info.add_column(style="white")
        info.add_row("PID",     str(os.getpid()))
        info.add_row("started", started_at.strftime("%Y-%m-%d %H:%M:%S"))
        info.add_row("transport", "stdio")

        config_snippet = Text()
        config_snippet.append('{ "mcpServers": { "mem": { "command": "mem", "args": ["serve"] } } }',
                               style=f"dim {ACCENT_YELLOW}")

        hint = Text.assemble(
            ("Claude Code  ", f"bold {ACCENT_ORANGE}"),
            ("~/.claude/settings.json\n", "dim"),
            ("", ""),
        )

        footer = Text.assemble(
            ("Ctrl+C", f"bold {ACCENT_YELLOW}"),
            (" to stop", "dim"),
        )

        return Group(
            Align.center(_build_logo()),
            Text(""),
            Align.center(Panel(
                Group(
                    Align.center(status_line),
                    Text(""),
                    info,
                    Text(""),
                    hint,
                    Align.center(config_snippet),
                    Text(""),
                    Align.center(footer),
                ),
                box=ROUNDED,
                border_style=ACCENT_PINK,
                title=Text("MCP server", style=f"bold {ACCENT_ORANGE}"),
                padding=(0, 2),
            )),
        )

    try:
        with Live(_make_display(), console=console, refresh_per_second=1) as live:
            while True:
                time.sleep(1)
                live.update(_make_display())
    except KeyboardInterrupt:
        pass
    finally:
        state_store.clear()
        console.print(Text.assemble(
            ("\n  MCP server stopped.\n", f"dim {ACCENT_CORAL}"),
        ))


@serve_app.callback(invoke_without_command=True)
def serve(
    ctx: typer.Context,
    autostart: bool = typer.Option(
        False,
        "--autostart",
        help="Install and enable an OS startup item so mem serve starts at login.",
    ),
    disable_autostart: bool = typer.Option(
        False,
        "--disable-autostart",
        help="Disable the OS startup item and remove the login entry.",
    ),
    background: bool = typer.Option(
        False,
        "--background",
        help="Run mem serve detached in the background and exit.",
    ),
    new_terminal: bool = typer.Option(
        False,
        "--new-terminal",
        help="Open mem serve in a new terminal window and exit.",
    ),
) -> None:
    """[bold #E93A7D]Start[/] the local [bold #F98C2B]MCP server[/] over stdio.

    Exposes memory and observability as MCP tools so agents can read and
    write project memories and inspect token usage programmatically.

    \b
    Register in Claude Code settings.json:
      {
        "mcpServers": {
          "mem": { "command": "mem", "args": ["serve"] }
        }
      }
    """
    import sys
    if ctx.invoked_subcommand is not None:
        selected_modes = [autostart, disable_autostart, background, new_terminal]
        if any(selected_modes):
            raise typer.BadParameter(
                "Choose only one of --autostart, --disable-autostart, --background, or --new-terminal."
            )
        return

    selected_modes = [autostart, disable_autostart, background, new_terminal]
    if sum(1 for mode in selected_modes if mode) > 1:
        raise typer.BadParameter(
            "Choose only one of --autostart, --disable-autostart, --background, or --new-terminal."
        )
    if not (autostart or disable_autostart) and _mcp_server_is_running():
        console.print(Panel.fit(
            "MCP server is already running. Stop it with `mem serve stop` before starting a new one.",
            border_style=ACCENT_ORANGE,
        ))
        raise typer.Exit(code=1)
    if autostart:
        if not is_supported_platform():
            console.print(Panel.fit(
                "Autostart is only available on macOS, Linux, and Windows.",
                border_style="red",
            ))
            raise typer.Exit(code=1)
        plist_path = install_launch_agent()
        console.print(_render_action_screen(_ActionResult(
            title="MCP autostart enabled",
            body=Panel.fit(
                Text.assemble(
                    ("LaunchAgent installed at ", "white"),
                    (str(plist_path), f"bold {ACCENT_YELLOW}"),
                    ("\nmem serve will start automatically when you log in.", "dim"),
                ),
                border_style=ACCENT_PINK,
            ),
            border_style=ACCENT_PINK,
        )))
        return
    if disable_autostart:
        if not is_supported_platform():
            console.print(Panel.fit(
                "Autostart is only available on macOS, Linux, and Windows.",
                border_style="red",
            ))
            raise typer.Exit(code=1)
        removed = remove_launch_agent()
        console.print(_render_action_screen(_ActionResult(
            title="MCP autostart disabled",
            body=Panel.fit(
                "LaunchAgent removed." if removed else "No LaunchAgent found.",
                border_style=ACCENT_YELLOW,
            ),
            border_style=ACCENT_CORAL if removed else ACCENT_YELLOW,
        )))
        return
    if background:
        log_path = _mcp_serve_log_path()
        process = start_hidden_mcp_server(stderr_log_path=log_path)
        if not _wait_for_mcp_server_running():
            trace = _tail_text(log_path)
            console.print(Panel.fit(
                Text.assemble(
                    ("MCP server failed to start.\n", "white"),
                    ("See log: ", "dim"),
                    (str(log_path), f"bold {ACCENT_YELLOW}"),
                    ("\n", ""),
                    (trace or "No error trace was captured.", "red"),
                ),
                border_style="red",
            ))
            raise typer.Exit(code=1)
        console.print(_render_action_screen(_ActionResult(
            title="MCP server started in background",
            body=Panel.fit(
                Text.assemble(
                    ("The MCP server is now running detached from this terminal.", "dim"),
                    ("\nUse ", "white"),
                    ("mem serve stop", f"bold {ACCENT_YELLOW}"),
                    (" to stop it.", "white"),
                ),
                border_style=ACCENT_PINK,
            ),
            border_style=ACCENT_PINK,
        )))
        return
    if new_terminal:
        start_new_terminal()
        if not _wait_for_mcp_server_running():
            console.print(Panel.fit(
                "MCP server failed to start.",
                border_style="red",
            ))
            raise typer.Exit(code=1)
        console.print(_render_action_screen(_ActionResult(
            title="MCP server opened in a new terminal",
            body=Panel.fit(
                Text.assemble(
                    ("A new terminal window was requested for ", "white"),
                    ("mem serve", f"bold {ACCENT_YELLOW}"),
                    (".", "white"),
                ),
                border_style=ACCENT_PINK,
            ),
            border_style=ACCENT_PINK,
        )))
        return
    if sys.stdin.isatty():
        _serve_tty()
    else:
        from .mcp.server import run as _run_mcp
        _run_mcp()


@serve_app.command(rich_help_panel=f"[bold {ACCENT_ORANGE}]Memory[/]")
def stop() -> None:
    """[bold #F25C5C]Stop[/] the local MCP server process."""
    result = _mcp_stop_action()
    console.print(_render_action_screen(result))


@app.command(rich_help_panel=f"[bold {ACCENT_ORANGE}]Memory[/]")
def setup() -> None:
    """Enable autostart and start the MCP server now on supported platforms."""
    if not is_supported_platform():
        console.print(Panel.fit(
            "Autostart setup is only available on macOS, Linux, and Windows.",
            border_style="red",
        ))
        raise typer.Exit(code=1)

    autostart_path = install_launch_agent()
    log_path = _mcp_serve_log_path()
    _process = start_hidden_mcp_server(stderr_log_path=log_path)
    if not _wait_for_mcp_server_running():
        trace = _tail_text(log_path)
        console.print(Panel.fit(
            Text.assemble(
                ("MCP setup enabled autostart, but the server failed to start.\n", "white"),
                ("See log: ", "dim"),
                (str(log_path), f"bold {ACCENT_YELLOW}"),
                ("\n", ""),
                (trace or "No error trace was captured.", "red"),
            ),
            border_style="red",
        ))
        raise typer.Exit(code=1)
    console.print(_render_action_screen(_ActionResult(
        title="MCP setup complete",
        body=Panel.fit(
            Text.assemble(
                ("Autostart enabled at ", "white"),
                (str(autostart_path), f"bold {ACCENT_YELLOW}"),
                ("\nThe MCP server is now running and will start automatically at login.", "dim"),
            ),
            border_style=ACCENT_PINK,
        ),
        border_style=ACCENT_PINK,
    )))


@app.command(rich_help_panel=f"[bold {ACCENT_ORANGE}]Memory[/]")
def adapters() -> None:
    """List available token source adapters and discovered plugins."""
    table = Table(expand=True, box=ROUNDED, border_style=ACCENT_PINK)
    table.add_column("Name", style=f"bold {ACCENT_YELLOW}", no_wrap=True)
    table.add_column("Kind", style=ACCENT_ORANGE, no_wrap=True)
    table.add_column("Source", style="white", ratio=2)

    table.add_row("jsonl", "built-in", "Local JSON/JSONL token files")

    plugins = discover_token_source_plugins()
    if plugins:
        for plugin in plugins:
            table.add_row(plugin.name, "plugin", plugin.entry_point)
    else:
        table.add_row("-", "plugin", "No external token source plugins discovered")

    console.print(_render_action_screen(_ActionResult(
        title="Token source adapters",
        body=table,
        border_style=ACCENT_PINK,
    )))


@app.command(rich_help_panel=f"[bold {ACCENT_YELLOW}]Other[/]")
def help() -> None:  # noqa: A001
    """Show all [bold #F7B500]available commands[/]."""
    import subprocess, sys
    subprocess.run([sys.argv[0], "--help"])


def main() -> None:
    import sys
    _bootstrap_env()
    if len(sys.argv) == 1:
        _run_menu()
    else:
        app()


if __name__ == "__main__":
    main()
