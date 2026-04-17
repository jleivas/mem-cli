from clar.models import AgentStatus
from clar.storage.dashboard_history import DashboardSnapshotStore


def test_dashboard_snapshot_store_roundtrip(tmp_path) -> None:
    store = DashboardSnapshotStore(root=tmp_path)
    snapshot = [
        AgentStatus(
            agent_name="codex",
            input_tokens=10,
            output_tokens=20,
            total_tokens=30,
            average_tokens_per_minute=15.0,
            last_updated="2026-04-17T00:00:00+00:00",
            state="active",
            source="test",
        )
    ]

    path = store.save(snapshot, source="live")
    entries = store.list()
    loaded = store.load(path)

    assert path.exists()
    assert len(entries) == 1
    assert entries[0].rows == 1
    assert loaded[0].agent_name == "codex"
    assert loaded[0].total_tokens == 30
