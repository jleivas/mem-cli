from __future__ import annotations

import plistlib
from pathlib import Path
from unittest.mock import patch

from mem.services import macos_launchd


def test_launch_agent_payload_targets_mem_serve() -> None:
    payload = macos_launchd.build_launch_agent_payload("/opt/homebrew/bin/mem")

    assert payload["Label"] == macos_launchd.LAUNCH_AGENT_LABEL
    assert payload["ProgramArguments"] == ["/opt/homebrew/bin/mem", "serve"]
    assert payload["RunAtLoad"] is True
    assert payload["KeepAlive"] is True


def test_install_launch_agent_writes_plist_and_bootstraps(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(macos_launchd, "is_supported_platform", lambda platform_name=None: True)
    monkeypatch.setattr(macos_launchd, "_resolve_mem_command", lambda explicit=None: "/opt/homebrew/bin/mem")
    monkeypatch.setattr(macos_launchd.os, "getuid", lambda: 501)

    calls: list[list[str]] = []

    def fake_run(cmd, check):
        calls.append(cmd)

    with patch.object(macos_launchd.subprocess, "run", side_effect=fake_run):
        plist_path = macos_launchd.install_launch_agent(home=tmp_path)

    assert plist_path == tmp_path / "Library" / "LaunchAgents" / macos_launchd.LAUNCH_AGENT_FILENAME
    assert plist_path.exists()
    payload = plistlib.loads(plist_path.read_bytes())
    assert payload["ProgramArguments"] == ["/opt/homebrew/bin/mem", "serve"]
    assert any(cmd[1] == "bootstrap" for cmd in calls)


def test_remove_launch_agent_unlinks_plist(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(macos_launchd, "is_supported_platform", lambda platform_name=None: True)
    monkeypatch.setattr(macos_launchd.os, "getuid", lambda: 501)

    plist_path = macos_launchd.launch_agent_path(tmp_path)
    plist_path.parent.mkdir(parents=True, exist_ok=True)
    plist_path.write_text("dummy", encoding="utf-8")

    with patch.object(macos_launchd.subprocess, "run") as run_mock:
        removed = macos_launchd.remove_launch_agent(home=tmp_path)

    assert removed is True
    assert not plist_path.exists()
    assert run_mock.called
