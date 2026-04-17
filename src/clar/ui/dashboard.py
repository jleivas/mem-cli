from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable, Literal

from rich.align import Align
from rich.box import ROUNDED
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..models import AgentStatus
from ..storage.dashboard_history import DashboardSnapshotMeta
from ..storage.dashboard_history import DashboardSnapshotStore
from ..config import clear_configured_jsonl_files


@dataclass(slots=True)
class DashboardOptions:
    title: str = "mem dashboard"
    refresh_per_second: float = 2.0


DashboardViewMode = Literal["summary", "detail", "both"]

ACCENT_PINK = "#E93A7D"
ACCENT_ORANGE = "#F98C2B"
ACCENT_YELLOW = "#F7B500"

DASHBOARD_ACTIONS = (
    ("1", "Save snapshot", "Save the currently visible dashboard to local history."),
    ("2", "Open history", "Browse saved snapshots and load one back into the dashboard."),
    ("3", "Reset live data", "Clear the tracker and truncate the watched JSONL files."),
    ("0", "Back to main menu", "Return to the main CLI menu."),
)

HISTORY_RECORD_ACTIONS = (
    ("1", "Delete record", "Remove this snapshot from local history."),
    ("0", "Back to history", "Return to the snapshot list."),
)


def _collect_rows(snapshot: Iterable[AgentStatus]) -> list[AgentStatus]:
    return list(snapshot)


def _format_timestamp(value: datetime | str | None) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            value = datetime.fromisoformat(normalized)
        except ValueError:
            return value
    if value.tzinfo is None:
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return value.astimezone().strftime("%Y-%m-%d %H:%M:%S")


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
    summary.add_row("Last update", _format_timestamp(last_update))

    title = Text("Overview", style=f"bold {ACCENT_YELLOW}")
    return Panel(summary, title=title, border_style=ACCENT_PINK if running else ACCENT_ORANGE)


def build_detail_table(snapshot: Iterable[AgentStatus]) -> Table:
    table = Table(title="Agent Token Usage", expand=True, show_lines=False)
    table.add_column("Agent", style=ACCENT_PINK, no_wrap=True)
    table.add_column("Input", justify="right", style=ACCENT_ORANGE)
    table.add_column("Output", justify="right", style=ACCENT_ORANGE)
    table.add_column("Total", justify="right", style=ACCENT_YELLOW)
    table.add_column("Avg/min", justify="right", style=ACCENT_YELLOW)
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
            _format_timestamp(item.last_updated),
            item.source,
            item.state,
        )
    return table


def _build_footer_actions() -> Table:
    table = Table.grid(expand=True)
    for _ in DASHBOARD_ACTIONS:
        table.add_column(ratio=1)

    cells = []
    for key, title, description in DASHBOARD_ACTIONS:
        key_style = f"bold {ACCENT_YELLOW}" if key == "0" else f"bold {ACCENT_ORANGE}"
        cells.append(
            Panel(
                Group(
                    Align.center(Text(key, style=key_style)),
                    Align.center(Text(title, style="bold white")),
                    Align.center(Text(description, style="dim")),
                ),
                border_style=ACCENT_ORANGE if key != "0" else ACCENT_YELLOW,
                box=ROUNDED,
                padding=(0, 1),
            )
        )

    table.add_row(*cells)
    return table


def _build_history_record_actions() -> Table:
    table = Table.grid(expand=True)
    for _ in HISTORY_RECORD_ACTIONS:
        table.add_column(ratio=1)

    cells = []
    for key, title, description in HISTORY_RECORD_ACTIONS:
        key_style = f"bold {ACCENT_YELLOW}" if key == "0" else f"bold {ACCENT_ORANGE}"
        cells.append(
            Panel(
                Group(
                    Align.center(Text(key, style=key_style)),
                    Align.center(Text(title, style="bold white")),
                    Align.center(Text(description, style="dim")),
                ),
                border_style=ACCENT_ORANGE if key != "0" else ACCENT_YELLOW,
                box=ROUNDED,
                padding=(0, 1),
            )
        )

    table.add_row(*cells)
    return table


