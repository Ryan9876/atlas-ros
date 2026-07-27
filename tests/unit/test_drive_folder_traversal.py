from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_v700_drive_folder_traversal import (
    DriveFolderTraversalError,
    canonical_sha256,
    load_and_validate,
    validate_folder_traversal,
)
from scripts.validate_v700_drive_folder_tree import load_expand_and_validate


def evidence() -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "captured_on": "2026-07-27",
        "source_root_id": "root",
        "folder_traversal_complete": True,
        "item_inventory_complete": False,
        "file_content_checksums_complete": False,
        "evidence_basis": "unit test",
        "folders": [
            {
                "folder_id": "root",
                "title": "Root",
                "parent_id": None,
                "child_folder_ids": ["child"],
                "listing_complete": True,
                "unconsumed_page_tokens": 0,
                "inaccessible_child_ids": [],
            },
            {
                "folder_id": "child",
                "title": "Child",
                "parent_id": "root",
                "child_folder_ids": [],
                "listing_complete": True,
                "unconsumed_page_tokens": 0,
                "inaccessible_child_ids": [],
            },
        ],
    }
    payload["folder_tree_sha256"] = canonical_sha256(payload)
    return payload


def resign(payload: dict[str, object]) -> dict[str, object]:
    payload.pop("folder_tree_sha256", None)
    payload["folder_tree_sha256"] = canonical_sha256(payload)
    return payload


def test_complete_folder_traversal_remains_fail_closed_for_item_inventory() -> None:
    result = validate_folder_traversal(evidence())

    assert result["folder_count"] == 2
    assert result["leaf_folder_count"] == 1
    assert result["max_depth"] == 1
    assert result["status"] == "folder_traversal_complete_item_inventory_incomplete"
    assert result["promotion_ready"] is False
    assert result["provider_writes"] == 0
    assert result["drive_retirement_authorized"] is False


def test_parent_child_mismatch_is_rejected() -> None:
    payload = evidence()
    payload["folders"][1]["parent_id"] = "other"
    resign(payload)

    with pytest.raises(
        DriveFolderTraversalError,
        match="parent mismatch|missing parent",
    ):
        validate_folder_traversal(payload)


def test_complete_traversal_rejects_unconsumed_page_tokens() -> None:
    payload = evidence()
    payload["folders"][0]["unconsumed_page_tokens"] = 1
    resign(payload)

    with pytest.raises(
        DriveFolderTraversalError,
        match="folder traversal cannot be complete",
    ):
        validate_folder_traversal(payload)


def test_complete_item_inventory_requires_file_checksums() -> None:
    payload = evidence()
    payload["item_inventory_complete"] = True
    resign(payload)

    with pytest.raises(
        DriveFolderTraversalError,
        match="complete item inventory requires complete file content checksums",
    ):
        validate_folder_traversal(payload)


def test_digest_tampering_is_rejected(tmp_path: Path) -> None:
    payload = evidence()
    path = tmp_path / "traversal.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    payload["folders"][1]["title"] = "Tampered"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(DriveFolderTraversalError, match="digest mismatch"):
        load_and_validate(path)


def test_live_folder_tree_is_complete_but_not_promotion_ready() -> None:
    result = load_expand_and_validate(Path("release/v700-drive-folder-tree.json"))

    assert result["status"] == "folder_traversal_complete_item_inventory_incomplete"
    assert result["folder_count"] == 93
    assert result["leaf_folder_count"] == 78
    assert result["max_depth"] == 6
    assert result["folder_traversal_complete"] is True
    assert result["item_inventory_complete"] is False
    assert result["file_content_checksums_complete"] is False
    assert result["unconsumed_page_tokens"] == 0
    assert result["inaccessible_child_ids"] == []
    assert result["promotion_ready"] is False
    assert result["provider_writes"] == 0
    assert result["drive_retirement_authorized"] is False
    assert result["source_evidence_sha256"] == (
        "574cac3a8e1a4f00710f593cf14ae0534c46a31ffce847aff474414ae8886cf8"
    )
