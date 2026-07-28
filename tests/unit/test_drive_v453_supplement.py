from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.validate_v700_drive_v453_supplement import (
    DriveV453SupplementError,
    canonical_sha256,
    validate_v453_supplement,
)


ROOT = Path(__file__).resolve().parents[2]


def load(name: str) -> dict[str, object]:
    value = json.loads((ROOT / name).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def validate(payload: dict[str, object]) -> dict[str, object]:
    return validate_v453_supplement(
        payload,
        v500_payload=load("release/v700-drive-v500-file-supplement.json"),
        folder_payload=load("release/v700-drive-folder-traversal.json"),
        base_inventory=load("release/v700-drive-file-inventory.json"),
        base_receipts=load(
            "release/v700-drive-file-listing-receipts.json"
        ),
    )


def resign(payload: dict[str, object]) -> dict[str, object]:
    payload.pop("supplement_sha256", None)
    payload["supplement_sha256"] = canonical_sha256(payload)
    return payload


def test_live_v453_supplement_is_complete_and_fail_closed() -> None:
    result = validate(load("release/v700-drive-v453-file-supplement.json"))

    assert result["status"] == (
        "partial_file_inventory_with_complete_v500_and_v453_supplements"
    )
    assert result["supplement_sha256"] == (
        "20d51011071c1a976c52756b1f1d667075e7d60a0001e692daf290209e9ab6d6"
    )
    assert result["v453_scanned_folder_count"] == 1
    assert result["v453_file_count"] == 13
    assert result["v453_content_hashed_count"] == 13
    assert result["v453_listing_count"] == 1
    assert result["v453_package_checksum_reconciled"] is True
    assert result["combined_known_folder_count"] == 93
    assert result["combined_scanned_folder_count"] == 7
    assert result["combined_unscanned_folder_count"] == 86
    assert result["combined_file_count"] == 47
    assert result["combined_content_hashed_count"] == 46
    assert result["combined_sensitive_item_count"] == 1
    assert result["combined_verified_github_equivalence_count"] == 1
    assert result["combined_governed_legacy_exception_count"] == 45
    assert result["promotion_ready"] is False
    assert result["provider_writes"] == 0
    assert result["drive_retirement_authorized"] is False
    assert result["credential_action_authorized"] is False


def test_v453_supplement_rejects_checksum_text_byte_mismatch() -> None:
    payload = copy.deepcopy(
        load("release/v700-drive-v453-file-supplement.json")
    )
    payload["release_checksum_file_text"] += "tampered"
    resign(payload)

    with pytest.raises(
        DriveV453SupplementError,
        match="checksum file text hash does not match captured bytes",
    ):
        validate(payload)


def test_v453_supplement_rejects_checksum_declaration_mismatch() -> None:
    payload = copy.deepcopy(
        load("release/v700-drive-v453-file-supplement.json")
    )
    payload["release_checksum_declared_sha256"] = "a" * 64
    resign(payload)

    with pytest.raises(
        DriveV453SupplementError,
        match="checksum text does not declare the expected package",
    ):
        validate(payload)


def test_v453_supplement_rejects_missing_listing_file() -> None:
    payload = copy.deepcopy(
        load("release/v700-drive-v453-file-supplement.json")
    )
    listing = payload["listings"][0]
    listing["file_ids"] = listing["file_ids"][:-1]
    listing.pop("listing_sha256", None)
    listing["listing_sha256"] = canonical_sha256(listing)
    resign(payload)

    with pytest.raises(
        DriveV453SupplementError,
        match="listing does not close the supplement",
    ):
        validate(payload)


def test_v453_supplement_rejects_digest_tampering() -> None:
    payload = copy.deepcopy(
        load("release/v700-drive-v453-file-supplement.json")
    )
    payload["files"][0][2] = "TAMPERED"

    with pytest.raises(
        DriveV453SupplementError,
        match="supplement digest mismatch",
    ):
        validate(payload)
