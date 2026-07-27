"""Provider-free promotion and rollback transaction simulation for Atlas ROS v7."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from atlas_ros.contracts.digests import sha256_digest


class ReleaseSimulationError(ValueError):
    """Raised when a proposed release transaction lacks mandatory evidence."""


@dataclass(frozen=True, slots=True)
class PromotionSimulationEvidence:
    candidate_version: str
    candidate_commit: str
    candidate_artifact_id: str
    candidate_artifact_digest: str
    candidate_source_sha256: str
    candidate_wheel_sha256: str
    standard_ci_passed: bool
    architecture_validation_passed: bool
    candidate_validation_passed: bool
    exact_artifact_validation_passed: bool
    active_v650_restored: bool
    rollback_v620_restored: bool
    performance_gate_passed: bool
    drive_migration_ledger_complete: bool
    required_integrations_ready: bool
    provider_writes_during_validation: int


@dataclass(frozen=True, slots=True)
class RollbackSimulationEvidence:
    target_version: str
    target_commit: str
    target_tag: str
    target_release_readable: bool
    target_checksums_passed: bool
    target_clean_install_passed: bool
    target_restoration_passed: bool
    current_candidate_deactivation_reversible: bool
    provider_writes_during_simulation: int


@dataclass(frozen=True, slots=True)
class ReleaseSimulationReceipt:
    transaction_type: Literal["promotion", "rollback"]
    transaction_id: str
    status: Literal["ready", "blocked"]
    evidence_digest: str
    planned_actions: tuple[str, ...]
    blockers: tuple[str, ...]
    provider_writes: int
    destructive_actions_performed: int


def simulate_promotion(
    evidence: PromotionSimulationEvidence,
    *,
    transaction_id: str,
) -> ReleaseSimulationReceipt:
    """Validate a future exact promotion sequence without publishing or writing providers."""
    _require_transaction_id(transaction_id)
    blockers: list[str] = []
    if evidence.candidate_version != "7.0.0rc1":
        blockers.append("candidate version must be 7.0.0rc1 before final-source freeze")
    if len(evidence.candidate_commit) != 40:
        blockers.append("candidate commit is not an immutable 40-character SHA")
    for field_name, value in (
        ("candidate artifact digest", evidence.candidate_artifact_digest),
        ("candidate source SHA-256", evidence.candidate_source_sha256),
        ("candidate wheel SHA-256", evidence.candidate_wheel_sha256),
    ):
        if len(value) != 64:
            blockers.append(f"{field_name} is invalid")
    gates = {
        "standard CI": evidence.standard_ci_passed,
        "architecture validation": evidence.architecture_validation_passed,
        "candidate validation": evidence.candidate_validation_passed,
        "exact-artifact Full Validation": evidence.exact_artifact_validation_passed,
        "v6.5 restoration": evidence.active_v650_restored,
        "v6.2 restoration": evidence.rollback_v620_restored,
        "performance": evidence.performance_gate_passed,
        "Drive migration ledger": evidence.drive_migration_ledger_complete,
        "required integrations": evidence.required_integrations_ready,
    }
    blockers.extend(f"{name} has not passed" for name, passed in gates.items() if not passed)
    if evidence.provider_writes_during_validation:
        blockers.append("candidate validation performed provider writes")
    planned_actions = (
        "freeze exact final 7.0.0 source commit",
        "validate non-publishing final controller",
        "obtain Ryan exact-package promotion authorization",
        "publish immutable v7.0.0 tag and GitHub Release",
        "independently read back every published asset and checksum",
        "activate GitHub authority and version-neutral Notion System State",
        "retain v6.5.0 as immediate immutable rollback",
    )
    return _receipt("promotion", transaction_id, evidence, planned_actions, tuple(blockers))


def simulate_rollback(
    evidence: RollbackSimulationEvidence,
    *,
    transaction_id: str,
) -> ReleaseSimulationReceipt:
    """Validate restoration to immutable v6.5.0 without changing live authority."""
    _require_transaction_id(transaction_id)
    blockers: list[str] = []
    if evidence.target_version != "6.5.0" or evidence.target_tag != "v6.5.0":
        blockers.append("rollback target must be immutable v6.5.0")
    if len(evidence.target_commit) != 40:
        blockers.append("rollback target commit is invalid")
    gates = {
        "rollback release readability": evidence.target_release_readable,
        "rollback checksums": evidence.target_checksums_passed,
        "rollback clean installation": evidence.target_clean_install_passed,
        "rollback restoration": evidence.target_restoration_passed,
        "candidate deactivation reversibility": (
            evidence.current_candidate_deactivation_reversible
        ),
    }
    blockers.extend(f"{name} has not passed" for name, passed in gates.items() if not passed)
    if evidence.provider_writes_during_simulation:
        blockers.append("rollback simulation performed provider writes")
    planned_actions = (
        "verify immutable v6.5.0 release and tag target",
        "restore v6.5.0 wheel and source from GitHub assets",
        "verify v6.5.0 checksums and clean installation",
        "switch GitHub authority and Notion System State to v6.5.0",
        "retain the failed v7 release as immutable historical evidence",
        "verify required integrations and published workspace readback",
    )
    return _receipt("rollback", transaction_id, evidence, planned_actions, tuple(blockers))


def _receipt(
    transaction_type: Literal["promotion", "rollback"],
    transaction_id: str,
    evidence: PromotionSimulationEvidence | RollbackSimulationEvidence,
    planned_actions: tuple[str, ...],
    blockers: tuple[str, ...],
) -> ReleaseSimulationReceipt:
    return ReleaseSimulationReceipt(
        transaction_type=transaction_type,
        transaction_id=transaction_id,
        status="blocked" if blockers else "ready",
        evidence_digest=sha256_digest(asdict(evidence)),
        planned_actions=planned_actions,
        blockers=blockers,
        provider_writes=0,
        destructive_actions_performed=0,
    )


def _require_transaction_id(transaction_id: str) -> None:
    if not transaction_id.strip():
        raise ReleaseSimulationError("an exact release transaction ID is required")
