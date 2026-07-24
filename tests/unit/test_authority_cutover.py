from __future__ import annotations

from datetime import UTC, datetime

import pytest

from atlas_ros.release.authority_cutover import (
    DevelopmentRecordSnapshot,
    DriveAllowlist,
    RecursiveDriveInventory,
    RecursiveInventoryItem,
    reconcile_development_records,
)
from atlas_ros.release.authority_migration import DriveRetention, TargetAuthority


def github_item(item_id: str = "release") -> RecursiveInventoryItem:
    return RecursiveInventoryItem(
        id=item_id,
        title="Atlas ROS v5.1.1",
        url=f"https://drive.google.com/{item_id}",
        item_type="file",
        parent_id="root",
        relative_path=f"Atlas_ROS/{item_id}",
        target_authority=TargetAuthority.GITHUB,
        drive_retention=DriveRetention.LEGACY_READ_ONLY,
        target_path=f"releases/legacy/{item_id}",
        source_sha256="a" * 64,
        representation_sha256="a" * 64,
        representation_url=f"https://github.com/Ryan9876/atlas-ros/releases/{item_id}",
    )


def bootstrap_item() -> RecursiveInventoryItem:
    return RecursiveInventoryItem(
        id="bootstrap",
        title="RELEASE_INDEX.md",
        url="https://drive.google.com/bootstrap",
        item_type="file",
        parent_id="root",
        relative_path="Atlas_ROS/RELEASE_INDEX.md",
        target_authority=TargetAuthority.DRIVE_BOOTSTRAP,
        drive_retention=DriveRetention.BOOTSTRAP,
    )


def inventory(*items: RecursiveInventoryItem) -> RecursiveDriveInventory:
    summary: dict[str, int] = {}
    for item in items:
        key = item.drive_retention.value
        summary[key] = summary.get(key, 0) + 1
    return RecursiveDriveInventory(
        generated_at=datetime.now(UTC).isoformat(),
        source_folder_id="root",
        bootstrap_file_id="bootstrap",
        items=list(items),
        summary=summary,
    )


def test_recursive_inventory_accepts_checksum_bound_representations() -> None:
    result = inventory(bootstrap_item(), github_item())
    assert DriveAllowlist(bootstrap_file_id="bootstrap").violations(result) == ()


def test_github_representation_must_match_source_checksum() -> None:
    payload = github_item().model_dump()
    payload["representation_sha256"] = "b" * 64
    with pytest.raises(ValueError, match="checksum mismatch"):
        RecursiveInventoryItem.model_validate(payload)


def test_recursive_inventory_rejects_review_required_items() -> None:
    unresolved = RecursiveInventoryItem(
        id="unknown",
        title="Unknown",
        url="https://drive.google.com/unknown",
        item_type="file",
        parent_id="root",
        relative_path="Atlas_ROS/Unknown",
        target_authority=TargetAuthority.REVIEW_REQUIRED,
        drive_retention=DriveRetention.REVIEW_REQUIRED,
    )
    with pytest.raises(ValueError, match="unresolved items"):
        inventory(bootstrap_item(), unresolved)


def test_allowlist_rejects_temporary_migration_retention() -> None:
    payload = github_item("temporary").model_dump()
    payload["drive_retention"] = DriveRetention.TEMPORARY_MIGRATION
    temporary = RecursiveInventoryItem.model_validate(payload)
    result = inventory(bootstrap_item(), temporary)
    assert DriveAllowlist(bootstrap_file_id="bootstrap").violations(result) == ("temporary",)


def record(record_id: str, scope: str = "done") -> DevelopmentRecordSnapshot:
    return DevelopmentRecordSnapshot(
        record_id=record_id,
        title=record_id,
        disposition="fully_implemented",
        implemented_scope=scope,
        evidence=("PR #10",),
    )


def test_development_record_reconciliation_matches_both_directions() -> None:
    report = reconcile_development_records(
        [record("IDEA-8"), record("IDEA-11")],
        [record("IDEA-8"), record("IDEA-11")],
        source_head="abc123",
    )
    assert report.valid
    assert report.matched == ("IDEA-11", "IDEA-8")
    assert len(report.report_sha256) == 64


def test_development_record_reconciliation_reports_all_drift() -> None:
    report = reconcile_development_records(
        [record("IDEA-8"), record("IDEA-11")],
        [record("IDEA-8", "different"), record("IDEA-10")],
        source_head="abc123",
    )
    assert not report.valid
    assert report.github_only == ("IDEA-11",)
    assert report.notion_only == ("IDEA-10",)
    assert report.drifted == ("IDEA-8",)
