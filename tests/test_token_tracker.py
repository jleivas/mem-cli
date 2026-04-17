from clar.models import TokenEvent
from clar.services.token_tracker import TokenTracker


def test_register_event_and_snapshot() -> None:
    tracker = TokenTracker()
    tracker.register_event(TokenEvent(agent_name="codex", input_tokens=10, output_tokens=20, source="test"))
    tracker.register_event(TokenEvent(agent_name="codex", input_tokens=5, output_tokens=7, source="test"))

    snapshot = tracker.snapshot()

    assert len(snapshot) == 1
    item = snapshot[0]
    assert item.agent_name == "codex"
    assert item.input_tokens == 15
    assert item.output_tokens == 27
    assert item.total_tokens == 42
    assert item.average_tokens_per_minute > 0
    assert item.source == "test"


def test_reset_clears_snapshot() -> None:
    tracker = TokenTracker()
    tracker.register_event(TokenEvent(agent_name="codex", input_tokens=10, output_tokens=20, source="test"))
    tracker.reset()

    assert tracker.snapshot() == []
