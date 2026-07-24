from datetime import datetime, timezone
from typing import Literal

import pytest
from pydantic import ValidationError

from atlas_ros.release.authority_migration import (
    DriveInventory,
    DriveItem,
    DriveRetention,
    ImplementationDisposition,
    ImplementationRecord,
    ImplementationRegistry,
    TargetAuthority,
    build_drive_inventory,
    classify_drive_item,
)

BOOTSTRAP_ID = "bootstrap"


def item(
    item_id: str,
    title: str,
    *,
    mime_type: str = "application/vnd.google-apps.folder",
    item_type: Literal["file", "folder"] = "folder",
) -> DriveItem:
    return DriveItem(
        id=item_id,
        title=title,
        url=f"https://example.invalid/{item_id}",
        mime_type=mime_type,
        item_type=item_type,
    )


def test_bootstrap_index_is_retained_as_fixed_pointer() -> None:
    result = classify_drive_item(
        item(
            BOOTSTRAP_ID,
            "RELEASE_INDEX.md",
            mime_type="text/markdown",
            item_type="file",
        ),
        bootstrap_file_id=BOOTSTRAP_ID,
    )
    assert result.target_authority == TargetAuthority.DRIVE_BOOTSTRAP
    assert result.drive_retention == DriveRetention.BOOTSTRAP
    assert result.deletion_authorized is False


def test_release_folder_migrates_to_github_and_remains_read_only() -> None:
    result = classify_drive_item(
        item("release", "Atlas ROS v5.1.1 Active"), bootstrap_file_id=BOOTSTRAP_ID
    )
    assert result.target_authority == TargetAuthority.GITHUB
    assert result.drive_retention == DriveRetention.LEGACY_READ_ONLY
    assert result.target_path.startswith("releases/legacy/")


def test_runtime_folder_requires_non_github_destination_review() -> None:
    result = classify_drive_item(
        item("runtime", "Runtime"), bootstrap_file_id=BOOTSTRAP_ID
    )
    assert result.target_authority == TargetAuthority.NOTION_OR_RUNTIME
    assert result.drive_retention == DriveRetention.REVIEW_REQUIRED
    assert result.checksum_required is False


def test_duplicate_google_release_index_is_temporary_migration() -> None:
    result = classify_drive_item(
        item(
            "duplicate",
            "RELEASE_INDEX.md",
            mime_type="application/vnd.google-apps.document",
            item_type="file",
        ),
        bootstrap_file_id=BOOTSTRAP_ID,
    )
    assert result.target_authority == TargetAuthority.GITHUB
    assert result.drive_retention == DriveRetention.TEMPORARY_MIGRATION


def test_inventory_summary_and_duplicate_ids_are_governed() -> None:
    inventory = build_drive_inventory(
        [
            item(
                BOOTSTRAP_ID,
                "RELEASE_INDEX.md",
                mime_type="text/markdown",
                item_type="file",
            ),
            item("release", "Atlas ROS v5.1.1 Active"),
        ],
        source_folder_id="root",
        bootstrap_file_id=BOOTSTRAP_ID,
    )
    assert inventory.summary == {"bootstrap": 1, "legacy_read_only": 1}

    with pytest.raises(ValidationError, match="duplicate item ids"):
        DriveInventory(
            generated_at=datetime.now(timezone.utc).isoformat(),
            source_folder_id="root",
            items=[inventory.items[0], inventory.items[0]],
            summary={"bootstrap": 2},
        )


def test_partial_implementation_requires_both_scopes() -> None:
    with pytest.raises(ValidationError, match="implemented and remaining scope"):
        ImplementationRecord(
            record_id="IDEA-11",
            title="GitHub-first authority",
            disposition=ImplementationDisposition.PARTIALLY_IMPLEMENTED,
            implemented_scope="Inventory schema",
            evidence=["commit:abc"],
        )


def test_registry_rejects_duplicate_record_ids() -> None:
    record = ImplementationRecord(
        record_id="IDEA-11",
        title="GitHub-first authority",
        disposition=ImplementationDisposition.IN_PROGRESS,
        evidence=["PR #10"],
    )
    with pytest.raises(ValidationError, match="duplicate record ids"):
        ImplementationRegistry(
            generated_at=datetime.now(timezone.utc).isoformat(),
            candidate_version="5.2.0.dev0",
            source_head="working-tree",
            records=[record, record],
        )
