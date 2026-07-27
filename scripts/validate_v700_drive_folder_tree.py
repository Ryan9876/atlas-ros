#!/usr/bin/env python3
"""Expand and validate compact Atlas ROS v7 Google Drive folder evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.validate_v700_drive_folder_traversal import (
    DriveFolderTraversalError,
    canonical_sha256,
    validate_folder_traversal,
)


def expand_compact_tree(payload: dict[str, Any]) -> dict[str, Any]:
    """Expand [id, title, children] nodes into explicit parent/child records."""
    expected = payload.get("folder_tree_sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        raise DriveFolderTraversalError("folder_tree_sha256 must be a SHA-256")
    unsigned = dict(payload)
    unsigned.pop("folder_tree_sha256", None)
    actual = canonical_sha256(unsigned)
    if actual != expected:
        raise DriveFolderTraversalError("compact folder tree digest mismatch")

    tree = payload.get("tree")
    folders: list[dict[str, Any]] = []
    seen: set[str] = set()

    def visit(node: Any, parent_id: str | None) -> str:
        if (
            not isinstance(node, list)
            or len(node) != 3
            or not isinstance(node[0], str)
            or not node[0].strip()
            or not isinstance(node[1], str)
            or not node[1].strip()
            or not isinstance(node[2], list)
        ):
            raise DriveFolderTraversalError(
                "compact folder nodes must be [folder_id, title, children]"
            )
        folder_id, title, raw_children = node
        if folder_id in seen:
            raise DriveFolderTraversalError(f"duplicate compact folder_id: {folder_id}")
        seen.add(folder_id)
        child_ids: list[str] = []
        for child in raw_children:
            child_id = visit(child, folder_id)
            child_ids.append(child_id)
        folders.append(
            {
                "folder_id": folder_id,
                "title": title,
                "parent_id": parent_id,
                "child_folder_ids": child_ids,
                "listing_complete": True,
                "unconsumed_page_tokens": 0,
                "inaccessible_child_ids": [],
            }
        )
        return folder_id

    root_id = visit(tree, None)
    source_root_id = payload.get("source_root_id")
    if root_id != source_root_id:
        raise DriveFolderTraversalError(
            "compact tree root does not match source_root_id"
        )

    expanded = {
        "schema_version": payload.get("schema_version"),
        "captured_on": payload.get("captured_on"),
        "source_root_id": source_root_id,
        "folder_traversal_complete": payload.get("folder_traversal_complete"),
        "item_inventory_complete": payload.get("item_inventory_complete"),
        "file_content_checksums_complete": payload.get(
            "file_content_checksums_complete"
        ),
        "evidence_basis": payload.get("evidence_basis"),
        "folders": folders,
        "source_evidence_sha256": actual,
    }
    expanded["folder_tree_sha256"] = canonical_sha256(expanded)
    return expanded


def load_expand_and_validate(path: Path) -> dict[str, Any]:
    """Load compact evidence, expand it, and validate fail-closed readiness."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DriveFolderTraversalError(
            f"invalid compact Drive folder evidence: {path}"
        ) from error
    if not isinstance(payload, dict):
        raise DriveFolderTraversalError("compact Drive folder evidence must be an object")
    expanded = expand_compact_tree(payload)
    result = validate_folder_traversal(expanded)
    result["source_evidence_sha256"] = expanded["source_evidence_sha256"]
    inventory_path = path.with_name("v700-drive-file-inventory.json")
    if inventory_path.is_file():
        from scripts.validate_v700_drive_file_inventory import (
            load_and_validate as validate_file_inventory,
        )

        result["file_inventory"] = validate_file_inventory(
            inventory_path,
            folder_path=path,
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = load_expand_and_validate(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
