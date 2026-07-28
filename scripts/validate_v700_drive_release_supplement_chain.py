#!/usr/bin/env python3
"""Validate an ordered, non-overlapping chain of Drive release supplements."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from scripts.validate_v700_drive_file_inventory import validate_file_inventory
from scripts.validate_v700_drive_file_listing_receipts import (
    validate_file_listing_receipts,
)
from scripts.validate_v700_drive_folder_tree import expand_compact_tree


class DriveReleaseSupplementChainError(ValueError):
    """Raised when release-scoped Drive evidence is incomplete or unsafe."""


def canonical_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _fail(message: str) -> None:
    raise DriveReleaseSupplementChainError(message)


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
        raise DriveReleaseSupplementChainError(
            f"invalid JSON evidence: {path}"
        ) from error
    if not isinstance(value, dict):
        _fail(f"JSON evidence must be an object: {path}")
    return value


def _artifact_fields(payload: dict[str, Any]) -> tuple[str, str, str, str, str]:
    if "candidate_package_file_id" in payload:
        return (
            "candidate_package_file_id",
            "candidate_package_sha256",
            "candidate_checksum_file_id",
            "candidate_checksum_declared_sha256",
            "candidate_checksum_file_text",
        )
    return (
        "release_package_file_id",
        "release_package_sha256",
        "release_checksum_file_id",
        "release_checksum_declared_sha256",
        "release_checksum_file_text",
    )


def _validate_one(
    payload: dict[str, Any],
    *,
    folder_payload: dict[str, Any],
    base_inventory: dict[str, Any],
    base_receipts: dict[str, Any],
    known_folders: set[str],
    occupied_folders: set[str],
    occupied_files: set[str],
) -> dict[str, Any]:
    if payload.get("schema_version") != "1.0":
        _fail("release supplement schema_version must be 1.0")
    release = payload.get("release")
    if not isinstance(release, str) or not release.strip():
        _fail("release supplement must identify a release")
    if payload.get("source_root_id") != folder_payload.get("source_root_id"):
        _fail(f"release {release} supplement source root mismatch")
    tree_sha = _sha(payload.get("folder_tree_sha256"), "folder_tree_sha256")
    if tree_sha != folder_payload.get("folder_tree_sha256"):
        _fail(f"release {release} supplement is not bound to the folder tree")
    if payload.get("base_inventory_sha256") != base_inventory.get(
        "inventory_sha256"
    ):
        _fail(f"release {release} supplement is not bound to the base inventory")
    if payload.get("base_listing_set_sha256") != base_receipts.get(
        "listing_set_sha256"
    ):
        _fail(f"release {release} supplement is not bound to the base listings")

    scanned = payload.get("scanned_folder_ids")
    if (
        not isinstance(scanned, list)
        or not scanned
        or not all(isinstance(item, str) and item for item in scanned)
        or len(scanned) != len(set(scanned))
    ):
        _fail(f"release {release} supplement must scan unique folders")
    scanned_set = set(scanned)
    if not scanned_set.issubset(known_folders):
        _fail(f"release {release} supplement contains an unknown folder")
    overlap = sorted(scanned_set & occupied_folders)
    if overlap:
        _fail(
            f"release {release} supplement folders overlap prior evidence: "
            + ", ".join(overlap)
        )
    if payload.get("enumeration_complete") is not True:
        _fail(f"release {release} supplement enumeration must be complete")
    if payload.get("content_checksums_complete") is not True:
        _fail(f"release {release} content checksums must be complete")
    if payload.get("inaccessible_file_ids") != []:
        _fail(f"release {release} supplement contains inaccessible files")
    if payload.get("unconsumed_page_tokens") != 0:
        _fail(f"release {release} supplement retains page tokens")
    if payload.get("classification") != "historical_release_artifact":
        _fail(f"release {release} files must be historical release artifacts")
    if payload.get("disposition") != "retain_legacy_read_only":
        _fail(f"release {release} files must remain legacy read only")
    if payload.get("exception_id") != "V700-DRIVE-LEGACY-READ-ONLY":
        _fail(f"release {release} files require the governed legacy exception")

    raw_files = payload.get("files")
    if not isinstance(raw_files, list) or not raw_files:
        _fail(f"release {release} supplement files must be non-empty")
    file_ids: set[str] = set()
    file_parent: dict[str, str] = {}
    file_sha: dict[str, str] = {}
    file_title: dict[str, str] = {}
    for raw in raw_files:
        if not isinstance(raw, list) or len(raw) != 7:
            _fail(
                f"release {release} files must use the seven-field compact contract"
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
            for value in (file_id, parent_id, title, mime_type, modified_time)
        ):
            _fail(f"release {release} file identity fields must be strings")
        if (
            not isinstance(size_bytes, int)
            or isinstance(size_bytes, bool)
            or size_bytes < 0
        ):
            _fail(f"invalid release {release} file size: {file_id}")
        digest = _sha(content_sha256, f"content SHA-256 for {file_id}")
        if file_id in file_ids or file_id in occupied_files:
            _fail(f"duplicate Drive file ID: {file_id}")
        if parent_id not in scanned_set:
            _fail(f"release {release} file has unscanned parent: {file_id}")
        file_ids.add(file_id)
        file_parent[file_id] = parent_id
        file_sha[file_id] = digest
        file_title[file_id] = title

    listings = payload.get("listings")
    if not isinstance(listings, list) or len(listings) != len(scanned_set):
        _fail(f"release {release} must contain one listing per scanned folder")
    listed_folders: set[str] = set()
    bound_files: set[str] = set()
    for listing in listings:
        if not isinstance(listing, dict):
            _fail(f"release {release} listing receipt must be an object")
        folder_id = listing.get("folder_id")
        if folder_id not in scanned_set or folder_id in listed_folders:
            _fail(f"release {release} listing folder is invalid or duplicated")
        listed_folders.add(folder_id)
        if listing.get("listing_complete") is not True:
            _fail(f"incomplete release {release} listing: {folder_id}")
        if listing.get("unconsumed_page_tokens") != 0:
            _fail(f"release {release} listing retains a page token: {folder_id}")
        if listing.get("inaccessible_file_ids") != []:
            _fail(f"release {release} listing contains inaccessible files")
        listed_ids = listing.get("file_ids")
        if (
            not isinstance(listed_ids, list)
            or not all(isinstance(item, str) and item for item in listed_ids)
            or len(listed_ids) != len(set(listed_ids))
        ):
            _fail(f"invalid release {release} file list: {folder_id}")
        for file_id in listed_ids:
            if file_id not in file_ids:
                _fail(f"listing references unknown release file: {file_id}")
            if file_parent[file_id] != folder_id:
                _fail(f"release {release} file-parent mismatch: {file_id}")
            if file_id in bound_files:
                _fail(f"release file appears in multiple listings: {file_id}")
            bound_files.add(file_id)
        expected_listing_sha = _sha(
            listing.get("listing_sha256"),
            f"listing SHA-256 for {folder_id}",
        )
        unsigned_listing = dict(listing)
        unsigned_listing.pop("listing_sha256", None)
        if expected_listing_sha != canonical_sha256(unsigned_listing):
            _fail(f"release {release} listing digest mismatch: {folder_id}")
    if listed_folders != scanned_set or bound_files != file_ids:
        _fail(f"release {release} listing receipts do not close the supplement")

    (
        package_id_key,
        package_sha_key,
        checksum_id_key,
        declared_sha_key,
        checksum_text_key,
    ) = _artifact_fields(payload)
    package_id = payload.get(package_id_key)
    checksum_id = payload.get(checksum_id_key)
    if package_id not in file_ids or checksum_id not in file_ids:
        _fail(f"release {release} package evidence is not in the supplement")
    package_sha = _sha(payload.get(package_sha_key), "release package SHA-256")
    declared_sha = _sha(payload.get(declared_sha_key), "declared package SHA-256")
    if package_sha != declared_sha or package_sha != file_sha[package_id]:
        _fail(f"release {release} package checksum does not reconcile")
    checksum_text = payload.get(checksum_text_key)
    expected_text = f"{declared_sha}  {file_title[package_id]}\n"
    if checksum_text != expected_text:
        _fail(f"release {release} checksum-file text does not reconcile")

    if payload.get("provider_writes") != 0:
        _fail(f"release {release} evidence cannot record provider writes")
    if payload.get("drive_retirement_authorized") is not False:
        _fail(f"release {release} evidence cannot authorize Drive retirement")
    if payload.get("credential_action_authorized") is not False:
        _fail(f"release {release} evidence cannot authorize credential actions")
    supplement_sha = _sha(payload.get("supplement_sha256"), "supplement_sha256")
    unsigned = dict(payload)
    unsigned.pop("supplement_sha256", None)
    if supplement_sha != canonical_sha256(unsigned):
        _fail(f"release {release} supplement digest mismatch")

    return {
        "release": release,
        "supplement_sha256": supplement_sha,
        "scanned_folder_count": len(scanned_set),
        "file_count": len(file_ids),
        "content_hashed_count": len(file_ids),
        "listing_count": len(listings),
        "package_checksum_reconciled": True,
        "folder_ids": scanned_set,
        "file_ids": file_ids,
    }


def validate_supplement_chain(
    supplements: Iterable[dict[str, Any]],
    *,
    folder_payload: dict[str, Any],
    base_inventory: dict[str, Any],
    base_receipts: dict[str, Any],
) -> dict[str, Any]:
    supplement_list = list(supplements)
    if not supplement_list:
        _fail("supplement chain must be non-empty")
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
    occupied_folders = set(base_inventory.get("scanned_folder_ids", []))
    occupied_files = {
        record.get("file_id") for record in base_inventory.get("records", [])
    }
    results: list[dict[str, Any]] = []
    for payload in supplement_list:
        result = _validate_one(
            payload,
            folder_payload=folder_payload,
            base_inventory=base_inventory,
            base_receipts=base_receipts,
            known_folders=known_folders,
            occupied_folders=occupied_folders,
            occupied_files=occupied_files,
        )
        occupied_folders.update(result.pop("folder_ids"))
        occupied_files.update(result.pop("file_ids"))
        results.append(result)

    supplement_folder_count = sum(item["scanned_folder_count"] for item in results)
    supplement_file_count = sum(item["file_count"] for item in results)
    combined_scanned = base_result["scanned_folder_count"] + supplement_folder_count
    return {
        "schema_version": "1.0",
        "status": "partial_file_inventory_with_complete_release_supplement_chain",
        "supplement_count": len(results),
        "releases": [item["release"] for item in results],
        "supplements": results,
        "combined_known_folder_count": base_result["known_folder_count"],
        "combined_scanned_folder_count": combined_scanned,
        "combined_unscanned_folder_count": (
            base_result["known_folder_count"] - combined_scanned
        ),
        "combined_file_count": base_result["file_count"] + supplement_file_count,
        "combined_content_hashed_count": (
            base_result["content_hashed_count"] + supplement_file_count
        ),
        "combined_sensitive_item_count": base_result["sensitive_item_count"],
        "combined_verified_github_equivalence_count": (
            base_result["verified_github_equivalence_count"]
        ),
        "combined_governed_legacy_exception_count": (
            base_result["governed_legacy_exception_count"] + supplement_file_count
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
    parser.add_argument("--supplement", type=Path, action="append", required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--receipts", type=Path, required=True)
    parser.add_argument("--folder-tree", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = validate_supplement_chain(
        [_read_json(path) for path in args.supplement],
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
