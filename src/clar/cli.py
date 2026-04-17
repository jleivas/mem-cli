from __future__ import annotations

from typing import cast

import typer
from rich.console import Console, Group
from rich.align import Align
from rich.box import ROUNDED
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from . import APP_VERSION
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
    table = Table.grid(expand=True, padding=(0, 1))
    table.add_column(no_wrap=True)
    table.add_column(ratio=1)
    table.add_column(justify="right", ratio=2)

    for key, title, description in MENU_ITEMS:
        key_style = f"bold {ACCENT_YELLOW}" if key == "0" else f"bold {ACCENT_ORANGE}"
        title_style = f"bold {ACCENT_PINK}" if key in {"1", "3"} else "white"
        table.add_row(
            Text(key, style=key_style),
            Text(title, style=title_style),
            Text(description, style="dim"),
        )
    return table


def _print_menu() -> None:
    console.clear()
    console.print(Panel.fit(f"[bold {ACCENT_PINK}]{CLI_NAME}[/bold {ACCENT_PINK}]  [dim]v{APP_VERSION}[/dim]", border_style=ACCENT_ORANGE))
    console.print()
    console.print(_build_menu_panel())
    console.print()
    console.print(Panel(_build_menu_options(), box=ROUNDED, border_style=ACCENT_ORANGE, title="Actions"))
    console.print()
    console.print(Panel.fit("[dim]Enter a number to continue.[/dim]", border_style=ACCENT_YELLOW))


def _run_menu() -> None:
    while True:
        _print_menu()
        try:
            choice = console.input("[bold #F7B500]>[/bold #F7B500] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            return

        if choice == "1":
            start()
        elif choice == "2":
            stop()
        elif choice == "3":
            _launch_dashboard()
            # blocks until Ctrl-C; loop back to menu after exit
        elif choice == "4":
            status()
        elif choice == "0" or choice.lower() in {"q", "quit", "exit"}:
            return
        else:
            console.print(f"[yellow]Unknown option: {choice!r}. Enter 0-4.[/yellow]")




@app.command()
def start() -> None:
    """Start the local monitor."""
    try:
        state = _registry().start()
    except RuntimeError as exc:
        console.print(Panel.fit(f"[red]{exc}[/red]", title=f"[bold #E93A7D]{CLI_NAME}[/bold #E93A7D]"))
        raise typer.Exit(code=1) from exc

    console.print(
        Panel.fit(
            f"[green]Started[/green]\nPID: {state.pid}\nState: {get_runtime_state_path()}",
            title=f"[bold #E93A7D]{CLI_NAME}[/bold #E93A7D]",
        )
    )


@app.command()
def stop() -> None:
    """Stop the local monitor."""
    state = _registry().stop()
    if state is None:
        console.print(Panel.fit("[yellow]No running monitor found.[/yellow]", title=f"[bold #E93A7D]{CLI_NAME}[/bold #E93A7D]"))
        return

    console.print(Panel.fit("[green]Stopped[/green]", title=f"[bold #E93A7D]{CLI_NAME}[/bold #E93A7D]"))


@app.command()
def status() -> None:
    """Show monitor status."""
    state = _registry().load_state()
    table = Table(title="Runtime Status", expand=True)
    table.add_column("Field", style="#F98C2B")
    table.add_column("Value", style="white")

    if not state:
        table.add_row("Service", "stopped")
        table.add_row("State file", str(get_runtime_state_path()))
        console.print(table)
        return

    table.add_row("Service", "running" if state.running else "stopped")
    table.add_row("PID", str(state.pid) if state.pid else "-")
    table.add_row("Started", state.started_at.isoformat() if state.started_at else "-")
    table.add_row("Updated", state.last_updated.isoformat() if state.last_updated else "-")
    table.add_row("State file", str(get_runtime_state_path()))
    console.print(table)


def _launch_dashboard(view: str = "both") -> None:
    service = build_monitor_service()
    service.start()

    def snapshot_provider():
        return service.snapshot()

    def running_provider() -> bool:
        return service.is_running()

    try:
        live_dashboard(snapshot_provider, running_provider, view=cast(DashboardViewMode, view))
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
    if len(sys.argv) == 1:
        _run_menu()
    else:
        app()


if __name__ == "__main__":
    main()
