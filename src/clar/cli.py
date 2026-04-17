from __future__ import annotations

from typing import cast

import typer
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
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


def _registry() -> ProcessRegistry:
    return ProcessRegistry(RuntimeStateStore(get_runtime_state_path()))


def _print_menu() -> None:
    console.print()
    console.print(Rule(f"[bold #E93A7D]{CLI_NAME}[/bold #E93A7D]  [dim]v{APP_VERSION}[/dim]"))
    console.print()
    menu = Table.grid(padding=(0, 2))
    menu.add_column(style="bold #F98C2B", justify="right")
    menu.add_column(style="white")
    menu.add_row("1", "Start monitor")
    menu.add_row("2", "Stop monitor")
    menu.add_row("3", "Dashboard")
    menu.add_row("4", "Status")
    menu.add_row("0", "Quit")
    console.print(menu)
    console.print()


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
