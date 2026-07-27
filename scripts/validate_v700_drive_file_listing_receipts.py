#!/usr/bin/env python3
"""Validate per-folder Google Drive file-listing receipts for Atlas ROS v7."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.validate_v700_drive_folder_tree import expand_compact_tree


class DriveFileListingReceiptError(ValueError):
    """Raised when file-listing receipts are incomplete or contradictory."""


def canonical_sha256(payload: dict[str, Any]) -> str:
    """Return a deterministic SHA-256 for one JSON object."""
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _sha(value: Any, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise DriveFileListingReceiptError(f"{field} must be a lowercase SHA-256")
    if any(character not in "0123456789abcdef" for character in value):
        raise DriveFileListingReceiptError(f"{field} must be a lowercase SHA-256")
    return value


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise DriveFileListingReceiptError(
            f"{field} must be a list of non-empty strings"
        )
    if len(value) != len(set(value)):
        raise DriveFileListingReceiptError(f"{field} contains duplicates")
    return value


def validate_file_listing_receipts(
    payload: dict[str, Any],
    *,
    inventory_payload: dict[str, Any],
    folder_payload: dict[str, Any],
) -> dict[str, Any]:
    """Bind every inventory record to one complete direct-folder listing."""
    if payload.get("schema_version") != "1.0":
        raise DriveFileListingReceiptError(
            "file listing receipt schema_version must be 1.0"
        )

    source_root_id = payload.get("source_root_id")
    if (
        not isinstance(source_root_id, str)
        or not source_root_id.strip()
        or source_root_id != folder_payload.get("source_root_id")
        or source_root_id != inventory_payload.get("source_root_id")
    ):
        raise DriveFileListingReceiptError("file listing source root mismatch")

    folder_tree_sha256 = _sha(
        payload.get("folder_tree_sha256"),
        "folder_tree_sha256",
    )
    if folder_tree_sha256 != folder_payload.get("folder_tree_sha256"):
        raise DriveFileListingReceiptError(
            "file listings are not bound to the current folder tree"
        )

    inventory_sha256 = _sha(
        payload.get("inventory_sha256"),
        "inventory_sha256",
    )
    if inventory_sha256 != inventory_payload.get("inventory_sha256"):
        raise DriveFileListingReceiptError(
            "file listings are not bound to the current file inventory"
        )

    expanded = expand_compact_tree(folder_payload)
    known_folder_ids = {
        record["folder_id"] for record in expanded["folders"]
    }

    scanned_folder_ids = _string_list(
        inventory_payload.get("scanned_folder_ids"),
        "inventory scanned_folder_ids",
    )
    inventory_records = inventory_payload.get("records")
    if not isinstance(inventory_records, list) or not inventory_records:
        raise DriveFileListingReceiptError(
            "file inventory records must be non-empty"
        )

    inventory_by_id: dict[str, dict[str, Any]] = {}
    for raw in inventory_records:
        if not isinstance(raw, dict):
            raise DriveFileListingReceiptError(
                "every file inventory record must be an object"
            )
        file_id = raw.get("file_id")
        parent_id = raw.get("parent_folder_id")
        if not isinstance(file_id, str) or not file_id.strip():
            raise DriveFileListingReceiptError("file inventory record lacks file_id")
        if file_id in inventory_by_id:
            raise DriveFileListingReceiptError(
                f"duplicate inventory file_id: {file_id}"
            )
        if parent_id not in known_folder_ids:
            raise DriveFileListingReceiptError(
                f"inventory file {file_id} has unknown parent {parent_id}"
            )
        inventory_by_id[file_id] = raw

    raw_listings = payload.get("listings")
    if not isinstance(raw_listings, list) or not raw_listings:
        raise DriveFileListingReceiptError("listings must be a non-empty list")

    listed_folder_ids: set[str] = set()
    bound_file_ids: set[str] = set()
    incomplete_listing_folder_ids: list[str] = []
    inaccessible_file_ids: set[str] = set()
    total_unconsumed_page_tokens = 0

    for raw_listing in raw_listings:
        if not isinstance(raw_listing, dict):
            raise DriveFileListingReceiptError(
                "every file listing receipt must be an object"
            )
        folder_id = raw_listing.get("folder_id")
        if not isinstance(folder_id, str) or not folder_id.strip():
            raise DriveFileListingReceiptError("folder_id is required")
        if folder_id not in known_folder_ids:
            raise DriveFileListingReceiptError(
                f"file listing contains unknown folder {folder_id}"
            )
        if folder_id in listed_folder_ids:
            raise DriveFileListingReceiptError(
                f"duplicate file listing for folder {folder_id}"
            )
        listed_folder_ids.add(folder_id)

        listing_complete = raw_listing.get("listing_complete")
        if not isinstance(listing_complete, bool):
            raise DriveFileListingReceiptError(
                f"listing_complete must be boolean for folder {folder_id}"
            )
        if not listing_complete:
            incomplete_listing_folder_ids.append(folder_id)

        unconsumed = raw_listing.get("unconsumed_page_tokens")
        if not isinstance(unconsumed, int) or isinstance(unconsumed, bool):
            raise DriveFileListingReceiptError(
                f"unconsumed_page_tokens must be integer for folder {folder_id}"
            )
        if unconsumed < 0:
            raise DriveFileListingReceiptError(
                f"negative unconsumed_page_tokens for folder {folder_id}"
            )
        total_unconsumed_page_tokens += unconsumed

        inaccessible = _string_list(
            raw_listing.get("inaccessible_file_ids"),
            f"inaccessible_file_ids for folder {folder_id}",
        )
        inaccessible_file_ids.update(inaccessible)

        file_ids = _string_list(
            raw_listing.get("file_ids"),
            f"file_ids for folder {folder_id}",
        )
        for file_id in file_ids:
            record = inventory_by_id.get(file_id)
            if record is None:
                raise DriveFileListingReceiptError(
                    f"listing references unknown file {file_id}"
                )
            if record.get("parent_folder_id") != folder_id:
                raise DriveFileListingReceiptError(
                    f"file {file_id} parent does not match listing folder"
                )
            if file_id in bound_file_ids:
                raise DriveFileListingReceiptError(
                    f"file {file_id} appears in multiple listing receipts"
                )
            bound_file_ids.add(file_id)

        expected_listing_sha256 = _sha(
            raw_listing.get("listing_sha256"),
            f"listing_sha256 for folder {folder_id}",
        )
        unsigned_listing = dict(raw_listing)
        unsigned_listing.pop("listing_sha256", None)
        actual_listing_sha256 = canonical_sha256(unsigned_listing)
        if expected_listing_sha256 != actual_listing_sha256:
            raise DriveFileListingReceiptError(
                f"file listing digest mismatch for folder {folder_id}"
            )

    if set(scanned_folder_ids) != listed_folder_ids:
        raise DriveFileListingReceiptError(
            "listing receipt folders do not match inventory scanned_folder_ids"
        )

    inventory_file_ids = set(inventory_by_id)
    if bound_file_ids != inventory_file_ids:
        missing = sorted(inventory_file_ids - bound_file_ids)
        unknown = sorted(bound_file_ids - inventory_file_ids)
        detail = []
        if missing:
            detail.append("unbound inventory files: " + ", ".join(missing))
        if unknown:
            detail.append("unknown bound files: " + ", ".join(unknown))
        raise DriveFileListingReceiptError("; ".join(detail))

    inventory_unconsumed = inventory_payload.get("unconsumed_page_tokens")
    if inventory_unconsumed != total_unconsumed_page_tokens:
        raise DriveFileListingReceiptError(
            "listing page-token total differs from file inventory"
        )
    inventory_inaccessible = inventory_payload.get("inaccessible_file_ids")
    if not isinstance(inventory_inaccessible, list):
        raise DriveFileListingReceiptError(
            "inventory inaccessible_file_ids must be a list"
        )
    if set(inventory_inaccessible) != inaccessible_file_ids:
        raise DriveFileListingReceiptError(
            "listing inaccessible files differ from file inventory"
        )

    enumeration_complete = inventory_payload.get("enumeration_complete")
    if not isinstance(enumeration_complete, bool):
        raise DriveFileListingReceiptError(
            "inventory enumeration_complete must be a boolean"
        )
    unscanned_folder_ids = sorted(known_folder_ids - listed_folder_ids)
    listing_evidence_complete = (
        not unscanned_folder_ids
        and not incomplete_listing_folder_ids
        and total_unconsumed_page_tokens == 0
        and not inaccessible_file_ids
    )
    if enumeration_complete != listing_evidence_complete:
        raise DriveFileListingReceiptError(
            "inventory enumeration_complete differs from listing receipts"
        )

    expected_set_sha256 = _sha(
        payload.get("listing_set_sha256"),
        "listing_set_sha256",
    )
    unsigned = dict(payload)
    unsigned.pop("listing_set_sha256", None)
    actual_set_sha256 = canonical_sha256(unsigned)
    if expected_set_sha256 != actual_set_sha256:
        raise DriveFileListingReceiptError("file listing set digest mismatch")

    return {
        "schema_version": "1.0",
        "status": (
            "complete_file_listing_receipts"
            if listing_evidence_complete
            else "partial_file_listing_receipts"
        ),
        "source_root_id": source_root_id,
        "folder_tree_sha256": folder_tree_sha256,
        "inventory_sha256": inventory_sha256,
        "known_folder_count": len(known_folder_ids),
        "listed_folder_count": len(listed_folder_ids),
        "unscanned_folder_count": len(unscanned_folder_ids),
        "unscanned_folder_ids": unscanned_folder_ids,
        "file_count": len(inventory_file_ids),
        "bound_file_count": len(bound_file_ids),
        "incomplete_listing_folder_ids": sorted(
            incomplete_listing_folder_ids
        ),
        "unconsumed_page_tokens": total_unconsumed_page_tokens,
        "inaccessible_file_ids": sorted(inaccessible_file_ids),
        "listing_set_sha256": actual_set_sha256,
        "enumeration_complete": enumeration_complete,
        "provider_writes": 0,
        "drive_retirement_authorized": False,
    }


def load_and_validate(
    receipt_path: Path,
    *,
    inventory_path: Path,
    folder_path: Path,
) -> dict[str, Any]:
    """Load listing receipts and their bound inventory and folder evidence."""
    try:
        receipts = json.loads(receipt_path.read_text(encoding="utf-8"))
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        folders = json.loads(folder_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DriveFileListingReceiptError(
            "invalid Drive file listing receipt JSON"
        ) from error
    if not all(isinstance(value, dict) for value in (receipts, inventory, folders)):
        raise DriveFileListingReceiptError(
            "Drive listing receipt evidence must be JSON objects"
        )
    return validate_file_listing_receipts(
        receipts,
        inventory_payload=inventory,
        folder_payload=folders,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipts", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--folder-tree", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = load_and_validate(
        args.receipts,
        inventory_path=args.inventory,
        folder_path=args.folder_tree,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
