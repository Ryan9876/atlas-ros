from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_v700_drive_documentation_supplement_chain import (
    DriveDocumentationSupplementChainError,
    canonical_sha256,
    validate_documentation_supplement_chain,
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


def resign(payload: dict[str, object]) -> dict[str, object]:
    payload.pop("supplement_sha256", None)
    payload["supplement_sha256"] = canonical_sha256(payload)
    return payload


def validate(
    documentation: list[dict[str, object]],
) -> dict[str, object]:
    return validate_documentation_supplement_chain(
        documentation,
        package_supplements=package_chain(),
        folder_payload=load("release/v700-drive-folder-traversal.json"),
        base_inventory=load("release/v700-drive-file-inventory.json"),
        base_receipts=load("release/v700-drive-file-listing-receipts.json"),
    )


def test_live_documentation_chain_is_complete_and_fail_closed() -> None:
    result = validate(documentation_chain())

    assert result["status"] == (
        "partial_file_inventory_with_complete_package_and_"
        "documentation_supplements"
    )
    assert result["package_supplement_count"] == 3
    assert result["package_releases"] == ["5.0", "4.5.3", "4.5.0"]
    assert result["documentation_supplement_count"] == 1
    assert result["documentation_releases"] == ["4.5.1"]
    assert result["combined_known_folder_count"] == 93
    assert result["combined_scanned_folder_count"] == 9
    assert result["combined_unscanned_folder_count"] == 84
    assert result["combined_file_count"] == 56
    assert result["combined_content_hashed_count"] == 55
    assert result["combined_sensitive_item_count"] == 1
    assert result["combined_verified_github_equivalence_count"] == 1
    assert result["combined_governed_legacy_exception_count"] == 54
    assert result["documentation_export_size_bytes"] == 8001
    assert result["package_claims_authorized_for_documentation"] is False
    assert result["promotion_ready"] is False
    assert result["provider_writes"] == 0
    assert result["drive_retirement_authorized"] is False
    assert result["credential_action_authorized"] is False


def test_documentation_chain_rejects_package_folder_overlap() -> None:
    documentation = documentation_chain()
    documentation[0]["scanned_folder_ids"] = [
        package_chain()[0]["scanned_folder_ids"][0]
    ]
    resign(documentation[0])

    with pytest.raises(
        DriveDocumentationSupplementChainError,
        match="folders overlap prior evidence",
    ):
        validate(documentation)


def test_documentation_chain_rejects_package_claim_fields() -> None:
    documentation = documentation_chain()
    documentation[0]["release_package_file_id"] = "not-authorized"
    resign(documentation[0])

    with pytest.raises(
        DriveDocumentationSupplementChainError,
        match="prohibited package fields",
    ):
        validate(documentation)


def test_documentation_chain_rejects_incomplete_document_set() -> None:
    documentation = documentation_chain()
    documentation[0]["required_document_titles"] = ["RELEASE_MANIFEST.md"]
    resign(documentation[0])

    with pytest.raises(
        DriveDocumentationSupplementChainError,
        match="required document set does not reconcile",
    ):
        validate(documentation)


def test_documentation_chain_rejects_invalid_export_size() -> None:
    documentation = documentation_chain()
    documentation[0]["files"][0][6] = -1
    resign(documentation[0])

    with pytest.raises(
        DriveDocumentationSupplementChainError,
        match="invalid export size",
    ):
        validate(documentation)


def test_documentation_chain_rejects_supplement_digest_tampering() -> None:
    documentation = documentation_chain()
    documentation[0]["files"][0][2] = "TAMPERED"

    with pytest.raises(
        DriveDocumentationSupplementChainError,
        match="documentation supplement digest mismatch",
    ):
        validate(documentation)
