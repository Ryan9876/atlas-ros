#!/usr/bin/env python3
"""Validate fail-closed Google Drive file-inventory evidence for Atlas ROS v7."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.validate_v700_drive_folder_tree import expand_compact_tree


class DriveFileInventoryError(ValueError):
    """Raised when file inventory evidence is incomplete or unsafe."""


def canonical_sha256(payload: dict[str, Any]) -> str:
    """Return a deterministic SHA-256 for one JSON object."""
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _sha(value: Any, field: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or len(value) != 64:
        raise DriveFileInventoryError(f"{field} must be a lowercase SHA-256")
    if any(character not in "0123456789abcdef" for character in value):
        raise DriveFileInventoryError(f"{field} must be a lowercase SHA-256")
    return value


def _safe_target(value: str, file_id: str) -> None:
    target = PurePosixPath(value)
    if target.is_absolute() or ".." in target.parts:
        raise DriveFileInventoryError(
            f"unsafe GitHub target for Drive file {file_id}: {value}"
        )


def _known_folder_ids(folder_payload: dict[str, Any]) -> set[str]:
    expanded = expand_compact_tree(folder_payload)
    return {record["folder_id"] for record in expanded["folders"]}


def validate_file_inventory(
    payload: dict[str, Any],
    *,
    folder_payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate file evidence without allowing partial data to unlock promotion."""
    if payload.get("schema_version") != "1.0":
        raise DriveFileInventoryError("file inventory schema_version must be 1.0")
    if folder_payload.get("folder_tree_sha256") != payload.get("folder_tree_sha256"):
        raise DriveFileInventoryError("file inventory is not bound to the folder tree")

    source_root_id = payload.get("source_root_id")
    if source_root_id != folder_payload.get("source_root_id"):
        raise DriveFileInventoryError("file inventory source root mismatch")

    known_folders = _known_folder_ids(folder_payload)
    scanned = payload.get("scanned_folder_ids")
    if not isinstance(scanned, list) or not all(
        isinstance(item, str) and item.strip() for item in scanned
    ):
        raise DriveFileInventoryError("scanned_folder_ids must be a list of strings")
    if len(scanned) != len(set(scanned)):
        raise DriveFileInventoryError("scanned_folder_ids contains duplicates")
    unknown_scans = sorted(set(scanned) - known_folders)
    if unknown_scans:
        raise DriveFileInventoryError(
            "file inventory scanned unknown folders: " + ", ".join(unknown_scans)
        )

    enumeration_complete = payload.get("enumeration_complete")
    content_checksums_complete = payload.get("content_checksums_complete")
    if not isinstance(enumeration_complete, bool):
        raise DriveFileInventoryError("enumeration_complete must be a boolean")
    if not isinstance(content_checksums_complete, bool):
        raise DriveFileInventoryError("content_checksums_complete must be a boolean")

    unconsumed_page_tokens = payload.get("unconsumed_page_tokens")
    if not isinstance(unconsumed_page_tokens, int) or isinstance(
        unconsumed_page_tokens, bool
    ):
        raise DriveFileInventoryError("unconsumed_page_tokens must be an integer")
    if unconsumed_page_tokens < 0:
        raise DriveFileInventoryError("unconsumed_page_tokens cannot be negative")

    inaccessible = payload.get("inaccessible_file_ids")
    if not isinstance(inaccessible, list) or not all(
        isinstance(item, str) and item.strip() for item in inaccessible
    ):
        raise DriveFileInventoryError("inaccessible_file_ids must be a list of strings")
    if len(inaccessible) != len(set(inaccessible)):
        raise DriveFileInventoryError("inaccessible_file_ids contains duplicates")

    raw_records = payload.get("records")
    if not isinstance(raw_records, list) or not raw_records:
        raise DriveFileInventoryError("file inventory records must be non-empty")

    file_ids: set[str] = set()
    github_targets: set[str] = set()
    content_hashed = 0
    sensitive = 0
    verified_equivalent = 0
    governed_exceptions = 0

    for raw in raw_records:
        if not isinstance(raw, dict):
            raise DriveFileInventoryError("every file record must be an object")
        required = {
            "file_id",
            "parent_folder_id",
            "title",
            "mime_type",
            "size_bytes",
            "modified_time",
            "capture_method",
            "content_sha256",
            "classification",
            "disposition",
            "github_target",
            "github_content_sha256",
            "content_equivalent",
            "exception_id",
        }
        missing = sorted(required - set(raw))
        if missing:
            raise DriveFileInventoryError(
                "file inventory record missing fields: " + ", ".join(missing)
            )

        file_id = raw["file_id"]
        parent_id = raw["parent_folder_id"]
        if not isinstance(file_id, str) or not file_id.strip():
            raise DriveFileInventoryError("file_id is required")
        if file_id in file_ids:
            raise DriveFileInventoryError(f"duplicate file_id: {file_id}")
        file_ids.add(file_id)
        if parent_id not in known_folders:
            raise DriveFileInventoryError(
                f"unknown parent folder {parent_id} for Drive file {file_id}"
            )
        for identity_field in ("title", "mime_type", "modified_time"):
            value = raw[identity_field]
            if not isinstance(value, str) or not value.strip():
                raise DriveFileInventoryError(
                    f"{identity_field} is required for Drive file {file_id}"
                )
        size_bytes = raw["size_bytes"]
        if not isinstance(size_bytes, int) or isinstance(size_bytes, bool):
            raise DriveFileInventoryError(
                f"size_bytes must be an integer for Drive file {file_id}"
            )
        if size_bytes < 0:
            raise DriveFileInventoryError(
                f"size_bytes cannot be negative for Drive file {file_id}"
            )

        capture_method = raw["capture_method"]
        classification = raw["classification"]
        disposition = raw["disposition"]
        content_digest = _sha(
            raw["content_sha256"],
            f"content_sha256 for Drive file {file_id}",
            optional=True,
        )
        github_digest = _sha(
            raw["github_content_sha256"],
            f"github_content_sha256 for Drive file {file_id}",
            optional=True,
        )
        github_target = raw["github_target"]
        content_equivalent = raw["content_equivalent"]
        exception_id = raw["exception_id"]

        if not isinstance(content_equivalent, bool):
            raise DriveFileInventoryError(
                f"content_equivalent must be boolean for Drive file {file_id}"
            )
        if github_target is not None:
            if not isinstance(github_target, str) or not github_target.strip():
                raise DriveFileInventoryError(
                    f"invalid GitHub target for Drive file {file_id}"
                )
            _safe_target(github_target, file_id)
            if github_target in github_targets:
                raise DriveFileInventoryError(
                    f"duplicate GitHub target in file inventory: {github_target}"
                )
            github_targets.add(github_target)

        if classification == "sensitive_credential":
            sensitive += 1
            if capture_method != "metadata_only_sensitive":
                raise DriveFileInventoryError(
                    f"sensitive Drive file {file_id} must remain metadata-only"
                )
            if content_digest is not None or github_digest is not None:
                raise DriveFileInventoryError(
                    f"sensitive Drive file {file_id} cannot include content digests"
                )
            if github_target is not None or content_equivalent:
                raise DriveFileInventoryError(
                    f"sensitive Drive file {file_id} cannot claim GitHub equivalence"
                )
            if disposition != "security_review_required":
                raise DriveFileInventoryError(
                    f"sensitive Drive file {file_id} requires security review"
                )
            if exception_id is not None:
                raise DriveFileInventoryError(
                    f"sensitive Drive file {file_id} cannot use a retention exception"
                )
            continue

        if capture_method not in {"raw_bytes", "google_export_text_plain"}:
            raise DriveFileInventoryError(
                f"Drive file {file_id} lacks a content-capture method"
            )
        if content_digest is None:
            raise DriveFileInventoryError(
                f"Drive file {file_id} lacks a content checksum"
            )
        content_hashed += 1

        if content_equivalent:
            if github_target is None or github_digest is None:
                raise DriveFileInventoryError(
                    f"equivalent Drive file {file_id} lacks GitHub evidence"
                )
            if github_digest != content_digest:
                raise DriveFileInventoryError(
                    f"Drive and GitHub checksums differ for file {file_id}"
                )
            verified_equivalent += 1
        elif github_target is not None or github_digest is not None:
            raise DriveFileInventoryError(
                f"non-equivalent Drive file {file_id} cannot retain GitHub evidence"
            )

        if disposition == "retain_legacy_read_only":
            if not isinstance(exception_id, str) or not exception_id.strip():
                raise DriveFileInventoryError(
                    f"legacy Drive file {file_id} requires a governed exception"
                )
            governed_exceptions += 1
        elif exception_id is not None:
            raise DriveFileInventoryError(
                f"Drive file {file_id} has an unexpected exception_id"
            )

        if classification == "current_bootstrap":
            if disposition != "stage_github" or not content_equivalent:
                raise DriveFileInventoryError(
                    "current bootstrap must be staged with GitHub equivalence"
                )

    unscanned = sorted(known_folders - set(scanned))
    if enumeration_complete and (
        unscanned or inaccessible or unconsumed_page_tokens != 0
    ):
        raise DriveFileInventoryError(
            "enumeration cannot be complete with unscanned folders, inaccessible files, "
            "or unconsumed page tokens"
        )
    if content_checksums_complete and not enumeration_complete:
        raise DriveFileInventoryError(
            "content checksums cannot be complete before enumeration"
        )
    if content_checksums_complete and sensitive:
        raise DriveFileInventoryError(
            "content checksums cannot be complete with unresolved sensitive items"
        )

    expected_digest = _sha(payload.get("inventory_sha256"), "inventory_sha256")
    unsigned = dict(payload)
    unsigned.pop("inventory_sha256", None)
    actual_digest = canonical_sha256(unsigned)
    if expected_digest != actual_digest:
        raise DriveFileInventoryError("file inventory digest mismatch")

    promotion_ready = (
        enumeration_complete
        and content_checksums_complete
        and not sensitive
        and not inaccessible
        and unconsumed_page_tokens == 0
    )
    if promotion_ready:
        status = "complete_for_promotion_readiness"
    elif enumeration_complete:
        status = "enumeration_complete_checksums_incomplete"
    else:
        status = "partial_file_inventory"

    return {
        "schema_version": "1.0",
        "status": status,
        "source_root_id": source_root_id,
        "folder_tree_sha256": payload["folder_tree_sha256"],
        "known_folder_count": len(known_folders),
        "scanned_folder_count": len(scanned),
        "unscanned_folder_count": len(unscanned),
        "unscanned_folder_ids": unscanned,
        "file_count": len(raw_records),
        "content_hashed_count": content_hashed,
        "sensitive_item_count": sensitive,
        "verified_github_equivalence_count": verified_equivalent,
        "governed_legacy_exception_count": governed_exceptions,
        "enumeration_complete": enumeration_complete,
        "content_checksums_complete": content_checksums_complete,
        "unconsumed_page_tokens": unconsumed_page_tokens,
        "inaccessible_file_ids": inaccessible,
        "inventory_sha256": actual_digest,
        "promotion_ready": promotion_ready,
        "provider_writes": 0,
        "drive_retirement_authorized": False,
        "credential_action_authorized": False,
    }


def load_and_validate(
    inventory_path: Path,
    *,
    folder_path: Path,
) -> dict[str, Any]:
    """Load and validate file inventory and its bound folder evidence."""
    try:
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        folder_payload = json.loads(folder_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DriveFileInventoryError("invalid Drive inventory JSON") from error
    if not isinstance(inventory, dict) or not isinstance(folder_payload, dict):
        raise DriveFileInventoryError("Drive inventory evidence must be JSON objects")
    return validate_file_inventory(inventory, folder_payload=folder_payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--folder-tree", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = load_and_validate(args.inventory, folder_path=args.folder_tree)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
