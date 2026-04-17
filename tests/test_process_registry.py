from pathlib import Path

from clar.config import get_runtime_state_path
from clar.services.process_registry import ProcessRegistry
from clar.storage.runtime_state import RuntimeState, RuntimeStateStore
from clar.utils.time import utc_now


def test_runtime_state_round_trip(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MEM_HOME", str(tmp_path))
    store = RuntimeStateStore(get_runtime_state_path())
    state = RuntimeState(running=True, pid=1234, started_at=utc_now(), last_updated=utc_now())

    store.save(state)
    loaded = store.load()

    assert loaded is not None
    assert loaded.running is True
    assert loaded.pid == 1234


def test_pid_alive_check() -> None:
    assert ProcessRegistry.is_pid_alive(999999) is False
