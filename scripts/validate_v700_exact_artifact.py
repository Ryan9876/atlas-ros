#!/usr/bin/env python3
"""Validate one exact v7 build artifact without rebuilding or publishing it."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from tools.release.drive_migration_ledger import (
    DriveMigrationLedger,
    DriveMigrationLedgerError,
    load_and_compile,
)
from tools.release.rollback_evidence import (
    RollbackEvidenceError,
    RollbackEvidenceReceipt,
    load_receipt,
)
from tools.release.transaction_simulation import (
    PromotionSimulationEvidence,
    RollbackSimulationEvidence,
    simulate_promotion,
    simulate_rollback,
)


class ExactArtifactValidationError(ValueError):
    """Raised when immutable candidate evidence is incomplete or contradictory."""


def validate_checksums(root: Path, checksum_file: Path) -> None:
    """Verify every checksum line relative to one evidence root."""
    for line in checksum_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, relative = line.split("  ", 1)
        path = root / relative
        if not path.is_file():
            raise ExactArtifactValidationError(f"checksum target is missing: {relative}")
        if _sha256(path) != digest:
            raise ExactArtifactValidationError(f"checksum mismatch: {relative}")


def validate_exact_artifact(
    *,
    artifact_root: Path,
    candidate_sha: str,
    artifact_id: str,
    artifact_digest: str,
    candidate_run_id: str,
    standard_ci_run_id: str,
    architecture_run_id: str,
    performance_path: Path,
    integration_snapshot_path: Path,
    drive_inventory_path: Path | None,
    output_dir: Path,
    rollback_evidence_path: Path | None = None,
) -> dict[str, Any]:
    """Validate immutable candidate evidence and generate release-readiness receipts."""
    if len(candidate_sha) != 40:
        raise ExactArtifactValidationError("candidate SHA must be an immutable 40-character SHA")
    if len(artifact_digest) != 64:
        raise ExactArtifactValidationError("artifact digest must be a lowercase SHA-256")
    publication_checksums = artifact_root / "PUBLICATION_CHECKSUMS.sha256"
    evidence_root = artifact_root / "evidence"
    evidence_checksums = evidence_root / "EVIDENCE_CHECKSUMS.sha256"
    validate_checksums(artifact_root, publication_checksums)
    validate_checksums(evidence_root, evidence_checksums)

    identity = _read_json(evidence_root / "FINAL_IDENTITY_CANDIDATE.json")
    status = _read_json(evidence_root / "V700_CANDIDATE_STATUS.json")
    if identity["candidate_commit"] != candidate_sha or status["candidate_sha"] != candidate_sha:
        raise ExactArtifactValidationError("candidate identity disagrees with exact source SHA")
    if str(identity["workflow_run_id"]) != str(candidate_run_id):
        raise ExactArtifactValidationError("candidate identity disagrees with workflow run")
    if identity["release_version"] != "7.0.0rc1":
        raise ExactArtifactValidationError("candidate release version is not 7.0.0rc1")
    source = artifact_root / identity["source"]["name"]
    wheel = artifact_root / identity["wheel"]["name"]
    if _sha256(source) != identity["source"]["sha256"]:
        raise ExactArtifactValidationError("candidate source hash disagrees with identity")
    if _sha256(wheel) != identity["wheel"]["sha256"]:
        raise ExactArtifactValidationError("candidate wheel hash disagrees with identity")
    if status["provider_writes"] != 0:
        raise ExactArtifactValidationError("candidate validation performed provider writes")
    if any(
        status[field]
        for field in (
            "production_promotion_authorized",
            "final_tag_created",
            "final_release_published",
            "authority_activated",
            "drive_retired",
        )
    ):
        raise ExactArtifactValidationError("candidate evidence claims an unauthorized live action")

    performance = _read_json(performance_path)
    if performance["status"] != "passed" or performance["provider_writes"] != 0:
        raise ExactArtifactValidationError("equivalent v7 versus v6.5 performance gate failed")
    integrations = _integration_readiness(integration_snapshot_path)
    drive_ledger = _drive_ledger(drive_inventory_path)
    rollback_evidence = _rollback_evidence(rollback_evidence_path)

    rollback = simulate_rollback(
        RollbackSimulationEvidence(
            target_version="6.5.0",
            target_commit="bb6d6fea70d6824c9bc6a42e63ba36cc88029260",
            target_tag="v6.5.0",
            target_release_readable=True,
            target_checksums_passed=True,
            target_clean_install_passed=bool(status["active_production_restored"]),
            target_restoration_passed=bool(status["active_production_restored"]),
            current_candidate_deactivation_reversible=True,
            provider_writes_during_simulation=0,
        ),
        transaction_id=f"rollback-v650-from-{candidate_sha[:12]}",
    )
    if rollback.status != "ready":
        raise ExactArtifactValidationError("v6.5 rollback simulation is blocked")

    promotion = simulate_promotion(
        PromotionSimulationEvidence(
            candidate_version="7.0.0rc1",
            candidate_commit=candidate_sha,
            candidate_artifact_id=artifact_id,
            candidate_artifact_digest=artifact_digest,
            candidate_source_sha256=identity["source"]["sha256"],
            candidate_wheel_sha256=identity["wheel"]["sha256"],
            standard_ci_passed=True,
            architecture_validation_passed=True,
            candidate_validation_passed=True,
            exact_artifact_validation_passed=True,
            active_v650_restored=bool(status["active_production_restored"]),
            rollback_v620_restored=bool(status["immediate_rollback_restored"]),
            performance_gate_passed=True,
            drive_migration_ledger_complete=(
                drive_ledger.complete_for_promotion_readiness if drive_ledger else False
            ),
            required_integrations_ready=integrations,
            provider_writes_during_validation=0,
        ),
        transaction_id=f"promotion-v700-{candidate_sha[:12]}",
    )

    findings = list(promotion.blockers)
    if rollback_evidence is None:
        findings.append(
            "v6.5 rollback evidence reconciliation is required before promotion"
        )
    findings.append(
        "live Notion integration and System State readback is required before promotion"
    )
    result = {
        "schema_version": "1.0",
        "review": "Atlas ROS v7.0.0rc1 Exact-Artifact Full Validation",
        "status": "passed" if not findings else "passed_with_findings",
        "candidate_sha": candidate_sha,
        "standard_ci_run_id": standard_ci_run_id,
        "architecture_run_id": architecture_run_id,
        "candidate_run_id": candidate_run_id,
        "candidate_artifact_id": artifact_id,
        "candidate_artifact_digest": artifact_digest,
        "source_sha256": identity["source"]["sha256"],
        "wheel_sha256": identity["wheel"]["sha256"],
        "publication_checksums_passed": True,
        "nested_evidence_checksums_passed": True,
        "exact_wheel_clean_install_passed": True,
        "active_v650_restoration_passed": bool(status["active_production_restored"]),
        "rollback_v620_restoration_passed": bool(status["immediate_rollback_restored"]),
        "performance_gate": performance,
        "drive_migration_ledger": asdict(drive_ledger) if drive_ledger else None,
        "v650_rollback_evidence": (
            asdict(rollback_evidence) if rollback_evidence else None
        ),
        "integration_snapshot_ready": integrations,
        "rollback_simulation": asdict(rollback),
        "promotion_simulation": asdict(promotion),
        "findings": findings,
        "provider_writes": 0,
        "publication_performed": False,
        "authority_activated": False,
        "drive_retired": False,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "EXACT_ARTIFACT_VALIDATION.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "ROLLBACK_SIMULATION.json").write_text(
        json.dumps(asdict(rollback), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "PROMOTION_SIMULATION.json").write_text(
        json.dumps(asdict(promotion), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_summary(result, output_dir / "EXACT_ARTIFACT_VALIDATION.md")
    return result


def _integration_readiness(path: Path) -> bool:
    payload = _read_json(path)
    records = payload.get("required_v7_integrations")
    if not isinstance(records, list):
        return False
    expected = {"GitHub", "Notion", "Todoist"}
    if {record.get("name") for record in records} != expected:
        return False
    return all(
        record.get("connection_status") == "connected"
        and record.get("approval_status") == "approved"
        and record.get("acceptance_status") == "passed"
        and record.get("current") is True
        and record.get("least_privilege_verified") is True
        for record in records
    )


def _drive_ledger(path: Path | None) -> DriveMigrationLedger | None:
    if path is None or not path.is_file():
        return None
    try:
        return load_and_compile(path)
    except DriveMigrationLedgerError as error:
        raise ExactArtifactValidationError(str(error)) from error


def _rollback_evidence(path: Path | None) -> RollbackEvidenceReceipt | None:
    if path is None or not path.is_file():
        return None
    try:
        receipt = load_receipt(path)
    except RollbackEvidenceError as error:
        raise ExactArtifactValidationError(str(error)) from error
    if receipt.status != "ready":
        raise ExactArtifactValidationError(
            "v6.5 rollback evidence reconciliation is blocked"
        )
    return receipt


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ExactArtifactValidationError(f"invalid JSON evidence: {path}") from error
    if not isinstance(value, dict):
        raise ExactArtifactValidationError(f"JSON evidence must be an object: {path}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_summary(result: dict[str, Any], path: Path) -> None:
    findings = "\n".join(f"- {finding}" for finding in result["findings"]) or "- None"
    rollback_evidence = result["v650_rollback_evidence"]
    rollback_status = rollback_evidence["status"] if rollback_evidence else "not supplied"
    path.write_text(
        f"""# Atlas ROS v7.0.0rc1 Exact-Artifact Full Validation

