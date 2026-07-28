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
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _fail(message: str) -> None:
    raise DriveReleaseSupplementError(message)


def _sha(value: Any, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail(f"{field} must be a lowercase SHA-256")
    return value


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DriveReleaseSupplementError(
            f"invalid JSON evidence: {path}"
        ) from error
    if not isinstance(value, dict):
        _fail(f"JSON evidence must be an object: {path}")
    return value


def validate_release_supplement(
    payload: dict[str, Any],
    *,
    folder_payload: dict[str, Any],
    base_inventory: dict[str, Any],
    base_receipts: dict[str, Any],
) -> dict[str, Any]:
    """Validate v5.0 evidence without allowing it to unlock promotion."""
    if payload.get("schema_version") != "1.0":
        _fail("release supplement schema_version must be 1.0")
    if payload.get("release") != "5.0":
        _fail("this supplement must identify historical release 5.0")
    if payload.get("source_root_id") != folder_payload.get("source_root_id"):
        _fail("release supplement source root mismatch")
    tree_sha = _sha(payload.get("folder_tree_sha256"), "folder_tree_sha256")
    if tree_sha != folder_payload.get("folder_tree_sha256"):
        _fail("release supplement is not bound to the current folder tree")
    if payload.get("base_inventory_sha256") != base_inventory.get(
        "inventory_sha256"
    ):
        _fail("release supplement is not bound to the base inventory")
    if payload.get("base_listing_set_sha256") != base_receipts.get(
        "listing_set_sha256"
    ):
        _fail("release supplement is not bound to the base listings")

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
        _fail("base file inventory and listing receipts are not closed")

    known_folders = {
        record["folder_id"]
        for record in expand_compact_tree(folder_payload)["folders"]
    }
    scanned = payload.get("scanned_folder_ids")
    if (
        not isinstance(scanned, list)
        or len(scanned) != 1
        or not all(isinstance(item, str) and item for item in scanned)
        or len(set(scanned)) != len(scanned)
    ):
        _fail("v5.0 supplement must scan exactly one unique folder")
    if not set(scanned).issubset(known_folders):
        _fail("release supplement contains an unknown folder")
    if set(scanned) & set(base_inventory.get("scanned_folder_ids", [])):
        _fail("release supplement folders overlap the base inventory")
    if payload.get("enumeration_complete") is not True:
        _fail("v5.0 supplement enumeration must be complete")
    if payload.get("content_checksums_complete") is not True:
        _fail("v5.0 supplement content checksums must be complete")
    if payload.get("inaccessible_file_ids") != []:
        _fail("v5.0 supplement cannot contain inaccessible files")
    if payload.get("unconsumed_page_tokens") != 0:
        _fail("v5.0 supplement cannot retain page tokens")
    if payload.get("classification") != "historical_release_artifact":
        _fail("v5.0 files must be historical release artifacts")
    if payload.get("disposition") != "retain_legacy_read_only":
        _fail("v5.0 files must remain legacy read only")
    if payload.get("exception_id") != "V700-DRIVE-LEGACY-READ-ONLY":
        _fail("v5.0 files require the governed legacy exception")

    raw_files = payload.get("files")
    if not isinstance(raw_files, list) or len(raw_files) != 18:
        _fail("v5.0 supplement must contain exactly 18 files")
    base_ids = {
        record.get("file_id") for record in base_inventory.get("records", [])
    }
    file_ids: set[str] = set()
    file_parent: dict[str, str] = {}
    file_sha: dict[str, str] = {}
    for raw in raw_files:
        if not isinstance(raw, list) or len(raw) != 7:
            _fail("every v5.0 file must use the seven-field compact contract")
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
            _fail("v5.0 file identity fields must be non-empty strings")
        if (
            not isinstance(size_bytes, int)
            or isinstance(size_bytes, bool)
            or size_bytes < 0
        ):
            _fail(f"invalid v5.0 file size: {file_id}")
        digest = _sha(content_sha256, f"content SHA-256 for {file_id}")
        if file_id in file_ids or file_id in base_ids:
            _fail(f"duplicate Drive file ID: {file_id}")
        if parent_id not in scanned:
            _fail(f"v5.0 file has unscanned parent: {file_id}")
        file_ids.add(file_id)
        file_parent[file_id] = parent_id
        file_sha[file_id] = digest

    package_id = payload.get("candidate_package_file_id")
    checksum_id = payload.get("candidate_checksum_file_id")
    if package_id not in file_ids or checksum_id not in file_ids:
        _fail("candidate package evidence is not present in the supplement")
    package_sha = _sha(
        payload.get("candidate_package_sha256"),
        "candidate package SHA-256",
    )
    declared_sha = _sha(
        payload.get("candidate_checksum_declared_sha256"),
        "declared candidate SHA-256",
    )
    checksum_text = payload.get("candidate_checksum_file_text")
    if not isinstance(checksum_text, str) or not checksum_text:
        _fail("candidate checksum file text is required")
    if hashlib.sha256(checksum_text.encode("utf-8")).hexdigest() != file_sha[
        checksum_id
    ]:
        _fail("candidate checksum file text hash does not match captured bytes")
    checksum_parts = checksum_text.strip().split()
    if (
        len(checksum_parts) != 2
        or checksum_parts[0] != declared_sha
        or checksum_parts[1] != "Atlas_ROS_v5.0.0rc1_Candidate.zip"
    ):
        _fail("candidate checksum file text does not declare the expected package")
    if package_sha != declared_sha or package_sha != file_sha[package_id]:
        _fail("v5.0 candidate package checksum does not reconcile")

    listings = payload.get("listings")
    if not isinstance(listings, list) or len(listings) != 1:
        _fail("v5.0 supplement must contain one listing receipt")
    listing = listings[0]
    if not isinstance(listing, dict):
        _fail("v5.0 listing receipt must be an object")
    folder_id = listing.get("folder_id")
    if folder_id not in scanned:
        _fail("v5.0 listing folder is invalid")
    if listing.get("listing_complete") is not True:
        _fail(f"incomplete v5.0 listing: {folder_id}")
    if listing.get("unconsumed_page_tokens") != 0:
        _fail(f"v5.0 listing retains a page token: {folder_id}")
    if listing.get("inaccessible_file_ids") != []:
        _fail(f"v5.0 listing contains inaccessible files: {folder_id}")
    listed_ids = listing.get("file_ids")
    if (
        not isinstance(listed_ids, list)
        or not all(isinstance(item, str) and item for item in listed_ids)
        or len(listed_ids) != len(set(listed_ids))
    ):
        _fail(f"invalid v5.0 file list: {folder_id}")
    if set(listed_ids) != file_ids:
        _fail("v5.0 listing receipts do not close the supplement")
    if any(file_parent[file_id] != folder_id for file_id in listed_ids):
        _fail("v5.0 listing contains a file-parent mismatch")
    expected_listing_sha = _sha(
        listing.get("listing_sha256"),
        f"listing SHA-256 for {folder_id}",
    )
    unsigned_listing = dict(listing)
    unsigned_listing.pop("listing_sha256", None)
    if expected_listing_sha != canonical_sha256(unsigned_listing):
        _fail(f"v5.0 listing digest mismatch: {folder_id}")

    if payload.get("provider_writes") != 0:
        _fail("v5.0 evidence cannot record provider writes")
    if payload.get("drive_retirement_authorized") is not False:
        _fail("v5.0 evidence cannot authorize Drive retirement")
    if payload.get("credential_action_authorized") is not False:
        _fail("v5.0 evidence cannot authorize credential actions")
    supplement_sha = _sha(
        payload.get("supplement_sha256"),
        "supplement_sha256",
    )
    unsigned = dict(payload)
    unsigned.pop("supplement_sha256", None)
    if supplement_sha != canonical_sha256(unsigned):
        _fail("v5.0 supplement digest mismatch")

    combined_scanned = base_result["scanned_folder_count"] + 1
    combined_files = base_result["file_count"] + len(file_ids)
    return {
        "schema_version": "1.0",
        "status": "partial_file_inventory_with_complete_v500_supplement",
        "release": "5.0",
        "supplement_sha256": supplement_sha,
        "v500_scanned_folder_count": 1,
        "v500_file_count": len(file_ids),
        "v500_content_hashed_count": len(file_ids),
        "v500_listing_count": 1,
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
