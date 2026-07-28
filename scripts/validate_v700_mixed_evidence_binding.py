#!/usr/bin/env python3
"""Bind mixed Drive evidence to one exact-head validation chain."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


class MixedEvidenceBindingError(ValueError):
    """Raised when exact-head mixed evidence cannot be safely bound."""


def _fail(message: str) -> None:
    raise MixedEvidenceBindingError(message)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise MixedEvidenceBindingError(
            f"invalid JSON evidence: {path}"
        ) from error
    if not isinstance(value, dict):
        _fail(f"JSON evidence must be an object: {path}")
    return value


def _hex(value: Any, length: int, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != length
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail(f"{field} must be {length} lowercase hexadecimal characters")
    return value


def _positive_integer(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        _fail(f"{field} must be a positive integer")
    return value


def _workflow_binding(
    *,
    run_id: int,
    artifact_id: int,
    artifact_digest: str,
) -> dict[str, Any]:
    return {
        "run_id": _positive_integer(run_id, "workflow run ID"),
        "artifact_id": _positive_integer(artifact_id, "artifact ID"),
        "artifact_sha256": _hex(
            artifact_digest,
            64,
            "artifact digest",
        ),
    }


def validate_mixed_evidence_binding(
    *,
    head_sha: str,
    exact_package_chain: dict[str, Any],
    documentation_result: dict[str, Any],
    internal_package_result: dict[str, Any],
    exact_run_id: int,
    exact_artifact_id: int,
    exact_artifact_digest: str,
    documentation_run_id: int,
    documentation_artifact_id: int,
    documentation_artifact_digest: str,
    internal_run_id: int,
    internal_artifact_id: int,
    internal_artifact_digest: str,
) -> dict[str, Any]:
    """Validate and bind three exact-head evidence artifacts."""
    validated_head = _hex(head_sha, 40, "head SHA")

    if exact_package_chain.get("status") != (
        "partial_file_inventory_with_complete_release_supplement_chain"
    ):
        _fail("exact-artifact package chain status is invalid")
    if exact_package_chain.get("supplement_count") != 3:
        _fail("exact-artifact package supplement count is invalid")
    if exact_package_chain.get("releases") != ["5.0", "4.5.3", "4.5.0"]:
        _fail("exact-artifact package release order is invalid")
    if exact_package_chain.get("combined_scanned_folder_count") != 8:
        _fail("exact-artifact package folder count is invalid")
    if exact_package_chain.get("combined_file_count") != 53:
        _fail("exact-artifact package file count is invalid")
    if exact_package_chain.get("combined_content_hashed_count") != 52:
        _fail("exact-artifact package hash count is invalid")
    if exact_package_chain.get("promotion_ready") is not False:
        _fail("exact-artifact package evidence cannot be promotion ready")

    if documentation_result.get("status") != (
        "partial_file_inventory_with_complete_package_and_"
        "documentation_supplements"
    ):
        _fail("documentation evidence status is invalid")
    if documentation_result.get("package_releases") != [
        "5.0",
        "4.5.3",
        "4.5.0",
    ]:
        _fail("documentation evidence package releases are inconsistent")
    if documentation_result.get("documentation_releases") != ["4.5.1"]:
        _fail("documentation evidence release set is invalid")
    if documentation_result.get("combined_scanned_folder_count") != 9:
        _fail("documentation evidence folder count is invalid")
    if documentation_result.get("combined_file_count") != 56:
        _fail("documentation evidence file count is invalid")
    if documentation_result.get("combined_content_hashed_count") != 55:
        _fail("documentation evidence hash count is invalid")
    if documentation_result.get("package_claims_authorized_for_documentation") is not False:
        _fail("documentation evidence cannot authorize package claims")
    if documentation_result.get("promotion_ready") is not False:
        _fail("documentation evidence cannot be promotion ready")

    if internal_package_result.get("status") != (
        "partial_file_inventory_with_complete_mixed_evidence_supplements"
    ):
        _fail("internal-package evidence status is invalid")
    if internal_package_result.get(
        "externally_reconciled_package_releases"
    ) != ["5.0", "4.5.3", "4.5.0"]:
        _fail("internal-package evidence package releases are inconsistent")
    if internal_package_result.get("documentation_releases") != ["4.5.1"]:
        _fail("internal-package documentation releases are inconsistent")
    if internal_package_result.get(
        "internally_closed_unreconciled_package_releases"
    ) != ["4.5.2"]:
        _fail("internally closed package release set is invalid")
    if internal_package_result.get("combined_scanned_folder_count") != 10:
        _fail("mixed evidence folder count is invalid")
    if internal_package_result.get("combined_file_count") != 64:
        _fail("mixed evidence file count is invalid")
    if internal_package_result.get("combined_content_hashed_count") != 63:
        _fail("mixed evidence hash count is invalid")
    if internal_package_result.get(
        "unreconciled_package_promotion_authorized"
    ) is not False:
        _fail("unreconciled package promotion cannot be authorized")
    if internal_package_result.get("promotion_ready") is not False:
        _fail("mixed evidence cannot be promotion ready")

    package_count = exact_package_chain.get("combined_file_count")
    documentation_increment = (
        documentation_result.get("combined_file_count") - package_count
    )
    internal_increment = (
        internal_package_result.get("combined_file_count")
        - documentation_result.get("combined_file_count")
    )
    if documentation_increment != 3:
        _fail("documentation evidence increment is invalid")
    if internal_increment != 8:
        _fail("internal-package evidence increment is invalid")

    for result, label in (
        (exact_package_chain, "exact package"),
        (documentation_result, "documentation"),
        (internal_package_result, "internal package"),
    ):
        if result.get("provider_writes") != 0:
            _fail(f"{label} evidence records provider writes")
        if result.get("drive_retirement_authorized") is not False:
            _fail(f"{label} evidence authorizes Drive retirement")
        if result.get("credential_action_authorized") is not False:
            _fail(f"{label} evidence authorizes credential actions")

    return {
        "schema_version": "1.0",
        "status": "mixed_drive_evidence_bound_to_exact_head",
        "head_sha": validated_head,
        "exact_artifact": _workflow_binding(
            run_id=exact_run_id,
            artifact_id=exact_artifact_id,
            artifact_digest=exact_artifact_digest,
        ),
        "documentation_evidence": _workflow_binding(
            run_id=documentation_run_id,
            artifact_id=documentation_artifact_id,
            artifact_digest=documentation_artifact_digest,
        ),
        "internal_package_evidence": _workflow_binding(
            run_id=internal_run_id,
            artifact_id=internal_artifact_id,
            artifact_digest=internal_artifact_digest,
        ),
        "externally_reconciled_package_releases": [
            "5.0",
            "4.5.3",
            "4.5.0",
        ],
        "documentation_releases": ["4.5.1"],
        "internally_closed_unreconciled_package_releases": ["4.5.2"],
        "combined_known_folder_count": 93,
        "combined_scanned_folder_count": 10,
        "combined_unscanned_folder_count": 83,
        "combined_file_count": 64,
        "combined_content_hashed_count": 63,
        "enumeration_complete": False,
        "content_checksums_complete": False,
        "promotion_ready": False,
        "provider_writes": 0,
        "drive_retirement_authorized": False,
        "credential_action_authorized": False,
        "unreconciled_package_promotion_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--exact-package-chain", type=Path, required=True)
    parser.add_argument("--documentation-result", type=Path, required=True)
    parser.add_argument("--internal-package-result", type=Path, required=True)
    parser.add_argument("--exact-run-id", type=int, required=True)
    parser.add_argument("--exact-artifact-id", type=int, required=True)
    parser.add_argument("--exact-artifact-digest", required=True)
    parser.add_argument("--documentation-run-id", type=int, required=True)
    parser.add_argument("--documentation-artifact-id", type=int, required=True)
    parser.add_argument("--documentation-artifact-digest", required=True)
    parser.add_argument("--internal-run-id", type=int, required=True)
    parser.add_argument("--internal-artifact-id", type=int, required=True)
    parser.add_argument("--internal-artifact-digest", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = validate_mixed_evidence_binding(
        head_sha=args.head_sha,
        exact_package_chain=_read_json(args.exact_package_chain),
        documentation_result=_read_json(args.documentation_result),
        internal_package_result=_read_json(args.internal_package_result),
        exact_run_id=args.exact_run_id,
        exact_artifact_id=args.exact_artifact_id,
        exact_artifact_digest=args.exact_artifact_digest,
        documentation_run_id=args.documentation_run_id,
        documentation_artifact_id=args.documentation_artifact_id,
        documentation_artifact_digest=args.documentation_artifact_digest,
        internal_run_id=args.internal_run_id,
        internal_artifact_id=args.internal_artifact_id,
        internal_artifact_digest=args.internal_artifact_digest,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
