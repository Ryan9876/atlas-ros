from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.validate_v800_cookbook import validate as validate_cookbook
from scripts.validate_v800_notion_migration import (
    MigrationValidationError,
    validate_migration,
)

ROOT = Path(__file__).resolve().parents[2]


def test_v800_migration_is_additive_unapplied_and_rollback_compatible() -> None:
    receipt = validate_migration(
        ROOT / "release/v800-notion-schema-migration.yaml",
        ROOT / "release/v800-notion-schema-fixture.json",
    )
    assert receipt["status"] == "validated_unapplied"
    assert receipt["destructive_operations"] == 0
    assert receipt["live_reads"] == 0
    assert receipt["live_writes"] == 0
    assert receipt["production_apply_authorized"] is False
    assert receipt["additive_fields"] == [
        "Command Digest",
        "Effective State",
        "Idempotency Identity",
        "Latest Reconciliation State",
        "Provenance",
        "Source Update",
        "Todoist Checkpoint ID",
        "Todoist Checkpoint URL",
    ]


def test_v800_migration_rejects_destructive_or_authorized_change(tmp_path: Path) -> None:
    migration = yaml.safe_load(
        (ROOT / "release/v800-notion-schema-migration.yaml").read_text()
    )
    migration["production_apply_authorized"] = True
    migration["destructive_operations"] = ["DROP COLUMN Status"]
    unsafe = tmp_path / "unsafe.yaml"
    unsafe.write_text(yaml.safe_dump(migration, sort_keys=False))
    with pytest.raises(MigrationValidationError):
        validate_migration(unsafe, ROOT / "release/v800-notion-schema-fixture.json")


def test_v800_cookbook_is_version_bound_and_fixture_verified() -> None:
    receipt = validate_cookbook(
        ROOT / "docs/operations/ATLAS_ROS_V800_DELEGATION_COOKBOOK.md",
        ROOT / "tests/fixtures/operational-awareness/v800-task-update-delegation.json",
    )
    assert receipt["status"] == "passed"
    assert receipt["provider_writes"] == 0


def test_v800_candidate_workflow_builds_once_and_never_publishes() -> None:
    workflow = (ROOT / ".github/workflows/v800-task-update-delegation-candidate.yml").read_text()
    assert workflow.count("python -m build") == 1
    assert "candidate_unapplied" in workflow
    assert "provider_writes': 0" in workflow
    assert "ACTIVE_VERSION" in workflow and "LIVE_AUTHORITY.json" in workflow
    assert "gh release create" not in workflow
    assert "git tag" not in workflow
    assert "agent/v8.0.0-task-update-delegation" in workflow


def test_v800_publication_control_requires_finalized_exact_authorization() -> None:
    workflow = (ROOT / ".github/workflows/v800-authorized-publication-controller.yml").read_text()
    assert "workflow_dispatch" in workflow
    assert "production-release" in workflow
    assert "V800_EXACT_PACKAGE_AUTHORIZATION.md" in workflow
    assert "! grep -q 'PENDING'" in workflow
    assert "python -m build" not in workflow
    assert "gh release create" in workflow
    assert "Publication does not activate production authority" in workflow


def test_v800_independent_readback_is_non_activating_and_restores_live_active() -> None:
    workflow = (ROOT / ".github/workflows/v800-independent-publication-readback.yml").read_text()
    assert "governance/AUTHORITY.json" in workflow
    assert "RESTORE_TAG" in workflow
    assert "rollback_v780_restoration" in workflow
    assert "authority_activated': False" in workflow
    assert "contents: write" not in workflow


def test_v800_draft_records_do_not_claim_authorization_or_activation() -> None:
    manifest = (ROOT / "release/RELEASE_MANIFEST_V800_DRAFT.md").read_text()
    authorization = (
        ROOT / "release/V800_EXACT_PACKAGE_AUTHORIZATION_TEMPLATE.md"
    ).read_text()
    report = (ROOT / "release/V800_FULL_VALIDATION_REPORT_DRAFT.md").read_text()
    assert "not authorized" in manifest.lower()
    assert "PENDING" in authorization
    assert "v7.8.0 remains Active" in report
