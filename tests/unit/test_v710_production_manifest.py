from __future__ import annotations

from pathlib import Path

import pytest

from scripts.validate_v710_production_manifest import (
    MANIFEST_PATH,
    validate_manifest,
)

SOURCE_COMMIT = "5793c1a82c7bf9dfa0d3bd0457a2fab08c23ec9f"


def test_committed_v710_production_manifest_passes() -> None:
    receipt = validate_manifest(Path.cwd(), SOURCE_COMMIT)
    assert receipt["status"] == "passed"
    assert receipt["release_version"] == "7.1.0"
    assert receipt["production_authorized"] is False
    assert receipt["published"] is False
    assert receipt["authority_activated"] is False
    assert receipt["required_integrations"] == ["GitHub", "Notion", "Todoist"]


def test_candidate_only_text_is_rejected(tmp_path: Path) -> None:
    for relative in (
        MANIFEST_PATH,
        Path("release/RELEASE_MANIFEST_V710_CANDIDATE.md"),
        Path("release/specifications/V710.yaml"),
    ):
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        source = (Path.cwd() / relative).read_text(encoding="utf-8")
        destination.write_text(source, encoding="utf-8")

    manifest = tmp_path / MANIFEST_PATH
    manifest.write_text(
        manifest.read_text(encoding="utf-8") + "\nStatus: Candidate only\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="candidate-only text"):
        validate_manifest(tmp_path, SOURCE_COMMIT)


def test_unbound_source_commit_is_rejected() -> None:
    with pytest.raises(ValueError, match="exact lowercase 40-character SHA"):
        validate_manifest(Path.cwd(), "main")
