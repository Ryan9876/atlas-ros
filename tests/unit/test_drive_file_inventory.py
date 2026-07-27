from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_v700_drive_file_inventory import (
    DriveFileInventoryError,
    canonical_sha256,
    load_and_validate,
    validate_file_inventory,
)
from scripts.validate_v700_drive_folder_traversal import canonical_sha256 as folder_sha


def folder_evidence() -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "captured_on": "2026-07-27",
        "source_root_id": "root",
        "folder_traversal_complete": True,
        "item_inventory_complete": False,
        "file_content_checksums_complete": False,
        "evidence_basis": "unit test",
        "tree": ["root", "Root", [["child", "Child", []]]],
    }
    payload["folder_tree_sha256"] = folder_sha(payload)
    return payload


def inventory() -> dict[str, object]:
    folder = folder_evidence()
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "captured_on": "2026-07-27",
        "source_root_id": "root",
        "folder_tree_sha256": folder["folder_tree_sha256"],
        "enumeration_complete": False,
        "content_checksums_complete": False,
        "scanned_folder_ids": ["root"],
        "unconsumed_page_tokens": 0,
        "inaccessible_file_ids": [],
        "records": [
            {
                "file_id": "bootstrap",
                "parent_folder_id": "root",
                "title": "RELEASE_INDEX.md",
                "mime_type": "text/markdown",
                "size_bytes": 100,
                "modified_time": "2026-07-27T00:00:00Z",
                "capture_method": "raw_bytes",
                "content_sha256": "a" * 64,
                "classification": "current_bootstrap",
                "disposition": "stage_github",
                "github_target": "governance/RELEASE_INDEX.md",
                "github_content_sha256": "a" * 64,
                "content_equivalent": True,
                "exception_id": None,
                "notes": "",
            },
            {
                "file_id": "credential",
                "parent_folder_id": "root",
                "title": "credential.json",
                "mime_type": "application/json",
                "size_bytes": 200,
                "modified_time": "2026-07-27T00:00:00Z",
                "capture_method": "metadata_only_sensitive",
                "content_sha256": None,
                "classification": "sensitive_credential",
                "disposition": "security_review_required",
                "github_target": None,
                "github_content_sha256": None,
                "content_equivalent": False,
                "exception_id": None,
                "notes": "",
            },
        ],
    }
    payload["inventory_sha256"] = canonical_sha256(payload)
    return payload


def resign(payload: dict[str, object]) -> dict[str, object]:
    payload.pop("inventory_sha256", None)
    payload["inventory_sha256"] = canonical_sha256(payload)
    return payload


def test_partial_inventory_remains_fail_closed() -> None:
    result = validate_file_inventory(inventory(), folder_payload=folder_evidence())

    assert result["status"] == "partial_file_inventory"
    assert result["known_folder_count"] == 2
    assert result["scanned_folder_count"] == 1
    assert result["sensitive_item_count"] == 1
    assert result["promotion_ready"] is False
    assert result["provider_writes"] == 0
    assert result["credential_action_authorized"] is False


def test_sensitive_item_cannot_include_content() -> None:
    payload = inventory()
    payload["records"][1]["content_sha256"] = "b" * 64
    resign(payload)

    with pytest.raises(DriveFileInventoryError, match="cannot include content digests"):
        validate_file_inventory(payload, folder_payload=folder_evidence())


def test_unknown_parent_is_rejected() -> None:
    payload = inventory()
    payload["records"][0]["parent_folder_id"] = "unknown"
    resign(payload)

    with pytest.raises(DriveFileInventoryError, match="unknown parent folder"):
        validate_file_inventory(payload, folder_payload=folder_evidence())


def test_complete_enumeration_requires_every_folder() -> None:
    payload = inventory()
    payload["enumeration_complete"] = True
    resign(payload)

    with pytest.raises(DriveFileInventoryError, match="enumeration cannot be complete"):
        validate_file_inventory(payload, folder_payload=folder_evidence())


def test_checksum_mismatch_is_rejected() -> None:
    payload = inventory()
    payload["records"][0]["github_content_sha256"] = "b" * 64
    resign(payload)

    with pytest.raises(DriveFileInventoryError, match="checksums differ"):
        validate_file_inventory(payload, folder_payload=folder_evidence())


def test_legacy_retention_requires_exception() -> None:
    payload = inventory()
    record = payload["records"][0]
    record["classification"] = "historical_release_artifact"
    record["disposition"] = "retain_legacy_read_only"
    record["content_equivalent"] = False
    record["github_target"] = None
    record["github_content_sha256"] = None
    record["exception_id"] = None
    resign(payload)

    with pytest.raises(DriveFileInventoryError, match="requires a governed exception"):
        validate_file_inventory(payload, folder_payload=folder_evidence())


def test_digest_tampering_is_rejected(tmp_path: Path) -> None:
    folder = folder_evidence()
    payload = inventory()
    folder_path = tmp_path / "folders.json"
    inventory_path = tmp_path / "inventory.json"
    folder_path.write_text(json.dumps(folder), encoding="utf-8")
    inventory_path.write_text(json.dumps(payload), encoding="utf-8")
    payload["records"][0]["title"] = "Tampered"
    inventory_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(DriveFileInventoryError, match="digest mismatch"):
        load_and_validate(inventory_path, folder_path=folder_path)
