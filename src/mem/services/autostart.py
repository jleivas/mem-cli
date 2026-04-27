from __future__ import annotations

import os
import plistlib
import shutil
import subprocess
from pathlib import Path

LAUNCH_AGENT_LABEL = "com.mem.cli.mcp"
LAUNCH_AGENT_FILENAME = f"{LAUNCH_AGENT_LABEL}.plist"
SYSTEMD_SERVICE_FILENAME = "mem-cli-mcp.service"
WINDOWS_STARTUP_FILENAME = "mem-cli-mcp.cmd"


def is_supported_platform(platform_name: str | None = None) -> bool:
    return (platform_name or os.sys.platform) in {"darwin", "linux", "win32"}


def _platform(platform_name: str | None = None) -> str:
    return platform_name or os.sys.platform


def autostart_path(home: Path | None = None, platform_name: str | None = None) -> Path:
    base = home or Path.home()
    platform = _platform(platform_name)
    if platform == "darwin":
        return base / "Library" / "LaunchAgents" / LAUNCH_AGENT_FILENAME
    if platform == "linux":
        return base / ".config" / "systemd" / "user" / SYSTEMD_SERVICE_FILENAME
    if platform == "win32":
        app_data = os.environ.get("APPDATA")
        startup = (
            Path(app_data)
            if app_data
            else base / "AppData" / "Roaming"
        ) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        return startup / WINDOWS_STARTUP_FILENAME
    raise RuntimeError(f"Unsupported platform for autostart: {platform}")


def _resolve_mem_command(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    resolved = shutil.which("mem")
    if resolved:
        return resolved
    raise FileNotFoundError("Could not find the mem executable in PATH.")


def build_autostart_payload(program: str, platform_name: str | None = None) -> str | dict[str, object]:
    platform = _platform(platform_name)
    if platform == "darwin":
        return {
            "Label": LAUNCH_AGENT_LABEL,
            "ProgramArguments": [program, "serve"],
            "RunAtLoad": True,
            "KeepAlive": True,
            "StandardOutPath": str(Path.home() / ".mem-cli" / "runtime" / "mcp.stdout.log"),
            "StandardErrorPath": str(Path.home() / ".mem-cli" / "runtime" / "mcp.stderr.log"),
        }
    if platform == "linux":
        return (
            "[Unit]\n"
            "Description=mem-cli MCP server\n"
            "After=default.target\n\n"
            "[Service]\n"
            "Type=simple\n"
            f"ExecStart={program} serve\n"
            "Restart=on-failure\n"
            "RestartSec=2\n\n"
            "[Install]\n"
            "WantedBy=default.target\n"
        )
    if platform == "win32":
        return (
            "@echo off\n"
            "setlocal\n"
            f'"{program}" serve\n'
        )
    raise RuntimeError(f"Unsupported platform for autostart: {platform}")


def install_autostart(
    home: Path | None = None,
    program: str | None = None,
    platform_name: str | None = None,
    uid: int | None = None,
) -> Path:
    platform = _platform(platform_name)
    if platform not in {"darwin", "linux", "win32"}:
        raise RuntimeError("Autostart is only supported on macOS, Linux, and Windows.")

    autostart_file = autostart_path(home, platform)
    autostart_file.parent.mkdir(parents=True, exist_ok=True)
    resolved_program = _resolve_mem_command(program)
    payload = build_autostart_payload(resolved_program, platform)

    if platform == "darwin":
        autostart_file.write_bytes(plistlib.dumps(payload))  # type: ignore[arg-type]
        user_id = uid if uid is not None else os.getuid()
        subprocess.run(["launchctl", "bootout", f"gui/{user_id}", str(autostart_file)], check=False)
        subprocess.run(["launchctl", "bootstrap", f"gui/{user_id}", str(autostart_file)], check=True)
        return autostart_file

    if platform == "linux":
        autostart_file.write_text(str(payload), encoding="utf-8")
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
        subprocess.run(["systemctl", "--user", "enable", "--now", SYSTEMD_SERVICE_FILENAME], check=False)
        return autostart_file

    autostart_file.write_text(str(payload), encoding="utf-8")
    return autostart_file


def remove_autostart(
    home: Path | None = None,
    platform_name: str | None = None,
    uid: int | None = None,
) -> bool:
    platform = _platform(platform_name)
    autostart_file = autostart_path(home, platform)
    if not autostart_file.exists():
        return False

    if platform == "darwin":
        user_id = uid if uid is not None else os.getuid()
        subprocess.run(["launchctl", "bootout", f"gui/{user_id}", str(autostart_file)], check=False)
    elif platform == "linux":
        subprocess.run(["systemctl", "--user", "disable", "--now", SYSTEMD_SERVICE_FILENAME], check=False)

    autostart_file.unlink(missing_ok=True)
    return True


def autostart_installed(home: Path | None = None, platform_name: str | None = None) -> bool:
    return autostart_path(home, platform_name).exists()


# Backwards-compatible aliases for the previous macOS-only naming.
LAUNCH_AGENT_PATH = autostart_path
build_launch_agent_payload = build_autostart_payload
install_launch_agent = install_autostart
launch_agent_installed = autostart_installed
launch_agent_path = autostart_path
remove_launch_agent = remove_autostart
