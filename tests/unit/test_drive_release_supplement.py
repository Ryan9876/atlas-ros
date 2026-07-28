from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.validate_v700_drive_release_supplement import (
    DriveReleaseSupplementError,
    canonical_sha256,
    validate_release_supplement,
)


ROOT = Path(__file__).resolve().parents[2]


def load(name: str) -> dict[str, object]:
    value = json.loads((ROOT / name).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def validate(payload: dict[str, object]) -> dict[str, object]:
    return validate_release_supplement(
        payload,
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


def test_live_v500_supplement_is_complete_and_fail_closed() -> None:
    result = validate(load("release/v700-drive-v500-file-supplement.json"))

    assert result["status"] == (
        "partial_file_inventory_with_complete_v500_supplement"
    )
    assert result["supplement_sha256"] == (
        "f2c9094c6836da57a1af759efe76cc882a6a37a69924b5f9f512bf60dff1c3a0"
    )
    assert result["v500_scanned_folder_count"] == 1
    assert result["v500_file_count"] == 18
    assert result["v500_content_hashed_count"] == 18
    assert result["v500_listing_count"] == 1
    assert result["v500_candidate_checksum_reconciled"] is True
    assert result["combined_known_folder_count"] == 93
    assert result["combined_scanned_folder_count"] == 6
    assert result["combined_unscanned_folder_count"] == 87
    assert result["combined_file_count"] == 34
    assert result["combined_content_hashed_count"] == 33
    assert result["combined_sensitive_item_count"] == 1
    assert result["combined_verified_github_equivalence_count"] == 1
    assert result["combined_governed_legacy_exception_count"] == 32
    assert result["promotion_ready"] is False
    assert result["provider_writes"] == 0
    assert result["drive_retirement_authorized"] is False
    assert result["credential_action_authorized"] is False


def test_v500_supplement_rejects_candidate_checksum_mismatch() -> None:
    payload = copy.deepcopy(
        load("release/v700-drive-v500-file-supplement.json")
    )
    payload["candidate_checksum_declared_sha256"] = "a" * 64
    resign(payload)

    with pytest.raises(
        DriveReleaseSupplementError,
        match="candidate package checksum does not reconcile",
    ):
        validate(payload)


def test_v500_supplement_rejects_missing_listing_file() -> None:
    payload = copy.deepcopy(
        load("release/v700-drive-v500-file-supplement.json")
    )
    listing = payload["listings"][0]
    listing["file_ids"] = listing["file_ids"][:-1]
    listing.pop("listing_sha256", None)
    listing["listing_sha256"] = canonical_sha256(listing)
    resign(payload)

    with pytest.raises(
        DriveReleaseSupplementError,
        match="do not close the supplement",
    ):
        validate(payload)


def test_v500_supplement_rejects_digest_tampering() -> None:
    payload = copy.deepcopy(
        load("release/v700-drive-v500-file-supplement.json")
    )
    payload["files"][0][2] = "TAMPERED"

    with pytest.raises(
        DriveReleaseSupplementError,
        match="supplement digest mismatch",
    ):
        validate(payload)
