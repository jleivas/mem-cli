from __future__ import annotations

import os
import plistlib
import shutil
import subprocess
import json
import sys
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


def start_detached_mcp_server(
    program: str | None = None,
    platform_name: str | None = None,
    stdout: object | None = None,
    stderr: object | None = None,
) -> subprocess.Popen[bytes]:
    resolved_program = _resolve_mem_command(program)
    platform = _platform(platform_name)
    kwargs: dict[str, object] = {
        "stdin": subprocess.DEVNULL,
        "stdout": stdout if stdout is not None else subprocess.DEVNULL,
        "stderr": stderr if stderr is not None else subprocess.DEVNULL,
    }

    if platform == "win32":
        creation_flags = 0
        creation_flags |= getattr(subprocess, "DETACHED_PROCESS", 0)
        creation_flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        kwargs["creationflags"] = creation_flags
    else:
        kwargs["start_new_session"] = True

    return subprocess.Popen([resolved_program, "serve"], **kwargs)  # type: ignore[arg-type]


def start_hidden_mcp_server(
    program: str | None = None,
    platform_name: str | None = None,
    stderr_log_path: Path | None = None,
) -> subprocess.Popen[bytes]:
    resolved_program = _resolve_mem_command(program)
    platform = _platform(platform_name)
    log_path = stderr_log_path or Path.home() / ".mem-cli" / "runtime" / "mcp-serve.stderr.log"
    supervisor_code = (
        "from pathlib import Path\n"
        "import subprocess\n"
        "import sys\n"
        "\n"
        "program = sys.argv[1]\n"
        "log_path = Path(sys.argv[2])\n"
        "log_path.parent.mkdir(parents=True, exist_ok=True)\n"
        "\n"
        "try:\n"
        "    with log_path.open('a', encoding='utf-8') as stderr_log:\n"
        "        proc = subprocess.Popen(\n"
        "            [program, 'serve'],\n"
        "            stdin=subprocess.PIPE,\n"
        "            stdout=subprocess.DEVNULL,\n"
        "            stderr=stderr_log,\n"
        "        )\n"
        "        return_code = proc.wait()\n"
        "        stderr_log.write(f'\\n[mem setup] mem serve exited with code {return_code}\\n')\n"
        "        stderr_log.flush()\n"
        "except BaseException:\n"
        "    with log_path.open('a', encoding='utf-8') as stderr_log:\n"
        "        import traceback\n"
        "        stderr_log.write('\\n[mem setup] supervisor failed while starting mem serve\\n')\n"
        "        traceback.print_exc(file=stderr_log)\n"
        "        stderr_log.flush()\n"
        "    raise\n"
    )
    kwargs: dict[str, object] = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
    }
    log_handle = log_path.open("a", encoding="utf-8")
    if platform == "win32":
        creation_flags = 0
        creation_flags |= getattr(subprocess, "DETACHED_PROCESS", 0)
        creation_flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        kwargs["creationflags"] = creation_flags
    else:
        kwargs["start_new_session"] = True
    try:
        kwargs["stderr"] = log_handle
        return subprocess.Popen(
            [sys.executable, "-c", supervisor_code, resolved_program, str(log_path)],
            **kwargs,  # type: ignore[arg-type]
        )
    finally:
        log_handle.close()


def open_serve_in_new_terminal(
    program: str | None = None,
    platform_name: str | None = None,
) -> subprocess.Popen[bytes] | None:
    resolved_program = _resolve_mem_command(program)
    platform = _platform(platform_name)

    if platform == "darwin":
        command = f"{resolved_program} serve"
        apple_script = (
            'tell application "Terminal"\n'
            '  activate\n'
            f"  do script {json.dumps(command)}\n"
            'end tell'
        )
        return subprocess.Popen(
            ["osascript", "-e", apple_script],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    if platform == "linux":
        for terminal in ("x-terminal-emulator", "gnome-terminal", "konsole", "xfce4-terminal", "xterm"):
            terminal_path = shutil.which(terminal)
            if terminal_path:
                cmd = [terminal_path]
                if terminal in {"gnome-terminal", "konsole", "xfce4-terminal"}:
                    cmd += ["--", resolved_program, "serve"]
                else:
                    cmd += ["-e", resolved_program, "serve"]
                return subprocess.Popen(
                    cmd,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
        return start_detached_mcp_server(resolved_program, platform)

    if platform == "win32":
        creation_flags = 0
        creation_flags |= getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        creation_flags |= getattr(subprocess, "DETACHED_PROCESS", 0)
        return subprocess.Popen(
            [resolved_program, "serve"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags,
        )

    raise RuntimeError(f"Unsupported platform for new-terminal launch: {platform}")


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
            "WorkingDirectory=%h\n"
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
        # bootout is a best-effort "stop if loaded" step — errors are expected when the
        # service was never bootstrapped, so suppress stderr to avoid alarming the user.
        subprocess.run(
            ["launchctl", "bootout", f"gui/{user_id}", str(autostart_file)],
            check=False,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(["launchctl", "bootstrap", f"gui/{user_id}", str(autostart_file)], check=True)
        return autostart_file

    if platform == "linux":
        autostart_file.write_text(str(payload), encoding="utf-8")
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
        subprocess.run(["systemctl", "--user", "enable", "--now", SYSTEMD_SERVICE_FILENAME], check=False)
        return autostart_file

    autostart_file.write_text(str(payload), encoding="utf-8")
    start_detached_mcp_server(resolved_program, platform)
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
start_new_terminal = open_serve_in_new_terminal
