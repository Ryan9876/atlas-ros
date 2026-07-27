#!/usr/bin/env python3
"""Validate recursive Google Drive folder-traversal evidence for Atlas ROS v7."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


class DriveFolderTraversalError(ValueError):
    """Raised when folder-traversal evidence is incomplete or contradictory."""


def canonical_sha256(payload: dict[str, Any]) -> str:
    """Return a deterministic SHA-256 for one JSON object."""
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_folder_traversal(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate parent/child closure, reachability, and fail-closed readiness."""
    if payload.get("schema_version") != "1.0":
        raise DriveFolderTraversalError("folder traversal schema_version must be 1.0")

    source_root_id = payload.get("source_root_id")
    if not isinstance(source_root_id, str) or not source_root_id.strip():
        raise DriveFolderTraversalError("source_root_id is required")

    folder_traversal_complete = payload.get("folder_traversal_complete")
    item_inventory_complete = payload.get("item_inventory_complete")
    file_content_checksums_complete = payload.get("file_content_checksums_complete")
    for name, value in (
        ("folder_traversal_complete", folder_traversal_complete),
        ("item_inventory_complete", item_inventory_complete),
        ("file_content_checksums_complete", file_content_checksums_complete),
    ):
        if not isinstance(value, bool):
            raise DriveFolderTraversalError(f"{name} must be a boolean")

    raw_folders = payload.get("folders")
    if not isinstance(raw_folders, list) or not raw_folders:
        raise DriveFolderTraversalError("folders must be a non-empty list")

    folders: dict[str, dict[str, Any]] = {}
    for raw in raw_folders:
        if not isinstance(raw, dict):
            raise DriveFolderTraversalError("every folder record must be an object")
        folder_id = raw.get("folder_id")
        title = raw.get("title")
        parent_id = raw.get("parent_id")
        child_folder_ids = raw.get("child_folder_ids")
        inaccessible_child_ids = raw.get("inaccessible_child_ids")
        listing_complete = raw.get("listing_complete")
        unconsumed_page_tokens = raw.get("unconsumed_page_tokens")

        if not isinstance(folder_id, str) or not folder_id.strip():
            raise DriveFolderTraversalError("folder_id is required")
        if folder_id in folders:
            raise DriveFolderTraversalError(f"duplicate folder_id: {folder_id}")
        if not isinstance(title, str) or not title.strip():
            raise DriveFolderTraversalError(f"title is required for folder {folder_id}")
        if parent_id is not None and (
            not isinstance(parent_id, str) or not parent_id.strip()
        ):
            raise DriveFolderTraversalError(f"invalid parent_id for folder {folder_id}")
        if not isinstance(child_folder_ids, list) or not all(
            isinstance(item, str) and item.strip() for item in child_folder_ids
        ):
            raise DriveFolderTraversalError(
                f"child_folder_ids must be non-empty strings for folder {folder_id}"
            )
        if len(child_folder_ids) != len(set(child_folder_ids)):
            raise DriveFolderTraversalError(
                f"duplicate child folder IDs for folder {folder_id}"
            )
        if not isinstance(inaccessible_child_ids, list) or not all(
            isinstance(item, str) and item.strip() for item in inaccessible_child_ids
        ):
            raise DriveFolderTraversalError(
                f"inaccessible_child_ids must be strings for folder {folder_id}"
            )
        if len(inaccessible_child_ids) != len(set(inaccessible_child_ids)):
            raise DriveFolderTraversalError(
                f"duplicate inaccessible IDs for folder {folder_id}"
            )
        if not isinstance(listing_complete, bool):
            raise DriveFolderTraversalError(
                f"listing_complete must be boolean for folder {folder_id}"
            )
        if not isinstance(unconsumed_page_tokens, int) or isinstance(
            unconsumed_page_tokens, bool
        ):
            raise DriveFolderTraversalError(
                f"unconsumed_page_tokens must be integer for folder {folder_id}"
            )
        if unconsumed_page_tokens < 0:
            raise DriveFolderTraversalError(
                f"negative unconsumed_page_tokens for folder {folder_id}"
            )

        folders[folder_id] = raw

    root = folders.get(source_root_id)
    if root is None:
        raise DriveFolderTraversalError("source root is missing from folders")
    if root.get("parent_id") is not None:
        raise DriveFolderTraversalError("source root parent_id must be null")

    for folder_id, record in folders.items():
        parent_id = record["parent_id"]
        if folder_id != source_root_id:
            if parent_id not in folders:
                raise DriveFolderTraversalError(
                    f"missing parent {parent_id} for folder {folder_id}"
                )
            if folder_id not in folders[parent_id]["child_folder_ids"]:
                raise DriveFolderTraversalError(
                    f"parent {parent_id} does not list folder {folder_id}"
                )
        for child_id in record["child_folder_ids"]:
            child = folders.get(child_id)
            if child is None:
                raise DriveFolderTraversalError(
                    f"folder {folder_id} lists unknown child {child_id}"
                )
            if child["parent_id"] != folder_id:
                raise DriveFolderTraversalError(
                    f"child {child_id} parent mismatch: {child['parent_id']}"
                )

    reached: set[str] = set()
    stack: list[tuple[str, int]] = [(source_root_id, 0)]
    max_depth = 0
    while stack:
        folder_id, depth = stack.pop()
        if folder_id in reached:
            raise DriveFolderTraversalError(
                f"folder graph contains a cycle or duplicate path at {folder_id}"
            )
        reached.add(folder_id)
        max_depth = max(max_depth, depth)
        stack.extend(
            (child_id, depth + 1)
            for child_id in folders[folder_id]["child_folder_ids"]
        )
    if reached != set(folders):
        missing = sorted(set(folders) - reached)
        raise DriveFolderTraversalError(
            "folder graph contains unreachable records: " + ", ".join(missing)
        )

    total_unconsumed = sum(
        record["unconsumed_page_tokens"] for record in folders.values()
    )
    inaccessible = sorted(
        {
            child_id
            for record in folders.values()
            for child_id in record["inaccessible_child_ids"]
        }
    )
    incomplete_listings = sorted(
        folder_id
        for folder_id, record in folders.items()
        if not record["listing_complete"]
    )

    if folder_traversal_complete and (
        total_unconsumed or inaccessible or incomplete_listings
    ):
        raise DriveFolderTraversalError(
            "folder traversal cannot be complete with incomplete listings, "
            "unconsumed page tokens, or inaccessible children"
        )
    if item_inventory_complete and not folder_traversal_complete:
        raise DriveFolderTraversalError(
            "item inventory cannot be complete before folder traversal"
        )
    if item_inventory_complete and not file_content_checksums_complete:
        raise DriveFolderTraversalError(
            "complete item inventory requires complete file content checksums"
        )
    if file_content_checksums_complete and not item_inventory_complete:
        raise DriveFolderTraversalError(
            "file content checksums cannot be complete before item inventory"
        )

    expected_digest = payload.get("folder_tree_sha256")
    if not isinstance(expected_digest, str) or len(expected_digest) != 64:
        raise DriveFolderTraversalError("folder_tree_sha256 must be a SHA-256")
    unsigned = dict(payload)
    unsigned.pop("folder_tree_sha256", None)
    actual_digest = canonical_sha256(unsigned)
    if actual_digest != expected_digest:
        raise DriveFolderTraversalError("folder tree digest mismatch")

    promotion_ready = (
        folder_traversal_complete
        and item_inventory_complete
        and file_content_checksums_complete
    )
    if promotion_ready:
        status = "complete_for_promotion_readiness"
    elif folder_traversal_complete:
        status = "folder_traversal_complete_item_inventory_incomplete"
    else:
        status = "folder_traversal_incomplete"

    return {
        "schema_version": "1.0",
        "status": status,
        "source_root_id": source_root_id,
        "folder_count": len(folders),
        "leaf_folder_count": sum(
            not record["child_folder_ids"] for record in folders.values()
        ),
        "max_depth": max_depth,
        "folder_traversal_complete": folder_traversal_complete,
        "item_inventory_complete": item_inventory_complete,
        "file_content_checksums_complete": file_content_checksums_complete,
        "unconsumed_page_tokens": total_unconsumed,
        "inaccessible_child_ids": inaccessible,
        "incomplete_listing_folder_ids": incomplete_listings,
        "folder_tree_sha256": actual_digest,
        "promotion_ready": promotion_ready,
        "provider_writes": 0,
        "drive_retirement_authorized": False,
    }


def load_and_validate(path: Path) -> dict[str, Any]:
    """Load one traversal file and validate its deterministic evidence."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DriveFolderTraversalError(
            f"invalid Drive folder traversal evidence: {path}"
        ) from error
    if not isinstance(payload, dict):
        raise DriveFolderTraversalError("Drive folder traversal must be an object")
    return validate_folder_traversal(payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = load_and_validate(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
