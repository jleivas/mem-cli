"""Build source and wheel distributions for mem-cli.

Usage:
    python scripts/release_build.py

This command synchronizes the package version from CHANGELOG.md, clears old
artifacts, builds sdist/wheel distributions, and prints the resulting files.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from release_utils import build_distribution


if __name__ == "__main__":
    version, artifacts = build_distribution(ROOT)
    print(f"Built mem-cli {version}")
    for artifact in artifacts:
        print(artifact.relative_to(ROOT))
