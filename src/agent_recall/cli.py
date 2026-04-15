from __future__ import annotations

from typing import cast

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import APP_VERSION
from .config import get_runtime_state_path
from .app import build_monitor_service
from .services.process_registry import ProcessRegistry
from .storage.runtime_state import RuntimeStateStore
from .ui.dashboard import live_dashboard
from .ui.dashboard import DashboardViewMode

app = typer.Typer(add_completion=False, help="Local agent memory and token observability.")
console = Console()


def _registry() -> ProcessRegistry:
    return ProcessRegistry(RuntimeStateStore(get_runtime_state_path()))


@app.command()
def start() -> None:
    """Start the local monitor."""
    try:
        state = _registry().start()
    except RuntimeError as exc:
        console.print(Panel.fit(f"[red]{exc}[/red]", title="agent-recall"))
        raise typer.Exit(code=1) from exc

    console.print(
        Panel.fit(
            f"[green]Started[/green]\nPID: {state.pid}\nState: {get_runtime_state_path()}",
            title="agent-recall",
        )
    )


@app.command()
def stop() -> None:
    """Stop the local monitor."""
    state = _registry().stop()
    if state is None:
        console.print(Panel.fit("[yellow]No running monitor found.[/yellow]", title="agent-recall"))
        return

    console.print(Panel.fit("[green]Stopped[/green]", title="agent-recall"))


@app.command()
def status() -> None:
    """Show monitor status."""
    state = _registry().load_state()
    table = Table(title="Runtime Status", expand=True)
    table.add_column("Field", style="cyan")
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

    service = build_monitor_service()
    service.start()

    def snapshot_provider():
        return service.snapshot()

    def running_provider() -> bool:
        return service.is_running()

    try:
        live_dashboard(snapshot_provider, running_provider, view=cast(DashboardViewMode, normalized_view))
    except KeyboardInterrupt:
        pass
    finally:
        service.stop()


@app.command()
def version() -> None:
    """Print the current version."""
    console.print(APP_VERSION)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
