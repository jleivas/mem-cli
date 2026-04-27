from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

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


def test_windows_autostart_starts_detached_process(monkeypatch) -> None:
    popen_calls = []

    class FakePopen:
        def __init__(self, cmd, **kwargs):
            popen_calls.append((cmd, kwargs))

    monkeypatch.setattr(autostart, "_resolve_mem_command", lambda explicit=None: "C:\\mem\\mem.exe")

    with patch.object(autostart.subprocess, "Popen", FakePopen):
        autostart.start_detached_mcp_server(platform_name="win32")

    assert popen_calls[0][0] == ["C:\\mem\\mem.exe", "serve"]
    assert "creationflags" in popen_calls[0][1]


def test_macos_open_serve_in_new_terminal_uses_osascript(monkeypatch) -> None:
    popen_calls = []

    class FakePopen:
        def __init__(self, cmd, **kwargs):
            popen_calls.append((cmd, kwargs))

    monkeypatch.setattr(autostart, "_resolve_mem_command", lambda explicit=None: "/opt/homebrew/bin/mem")

    with patch.object(autostart.subprocess, "Popen", FakePopen):
        autostart.open_serve_in_new_terminal(platform_name="darwin")

    assert popen_calls[0][0][0] == "osascript"
    assert "do script \"/opt/homebrew/bin/mem serve\"" in popen_calls[0][0][2]


def test_linux_open_serve_in_new_terminal_uses_terminal_emulator(monkeypatch) -> None:
    popen_calls = []

    class FakePopen:
        def __init__(self, cmd, **kwargs):
            popen_calls.append((cmd, kwargs))

    monkeypatch.setattr(autostart, "_resolve_mem_command", lambda explicit=None: "/usr/bin/mem")
    monkeypatch.setattr(autostart.shutil, "which", lambda name: "/usr/bin/xterm" if name == "xterm" else None)

    with patch.object(autostart.subprocess, "Popen", FakePopen):
        autostart.open_serve_in_new_terminal(platform_name="linux")

    assert popen_calls[0][0] == ["/usr/bin/xterm", "-e", "/usr/bin/mem", "serve"]


def test_windows_open_serve_in_new_terminal_uses_new_console(monkeypatch) -> None:
    popen_calls = []

    class FakePopen:
        def __init__(self, cmd, **kwargs):
            popen_calls.append((cmd, kwargs))

    monkeypatch.setattr(autostart, "_resolve_mem_command", lambda explicit=None: "C:\\mem\\mem.exe")

    with patch.object(autostart.subprocess, "Popen", FakePopen):
        autostart.open_serve_in_new_terminal(platform_name="win32")

    assert popen_calls[0][0] == ["C:\\mem\\mem.exe", "serve"]
    assert "creationflags" in popen_calls[0][1]
