from __future__ import annotations

import os
import plistlib
import shutil
import subprocess
from pathlib import Path

LAUNCH_AGENT_LABEL = "com.mem.cli.mcp"
LAUNCH_AGENT_FILENAME = f"{LAUNCH_AGENT_LABEL}.plist"


def is_supported_platform(platform_name: str | None = None) -> bool:
    return (platform_name or os.sys.platform) == "darwin"


def launch_agent_path(home: Path | None = None) -> Path:
    base = home or Path.home()
    return base / "Library" / "LaunchAgents" / LAUNCH_AGENT_FILENAME


def _resolve_mem_command(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    resolved = shutil.which("mem")
    if resolved:
        return resolved
    raise FileNotFoundError("Could not find the mem executable in PATH.")


def build_launch_agent_payload(program: str) -> dict[str, object]:
    return {
        "Label": LAUNCH_AGENT_LABEL,
        "ProgramArguments": [program, "serve"],
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": str(Path.home() / ".mem-cli" / "runtime" / "mcp.stdout.log"),
        "StandardErrorPath": str(Path.home() / ".mem-cli" / "runtime" / "mcp.stderr.log"),
    }


def install_launch_agent(
    home: Path | None = None,
    program: str | None = None,
    platform_name: str | None = None,
    uid: int | None = None,
) -> Path:
    if not is_supported_platform(platform_name):
        raise RuntimeError("macOS LaunchAgent autostart is only supported on macOS.")

    plist_path = launch_agent_path(home)
    plist_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_program = _resolve_mem_command(program)
    payload = build_launch_agent_payload(resolved_program)
    plist_path.write_bytes(plistlib.dumps(payload))

    user_id = uid if uid is not None else os.getuid()
    launchctl = ["launchctl"]
    subprocess.run([*launchctl, "bootout", f"gui/{user_id}", str(plist_path)], check=False)
    subprocess.run([*launchctl, "bootstrap", f"gui/{user_id}", str(plist_path)], check=True)
    return plist_path


def remove_launch_agent(
    home: Path | None = None,
    platform_name: str | None = None,
    uid: int | None = None,
) -> bool:
    if not is_supported_platform(platform_name):
        return False

    plist_path = launch_agent_path(home)
    if not plist_path.exists():
        return False

    user_id = uid if uid is not None else os.getuid()
    launchctl = ["launchctl"]
    subprocess.run([*launchctl, "bootout", f"gui/{user_id}", str(plist_path)], check=False)
    plist_path.unlink(missing_ok=True)
    return True


def launch_agent_installed(home: Path | None = None) -> bool:
    return launch_agent_path(home).exists()
