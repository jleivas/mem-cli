from __future__ import annotations

from dataclasses import dataclass
import os
from typing import cast

import typer
from rich.console import Console, Group
from rich.align import Align
from rich.box import ROUNDED
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.padding import Padding
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


def _brand_wave() -> Text:
    wave = Text()
    wave.append("╭────╮    ", style=ACCENT_PINK)
    wave.append("╭──╮", style=ACCENT_ORANGE)
    wave.append("    ╭──╮        ", style=ACCENT_YELLOW)
    wave.append("╭──", style=ACCENT_YELLOW)
    return wave


def _build_menu_panel() -> Panel:
    header = Text()
    header.append("mem", style=f"bold {ACCENT_PINK}")
    header.append("  ")
    header.append("CLI", style=f"bold {ACCENT_YELLOW}")
    header.append("  ")
    header.append(f"v{APP_VERSION}", style=f"bold {ACCENT_YELLOW}")

    subtitle = Text("Local token observability & agent memory", style="dim white")
    wave = Align.center(_brand_wave())

    return Panel(
        Align.center(
            Group(
                Align.center(header),
                Align.center(subtitle),
                wave,
            )
        ),
        box=ROUNDED,
        border_style=ACCENT_PINK,
        padding=(1, 2),
    )


def _build_menu_options() -> Table:
    table = Table.grid(expand=True)
    for _ in MENU_ITEMS:
        table.add_column(ratio=1)

    cells = []
    for key, title, description in MENU_ITEMS:
        key_style = f"bold {ACCENT_YELLOW}" if key == "0" else f"bold {ACCENT_ORANGE}"
        title_style = f"bold {ACCENT_PINK}" if key in {"1", "3"} else "white"
        cells.append(
            Panel(
                Group(
                    Align.center(Text(key, style=key_style)),
                    Align.center(Text(title, style=title_style)),
                    Align.center(Text(description, style="dim")),
                ),
                box=ROUNDED,
                border_style=ACCENT_ORANGE if key != "0" else ACCENT_YELLOW,
                padding=(1, 1),
            )
        )

    table.add_row(*cells)
    return table


def _make_shell(header: Panel | None, body: Panel | Table | Group, footer: Panel) -> Layout:
    layout = Layout(name="root")
    if header is None:
        layout.split_column(
            Layout(body, name="body", ratio=1),
            Layout(footer, name="footer", size=3),
        )
    else:
        layout.split_column(
            Layout(header, name="header", size=5),
            Layout(body, name="body", ratio=1),
            Layout(footer, name="footer", size=3),
        )
    return layout


def _render_footer(message: str = "Use the number keys to navigate.") -> Panel:
    footer = Text()
    footer.append("1", style=f"bold {ACCENT_ORANGE}")
    footer.append(" Start  ")
    footer.append("2", style=f"bold {ACCENT_ORANGE}")
    footer.append(" Stop  ")
    footer.append("3", style=f"bold {ACCENT_ORANGE}")
    footer.append(" Dashboard  ")
    footer.append("4", style=f"bold {ACCENT_ORANGE}")
    footer.append(" Status  ")
    footer.append("0", style=f"bold {ACCENT_YELLOW}")
    footer.append(" Quit", style="white")

    return Panel(
        Group(
            Align.center(Text(message, style="bold white")),
            Align.center(footer),
        ),
        box=ROUNDED,
        border_style=ACCENT_YELLOW,
        padding=(0, 1),
    )


def _render_home_screen() -> Panel:
    body = Group(
        _build_menu_panel(),
        Panel(_build_menu_options(), box=ROUNDED, border_style=ACCENT_ORANGE, title="Actions"),
        Panel.fit("[dim]Enter a number to continue.[/dim]", border_style=ACCENT_YELLOW),
    )
    return Padding(Panel(
        body,
        box=ROUNDED,
        border_style=ACCENT_PINK,
        padding=(1, 2),
    ), (1, 0, 0, 0))


def _render_home_layout() -> Layout:
    body = Panel(
        Group(
            Align.center(_build_menu_panel()),
            Align.center(_build_menu_options()),
        ),
        box=ROUNDED,
        border_style=ACCENT_PINK,
        padding=(0, 1),
    )
    return Padding(_make_shell(None, body, _render_footer()), (1, 0, 0, 0))


def _render_action_screen(result: _ActionResult) -> Panel:
    title = Text(result.title, style=f"bold {ACCENT_PINK}")
    return Padding(Panel(
        result.body,
        box=ROUNDED,
        border_style=result.border_style,
        title=title,
        padding=(1, 2),
    ), (1, 0, 0, 0))


def _render_action_layout(result: _ActionResult, message: str = "Press Enter to return to the menu.") -> Layout:
    header = Panel.fit(
        Text.assemble(
            ("mem", f"bold {ACCENT_PINK}"),
            ("  ", "white"),
            (result.title, f"bold {ACCENT_YELLOW}"),
        ),
        box=ROUNDED,
        border_style=result.border_style,
        padding=(0, 2),
    )
    body = Panel(
        result.body,
        box=ROUNDED,
        border_style=result.border_style,
        padding=(1, 2),
        title=Text(result.title, style=f"bold {ACCENT_PINK}"),
    )
    return Padding(_make_shell(header, body, _render_footer(message)), (1, 0, 0, 0))


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
    with Live(_render_home_layout(), console=console, screen=True, auto_refresh=False, refresh_per_second=30) as live:
        while True:
            live.update(_render_home_layout())
            live.refresh()
            try:
                choice = console.input("[bold #F7B500]>[/bold #F7B500] ").strip()
            except (EOFError, KeyboardInterrupt):
                return

            if choice == "1":
                result = _start_monitor_action()
                live.update(_render_action_layout(result))
                live.refresh()
                _pause_for_continue()
            elif choice == "2":
                result = _stop_monitor_action()
                live.update(_render_action_layout(result))
                live.refresh()
                _pause_for_continue()
            elif choice == "3":
                live.update(_render_action_layout(_ActionResult(
                    title="Dashboard",
                    body=Panel.fit("Launching dashboard...", border_style=ACCENT_YELLOW),
                    border_style=ACCENT_YELLOW,
                )))
                live.refresh()
                _launch_dashboard()
            elif choice == "4":
                result = _status_action()
                live.update(_render_action_layout(result))
                live.refresh()
                _pause_for_continue()
            elif choice == "0" or choice.lower() in {"q", "quit", "exit"}:
                console.clear()
                return
            else:
                live.update(_render_action_layout(_ActionResult(
                    title="Unknown option",
                    body=Panel.fit(f"Unknown option: {choice!r}. Enter 0-4.", border_style="red"),
                    border_style="red",
                )))
                live.refresh()
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
