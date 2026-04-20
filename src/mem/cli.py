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
from .services.memory_service import MemoryService
from .services.prompt_service import (
    AgentResult,
    build_prompt,
    run_agent,
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
    help="Mem CLI for AI agents — local token observability and memory.",
)
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




@app.command(rich_help_panel="Monitor")
def start() -> None:
    """Start the local monitor."""
    result = _start_monitor_action()
    console.print(_render_action_screen(result))
    if result.border_style == "red":
        raise typer.Exit(code=1)


@app.command(rich_help_panel="Monitor")
def stop() -> None:
    """Stop the local monitor."""
    result = _stop_monitor_action()
    console.print(_render_action_screen(result))


@app.command(rich_help_panel="Monitor")
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


@app.command(rich_help_panel="Monitor")
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


@app.command(rich_help_panel="Monitor")
def version() -> None:
    """Print the current version."""
    console.print(APP_VERSION)


# ---------------------------------------------------------------------------
# Memory commands
# ---------------------------------------------------------------------------

def _memory_service() -> MemoryService:
    return MemoryService()


def _render_memory_table(memories: list) -> Table:
    table = Table(expand=True, box=ROUNDED, border_style=ACCENT_PINK)
    table.add_column("ID", style=f"bold {ACCENT_YELLOW}", no_wrap=True, width=10)
    table.add_column("Content", style="white", ratio=3)
    table.add_column("Tags", style=ACCENT_ORANGE, ratio=1)
    table.add_column("Saved", style="dim", no_wrap=True)
    for m in memories:
        tags = ", ".join(m.tags) if m.tags else "-"
        ts = m.timestamp.strftime("%Y-%m-%d %H:%M")
        table.add_row(m.id, m.content, tags, ts)
    return table


@app.command(rich_help_panel="Memory")
def remember(
    content: str = typer.Argument(..., help="The memory to store."),
    tags: list[str] = typer.Option([], "--tag", "-t", help="Optional tags (repeatable)."),
    cwd: str = typer.Option("", "--cwd", hidden=True, help="Project path override."),
) -> None:
    """Store a memory for the current project."""
    svc = _memory_service()
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


@app.command(rich_help_panel="Memory")
def recall(
    query: str = typer.Argument("", help="Optional search query."),
    cwd: str = typer.Option("", "--cwd", hidden=True, help="Project path override."),
) -> None:
    """List memories for the current project."""
    svc = _memory_service()
    memories = svc.recall(cwd=cwd or None, query=query or None)

    if not memories:
        msg = f"No memories found{f' matching {query!r}' if query else ''}."
        console.print(_render_action_screen(_ActionResult(
            title="Recall",
            body=Panel.fit(msg, border_style=ACCENT_YELLOW),
            border_style=ACCENT_YELLOW,
        )))
        return

    console.print(_render_action_screen(_ActionResult(
        title=f"Memories — {memories[0].project_name}",
        body=_render_memory_table(memories),
        border_style=ACCENT_PINK,
    )))


@app.command(rich_help_panel="Memory")
def forget(
    memory_id: str = typer.Argument(..., help="ID of the memory to delete."),
    cwd: str = typer.Option("", "--cwd", hidden=True, help="Project path override."),
) -> None:
    """Delete a memory by ID."""
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


@app.command(rich_help_panel="Memory")
def projects() -> None:
    """List all projects that have stored memories."""
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


@app.command(rich_help_panel="Memory")
def init(
    agent: str = typer.Option(
        "",
        "--agent",
        "-a",
        help="Agent to use: 'claude' or 'codex'. Omit to pick interactively.",
    ),
    cwd: str = typer.Option("", "--cwd", hidden=True, help="Project path override."),
) -> None:
    """Initialize memories for the current project using an AI agent.

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
            # Interactive picker
            console.print()
            console.print(Text("Available agents:", style=f"bold {ACCENT_ORANGE}"))
            for i, name in enumerate(available, 1):
                console.print(f"  [{i}] {name}")
            console.print()
            while True:
                try:
                    raw = console.input(f"[bold {ACCENT_YELLOW}]Select agent (1-{len(available)}): [/]").strip()
                except (EOFError, KeyboardInterrupt):
                    raise typer.Exit(code=0)
                if raw.isdigit() and 1 <= int(raw) <= len(available):
                    chosen = available[int(raw) - 1]
                    break
                console.print("  Invalid choice, try again.", style="red")

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


@app.command(rich_help_panel="Other")
def help() -> None:  # noqa: A001
    """Show all available commands."""
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
