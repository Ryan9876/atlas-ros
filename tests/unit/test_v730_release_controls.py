from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts.finalize_v730_package import assemble
from scripts.validate_v730_candidate import CandidateValidationError, validate
from scripts.validate_v730_notion_migration import MigrationValidationError, validate_migration

ROOT = Path(__file__).resolve().parents[2]


def test_v730_migration_is_additive_unapplied_and_fixture_compatible() -> None:
    receipt = validate_migration(
        ROOT / "release/v730-notion-schema-migration.yaml",
        ROOT / "release/v730-notion-schema-fixture.json",
    )
    assert receipt["status"] == "validated_unapplied"
    assert receipt["destructive_operations"] == 0
    assert receipt["live_writes"] == 0
    assert receipt["production_apply_authorized"] is False
    assert receipt["additive_fields"] == [
        "Acceptance Status",
        "Commitment Source",
        "Completion Evidence State",
        "Expected Evidence",
        "Last Verified",
    ]


def test_v730_migration_rejects_destructive_or_live_authorized_change(tmp_path: Path) -> None:
    migration = yaml.safe_load(
        (ROOT / "release/v730-notion-schema-migration.yaml").read_text(encoding="utf-8")
    )
    migration["production_apply_authorized"] = True
    migration["destructive_operations"] = ["DROP COLUMN Status"]
    path = tmp_path / "unsafe.yaml"
    path.write_text(yaml.safe_dump(migration, sort_keys=False), encoding="utf-8")
    with pytest.raises(MigrationValidationError):
        validate_migration(path, ROOT / "release/v730-notion-schema-fixture.json")


def test_v730_workflow_controls_enforce_lean_full_and_build_once() -> None:
    lean = (ROOT / ".github/workflows/v730-lean-ci.yml").read_text(encoding="utf-8")
    full = (ROOT / ".github/workflows/v730-full-validation.yml").read_text(encoding="utf-8")
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "cancel-in-progress: true" in lean
    assert "fetch-depth: 1" in lean
    assert "types: [opened, synchronize, reopened]" in lean
    assert "types: [ready_for_review]" in full
    assert "fetch-depth: 0" in full
    assert full.count("python -m build") == 1
    assert "actions/download-artifact" in full
    assert "BUILD_COUNT.txt" in full
    assert "v7.1.1" in full and "v7.1.0" in full
    assert "PUBLISH" not in full
    assert "gh release create" not in full
    assert "gh release upload" not in full
    assert "agent/v730-operational-awareness-impl" in ci


def test_v730_workflow_path_matrix_covers_required_change_classes() -> None:
    lean = (ROOT / ".github/workflows/v730-lean-ci.yml").read_text(encoding="utf-8")
    required = (
        "contracts/operational_awareness",
        "capabilities/operational_awareness",
        "application/command_lifecycle.py",
        "planning/operational_awareness.py",
        "operational-awareness.yaml",
        "schemas/operational-awareness",
        "governance/architecture.yaml",
        "release/v730-*",
        "scripts/*v730*",
        "tests/unit/test_v730_*",
    )
    for path_class in required:
        assert path_class in lean


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_v730_finalizer_and_exact_validator_are_non_publishing(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    package = tmp_path / "package"
    (root / "release").mkdir(parents=True)
    package.mkdir()
    (root / "release/RELEASE_MANIFEST_V730_CANDIDATE.md").write_text(
        "# v7.3.0 candidate\nPublication is not authorized.\n", encoding="utf-8"
    )
    (root / "release/v730-notion-schema-migration.yaml").write_text(
        "status: candidate_unapplied\nproduction_apply_authorized: false\n",
        encoding="utf-8",
    )
    (package / "atlas_ros-7.3.0.tar.gz").write_bytes(b"source")
    (package / "atlas_ros-7.3.0-py3-none-any.whl").write_bytes(b"wheel")
    _write_json(package / "installed.json", [{"name": "atlas-ros", "version": "7.3.0"}])
    _write_json(package / "performance.json", {"status": "passed", "provider_writes": 0})
    _write_json(
        package / "migration-validation.json",
        {"status": "validated_unapplied", "live_writes": 0},
    )
    _write_json(package / "validation-summary.json", {"status": "passed", "provider_writes": 0})
    commit = "a" * 40
    identity = assemble(
        repository_root=root,
        package_root=package,
        source_commit=commit,
        source_timestamp="2026-07-28T16:00:00+00:00",
        installed_packages_path=package / "installed.json",
        performance_path=package / "performance.json",
        migration_receipt_path=package / "migration-validation.json",
        validation_summary_path=package / "validation-summary.json",
    )
    assert identity["provider_writes"] == 0
    assert identity["build_count"] == 1
    assert identity["production_promotion_authorized"] is False
    assert identity["authority_activated"] is False
    checksum_lines = []
    for path in sorted(package.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS":
            import hashlib

            checksum_lines.append(
                f"{hashlib.sha256(path.read_bytes()).hexdigest()}  "
                f"{path.relative_to(package)}"
            )
    (package / "SHA256SUMS").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    result = validate(package, commit)
    assert result["completion_state"] == "IMPLEMENTATION READY FOR RYAN PROMOTION REVIEW"
    assert result["provider_writes"] == 0


def test_v730_exact_validator_rejects_live_action_claim(tmp_path: Path) -> None:
    package = tmp_path / "package"
    package.mkdir()
    _write_json(
        package / "FINAL_PACKAGE_IDENTITY.json",
        {
            "candidate_commit": "a" * 40,
            "release_version": "7.3.0",
            "provider_writes": 1,
        },
    )
    (package / "SHA256SUMS").write_text("", encoding="utf-8")
    with pytest.raises((CandidateValidationError, FileNotFoundError)):
        validate(package, "a" * 40)
