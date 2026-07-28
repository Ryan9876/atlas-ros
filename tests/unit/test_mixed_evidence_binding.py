from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.validate_v700_drive_documentation_supplement_chain import (
    validate_documentation_supplement_chain,
)
from scripts.validate_v700_drive_internal_package_supplement_chain import (
    validate_internal_package_supplement_chain,
)
from scripts.validate_v700_drive_release_supplement_chain import (
    validate_supplement_chain,
)
from scripts.validate_v700_mixed_evidence_binding import (
    MixedEvidenceBindingError,
    validate_mixed_evidence_binding,
)


ROOT = Path(__file__).resolve().parents[2]
HEAD = "9" * 40
DIGEST = "a" * 64


def load(name: str) -> dict[str, object]:
    value = json.loads((ROOT / name).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def package_supplements() -> list[dict[str, object]]:
    return [
        load("release/v700-drive-v500-file-supplement.json"),
        load("release/v700-drive-v453-file-supplement.json"),
        load("release/v700-drive-v450-file-supplement.json"),
    ]


def documentation_supplements() -> list[dict[str, object]]:
    return [load("release/v700-drive-v451-documentation-supplement.json")]


def internal_supplements() -> list[dict[str, object]]:
    return [load("release/v700-drive-v452-internal-package-supplement.json")]


def evidence() -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    folders = load("release/v700-drive-folder-traversal.json")
    inventory = load("release/v700-drive-file-inventory.json")
    receipts = load("release/v700-drive-file-listing-receipts.json")
    packages = package_supplements()
    documentation = documentation_supplements()

    package_result = validate_supplement_chain(
        packages,
        folder_payload=folders,
        base_inventory=inventory,
        base_receipts=receipts,
    )
    documentation_result = validate_documentation_supplement_chain(
        documentation,
        package_supplements=packages,
        folder_payload=folders,
        base_inventory=inventory,
        base_receipts=receipts,
    )
    internal_result = validate_internal_package_supplement_chain(
        internal_supplements(),
        package_supplements=packages,
        documentation_supplements=documentation,
        folder_payload=folders,
        base_inventory=inventory,
        base_receipts=receipts,
    )
    return package_result, documentation_result, internal_result


def validate(
    package_result: dict[str, object],
    documentation_result: dict[str, object],
    internal_result: dict[str, object],
    *,
    head_sha: str = HEAD,
) -> dict[str, object]:
    return validate_mixed_evidence_binding(
        head_sha=head_sha,
        exact_package_chain=package_result,
        documentation_result=documentation_result,
        internal_package_result=internal_result,
        exact_run_id=101,
        exact_artifact_id=201,
        exact_artifact_digest=DIGEST,
        documentation_run_id=102,
        documentation_artifact_id=202,
        documentation_artifact_digest="b" * 64,
        internal_run_id=103,
        internal_artifact_id=203,
        internal_artifact_digest="c" * 64,
    )


def test_live_evidence_binds_to_one_exact_head() -> None:
    package_result, documentation_result, internal_result = evidence()

    result = validate(package_result, documentation_result, internal_result)

    assert result["status"] == "mixed_drive_evidence_bound_to_exact_head"
    assert result["head_sha"] == HEAD
    assert result["combined_known_folder_count"] == 93
    assert result["combined_scanned_folder_count"] == 10
    assert result["combined_unscanned_folder_count"] == 83
    assert result["combined_file_count"] == 64
    assert result["combined_content_hashed_count"] == 63
    assert result["promotion_ready"] is False
    assert result["provider_writes"] == 0
    assert result["drive_retirement_authorized"] is False
    assert result["credential_action_authorized"] is False
    assert result["unreconciled_package_promotion_authorized"] is False


def test_binding_rejects_invalid_head_sha() -> None:
    package_result, documentation_result, internal_result = evidence()

    with pytest.raises(
        MixedEvidenceBindingError,
        match="head SHA must be 40 lowercase hexadecimal characters",
    ):
        validate(
            package_result,
            documentation_result,
            internal_result,
            head_sha="not-a-sha",
        )


def test_binding_rejects_documentation_count_drift() -> None:
    package_result, documentation_result, internal_result = evidence()
    documentation_result = copy.deepcopy(documentation_result)
    documentation_result["combined_file_count"] = 57

    with pytest.raises(
        MixedEvidenceBindingError,
        match="documentation evidence file count is invalid",
    ):
        validate(package_result, documentation_result, internal_result)


def test_binding_rejects_internal_package_promotion_claim() -> None:
    package_result, documentation_result, internal_result = evidence()
    internal_result = copy.deepcopy(internal_result)
    internal_result["unreconciled_package_promotion_authorized"] = True

    with pytest.raises(
        MixedEvidenceBindingError,
        match="unreconciled package promotion cannot be authorized",
    ):
        validate(package_result, documentation_result, internal_result)


def test_binding_rejects_provider_writes() -> None:
    package_result, documentation_result, internal_result = evidence()
    internal_result = copy.deepcopy(internal_result)
    internal_result["provider_writes"] = 1

    with pytest.raises(
        MixedEvidenceBindingError,
        match="internal package evidence records provider writes",
    ):
        validate(package_result, documentation_result, internal_result)


def test_binding_rejects_invalid_artifact_digest() -> None:
    package_result, documentation_result, internal_result = evidence()

    with pytest.raises(
        MixedEvidenceBindingError,
        match="artifact digest must be 64 lowercase hexadecimal characters",
    ):
        validate_mixed_evidence_binding(
            head_sha=HEAD,
            exact_package_chain=package_result,
            documentation_result=documentation_result,
            internal_package_result=internal_result,
            exact_run_id=101,
            exact_artifact_id=201,
            exact_artifact_digest="bad",
            documentation_run_id=102,
            documentation_artifact_id=202,
            documentation_artifact_digest="b" * 64,
            internal_run_id=103,
            internal_artifact_id=203,
            internal_artifact_digest="c" * 64,
        )
