"""Build a standalone binary for mem-cli using PyInstaller.

Usage:
    python scripts/build_binary.py

Produces dist/mem/ (onedir) ready to be packaged as a tarball.
"""

from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def asset_name() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    arch = "arm64" if machine in ("arm64", "aarch64") else "amd64"
    os_name = "darwin" if system == "darwin" else "linux"
    return f"mem-{os_name}-{arch}"


def build() -> Path:
    sep = ";" if sys.platform == "win32" else ":"
    prompts_src = ROOT / "src" / "mem" / "prompts"
    add_data = f"{prompts_src}{sep}mem/prompts"

    subprocess.run(
        [
            sys.executable, "-m", "PyInstaller",
            "--onedir",
            "--name", "mem",
            "--add-data", add_data,
            "--collect-all", "sentence_transformers",
            "--collect-all", "transformers",
            "--hidden-import", "mcp",
            "--hidden-import", "typer",
            "--hidden-import", "rich",
            "--noconfirm",
            str(ROOT / "src" / "mem" / "cli.py"),
        ],
        cwd=ROOT,
        check=True,
    )
    return ROOT / "dist" / "mem"


if __name__ == "__main__":
    dist_dir = build()
    name = asset_name()
    print(f"asset={name}")
    print(f"dist={dist_dir}")