def _build_footer_panel(message: str, mode_label: str) -> Panel:
    banner = Text()
    banner.append("Mode: ", style="dim")
    banner.append(mode_label, style=f"bold {ACCENT_YELLOW}")
    banner.append("  ")
    banner.append(message, style="white")

    return Panel(
        Group(
            Align.center(banner),
            _build_footer_actions(),
        ),
        border_style=ACCENT_ORANGE,
        padding=(0, 1),
    )


def _build_live_footer_panel(message: str) -> Panel:
    return Panel(
        Align.center(Text(message, style=f"bold {ACCENT_YELLOW}")),
        border_style=ACCENT_ORANGE,
        padding=(0, 1),
    )


def _normalize_choice(raw: str) -> str:
    value = raw.strip().lower()
    aliases = {
        "snapshot": "1",
        "save": "1",
        "history": "2",
        "browse": "2",
        "open": "2",
        "reset": "3",
        "clear": "3",
        "back": "0",
        "menu": "0",
        "quit": "0",
        "exit": "0",
        "q": "0",
    }
    return aliases.get(value, value)


def _prompt_for_choice(console: Console, allowed: set[str], prompt: str = "[bold #F7B500]>[/bold #F7B500] ") -> str:
    while True:
        try:
            choice = _normalize_choice(console.input(prompt))
        except (EOFError, KeyboardInterrupt):
            return "0"
        if choice in allowed:
            return choice


def _build_history_panel(entries: list[DashboardSnapshotMeta]) -> Panel:
    table = Table(title="Saved Snapshots", expand=True)
    table.add_column("#", style=ACCENT_YELLOW, justify="right", no_wrap=True)
    table.add_column("Created", style="white", no_wrap=True)
    table.add_column("Rows", style="white", justify="right", no_wrap=True)
    table.add_column("Source", style="white", no_wrap=True)
    table.add_column("File", style="white", no_wrap=True)

    if not entries:
        table.add_row("-", "-", "-", "-", "No saved snapshots found.")
    else:
        for index, entry in enumerate(entries, start=1):
            table.add_row(
                str(index),
                _format_timestamp(entry.created_at),
                str(entry.rows),
                entry.source,
                entry.path.name,
            )

    caption = "Enter a number to load a snapshot. 0. Back to dashboard."
    return Panel(table, title=Text("History", style=f"bold {ACCENT_PINK}"), subtitle=caption, border_style=ACCENT_ORANGE)


def _build_history_footer_panel() -> Panel:
    return Panel(
        Align.center(Text("0. Back to dashboard", style=f"bold {ACCENT_YELLOW}")),
        border_style=ACCENT_ORANGE,
        padding=(0, 1),
    )


def _build_history_record_footer_panel() -> Panel:
    return Panel(
        Group(
            Align.center(Text("Saved snapshot", style=f"bold {ACCENT_PINK}")),
            _build_history_record_actions(),
        ),
        border_style=ACCENT_ORANGE,
        padding=(0, 1),
    )


def _render_history_record(snapshot: Iterable[AgentStatus], source_path: Path | None) -> Panel:
    body = _render_body(snapshot, running=False, view="both")
    title = Text("History record", style=f"bold {ACCENT_PINK}")
    if source_path is not None:
        title.append("\n")
        title.append(source_path.name, style=f"bold {ACCENT_YELLOW}")
    return Panel(body.renderable, title=title, border_style=ACCENT_ORANGE)


def _render_body(snapshot: Iterable[AgentStatus], running: bool, view: DashboardViewMode) -> Panel:
    summary_panel = build_summary_panel(snapshot, running)
    detail_table = build_detail_table(snapshot)
    header = Text()
    header.append("mem", style=f"bold {ACCENT_PINK}")
    header.append("\n")
    header.append(f"Service: {'running' if running else 'stopped'}", style="green" if running else "yellow")

    if view == "summary":
        return Panel(summary_panel.renderable, title=header, border_style=ACCENT_PINK if running else ACCENT_ORANGE)
    if view == "detail":
        return Panel(detail_table, title=header, border_style=ACCENT_PINK if running else ACCENT_ORANGE)
    return Panel(Group(summary_panel, detail_table), title=header, border_style=ACCENT_PINK if running else ACCENT_ORANGE)


