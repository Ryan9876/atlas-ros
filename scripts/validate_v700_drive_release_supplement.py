#!/usr/bin/env python3
"""Validate the checksum-bound Atlas ROS v5.0 Drive file supplement."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.validate_v700_drive_file_inventory import validate_file_inventory
from scripts.validate_v700_drive_file_listing_receipts import (
    validate_file_listing_receipts,
)
from scripts.validate_v700_drive_folder_tree import expand_compact_tree


class DriveReleaseSupplementError(ValueError):
    """Raised when one release-scoped Drive supplement is unsafe."""


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
        raise DriveReleaseSupplementError(
            f"{field} must be a lowercase SHA-256"
        )
    if any(character not in "0123456789abcdef" for character in value):
        raise DriveReleaseSupplementError(
            f"{field} must be a lowercase SHA-256"
        )
    return value


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DriveReleaseSupplementError(
            f"invalid JSON evidence: {path}"
        ) from error
    if not isinstance(value, dict):
        raise DriveReleaseSupplementError(
            f"JSON evidence must be an object: {path}"
        )
    return value


def validate_release_supplement(
    payload: dict[str, Any],
    *,
    folder_payload: dict[str, Any],
    base_inventory: dict[str, Any],
    base_receipts: dict[str, Any],
) -> dict[str, Any]:
    """Validate one complete release supplement against fail-closed base data."""
    if payload.get("schema_version") != "1.0":
        raise DriveReleaseSupplementError(
            "release supplement schema_version must be 1.0"
        )
    if payload.get("release") != "5.0":
        raise DriveReleaseSupplementError(
            "this supplement must identify historical release 5.0"
        )
    source_root_id = folder_payload.get("source_root_id")
    if payload.get("source_root_id") != source_root_id:
        raise DriveReleaseSupplementError(
            "release supplement source root mismatch"
        )
    folder_tree_sha256 = _sha(
        payload.get("folder_tree_sha256"),
        "folder_tree_sha256",
    )
    if folder_tree_sha256 != folder_payload.get("folder_tree_sha256"):
        raise DriveReleaseSupplementError(
            "release supplement is not bound to the current folder tree"
        )
    if payload.get("base_inventory_sha256") != base_inventory.get(
        "inventory_sha256"
    ):
        raise DriveReleaseSupplementError(
            "release supplement is not bound to the base inventory"
        )
    if payload.get("base_listing_set_sha256") != base_receipts.get(
        "listing_set_sha256"
    ):
        raise DriveReleaseSupplementError(
            "release supplement is not bound to the base listings"
        )

    base_result = validate_file_inventory(
        base_inventory,
        folder_payload=folder_payload,
    )
    receipt_result = validate_file_listing_receipts(
        base_receipts,
        inventory_payload=base_inventory,
        folder_payload=folder_payload,
    )
    if receipt_result["bound_file_count"] != base_result["file_count"]:
        raise DriveReleaseSupplementError(
            "base file inventory and listing receipts are not closed"
        )

    expanded = expand_compact_tree(folder_payload)
    known_folder_ids = {
        record["folder_id"] for record in expanded["folders"]
    }
    scanned = payload.get("scanned_folder_ids")
    if (
        not isinstance(scanned, list)
        or len(scanned) != 2
        or not all(isinstance(item, str) and item for item in scanned)
        or len(set(scanned)) != len(scanned)
    ):
        raise DriveReleaseSupplementError(
            "release supplement must scan exactly two unique folders"
        )
    if not set(scanned).issubset(known_folder_ids):
        raise DriveReleaseSupplementError(
            "release supplement contains an unknown folder"
        )
    if set(scanned) & set(base_inventory.get("scanned_folder_ids", [])):
        raise DriveReleaseSupplementError(
            "release supplement folders overlap the base inventory"
        )
    if payload.get("enumeration_complete") is not True:
        raise DriveReleaseSupplementError(
            "v5.0 supplement enumeration must be complete"
        )
    if payload.get("content_checksums_complete") is not True:
        raise DriveReleaseSupplementError(
            "v5.0 supplement content checksums must be complete"
        )
    if payload.get("inaccessible_file_ids") != []:
        raise DriveReleaseSupplementError(
            "v5.0 supplement cannot contain inaccessible files"
        )
    if payload.get("unconsumed_page_tokens") != 0:
        raise DriveReleaseSupplementError(
            "v5.0 supplement cannot retain page tokens"
        )
    if payload.get("classification") != "historical_release_artifact":
        raise DriveReleaseSupplementError(
            "v5.0 files must be historical release artifacts"
        )
    if payload.get("disposition") != "retain_legacy_read_only":
        raise DriveReleaseSupplementError(
            "v5.0 files must remain legacy read only"
        )
    if payload.get("exception_id") != "V700-DRIVE-LEGACY-READ-ONLY":
        raise DriveReleaseSupplementError(
            "v5.0 files require the governed legacy exception"
        )

    raw_files = payload.get("files")
    if not isinstance(raw_files, list) or len(raw_files) != 20:
        raise DriveReleaseSupplementError(
            "v5.0 supplement must contain exactly 20 files"
        )
    base_ids = {
        record.get("file_id") for record in base_inventory.get("records", [])
    }
    file_ids: set[str] = set()
    file_parent: dict[str, str] = {}
    file_sha: dict[str, str] = {}
    for raw in raw_files:
        if not isinstance(raw, list) or len(raw) != 7:
            raise DriveReleaseSupplementError(
                "every v5.0 file must use the seven-field compact contract"
            )
        (
            file_id,
            parent_id,
            title,
            mime_type,
            size_bytes,
            modified_time,
            content_sha256,
        ) = raw
        if not all(
            isinstance(value, str) and value
            for value in (
                file_id,
                parent_id,
                title,
                mime_type,
                modified_time,
            )
        ):
            raise DriveReleaseSupplementError(
                "v5.0 file identity fields must be non-empty strings"
            )
        if not isinstance(size_bytes, int) or isinstance(size_bytes, bool):
            raise DriveReleaseSupplementError(
                f"invalid v5.0 file size: {file_id}"
            )
        if size_bytes < 0:
            raise DriveReleaseSupplementError(
                f"negative v5.0 file size: {file_id}"
            )
        digest = _sha(content_sha256, f"content SHA-256 for {file_id}")
        if file_id in file_ids or file_id in base_ids:
            raise DriveReleaseSupplementError(
                f"duplicate Drive file ID: {file_id}"
            )
        if parent_id not in scanned:
            raise DriveReleaseSupplementError(
                f"v5.0 file has unscanned parent: {file_id}"
            )
        file_ids.add(file_id)
        file_parent[file_id] = parent_id
        file_sha[file_id] = digest

    package_id = payload.get("candidate_package_file_id")
    checksum_id = payload.get("candidate_checksum_file_id")
    if package_id not in file_ids or checksum_id not in file_ids:
        raise DriveReleaseSupplementError(
            "candidate package evidence is not present in the supplement"
        )
    package_sha = _sha(
        payload.get("candidate_package_sha256"),
        "candidate package SHA-256",
    )
    declared_sha = _sha(
        payload.get("candidate_checksum_declared_sha256"),
        "declared candidate SHA-256",
    )
    if package_sha != declared_sha or package_sha != file_sha[package_id]:
        raise DriveReleaseSupplementError(
            "v5.0 candidate package checksum does not reconcile"
        )

    raw_listings = payload.get("listings")
    if not isinstance(raw_listings, list) or len(raw_listings) != 2:
        raise DriveReleaseSupplementError(
            "v5.0 supplement must contain two listing receipts"
        )
    listed_folders: set[str] = set()
    bound_files: set[str] = set()
    for listing in raw_listings:
        if not isinstance(listing, dict):
            raise DriveReleaseSupplementError(
                "v5.0 listing receipt must be an object"
            )
        folder_id = listing.get("folder_id")
        if folder_id not in scanned or folder_id in listed_folders:
            raise DriveReleaseSupplementError(
                "v5.0 listing folder is invalid or duplicated"
            )
        listed_folders.add(folder_id)
        if listing.get("listing_complete") is not True:
            raise DriveReleaseSupplementError(
                f"incomplete v5.0 listing: {folder_id}"
            )
        if listing.get("unconsumed_page_tokens") != 0:
            raise DriveReleaseSupplementError(
                f"v5.0 listing retains a page token: {folder_id}"
            )
        if listing.get("inaccessible_file_ids") != []:
            raise DriveReleaseSupplementError(
                f"v5.0 listing contains inaccessible files: {folder_id}"
            )
        ids = listing.get("file_ids")
        if (
            not isinstance(ids, list)
            or not all(isinstance(item, str) and item for item in ids)
            or len(ids) != len(set(ids))
        ):
            raise DriveReleaseSupplementError(
                f"invalid v5.0 file list: {folder_id}"
            )
        for file_id in ids:
            if file_id not in file_ids:
                raise DriveReleaseSupplementError(
                    f"listing references unknown v5.0 file: {file_id}"
                )
            if file_parent[file_id] != folder_id:
                raise DriveReleaseSupplementError(
                    f"v5.0 file parent mismatch: {file_id}"
                )
            if file_id in bound_files:
                raise DriveReleaseSupplementError(
                    f"v5.0 file appears in multiple listings: {file_id}"
                )
            bound_files.add(file_id)
        expected = _sha(
            listing.get("listing_sha256"),
            f"listing SHA-256 for {folder_id}",
        )
        unsigned_listing = dict(listing)
        unsigned_listing.pop("listing_sha256", None)
        if expected != canonical_sha256(unsigned_listing):
            raise DriveReleaseSupplementError(
                f"v5.0 listing digest mismatch: {folder_id}"
            )
    if listed_folders != set(scanned) or bound_files != file_ids:
        raise DriveReleaseSupplementError(
            "v5.0 listing receipts do not close the supplement"
        )

    if payload.get("provider_writes") != 0:
        raise DriveReleaseSupplementError(
            "v5.0 evidence cannot record provider writes"
        )
    if payload.get("drive_retirement_authorized") is not False:
        raise DriveReleaseSupplementError(
            "v5.0 evidence cannot authorize Drive retirement"
        )
    if payload.get("credential_action_authorized") is not False:
        raise DriveReleaseSupplementError(
            "v5.0 evidence cannot authorize credential actions"
        )
    expected_supplement_sha = _sha(
        payload.get("supplement_sha256"),
        "supplement_sha256",
    )
    unsigned = dict(payload)
    unsigned.pop("supplement_sha256", None)
    if expected_supplement_sha != canonical_sha256(unsigned):
        raise DriveReleaseSupplementError(
            "v5.0 supplement digest mismatch"
        )

    combined_scanned = base_result["scanned_folder_count"] + len(scanned)
    combined_files = base_result["file_count"] + len(file_ids)
    return {
        "schema_version": "1.0",
        "status": "partial_file_inventory_with_complete_v500_supplement",
        "release": "5.0",
        "supplement_sha256": expected_supplement_sha,
        "v500_scanned_folder_count": len(scanned),
        "v500_file_count": len(file_ids),
        "v500_content_hashed_count": len(file_ids),
        "v500_listing_count": len(raw_listings),
        "v500_candidate_checksum_reconciled": True,
        "combined_known_folder_count": base_result["known_folder_count"],
        "combined_scanned_folder_count": combined_scanned,
        "combined_unscanned_folder_count": (
            base_result["known_folder_count"] - combined_scanned
        ),
        "combined_file_count": combined_files,
        "combined_content_hashed_count": (
            base_result["content_hashed_count"] + len(file_ids)
        ),
        "combined_sensitive_item_count": base_result["sensitive_item_count"],
        "combined_verified_github_equivalence_count": (
            base_result["verified_github_equivalence_count"]
        ),
        "combined_governed_legacy_exception_count": (
            base_result["governed_legacy_exception_count"] + len(file_ids)
        ),
        "enumeration_complete": False,
        "content_checksums_complete": False,
        "promotion_ready": False,
        "provider_writes": 0,
        "drive_retirement_authorized": False,
        "credential_action_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--supplement", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--receipts", type=Path, required=True)
    parser.add_argument("--folder-tree", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = validate_release_supplement(
        _read_json(args.supplement),
        folder_payload=_read_json(args.folder_tree),
        base_inventory=_read_json(args.inventory),
        base_receipts=_read_json(args.receipts),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
