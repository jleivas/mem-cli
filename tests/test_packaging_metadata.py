from __future__ import annotations

from pathlib import Path


def test_release_workflow_exists() -> None:
    workflow = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "release.yml"
    assert workflow.exists()


def test_project_metadata_mentions_cross_platform_support() -> None:
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    assert "Operating System :: OS Independent" in text
    assert "mem-cli" in text
