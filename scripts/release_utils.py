from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path


VERSION_PATTERN = re.compile(r"^## \[(\d+\.\d+\.\d+)\]", re.MULTILINE)


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def latest_changelog_version(root: Path | None = None) -> str:
    base = root or project_root()
    changelog = base / "CHANGELOG.md"
    if not changelog.exists():
        raise FileNotFoundError(f"{changelog} not found")

    text = changelog.read_text(encoding="utf-8")
    match = VERSION_PATTERN.search(text)
    if not match:
        raise ValueError("No released version found in CHANGELOG.md")
    return match.group(1)


def sync_pyproject_version(root: Path | None = None) -> str:
    base = root or project_root()
    version = latest_changelog_version(base)
    pyproject = base / "pyproject.toml"
    content = pyproject.read_text(encoding="utf-8")
    updated = re.sub(
        r'^(version\s*=\s*")[^"]*(")',
        rf"\g<1>{version}\g<2>",
        content,
        flags=re.MULTILINE,
    )
    if updated != content:
        pyproject.write_text(updated, encoding="utf-8")
    return version


def _distribution_dirs(root: Path) -> list[Path]:
    return [root / "build", root / "dist"]


def clean_distribution_dirs(root: Path | None = None) -> None:
    base = root or project_root()
    for directory in _distribution_dirs(base):
        if directory.exists():
            shutil.rmtree(directory)


def run_build(root: Path | None = None) -> None:
    base = root or project_root()
    subprocess.run(
        [sys.executable, "-m", "build", "--sdist", "--wheel"],
        cwd=base,
        check=True,
    )


def find_distribution_artifacts(root: Path | None = None) -> list[Path]:
    base = root or project_root()
    dist_dir = base / "dist"
    if not dist_dir.exists():
        return []
    return sorted(
        [*dist_dir.glob("*.whl"), *dist_dir.glob("*.tar.gz")],
        key=lambda path: path.name,
    )


def build_distribution(root: Path | None = None) -> tuple[str, list[Path]]:
    base = root or project_root()
    version = sync_pyproject_version(base)
    clean_distribution_dirs(base)
    run_build(base)
    artifacts = find_distribution_artifacts(base)
    if not artifacts:
        raise RuntimeError("No distribution artifacts were produced")
    return version, artifacts
