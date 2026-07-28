#!/usr/bin/env python3
"""Validate internally checksum-closed Drive package evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from scripts.validate_v700_drive_documentation_supplement_chain import (
    validate_documentation_supplement_chain,
)
from scripts.validate_v700_drive_file_inventory import validate_file_inventory
from scripts.validate_v700_drive_file_listing_receipts import (
    validate_file_listing_receipts,
)
from scripts.validate_v700_drive_folder_tree import expand_compact_tree


class DriveInternalPackageSupplementChainError(ValueError):
    """Raised when internal-package Drive evidence is incomplete or unsafe."""


def canonical_sha256(payload: dict[str, Any]) -> str:
    """Return a deterministic SHA-256 for a JSON object."""
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _fail(message: str) -> None:
    raise DriveInternalPackageSupplementChainError(message)


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
        raise DriveInternalPackageSupplementChainError(
            f"invalid JSON evidence: {path}"
        ) from error
    if not isinstance(value, dict):
        _fail(f"JSON evidence must be an object: {path}")
    return value


def _supplement_occupancy(
    supplements: Iterable[dict[str, Any]],
) -> tuple[set[str], set[str]]:
    folders: set[str] = set()
    files: set[str] = set()
    for payload in supplements:
        raw_folders = payload.get("scanned_folder_ids", [])
        raw_files = payload.get("files", [])
        if not isinstance(raw_folders, list) or not isinstance(raw_files, list):
            _fail("validated supplement evidence has an invalid compact shape")
        folders.update(item for item in raw_folders if isinstance(item, str))
        for raw in raw_files:
            if isinstance(raw, list) and raw and isinstance(raw[0], str):
                files.add(raw[0])
    return folders, files


def _parse_checksum_text(text: str, release: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in text.splitlines():
        if not line:
            continue
        parts = line.split("  ", 1)
        if len(parts) != 2 or not parts[1]:
            _fail(f"release {release} checksum text has an invalid line")
        digest = _sha(parts[0], f"checksum digest for {parts[1]}")
        title = parts[1]
        if title in parsed:
            _fail(f"release {release} checksum text duplicates {title}")
        parsed[title] = digest
    if not parsed:
        _fail(f"release {release} checksum text must be non-empty")
    return parsed


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
        _fail("internal-package supplement schema_version must be 1.0")
    release = payload.get("release")
    if not isinstance(release, str) or not release.strip():
        _fail("internal-package supplement must identify a release")
    if payload.get("evidence_class") != "internal_checksum_closed_package":
        _fail(
            f"release {release} evidence class must be "
            "internal_checksum_closed_package"
        )
    if payload.get("source_root_id") != folder_payload.get("source_root_id"):
        _fail(f"release {release} internal-package source root mismatch")
    tree_sha = _sha(payload.get("folder_tree_sha256"), "folder_tree_sha256")
    if tree_sha != folder_payload.get("folder_tree_sha256"):
        _fail(f"release {release} evidence is not bound to the folder tree")
    if payload.get("base_inventory_sha256") != base_inventory.get(
        "inventory_sha256"
    ):
        _fail(f"release {release} evidence is not bound to the base inventory")
    if payload.get("base_listing_set_sha256") != base_receipts.get(
        "listing_set_sha256"
    ):
        _fail(f"release {release} evidence is not bound to the base listings")

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
            f"release {release} internal-package folders overlap prior evidence: "
            + ", ".join(overlap)
        )

    if payload.get("enumeration_complete") is not True:
        _fail(f"release {release} direct-folder enumeration must be complete")
    if payload.get("content_checksums_complete") is not True:
        _fail(f"release {release} direct-file checksums must be complete")
    if payload.get("inaccessible_file_ids") != []:
        _fail(f"release {release} supplement contains inaccessible files")
    if payload.get("unconsumed_page_tokens") != 0:
        _fail(f"release {release} supplement retains page tokens")
    if payload.get("classification") != "historical_release_artifact":
        _fail(f"release {release} files must be historical release artifacts")
    if payload.get("disposition") != "retain_legacy_read_only":
        _fail(f"release {release} files must remain legacy read only")
    if payload.get("exception_id") != "V700-DRIVE-LEGACY-READ-ONLY":
        _fail(f"release {release} files require the governed exception")

    raw_files = payload.get("files")
    if not isinstance(raw_files, list) or not raw_files:
        _fail(f"release {release} direct files must be non-empty")
    file_ids: set[str] = set()
    file_parent: dict[str, str] = {}
    file_title: dict[str, str] = {}
    file_size: dict[str, int] = {}
    file_sha: dict[str, str] = {}
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
        file_title[file_id] = title
        file_size[file_id] = size_bytes
        file_sha[file_id] = digest

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

    package_id = payload.get("package_file_id")
    if package_id not in file_ids:
        _fail(f"release {release} package file is not in the direct listing")
    package_sha = _sha(payload.get("package_sha256"), "package_sha256")
    if package_sha != file_sha[package_id]:
        _fail(f"release {release} independently recorded package hash mismatches")
    if payload.get("external_package_sidecar_present") is not False:
        _fail(f"release {release} cannot claim an external package sidecar")
    if payload.get("external_package_digest_reconciled") is not False:
        _fail(f"release {release} package digest is not externally reconciled")
    if payload.get("package_promotion_claim_authorized") is not False:
        _fail(f"release {release} evidence cannot authorize package promotion")

    checksum_id = payload.get("checksum_file_id")
    if checksum_id not in file_ids:
        _fail(f"release {release} checksum file is not in the direct listing")
    checksum_text = payload.get("checksum_file_text")
    if not isinstance(checksum_text, str):
        _fail(f"release {release} checksum-file text must be a string")
    if hashlib.sha256(checksum_text.encode("utf-8")).hexdigest() != file_sha[
        checksum_id
    ]:
        _fail(f"release {release} checksum-file text hash does not match bytes")
    parsed_checksums = _parse_checksum_text(checksum_text, release)

    attestation_id = payload.get("attestation_file_id")
    if attestation_id not in file_ids:
        _fail(f"release {release} attestation file is not in the direct listing")
    attestation_text = payload.get("attestation_file_text")
    if not isinstance(attestation_text, str):
        _fail(f"release {release} attestation text must be a string")
    if hashlib.sha256(attestation_text.encode("utf-8")).hexdigest() != file_sha[
        attestation_id
    ]:
        _fail(f"release {release} attestation text hash does not match bytes")
    required_attestation = payload.get("required_attestation_line")
    if (
        not isinstance(required_attestation, str)
        or not required_attestation
        or required_attestation not in attestation_text.splitlines()
    ):
        _fail(f"release {release} checksum attestation is absent")

    raw_internal = payload.get("internal_archive_entries")
    if not isinstance(raw_internal, list) or not raw_internal:
        _fail(f"release {release} archive entries must be non-empty")
    internal: dict[str, tuple[int, str]] = {}
    for raw in raw_internal:
        if not isinstance(raw, list) or len(raw) != 3:
            _fail(f"release {release} archive entries use an invalid contract")
        title, size_bytes, content_sha256 = raw
        if not isinstance(title, str) or not title:
            _fail(f"release {release} archive entry title is invalid")
        if (
            not isinstance(size_bytes, int)
            or isinstance(size_bytes, bool)
            or size_bytes < 0
        ):
            _fail(f"release {release} archive entry size is invalid: {title}")
        digest = _sha(content_sha256, f"archive entry SHA-256 for {title}")
        if title in internal:
            _fail(f"release {release} archive entry is duplicated: {title}")
        internal[title] = (size_bytes, digest)
    if payload.get("archive_entry_count") != len(internal):
        _fail(f"release {release} archive entry count does not reconcile")
    if payload.get("checksum_covered_entry_count") != len(parsed_checksums):
        _fail(f"release {release} checksum-covered count does not reconcile")
    for title, digest in parsed_checksums.items():
        if title not in internal or internal[title][1] != digest:
            _fail(f"release {release} internal checksum mismatch: {title}")

    unlisted = payload.get("unlisted_archive_entries")
    if (
        not isinstance(unlisted, list)
        or not all(isinstance(item, str) and item for item in unlisted)
        or len(unlisted) != len(set(unlisted))
    ):
        _fail(f"release {release} unlisted archive entries are invalid")
    expected_unlisted = set(internal) - set(parsed_checksums)
    if set(unlisted) != expected_unlisted:
        _fail(f"release {release} unlisted archive entries do not reconcile")

    raw_bindings = payload.get("direct_internal_bindings")
    if not isinstance(raw_bindings, list):
        _fail(f"release {release} direct/internal bindings must be a list")
    bound_direct: set[str] = set()
    bound_internal: set[str] = set()
    for raw in raw_bindings:
        if not isinstance(raw, list) or len(raw) != 2:
            _fail(f"release {release} direct/internal binding is invalid")
        file_id, internal_title = raw
        if not isinstance(file_id, str) or not isinstance(internal_title, str):
            _fail(f"release {release} direct/internal binding fields are invalid")
        if file_id in bound_direct or internal_title in bound_internal:
            _fail(f"release {release} direct/internal binding is duplicated")
        if file_id not in file_ids or internal_title not in internal:
            _fail(f"release {release} direct/internal binding is unresolved")
        if file_title[file_id] != internal_title:
            _fail(f"release {release} direct/internal title mismatch: {file_id}")
        internal_size, internal_sha = internal[internal_title]
        if file_size[file_id] != internal_size or file_sha[file_id] != internal_sha:
            _fail(f"release {release} direct/internal byte mismatch: {file_id}")
        bound_direct.add(file_id)
        bound_internal.add(internal_title)
    expected_bound_direct = file_ids - {package_id}
    if bound_direct != expected_bound_direct:
        _fail(f"release {release} direct/internal bindings are incomplete")

    raw_absent = payload.get("direct_folder_absent_internal_entries")
    if (
        not isinstance(raw_absent, list)
        or not all(isinstance(item, str) and item for item in raw_absent)
        or len(raw_absent) != len(set(raw_absent))
    ):
        _fail(f"release {release} absent internal entries are invalid")
    expected_absent = set(internal) - bound_internal
    if set(raw_absent) != expected_absent:
        _fail(f"release {release} absent internal entries do not reconcile")

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
        _fail(f"release {release} internal-package supplement digest mismatch")

    return {
        "release": release,
        "evidence_class": "internal_checksum_closed_package",
        "supplement_sha256": supplement_sha,
        "scanned_folder_count": len(scanned_set),
        "direct_file_count": len(file_ids),
        "direct_content_hashed_count": len(file_ids),
        "archive_entry_count": len(internal),
        "checksum_covered_entry_count": len(parsed_checksums),
        "direct_internal_binding_count": len(bound_direct),
        "direct_folder_absent_internal_entry_count": len(expected_absent),
        "package_sha256": package_sha,
        "internal_checksums_closed": True,
        "external_package_sidecar_present": False,
        "external_package_digest_reconciled": False,
        "package_promotion_claim_authorized": False,
        "folder_ids": scanned_set,
        "file_ids": file_ids,
    }


def validate_internal_package_supplement_chain(
    internal_package_supplements: Iterable[dict[str, Any]],
    *,
    package_supplements: Iterable[dict[str, Any]],
    documentation_supplements: Iterable[dict[str, Any]],
    folder_payload: dict[str, Any],
    base_inventory: dict[str, Any],
    base_receipts: dict[str, Any],
) -> dict[str, Any]:
    """Validate the mixed package, documentation, and internal-package ledger."""
    internal_list = list(internal_package_supplements)
    package_list = list(package_supplements)
    documentation_list = list(documentation_supplements)
    if not internal_list:
        _fail("internal-package supplement chain must be non-empty")

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
    documentation_result = validate_documentation_supplement_chain(
        documentation_list,
        package_supplements=package_list,
        folder_payload=folder_payload,
        base_inventory=base_inventory,
        base_receipts=base_receipts,
    )

    known_folders = {
        record["folder_id"]
        for record in expand_compact_tree(folder_payload)["folders"]
    }
    package_folders, package_files = _supplement_occupancy(package_list)
    documentation_folders, documentation_files = _supplement_occupancy(
        documentation_list
    )
    occupied_folders = set(base_inventory.get("scanned_folder_ids", []))
    occupied_folders.update(package_folders)
    occupied_folders.update(documentation_folders)
    occupied_files = {
        record.get("file_id") for record in base_inventory.get("records", [])
    }
    occupied_files.update(package_files)
    occupied_files.update(documentation_files)

    results: list[dict[str, Any]] = []
    for payload in internal_list:
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

    internal_folder_count = sum(item["scanned_folder_count"] for item in results)
    internal_file_count = sum(item["direct_file_count"] for item in results)
    combined_scanned = (
        documentation_result["combined_scanned_folder_count"]
        + internal_folder_count
    )
    return {
        "schema_version": "1.0",
        "status": "partial_file_inventory_with_complete_mixed_evidence_supplements",
        "externally_reconciled_package_count": documentation_result[
            "package_supplement_count"
        ],
        "externally_reconciled_package_releases": documentation_result[
            "package_releases"
        ],
        "documentation_supplement_count": documentation_result[
            "documentation_supplement_count"
        ],
        "documentation_releases": documentation_result[
            "documentation_releases"
        ],
        "internally_closed_unreconciled_package_count": len(results),
        "internally_closed_unreconciled_package_releases": [
            item["release"] for item in results
        ],
        "internal_package_supplements": results,
        "combined_known_folder_count": base_result["known_folder_count"],
        "combined_scanned_folder_count": combined_scanned,
        "combined_unscanned_folder_count": (
            base_result["known_folder_count"] - combined_scanned
        ),
        "combined_file_count": (
            documentation_result["combined_file_count"] + internal_file_count
        ),
        "combined_content_hashed_count": (
            documentation_result["combined_content_hashed_count"]
            + internal_file_count
        ),
        "combined_sensitive_item_count": documentation_result[
            "combined_sensitive_item_count"
        ],
        "combined_verified_github_equivalence_count": documentation_result[
            "combined_verified_github_equivalence_count"
        ],
        "combined_governed_legacy_exception_count": (
            documentation_result["combined_governed_legacy_exception_count"]
            + internal_file_count
        ),
        "enumeration_complete": False,
        "content_checksums_complete": False,
        "promotion_ready": False,
        "provider_writes": 0,
        "drive_retirement_authorized": False,
        "credential_action_authorized": False,
        "unreconciled_package_promotion_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--internal-package-supplement",
        type=Path,
        action="append",
        required=True,
    )
    parser.add_argument(
        "--package-supplement",
        type=Path,
        action="append",
        required=True,
    )
    parser.add_argument(
        "--documentation-supplement",
        type=Path,
        action="append",
        required=True,
    )
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--receipts", type=Path, required=True)
    parser.add_argument("--folder-tree", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = validate_internal_package_supplement_chain(
        [_read_json(path) for path in args.internal_package_supplement],
        package_supplements=[
            _read_json(path) for path in args.package_supplement
        ],
        documentation_supplements=[
            _read_json(path) for path in args.documentation_supplement
        ],
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
