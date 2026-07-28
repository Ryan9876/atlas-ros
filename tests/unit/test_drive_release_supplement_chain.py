from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.validate_v700_drive_release_supplement_chain import (
    DriveReleaseSupplementChainError,
    canonical_sha256,
    validate_supplement_chain,
)


ROOT = Path(__file__).resolve().parents[2]


def load(name: str) -> dict[str, object]:
    value = json.loads((ROOT / name).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def validate(supplements: list[dict[str, object]]) -> dict[str, object]:
    return validate_supplement_chain(
        supplements,
        folder_payload=load("release/v700-drive-folder-traversal.json"),
        base_inventory=load("release/v700-drive-file-inventory.json"),
        base_receipts=load("release/v700-drive-file-listing-receipts.json"),
    )


def resign(payload: dict[str, object]) -> dict[str, object]:
    payload.pop("supplement_sha256", None)
    payload["supplement_sha256"] = canonical_sha256(payload)
    return payload


def live_chain() -> list[dict[str, object]]:
    return [
        load("release/v700-drive-v500-file-supplement.json"),
        load("release/v700-drive-v453-file-supplement.json"),
        load("release/v700-drive-v450-file-supplement.json"),
    ]


def test_live_release_supplement_chain_is_complete_and_fail_closed() -> None:
    result = validate(live_chain())

    assert result["status"] == (
        "partial_file_inventory_with_complete_release_supplement_chain"
    )
    assert result["supplement_count"] == 3
    assert result["releases"] == ["5.0", "4.5.3", "4.5.0"]
    assert result["combined_known_folder_count"] == 93
    assert result["combined_scanned_folder_count"] == 8
    assert result["combined_unscanned_folder_count"] == 85
    assert result["combined_file_count"] == 53
    assert result["combined_content_hashed_count"] == 52
    assert result["combined_sensitive_item_count"] == 1
    assert result["combined_verified_github_equivalence_count"] == 1
    assert result["combined_governed_legacy_exception_count"] == 51
    assert result["promotion_ready"] is False
    assert result["provider_writes"] == 0
    assert result["drive_retirement_authorized"] is False
    assert result["credential_action_authorized"] is False


def test_chain_rejects_overlapping_release_folders() -> None:
    supplements = live_chain()
    supplements[1]["scanned_folder_ids"] = supplements[0]["scanned_folder_ids"]
    resign(supplements[1])

    with pytest.raises(
        DriveReleaseSupplementChainError,
        match="folders overlap prior evidence",
    ):
        validate(supplements)


def test_chain_rejects_checksum_file_text_mismatch() -> None:
    supplements = live_chain()
    supplements[1]["release_checksum_file_text"] = "incorrect\n"
    resign(supplements[1])

    with pytest.raises(
        DriveReleaseSupplementChainError,
        match="checksum-file text hash does not match bytes",
    ):
        validate(supplements)


def test_chain_rejects_v450_package_checksum_mismatch() -> None:
    supplements = live_chain()
    supplements[2]["release_checksum_declared_sha256"] = "0" * 64
    resign(supplements[2])

    with pytest.raises(
        DriveReleaseSupplementChainError,
        match="package checksum does not reconcile",
    ):
        validate(supplements)


def test_chain_rejects_supplement_digest_tampering() -> None:
    supplements = live_chain()
    supplements[1]["files"][0][2] = "TAMPERED"

    with pytest.raises(
        DriveReleaseSupplementChainError,
        match="supplement digest mismatch",
    ):
        validate(supplements)
