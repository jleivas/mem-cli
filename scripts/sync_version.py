"""Sync the version in pyproject.toml from the latest entry in CHANGELOG.md.

Run before building a distribution:

    python scripts/sync_version.py
    pip install -e .
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def latest_changelog_version() -> str:
    changelog = ROOT / "CHANGELOG.md"
    if not changelog.exists():
        sys.exit(f"ERROR: {changelog} not found")

    text = changelog.read_text(encoding="utf-8")
    match = re.search(r"^## \[(\d+\.\d+\.\d+)\]", text, re.MULTILINE)
    if not match:
        sys.exit("ERROR: No released version found in CHANGELOG.md (need a '## [X.Y.Z]' heading)")
    return match.group(1)


def sync_pyproject(version: str) -> None:
    pyproject = ROOT / "pyproject.toml"
    content = pyproject.read_text(encoding="utf-8")
    updated = re.sub(
        r'^(version\s*=\s*")[^"]*(")',
        rf"\g<1>{version}\g<2>",
        content,
        flags=re.MULTILINE,
    )
    if updated == content:
        print(f"pyproject.toml already at {version}")
        return
    pyproject.write_text(updated, encoding="utf-8")
    print(f"pyproject.toml updated → {version}")


if __name__ == "__main__":
    v = latest_changelog_version()
    sync_pyproject(v)
    print(f"Version: {v}")
