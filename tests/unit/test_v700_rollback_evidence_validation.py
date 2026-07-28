from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

from scripts.validate_v650_rollback_evidence import (
    RollbackEvidenceValidationError,
    validate_v650_rollback_evidence,
)
from tools.release.rollback_evidence import load_receipt


def git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def repository(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "repository"
    (root / "release").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        '[project]\nname = "atlas-ros"\nversion = "6.5.0"\n',
        encoding="utf-8",
    )
    (root / "release" / "RELEASE_MANIFEST.md").write_text(
        "# Release Manifest\n\nRelease: Atlas ROS v6.2.0\n",
        encoding="utf-8",
    )
    git(root, "init")
    git(root, "config", "user.email", "atlas@example.test")
    git(root, "config", "user.name", "Atlas Test")
    git(root, "add", ".")
    git(root, "commit", "-m", "release: add explicit v6.5.0 publication controller")
    git(root, "tag", "v6.5.0")
    return root, git(root, "rev-parse", "HEAD")


def assets(tmp_path: Path) -> Path:
    root = tmp_path / "assets"
    root.mkdir()
    wheel = root / "atlas_ros-6.5.0-py3-none-any.whl"
    source = root / "atlas_ros-6.5.0.tar.gz"
    wheel.write_bytes(b"wheel-v650")
    source.write_bytes(b"source-v650")
    checksum_lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}"
        for path in (wheel, source)
    ]
    (root / "CHECKSUMS.sha256").write_text(
        "\n".join(checksum_lines) + "\n",
        encoding="utf-8",
    )
    return root


def test_validator_generates_ready_reconciled_rollback_receipt(tmp_path: Path) -> None:
    repo, commit = repository(tmp_path)
    output = tmp_path / "rollback-evidence.json"

    receipt = validate_v650_rollback_evidence(
        repository_root=repo,
        source_commit=commit,
        release_assets_dir=assets(tmp_path),
        clean_install_version="6.5.0",
        restoration_passed=True,
        metadata_exception_record_url="https://app.notion.com/p/exception",
        output_path=output,
    )

    assert receipt.status == "ready"
    assert receipt.metadata_discrepancy is True
    assert receipt.verified_version == "6.5.0"
    assert receipt.immutable_history_rewritten is False
    assert receipt.provider_writes == 0
    assert load_receipt(output) == receipt


def test_validator_rejects_release_checksum_tampering(tmp_path: Path) -> None:
    repo, commit = repository(tmp_path)
    release_assets = assets(tmp_path)
    (release_assets / "atlas_ros-6.5.0.tar.gz").write_bytes(b"tampered")

    with pytest.raises(RollbackEvidenceValidationError, match="checksum failed"):
        validate_v650_rollback_evidence(
            repository_root=repo,
            source_commit=commit,
            release_assets_dir=release_assets,
            clean_install_version="6.5.0",
            restoration_passed=True,
            metadata_exception_record_url="https://app.notion.com/p/exception",
            output_path=tmp_path / "rollback-evidence.json",
        )


def test_validator_requires_clean_install_and_restoration(tmp_path: Path) -> None:
    repo, commit = repository(tmp_path)

    receipt = validate_v650_rollback_evidence(
        repository_root=repo,
        source_commit=commit,
        release_assets_dir=assets(tmp_path),
        clean_install_version="6.2.0",
        restoration_passed=False,
        metadata_exception_record_url="https://app.notion.com/p/exception",
        output_path=tmp_path / "rollback-evidence.json",
    )

    assert receipt.status == "blocked"
    assert "clean installation does not identify v6.5.0" in receipt.blockers
    assert "clean installation has not passed" in receipt.blockers
    assert "rollback restoration tests has not passed" in receipt.blockers
