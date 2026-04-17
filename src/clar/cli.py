from __future__ import annotations

from dataclasses import dataclass
import os
from typing import cast

import typer
from rich.align import Align
from rich.box import ROUNDED
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from . import APP_VERSION
from .config import get_default_claude_jsonl_path
from .config import get_default_codex_jsonl_path
from .config import get_runtime_state_path
from .app import build_monitor_service
from .services.process_registry import ProcessRegistry
from .storage.runtime_state import RuntimeStateStore
from .ui.dashboard import live_dashboard
from .ui.dashboard import DashboardViewMode

app = typer.Typer(add_completion=False, help="Mem CLI for AI agents — local token observability and memory.")
console = Console()
CLI_NAME = "mem"
ACCENT_PINK = "#E93A7D"
ACCENT_ORANGE = "#F98C2B"
ACCENT_YELLOW = "#F7B500"
MENU_ITEMS = (
    ("1", "Start monitor", "Launch the background watcher."),
    ("2", "Stop monitor", "Shut down the watcher cleanly."),
    ("3", "Dashboard", "Open the live usage screen."),
    ("4", "Status", "Inspect the runtime state."),
    ("0", "Quit", "Close the interactive menu."),
)


@dataclass(slots=True)
class _ActionResult:
    title: str
    body: Panel | Table
    border_style: str


def _bootstrap_env() -> None:
    os.environ.setdefault("MEM_CLAUDE_JSONL", str(get_default_claude_jsonl_path()))
    os.environ.setdefault("MEM_CODEX_JSONL", str(get_default_codex_jsonl_path()))


@app.callback(invoke_without_command=True)
def _bootstrap() -> None:
    _bootstrap_env()


def _registry() -> ProcessRegistry:
    return ProcessRegistry(RuntimeStateStore(get_runtime_state_path()))


def _build_brand_line() -> Text:
    t = Text()
    t.append("mem", style=f"bold {ACCENT_PINK}")
    t.append(f"  v{APP_VERSION}", style=ACCENT_YELLOW)
    t.append("  ·  ", style="dim")
    t.append("Token observability & agent memory", style="dim white")
    return t


def _build_menu_options() -> Table:
    table = Table.grid(padding=(0, 1))
    for _ in MENU_ITEMS:
        table.add_column()

    cells = []
    for key, title, _ in MENU_ITEMS:
        is_quit = key == "0"
        key_style = f"bold {ACCENT_YELLOW}" if is_quit else f"bold {ACCENT_ORANGE}"
        title_style = f"bold {ACCENT_PINK}" if key in {"1", "3"} else ("dim white" if is_quit else "white")
        label = Text()
        label.append(f" {key} ", style=f"reverse {key_style}")
        label.append(f" {title}", style=title_style)
        cells.append(Panel(
            Align.center(label),
            box=ROUNDED,
            border_style=ACCENT_YELLOW if is_quit else ACCENT_ORANGE,
            padding=(0, 0),
        ))

    table.add_row(*cells)
    return table



def _render_footer(message: str = "Use the number keys to navigate.") -> Panel:
    line = Text()
    line.append("1", style=f"bold {ACCENT_ORANGE}")
    line.append(" Start  ")
    line.append("2", style=f"bold {ACCENT_ORANGE}")
    line.append(" Stop  ")
    line.append("3", style=f"bold {ACCENT_ORANGE}")
    line.append(" Dashboard  ")
    line.append("4", style=f"bold {ACCENT_ORANGE}")
    line.append(" Status  ")
    line.append("0", style=f"bold {ACCENT_YELLOW}")
    line.append(" Quit")
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
            _build_brand_line(),
            box=ROUNDED,
            border_style=ACCENT_PINK,
            padding=(0, 1),
        ),
        Text(""),
        Panel(
            _build_menu_options(),
            box=ROUNDED,
            border_style=ACCENT_ORANGE,
            padding=(0, 1),
        ),
        Text(""),
        _render_footer(),
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


def _render_action_layout(result: _ActionResult, message: str = "Press Enter to return to the menu.") -> Group:
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
    return Group(header, body, _render_footer(message))


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
    table.add_row(Text("PID", style=f"bold {ACCENT_ORANGE}"), Text(str(state.pid), style="white"))
    return _ActionResult(title="Monitor stopped", body=table, border_style=ACCENT_ORANGE)


def _status_action() -> _ActionResult:
    state = _registry().load_state()
    table = Table(title="Runtime Status", expand=True)
    table.add_column("Field", style=ACCENT_ORANGE)
    table.add_column("Value", style="white")

    if not state:
        table.add_row("Service", "stopped")
        table.add_row("State file", str(get_runtime_state_path()))
        return _ActionResult(title="Status", body=table, border_style=ACCENT_YELLOW)

    table.add_row("Service", "running" if state.running else "stopped")
    table.add_row("PID", str(state.pid) if state.pid else "-")
    table.add_row("Started", state.started_at.isoformat() if state.started_at else "-")
    table.add_row("Updated", state.last_updated.isoformat() if state.last_updated else "-")
    table.add_row("State file", str(get_runtime_state_path()))
    return _ActionResult(title="Status", body=table, border_style=ACCENT_PINK)


def _run_menu() -> None:
    while True:
        console.clear()
        console.print(_render_home_screen())
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
        elif choice == "0" or choice.lower() in {"q", "quit", "exit"}:
            console.clear()
            return
        else:
            console.clear()
            console.print(_render_action_screen(_ActionResult(
                title="Unknown option",
                body=Panel.fit(f"Unknown option: {choice!r}. Enter 0-4.", border_style="red"),
                border_style="red",
            )))
            _pause_for_continue()




@app.command()
def start() -> None:
    """Start the local monitor."""
    result = _start_monitor_action()
    console.print(_render_action_screen(result))
    if result.border_style == "red":
        raise typer.Exit(code=1)


@app.command()
def stop() -> None:
    """Stop the local monitor."""
    result = _stop_monitor_action()
    console.print(_render_action_screen(result))


@app.command()
def status() -> None:
    """Show monitor status."""
    result = _status_action()
    console.print(_render_action_screen(result))


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


@app.command()
def dashboard(
    view: str = typer.Option(
        "both",
        "--view",
        "-v",
        help="Dashboard view mode: summary, detail, or both.",
        case_sensitive=False,
    ),
) -> None:
    """Open a live token dashboard in the terminal."""
    normalized_view = view.lower()
    if normalized_view not in {"summary", "detail", "both"}:
        raise typer.BadParameter("view must be one of: summary, detail, both")
    _launch_dashboard(normalized_view)


@app.command()
def version() -> None:
    """Print the current version."""
    console.print(APP_VERSION)


def main() -> None:
    import sys
    _bootstrap_env()
    if len(sys.argv) == 1:
        _run_menu()
    else:
        app()


if __name__ == "__main__":
    main()
