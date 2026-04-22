from __future__ import annotations

from mem.services.adapters.registry import discover_token_source_plugins
from mem.services.monitor_service import NullTokenSource


class _FakeEntryPoint:
    def __init__(self, name: str, value: str, factory):
        self.name = name
        self.value = value
        self._factory = factory

    def load(self):
        return self._factory


class _FakeEntryPoints:
    def __init__(self, entry_points):
        self._entry_points = entry_points

    def select(self, group: str):
        return self._entry_points if group == "mem.token_sources" else []


def test_discover_token_source_plugins_loads_entry_points(monkeypatch) -> None:
    monkeypatch.setattr(
        "mem.services.adapters.registry.metadata.entry_points",
        lambda: _FakeEntryPoints([
            _FakeEntryPoint("custom", "pkg.adapters:build", lambda: NullTokenSource()),
        ]),
    )

    plugins = discover_token_source_plugins()

    assert len(plugins) == 1
    assert plugins[0].name == "custom"
    assert plugins[0].entry_point == "pkg.adapters:build"
    assert hasattr(plugins[0].source, "poll")
