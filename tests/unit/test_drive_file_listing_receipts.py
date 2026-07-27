from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_v700_drive_file_listing_receipts import (
    DriveFileListingReceiptError,
    canonical_sha256,
    load_and_validate,
    validate_file_listing_receipts,
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
    tree = folder_evidence()
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "source_root_id": "root",
        "folder_tree_sha256": tree["folder_tree_sha256"],
        "enumeration_complete": False,
        "content_checksums_complete": False,
        "scanned_folder_ids": ["root"],
        "unconsumed_page_tokens": 0,
        "inaccessible_file_ids": [],
        "records": [
            {
                "file_id": "file-one",
                "parent_folder_id": "root",
            }
        ],
    }
    payload["inventory_sha256"] = canonical_sha256(payload)
    return payload


def receipts() -> dict[str, object]:
    item = {
        "folder_id": "root",
        "listing_complete": True,
        "unconsumed_page_tokens": 0,
        "inaccessible_file_ids": [],
        "file_ids": ["file-one"],
    }
    item["listing_sha256"] = canonical_sha256(item)
    inv = inventory()
    tree = folder_evidence()
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "source_root_id": "root",
        "folder_tree_sha256": tree["folder_tree_sha256"],
        "inventory_sha256": inv["inventory_sha256"],
        "listings": [item],
    }
    payload["listing_set_sha256"] = canonical_sha256(payload)
    return payload


def resign(payload: dict[str, object]) -> None:
    payload.pop("listing_set_sha256", None)
    payload["listing_set_sha256"] = canonical_sha256(payload)


def test_partial_receipts_bind_every_current_inventory_record() -> None:
    result = validate_file_listing_receipts(
        receipts(),
        inventory_payload=inventory(),
        folder_payload=folder_evidence(),
    )

    assert result["status"] == "partial_file_listing_receipts"
    assert result["known_folder_count"] == 2
    assert result["listed_folder_count"] == 1
    assert result["unscanned_folder_ids"] == ["child"]
    assert result["file_count"] == 1
    assert result["bound_file_count"] == 1
    assert result["provider_writes"] == 0
    assert result["drive_retirement_authorized"] is False


def test_listing_digest_tampering_is_rejected() -> None:
    payload = receipts()
    payload["listings"][0]["file_ids"].append("tampered")
    resign(payload)

    with pytest.raises(
        DriveFileListingReceiptError,
        match="listing digest mismatch",
    ):
        validate_file_listing_receipts(
            payload,
            inventory_payload=inventory(),
            folder_payload=folder_evidence(),
        )


def test_unbound_inventory_file_is_rejected() -> None:
    payload = receipts()
    payload["listings"][0]["file_ids"] = []
    listing = payload["listings"][0]
    listing.pop("listing_sha256", None)
    listing["listing_sha256"] = canonical_sha256(listing)
    resign(payload)

    with pytest.raises(
        DriveFileListingReceiptError,
        match="unbound inventory files",
    ):
        validate_file_listing_receipts(
            payload,
            inventory_payload=inventory(),
            folder_payload=folder_evidence(),
        )


def test_parent_mismatch_and_scanned_folder_mismatch_are_rejected() -> None:
    inv = inventory()
    inv["records"][0]["parent_folder_id"] = "child"
    inv.pop("inventory_sha256", None)
    inv["inventory_sha256"] = canonical_sha256(inv)
    payload = receipts()
    payload["inventory_sha256"] = inv["inventory_sha256"]
    resign(payload)

    with pytest.raises(
        DriveFileListingReceiptError,
        match="parent does not match",
    ):
        validate_file_listing_receipts(
            payload,
            inventory_payload=inv,
            folder_payload=folder_evidence(),
        )

    inv = inventory()
    inv["scanned_folder_ids"] = ["child"]
    inv.pop("inventory_sha256", None)
    inv["inventory_sha256"] = canonical_sha256(inv)
    payload = receipts()
    payload["inventory_sha256"] = inv["inventory_sha256"]
    resign(payload)
    with pytest.raises(
        DriveFileListingReceiptError,
        match="do not match inventory scanned_folder_ids",
    ):
        validate_file_listing_receipts(
            payload,
            inventory_payload=inv,
            folder_payload=folder_evidence(),
        )


def test_complete_enumeration_requires_receipts_for_every_folder() -> None:
    inv = inventory()
    inv["enumeration_complete"] = True
    inv.pop("inventory_sha256", None)
    inv["inventory_sha256"] = canonical_sha256(inv)
    payload = receipts()
    payload["inventory_sha256"] = inv["inventory_sha256"]
    resign(payload)

    with pytest.raises(
        DriveFileListingReceiptError,
        match="enumeration_complete differs",
    ):
        validate_file_listing_receipts(
            payload,
            inventory_payload=inv,
            folder_payload=folder_evidence(),
        )


def test_receipt_round_trip(tmp_path: Path) -> None:
    receipt_path = tmp_path / "receipts.json"
    inventory_path = tmp_path / "inventory.json"
    folder_path = tmp_path / "folders.json"
    receipt_path.write_text(json.dumps(receipts()), encoding="utf-8")
    inventory_path.write_text(json.dumps(inventory()), encoding="utf-8")
    folder_path.write_text(json.dumps(folder_evidence()), encoding="utf-8")

    result = load_and_validate(
        receipt_path,
        inventory_path=inventory_path,
        folder_path=folder_path,
    )

    assert result["status"] == "partial_file_listing_receipts"
