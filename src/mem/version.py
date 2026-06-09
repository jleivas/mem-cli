from __future__ import annotations

import re
import sys
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as metadata_version
from pathlib import Path


APP_NAME = "mem-cli"


def _version_from_baked() -> str | None:
    """Return version baked in at PyInstaller build time, or None if absent."""
    try:
        from mem._baked_version import VERSION  # noqa: PLC0415
        return VERSION
    except ImportError:
        return None


def _version_from_changelog() -> str:
    """Return the latest version from CHANGELOG.md, searching up the tree."""
    start_dirs: list[Path] = []
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        start_dirs.append(Path(sys._MEIPASS))
    start_dirs.append(Path(__file__).resolve().parent)

    for start in start_dirs:
        current = start
        for _ in range(6):
            candidate = current / "CHANGELOG.md"
            if candidate.exists():
                text = candidate.read_text(encoding="utf-8")
                m = re.search(r"^## \[(\d+\.\d+\.\d+)\]", text, re.MULTILINE)
                if m:
                    return m.group(1)
            current = current.parent
    return "0.0.0"


def get_app_version() -> str:
    """Resolve version across all deployment scenarios.

    Priority:
    1. importlib.metadata  — pip / editable installs (dist-info present)
    2. _baked_version      — PyInstaller builds (written by build_binary.py)
    3. CHANGELOG.md search — source checkouts without pip install
    """
    try:
        return metadata_version(APP_NAME)
    except PackageNotFoundError:
        pass

    baked = _version_from_baked()
    if baked:
        return baked

    return _version_from_changelog()


APP_VERSION = get_app_version()
__version__ = APP_VERSION
