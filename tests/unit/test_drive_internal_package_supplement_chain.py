from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_v700_drive_internal_package_supplement_chain import (
    DriveInternalPackageSupplementChainError,
    canonical_sha256,
    validate_internal_package_supplement_chain,
)


ROOT = Path(__file__).resolve().parents[2]


def load(name: str) -> dict[str, object]:
    value = json.loads((ROOT / name).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def package_chain() -> list[dict[str, object]]:
    return [
        load("release/v700-drive-v500-file-supplement.json"),
        load("release/v700-drive-v453-file-supplement.json"),
        load("release/v700-drive-v450-file-supplement.json"),
    ]


def documentation_chain() -> list[dict[str, object]]:
    return [load("release/v700-drive-v451-documentation-supplement.json")]


def internal_chain() -> list[dict[str, object]]:
    return [load("release/v700-drive-v452-internal-package-supplement.json")]


def resign(payload: dict[str, object]) -> dict[str, object]:
    payload.pop("supplement_sha256", None)
    payload["supplement_sha256"] = canonical_sha256(payload)
    return payload


def validate(internal: list[dict[str, object]]) -> dict[str, object]:
    return validate_internal_package_supplement_chain(
        internal,
        package_supplements=package_chain(),
        documentation_supplements=documentation_chain(),
        folder_payload=load("release/v700-drive-folder-traversal.json"),
        base_inventory=load("release/v700-drive-file-inventory.json"),
        base_receipts=load("release/v700-drive-file-listing-receipts.json"),
    )


def test_live_internal_package_chain_is_complete_and_fail_closed() -> None:
    result = validate(internal_chain())

    assert result["status"] == (
        "partial_file_inventory_with_complete_mixed_evidence_supplements"
    )
    assert result["externally_reconciled_package_count"] == 3
    assert result["externally_reconciled_package_releases"] == [
        "5.0",
        "4.5.3",
        "4.5.0",
    ]
    assert result["documentation_supplement_count"] == 1
    assert result["documentation_releases"] == ["4.5.1"]
    assert result["internally_closed_unreconciled_package_count"] == 1
    assert result["internally_closed_unreconciled_package_releases"] == [
        "4.5.2"
    ]
    supplement = result["internal_package_supplements"][0]
    assert supplement["supplement_sha256"] == (
        "7f87a1410cce585d0520027479a1e5448e04d7ed392c57437d79d905112ed4b4"
    )
    assert supplement["direct_file_count"] == 8
    assert supplement["archive_entry_count"] == 10
    assert supplement["checksum_covered_entry_count"] == 9
    assert supplement["direct_internal_binding_count"] == 7
    assert supplement["direct_folder_absent_internal_entry_count"] == 3
    assert supplement["internal_checksums_closed"] is True
    assert supplement["external_package_sidecar_present"] is False
    assert supplement["external_package_digest_reconciled"] is False
    assert supplement["package_promotion_claim_authorized"] is False
    assert result["combined_known_folder_count"] == 93
    assert result["combined_scanned_folder_count"] == 10
    assert result["combined_unscanned_folder_count"] == 83
    assert result["combined_file_count"] == 64
    assert result["combined_content_hashed_count"] == 63
    assert result["combined_sensitive_item_count"] == 1
    assert result["combined_verified_github_equivalence_count"] == 1
    assert result["combined_governed_legacy_exception_count"] == 62
    assert result["promotion_ready"] is False
    assert result["provider_writes"] == 0
    assert result["drive_retirement_authorized"] is False
    assert result["credential_action_authorized"] is False
    assert result["unreconciled_package_promotion_authorized"] is False


def test_internal_package_rejects_external_sidecar_claim() -> None:
    internal = internal_chain()
    internal[0]["external_package_sidecar_present"] = True
    resign(internal[0])

    with pytest.raises(
        DriveInternalPackageSupplementChainError,
        match="cannot claim an external package sidecar",
    ):
        validate(internal)


def test_internal_package_rejects_checksum_text_mismatch() -> None:
    internal = internal_chain()
    internal[0]["checksum_file_text"] = "incorrect\n"
    resign(internal[0])

    with pytest.raises(
        DriveInternalPackageSupplementChainError,
        match="checksum-file text hash does not match bytes",
    ):
        validate(internal)


def test_internal_package_rejects_missing_archive_entry() -> None:
    internal = internal_chain()
    internal[0]["internal_archive_entries"] = internal[0][
        "internal_archive_entries"
    ][:-1]
    internal[0]["archive_entry_count"] = 9
    resign(internal[0])

    with pytest.raises(
        DriveInternalPackageSupplementChainError,
        match="internal checksum mismatch",
    ):
        validate(internal)


def test_internal_package_rejects_direct_internal_byte_mismatch() -> None:
    internal = internal_chain()
    internal[0]["files"][0][6] = "0" * 64
    resign(internal[0])

    with pytest.raises(
        DriveInternalPackageSupplementChainError,
        match="attestation text hash does not match bytes",
    ):
        validate(internal)


def test_internal_package_rejects_promotion_claim() -> None:
    internal = internal_chain()
    internal[0]["package_promotion_claim_authorized"] = True
    resign(internal[0])

    with pytest.raises(
        DriveInternalPackageSupplementChainError,
        match="cannot authorize package promotion",
    ):
        validate(internal)


def test_internal_package_rejects_supplement_digest_tampering() -> None:
    internal = internal_chain()
    internal[0]["files"][0][2] = "TAMPERED"

    with pytest.raises(
        DriveInternalPackageSupplementChainError,
        match="internal-package supplement digest mismatch",
    ):
        validate(internal)