def render_dashboard(
    snapshot: Iterable[AgentStatus],
    running: bool,
    title: str = "mem",
    view: DashboardViewMode = "both",
    mode_label: str = "live",
    footer_message: str = "Choose an action below.",
    show_actions: bool = True,
) -> Group:
    body = _render_body(snapshot, running, view)
    footer = _build_footer_panel(footer_message, mode_label) if show_actions else _build_live_footer_panel(footer_message)
    return Group(body, footer)


def _choose_history_entry(
    console: Console,
    store: DashboardSnapshotStore,
) -> DashboardSnapshotMeta | None:
    entries = store.list()
    console.clear()
    console.print(Group(_build_history_panel(entries), _build_history_footer_panel()))

    if not entries:
        _prompt_for_choice(console, {"0"})
        return None

    choice = _prompt_for_choice(console, {str(i) for i in range(1, len(entries) + 1)} | {"0"})
    if choice == "0":
        return None

    index = int(choice) - 1
    if index < 0 or index >= len(entries):
        return None

    return entries[index]


def live_dashboard(
    snapshot_provider: Callable[[], Iterable[AgentStatus]],
    running_provider: Callable[[], bool],
    reset_provider: Callable[[], None] | None = None,
    refresh_per_second: float = 2.0,
    view: DashboardViewMode = "both",
    history_store: DashboardSnapshotStore | None = None,
) -> None:
    console = Console()
    store = history_store or DashboardSnapshotStore()
    pinned_snapshot: list[AgentStatus] | None = None
    pinned_history_path: Path | None = None
    footer_message = "Press Ctrl+C to pause real-time updates."
    active_snapshot = _collect_rows(snapshot_provider())
    renderable = render_dashboard(
        active_snapshot,
        running_provider(),
        view=view,
        mode_label="live",
        footer_message=footer_message,
        show_actions=False,
    )

    try:
        with Live(renderable, console=console, refresh_per_second=refresh_per_second, screen=True, auto_refresh=False) as live:
            while True:
                active_snapshot = _collect_rows(snapshot_provider())
                renderable = render_dashboard(
                    active_snapshot,
                    running_provider(),
                    view=view,
                    mode_label="live",
                    footer_message="Press Ctrl+C to pause real-time updates.",
                    show_actions=False,
                )
                live.update(renderable)
                live.refresh()
                time.sleep(max(0.1, 1.0 / refresh_per_second))
    except KeyboardInterrupt:
        pass

    footer_message = "Choose an action below."
    mode: Literal["live", "history_list", "history_record"] = "live"

    while True:
        console.clear()
        if mode == "live":
            active_snapshot = _collect_rows(snapshot_provider())
            console.print(
                render_dashboard(
                    active_snapshot,
                    running_provider(),
                    view=view,
                    mode_label="paused",
                    footer_message=footer_message,
                    show_actions=True,
                )
            )
            choice = _prompt_for_choice(console, {"1", "2", "3", "0"}, prompt="[bold #F7B500]>[/bold #F7B500] ")

            if choice == "1":
                saved_path = store.save(active_snapshot, source="live")
                footer_message = f"Snapshot saved: {saved_path.name}"
            elif choice == "2":
                mode = "history_list"
                footer_message = "Choose a saved snapshot."
            elif choice == "3":
                if reset_provider is not None:
                    reset_provider()
                clear_configured_jsonl_files()
                footer_message = "Live data reset."
            elif choice == "0":
                return
        elif mode == "history_list":
            entries = store.list()
            console.print(Group(_build_history_panel(entries), _build_history_footer_panel()))
            selected_entry = _choose_history_entry(console, store)
            if selected_entry is None:
                mode = "live"
                footer_message = "Choose an action below."
            else:
                pinned_history_path = selected_entry.path
                pinned_snapshot = store.load(selected_entry.path)
                mode = "history_record"
                footer_message = "History record loaded."
        else:
            console.print(Group(_render_history_record(pinned_snapshot or [], pinned_history_path), _build_history_record_footer_panel()))
            choice = _prompt_for_choice(console, {"1", "0"}, prompt="[bold #F7B500]>[/bold #F7B500] ")
            if choice == "1" and pinned_history_path is not None:
                store.delete(pinned_history_path)
                pinned_history_path = None
                pinned_snapshot = None
                mode = "history_list"
                footer_message = "Snapshot deleted."
            elif choice == "0":
                mode = "history_list"
                footer_message = "Choose a saved snapshot."
