from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import patch


def _load_release_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "release_utils.py"
    spec = importlib.util.spec_from_file_location("release_utils", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


release = _load_release_module()


def test_latest_changelog_version_reads_first_released_version(tmp_path: Path) -> None:
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [1.2.3] — 2026-04-21\n",
        encoding="utf-8",
    )

    assert release.latest_changelog_version(tmp_path) == "1.2.3"


def test_sync_pyproject_version_updates_version_line(tmp_path: Path) -> None:
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [2.0.1] — 2026-04-21\n",
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nversion = "0.1.0"\n',
        encoding="utf-8",
    )

    version = release.sync_pyproject_version(tmp_path)

    assert version == "2.0.1"
    assert 'version = "2.0.1"' in (tmp_path / "pyproject.toml").read_text(encoding="utf-8")


def test_build_distribution_cleans_and_builds_artifacts(tmp_path: Path) -> None:
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [3.1.4] — 2026-04-21\n",
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    dist_dir = tmp_path / "dist"
    build_dir = tmp_path / "build"
    dist_dir.mkdir()
    build_dir.mkdir()
    (dist_dir / "old.whl").write_text("old", encoding="utf-8")
    (build_dir / "old.txt").write_text("old", encoding="utf-8")

    def fake_run(*args, **kwargs):
        dist_dir.mkdir(exist_ok=True)
        (dist_dir / "mem_cli-3.1.4-py3-none-any.whl").write_text("wheel", encoding="utf-8")
        (dist_dir / "mem_cli-3.1.4.tar.gz").write_text("sdist", encoding="utf-8")
        return None

    with patch.object(release.subprocess, "run", side_effect=fake_run) as run_mock:
        version, artifacts = release.build_distribution(tmp_path)

    assert version == "3.1.4"
    assert run_mock.called
    assert not build_dir.exists()
    assert sorted(path.name for path in artifacts) == [
        "mem_cli-3.1.4-py3-none-any.whl",
        "mem_cli-3.1.4.tar.gz",
    ]
