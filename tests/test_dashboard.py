from clar.models import TokenEvent
from clar.services.token_tracker import TokenTracker
from clar.ui.dashboard import build_detail_table, build_summary_panel, render_dashboard


def _snapshot():
    tracker = TokenTracker()
    tracker.register_event(TokenEvent(agent_name="codex", input_tokens=12, output_tokens=24, source="simulated"))
    tracker.register_event(TokenEvent(agent_name="claude", input_tokens=4, output_tokens=8, source="simulated"))
    return tracker.snapshot()


def test_build_summary_panel_contains_overview() -> None:
    panel = build_summary_panel(_snapshot(), running=True)
    assert panel.title is not None


def test_build_detail_table_contains_source_column() -> None:
    table = build_detail_table(_snapshot())
    assert any(column.header == "Source" for column in table.columns)
    assert any(column.header == "Avg/record" for column in table.columns)


def test_render_dashboard_supports_both_view() -> None:
    renderable = render_dashboard(_snapshot(), True, view="both")
    assert renderable is not None
