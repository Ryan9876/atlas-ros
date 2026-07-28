#!/usr/bin/env python3
"""Validate the Atlas ROS v7 final controller without publishing or activation."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from tools.release.drive_migration_ledger import load_ledger
from tools.release.final_controller import (
    AuthorityActivationEvidence,
    FinalPackageEvidence,
    PostPublicationEvidence,
    compile_authority_activation,
    compile_final_controller,
    verify_post_publication,
)
from tools.release.live_authority_snapshot import LiveAuthoritySnapshot, load_snapshot
from tools.release.rollback_evidence import load_receipt


class FinalControllerValidationError(ValueError):
    """Raised when exact-artifact evidence cannot support controller validation."""


def validate_final_controller(
    *,
    exact_artifact_validation_path: Path,
    final_package_validation_path: Path,
    final_package_artifact_id: str,
    final_package_artifact_digest: str,
    final_source_commit: str,
    candidate_pr_merged: bool,
    decision_record_url: str,
    review_record_url: str,
    output_dir: Path,
    drive_ledger_path: Path | None = None,
    live_authority_snapshot_path: Path | None = None,
    v650_rollback_evidence_path: Path | None = None,
    exact_package_authorization_id: str | None = None,
) -> dict[str, Any]:
    """Generate non-publishing final, verification, and activation evidence."""
    exact = _read_json(exact_artifact_validation_path)
    if exact.get("status") not in {"passed", "passed_with_findings"}:
        raise FinalControllerValidationError(
            "exact-artifact validation must pass before final-controller validation"
        )
    if exact.get("provider_writes") != 0:
        raise FinalControllerValidationError(
            "exact-artifact validation performed provider writes"
        )
    candidate_sha = _required_string(exact, "candidate_sha")
    artifact_id = str(exact.get("candidate_artifact_id", ""))
    artifact_digest = _required_string(exact, "candidate_artifact_digest")
    final_package = _read_json(final_package_validation_path)
    if final_package.get("status") not in {"passed", "passed_with_findings"}:
        raise FinalControllerValidationError(
            "final-package validation must pass before final-controller validation"
        )
    if final_package.get("provider_writes") != 0:
        raise FinalControllerValidationError("final-package validation performed provider writes")
    if final_package.get("final_version") != "7.0.0":
        raise FinalControllerValidationError("final package version is not 7.0.0")
    if final_package.get("final_source_commit") != final_source_commit:
        raise FinalControllerValidationError(
            "final-package validation references a different final source commit"
        )
    source_sha256 = _required_string(final_package, "source_sha256")
    wheel_sha256 = _required_string(final_package, "wheel_sha256")
    _require_digest("final package artifact digest", final_package_artifact_digest, 64)
    if not final_package_artifact_id.strip():
        raise FinalControllerValidationError("final package artifact ID is required")
    drive_ledger = load_ledger(drive_ledger_path) if drive_ledger_path else None
    live_authority = _live_authority_snapshot(
        live_authority_snapshot_path,
        final_source_commit=final_source_commit,
        artifact_digest=final_package_artifact_digest,
    )
    rollback_evidence = (
        load_receipt(v650_rollback_evidence_path)
        if v650_rollback_evidence_path
        else None
    )

    final_receipt = compile_final_controller(
        FinalPackageEvidence(
            candidate_version="7.0.0rc1",
            candidate_commit=candidate_sha,
            final_source_commit=final_source_commit,
            candidate_pr_merged=candidate_pr_merged,
            candidate_artifact_id=artifact_id,
            candidate_artifact_digest=artifact_digest,
            final_package_version="7.0.0",
            final_package_artifact_id=final_package_artifact_id,
            final_package_artifact_digest=final_package_artifact_digest,
            source_sha256=source_sha256,
            wheel_sha256=wheel_sha256,
            standard_ci_passed=True,
            architecture_validation_passed=True,
            candidate_validation_passed=True,
            exact_artifact_validation_passed=True,
            final_package_validation_passed=True,
            drive_migration_ledger_complete=(
                drive_ledger.complete_for_promotion_readiness if drive_ledger else False
            ),
            drive_migration_ledger_sha256=(
                drive_ledger.ledger_sha256 if drive_ledger else None
            ),
            live_authority_readback_complete=(
                live_authority.complete if live_authority else False
            ),
            required_integrations_ready=bool(exact.get("integration_snapshot_ready")),
            v650_rollback_restored=bool(
                exact.get("active_v650_restoration_passed")
            ),
            v650_rollback_evidence_reconciled=(
                rollback_evidence.status == "ready" if rollback_evidence else False
            ),
            v650_rollback_evidence_sha256=(
                rollback_evidence.evidence_digest if rollback_evidence else None
            ),
            review_record_url=review_record_url,
            decision_record_url=decision_record_url,
            exact_package_authorization_id=exact_package_authorization_id,
            provider_writes_during_validation=0,
        ),
        transaction_id=f"final-controller-v700-{final_source_commit[:12]}",
    )

    publication_receipt = verify_post_publication(
        PostPublicationEvidence(
            final_version="7.0.0",
            final_tag="v7.0.0",
            final_source_commit=final_source_commit,
            published_release_readable=False,
            immutable_tag_points_to_final_source=False,
            publication_checksums_passed=False,
            source_sha256_matches_identity=False,
            wheel_sha256_matches_identity=False,
            clean_install_passed=False,
            v650_rollback_restored=bool(
                exact.get("active_v650_restoration_passed")
            ),
            v620_historical_rollback_restored=bool(
                exact.get("rollback_v620_restoration_passed")
            ),
            live_authority_readback_complete=False,
            provider_writes_during_verification=0,
        ),
        transaction_id=f"post-publication-v700-{final_source_commit[:12]}",
    )

    activation_receipt = compile_authority_activation(
        AuthorityActivationEvidence(
            final_version="7.0.0",
            final_tag="v7.0.0",
            final_source_commit=final_source_commit,
            post_publication_verification_passed=False,
            release_index_digest="",
            authority_record_digest="",
            active_manifest_digest="",
            notion_system_state_readback_passed=False,
            integration_inventory_readback_passed=False,
            v650_rollback_restored=bool(
                exact.get("active_v650_restoration_passed")
            ),
            exact_package_authorization_id=exact_package_authorization_id,
            provider_writes_during_activation_validation=0,
        ),
        transaction_id=f"authority-activation-v700-{final_source_commit[:12]}",
    )

    result = {
        "schema_version": "1.0",
        "status": "validated_not_authorized",
        "candidate_sha": candidate_sha,
        "final_source_commit": final_source_commit,
        "final_package_validation_present": True,
        "final_package_artifact_id": final_package_artifact_id,
        "final_package_artifact_digest": final_package_artifact_digest,
        "final_package_digest": final_package.get("final_package_digest"),
        "final_source_sha256": source_sha256,
        "final_wheel_sha256": wheel_sha256,
        "final_controller": asdict(final_receipt),
        "post_publication_verification": asdict(publication_receipt),
        "authority_activation": asdict(activation_receipt),
        "drive_migration_ledger_present": drive_ledger is not None,
        "drive_migration_ledger_sha256": (
            drive_ledger.ledger_sha256 if drive_ledger else None
        ),
        "live_authority_snapshot_present": live_authority is not None,
        "live_authority_snapshot_sha256": (
            live_authority.snapshot_sha256 if live_authority else None
        ),
        "v650_rollback_evidence_present": rollback_evidence is not None,
        "v650_rollback_evidence_sha256": (
            rollback_evidence.evidence_digest if rollback_evidence else None
        ),
        "provider_writes": 0,
        "publication_performed": False,
        "tag_created": False,
        "authority_activated": False,
        "drive_retired": False,
    }
    _require_non_publishing_result(result)
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "V700_FINAL_CONTROLLER_VALIDATION.json", result)
    _write_json(
        output_dir / "FINAL_PUBLICATION_CONTROLLER_PLAN.json",
        asdict(final_receipt),
    )
    _write_json(
        output_dir / "POST_PUBLICATION_VERIFICATION_PLAN.json",
        asdict(publication_receipt),
    )
    _write_json(
        output_dir / "AUTHORITY_ACTIVATION_PLAN.json",
        asdict(activation_receipt),
    )
    _write_summary(result, output_dir / "V700_FINAL_CONTROLLER_VALIDATION.md")
    return result


def _live_authority_snapshot(
    path: Path | None,
    *,
    final_source_commit: str,
    artifact_digest: str,
) -> LiveAuthoritySnapshot | None:
    if path is None:
        return None
    snapshot = load_snapshot(path)
    if snapshot.phase != "pre_promotion_baseline":
        raise FinalControllerValidationError(
            "final controller requires a pre-promotion baseline authority snapshot"
        )
    if snapshot.exact_package_commit != final_source_commit:
        raise FinalControllerValidationError(
            "live authority snapshot references a different final source commit"
        )
    if snapshot.exact_artifact_digest != artifact_digest:
        raise FinalControllerValidationError(
            "live authority snapshot references a different candidate artifact"
        )
    return snapshot


def _require_non_publishing_result(result: dict[str, Any]) -> None:
    if result["provider_writes"] != 0:
        raise FinalControllerValidationError("final-controller validation wrote providers")
    for field in (
        "publication_performed",
        "tag_created",
        "authority_activated",
        "drive_retired",
    ):
        if result[field] is not False:
            raise FinalControllerValidationError(
                f"final-controller validation claimed prohibited action: {field}"
            )


def _require_digest(field: str, value: str, length: int) -> None:
    if len(value) != length or any(character not in "0123456789abcdef" for character in value):
        raise FinalControllerValidationError(
            f"{field} is not a lowercase {length}-character hexadecimal digest"
        )


def _required_string(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise FinalControllerValidationError(f"missing exact-artifact field: {field}")
    return value


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise FinalControllerValidationError(f"invalid JSON evidence: {path}") from error
    if not isinstance(value, dict):
        raise FinalControllerValidationError(f"JSON evidence must be an object: {path}")
    return value


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_summary(result: dict[str, Any], path: Path) -> None:
    final = result["final_controller"]
    publication = result["post_publication_verification"]
    activation = result["authority_activation"]
    final_blockers = "\n".join(f"- {item}" for item in final["blockers"]) or "- None"
    path.write_text(
        f"""# Atlas ROS v7 Final Controller Validation

