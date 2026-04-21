"""Sync the version in pyproject.toml from the latest entry in CHANGELOG.md."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from release_utils import sync_pyproject_version


if __name__ == "__main__":
    version = sync_pyproject_version(ROOT)
    print(f"Version: {version}")
