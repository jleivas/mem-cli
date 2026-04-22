from __future__ import annotations

from pathlib import Path

from mem.config import _default_app_home
from mem.config import get_app_home


def test_get_app_home_prefers_mem_home(monkeypatch, tmp_path: Path) -> None:
    custom_home = tmp_path / "custom-home"
    monkeypatch.setenv("MEM_HOME", str(custom_home))

    assert get_app_home() == custom_home


def test_get_app_home_uses_localappdata_on_windows(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("MEM_HOME", raising=False)
    local_app_data = tmp_path / "LocalAppData"

    assert _default_app_home(platform_name="nt", home_dir=tmp_path / "home", local_app_data=str(local_app_data)) == local_app_data / "mem-cli"