- Status: `{result['status']}`
- Candidate SHA: `{result['candidate_sha']}`
- Final source commit: `{result['final_source_commit']}`
- Final package artifact: `{result['final_package_artifact_id']}`
- Final package artifact digest: `{result['final_package_artifact_digest']}`
- Final source SHA-256: `{result['final_source_sha256']}`
- Final wheel SHA-256: `{result['final_wheel_sha256']}`
- Final controller: `{final['status']}`
- Post-publication verification: `{publication['status']}`
- Authority activation: `{activation['status']}`
- Drive ledger: `{result['drive_migration_ledger_sha256'] or 'not supplied'}`
- Live authority snapshot: `{result['live_authority_snapshot_sha256'] or 'not supplied'}`
- v6.5 rollback evidence: `{result['v650_rollback_evidence_sha256'] or 'not supplied'}`
- Provider writes: `0`
- Publication performed: `false`
- Tag created: `false`
- Authority activated: `false`
- Drive retired: `false`

## Final-controller blockers

{final_blockers}
""",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exact-artifact-validation", type=Path, required=True)
    parser.add_argument("--final-package-validation", type=Path, required=True)
    parser.add_argument("--final-package-artifact-id", required=True)
    parser.add_argument("--final-package-artifact-digest", required=True)
    parser.add_argument("--final-source-commit", required=True)
    parser.add_argument("--candidate-pr-merged", action="store_true")
    parser.add_argument("--decision-record-url", required=True)
    parser.add_argument("--review-record-url", required=True)
    parser.add_argument("--drive-ledger", type=Path)
    parser.add_argument("--live-authority-snapshot", type=Path)
    parser.add_argument("--v650-rollback-evidence", type=Path)
    parser.add_argument("--authorization-id")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    validate_final_controller(
        exact_artifact_validation_path=args.exact_artifact_validation,
        final_package_validation_path=args.final_package_validation,
        final_package_artifact_id=args.final_package_artifact_id,
        final_package_artifact_digest=args.final_package_artifact_digest,
        final_source_commit=args.final_source_commit,
        candidate_pr_merged=args.candidate_pr_merged,
        decision_record_url=args.decision_record_url,
        review_record_url=args.review_record_url,
        output_dir=args.output_dir,
        drive_ledger_path=args.drive_ledger,
        live_authority_snapshot_path=args.live_authority_snapshot,
        v650_rollback_evidence_path=args.v650_rollback_evidence,
        exact_package_authorization_id=args.authorization_id,
    )


if __name__ == "__main__":
    main()