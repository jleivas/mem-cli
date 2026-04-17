from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Iterable, Literal

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..models import AgentStatus


@dataclass(slots=True)
class DashboardOptions:
    title: str = "mem dashboard"
    refresh_per_second: float = 2.0


DashboardViewMode = Literal["summary", "detail", "both"]


def _collect_rows(snapshot: Iterable[AgentStatus]) -> list[AgentStatus]:
    return list(snapshot)


def build_summary_panel(snapshot: Iterable[AgentStatus], running: bool) -> Panel:
    rows = _collect_rows(snapshot)
    total_agents = len(rows)
    total_input = sum(item.input_tokens for item in rows)
    total_output = sum(item.output_tokens for item in rows)
    total_tokens = sum(item.total_tokens for item in rows)
    top_agent = max(rows, key=lambda item: item.total_tokens).agent_name if rows else "-"
    last_update = max((item.last_updated for item in rows if item.last_updated), default="-")

    summary = Table.grid(expand=True)
    summary.add_column(ratio=1)
    summary.add_column(ratio=1)
    summary.add_row("Service", "running" if running else "stopped")
    summary.add_row("Agents", str(total_agents))
    summary.add_row("Input tokens", str(total_input))
    summary.add_row("Output tokens", str(total_output))
    summary.add_row("Total tokens", str(total_tokens))
    summary.add_row("Top agent", top_agent)
    summary.add_row("Last update", last_update)

    title = Text("Overview", style="bold #F7B500")
    return Panel(summary, title=title, border_style="#E93A7D" if running else "#F98C2B")


def build_detail_table(snapshot: Iterable[AgentStatus]) -> Table:
    table = Table(title="Agent Token Usage", expand=True, show_lines=False)
    table.add_column("Agent", style="#E93A7D", no_wrap=True)
    table.add_column("Input", justify="right", style="#F98C2B")
    table.add_column("Output", justify="right", style="#F98C2B")
    table.add_column("Total", justify="right", style="#F7B500")
    table.add_column("Avg/min", justify="right", style="#F7B500")
    table.add_column("Last Update", no_wrap=True)
    table.add_column("Source", no_wrap=True)
    table.add_column("State", no_wrap=True)

    rows = _collect_rows(snapshot)
    if not rows:
        table.add_row("-", "0", "0", "0", "0.0", "-", "-", "waiting")
        return table

    for item in rows:
        table.add_row(
            item.agent_name,
            str(item.input_tokens),
            str(item.output_tokens),
            str(item.total_tokens),
            f"{item.average_tokens_per_minute:.1f}",
            item.last_updated or "-",
            item.source,
            item.state,
        )
    return table


def render_dashboard(
    snapshot: Iterable[AgentStatus],
    running: bool,
    title: str = "mem",
    view: DashboardViewMode = "both",
) -> Panel | Group:
    summary_panel = build_summary_panel(snapshot, running)
    detail_table = build_detail_table(snapshot)
    header = Text()
    header.append(f"{title}\n", style="bold #E93A7D")
    header.append(f"Service: {'running' if running else 'stopped'}", style="green" if running else "yellow")
    if view == "summary":
        return Panel(summary_panel.renderable, title=header)
    if view == "detail":
        return Panel(detail_table, title=header)
    return Panel(Group(summary_panel, detail_table), title=header)


def live_dashboard(
    snapshot_provider,
    running_provider,
    refresh_per_second: float = 2.0,
    view: DashboardViewMode = "both",
) -> None:
    console = Console()
    with Live(
        render_dashboard(snapshot_provider(), running_provider(), view=view),
        console=console,
        refresh_per_second=refresh_per_second,
        screen=True,
    ) as live:
        while True:
            live.update(render_dashboard(snapshot_provider(), running_provider(), view=view))
            live.refresh()
            time.sleep(max(0.1, 1.0 / refresh_per_second))
