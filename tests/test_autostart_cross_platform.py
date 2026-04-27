from __future__ import annotations

from pathlib import Path

from mem.services import autostart


def test_linux_autostart_path_uses_systemd_user_dir(tmp_path: Path) -> None:
    path = autostart.autostart_path(tmp_path, platform_name="linux")
    assert path == tmp_path / ".config" / "systemd" / "user" / autostart.SYSTEMD_SERVICE_FILENAME


def test_windows_autostart_path_uses_startup_folder(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData" / "Roaming"))
    path = autostart.autostart_path(tmp_path, platform_name="win32")
    assert path == tmp_path / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / autostart.WINDOWS_STARTUP_FILENAME


def test_linux_autostart_payload_contains_execstart() -> None:
    payload = autostart.build_autostart_payload("/opt/homebrew/bin/mem", platform_name="linux")
    assert "ExecStart=/opt/homebrew/bin/mem serve" in payload


def test_windows_autostart_payload_contains_mem_serve() -> None:
    payload = autostart.build_autostart_payload("C:\\Program Files\\mem\\mem.exe", platform_name="win32")
    assert '"C:\\Program Files\\mem\\mem.exe" serve' in payload