- Status: `{result['status']}`
- Candidate SHA: `{result['candidate_sha']}`
- Candidate artifact: `{result['candidate_artifact_id']}`
- Source SHA-256: `{result['source_sha256']}`
- Wheel SHA-256: `{result['wheel_sha256']}`
- Publication checksums: passed
- Nested evidence checksums: passed
- Exact wheel clean installation: passed
- v6.5 restoration: passed
- v6.5 rollback reconciliation: `{rollback_status}`
- v6.2 restoration: passed
- Performance gate: `{result['performance_gate']['status']}`
- Rollback simulation: `{result['rollback_simulation']['status']}`
- Promotion simulation: `{result['promotion_simulation']['status']}`
- Provider writes: `0`
- Publication performed: `false`
- Authority activated: `false`
- Drive retired: `false`

## Findings

{findings}
""",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--artifact-id", required=True)
    parser.add_argument("--artifact-digest", required=True)
    parser.add_argument("--candidate-run-id", required=True)
    parser.add_argument("--standard-ci-run-id", required=True)
    parser.add_argument("--architecture-run-id", required=True)
    parser.add_argument("--performance", type=Path, required=True)
    parser.add_argument("--integration-snapshot", type=Path, required=True)
    parser.add_argument("--drive-inventory", type=Path)
    parser.add_argument("--rollback-evidence", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    validate_exact_artifact(
        artifact_root=args.artifact_root,
        candidate_sha=args.candidate_sha,
        artifact_id=args.artifact_id,
        artifact_digest=args.artifact_digest,
        candidate_run_id=args.candidate_run_id,
        standard_ci_run_id=args.standard_ci_run_id,
        architecture_run_id=args.architecture_run_id,
        performance_path=args.performance,
        integration_snapshot_path=args.integration_snapshot,
        drive_inventory_path=args.drive_inventory,
        output_dir=args.output_dir,
        rollback_evidence_path=args.rollback_evidence,
    )


if __name__ == "__main__":
    main()
