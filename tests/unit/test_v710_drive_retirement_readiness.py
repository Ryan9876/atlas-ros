from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from tools.release.drive_dependency_inventory import (
    assert_zero_current_drive_dependencies,
    inventory_drive_dependencies,
)
from tools.release.drive_retirement import (
    DriveRetirementAuthorization,
    DriveRetirementPreflight,
    RetirementPreconditionError,
    simulate_retirement_transaction,
)


def test_dependency_inventory_classifies_current_and_historical_references(
    tmp_path: Path,
) -> None:
    runtime = tmp_path / "src" / "atlas_ros" / "runtime" / "bad.py"
    runtime.parent.mkdir(parents=True)
    runtime.write_text("# Google Drive required at runtime\n", encoding="utf-8")
    docs = tmp_path / "docs" / "history.md"
    docs.parent.mkdir()
    docs.write_text("Google Drive remains optional historical storage.\n", encoding="utf-8")
    tool = tmp_path / "tools" / "release" / "drive_migration_cli.py"
    tool.parent.mkdir(parents=True)
    tool.write_text("# Google Drive migration tooling\n", encoding="utf-8")

    inventory = inventory_drive_dependencies(tmp_path)

    assert inventory.summary == {
        "current_runtime": 1,
        "historical_reference": 1,
        "migration_tooling": 1,
    }
    with pytest.raises(ValueError, match="current Google Drive dependencies"):
        assert_zero_current_drive_dependencies(inventory)


def preflight() -> DriveRetirementPreflight:
    return DriveRetirementPreflight(
        dependency_inventory_sha256="a" * 64,
        historical_inventory_sha256="b" * 64,
        exclusion_review_sha256="c" * 64,
        zero_current_dependencies=True,
        historical_inventory_complete=True,
        exclusion_review_complete=True,
        rollback_restoration_passed=True,
        post_promotion_readback_passed=True,
        account_scope="ryan-drive-account",
        credential_scope_sha256="d" * 64,
        target_ids=("folder-1", "connector-1"),
        object_count=2,
        byte_count=1024,
    )


def authorization() -> DriveRetirementAuthorization:
    return DriveRetirementAuthorization(
        authorization_id="ryan-drive-retirement-001",
        transaction_id="drive-retirement-001",
        dependency_inventory_sha256="a" * 64,
        historical_inventory_sha256="b" * 64,
        exclusion_review_sha256="c" * 64,
        account_scope="ryan-drive-account",
        credential_scope_sha256="d" * 64,
        object_budget=2,
        byte_budget=1024,
        exact_target_ids=("folder-1", "connector-1"),
        connector_removal_authorized=True,
    )


def test_retirement_simulation_is_exact_and_non_destructive() -> None:
    receipt = simulate_retirement_transaction(preflight(), authorization())

    assert receipt.status == "simulated"
    assert receipt.provider_writes == 0
    assert receipt.destructive_actions == 0
    assert receipt.authorized_actions == ("connector_removal",)


def test_retirement_simulation_rejects_incomplete_or_mismatched_evidence() -> None:
    with pytest.raises(RetirementPreconditionError, match="current Drive dependencies"):
        simulate_retirement_transaction(
            replace(preflight(), zero_current_dependencies=False), authorization()
        )
    with pytest.raises(RetirementPreconditionError, match="target set"):
        simulate_retirement_transaction(
            preflight(), replace(authorization(), exact_target_ids=("other",))
        )
