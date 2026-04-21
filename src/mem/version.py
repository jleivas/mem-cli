from __future__ import annotations

import re
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as metadata_version
from pathlib import Path


APP_NAME = "mem-cli"


def _version_from_changelog() -> str:
    """Return the latest released version from CHANGELOG.md."""
    current = Path(__file__).resolve().parent
    for _ in range(6):
        candidate = current / "CHANGELOG.md"
        if candidate.exists():
            text = candidate.read_text(encoding="utf-8")
            match = re.search(r"^## \[(\d+\.\d+\.\d+)\]", text, re.MULTILINE)
            if match:
                return match.group(1)
        current = current.parent
    return "0.0.0"


def get_app_version() -> str:
    """Return the package version for source checkouts and installed builds."""
    try:
        return metadata_version(APP_NAME)
    except PackageNotFoundError:
        return _version_from_changelog()


APP_VERSION = get_app_version()
__version__ = APP_VERSION
