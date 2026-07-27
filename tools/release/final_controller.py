"""Fail-closed final release controls for Atlas ROS v7.

The functions in this module compile and validate release transactions. They do
not publish a release, create or move tags, activate authority, write providers,
or retire Google Drive.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from atlas_ros.contracts.digests import sha256_digest

ControlStatus = Literal["ready", "blocked"]


class FinalReleaseControlError(ValueError):
    """Raised when release-control evidence is malformed or contradictory."""


@dataclass(frozen=True, slots=True)
class FinalPackageEvidence:
    candidate_version: str
    candidate_commit: str
    final_source_commit: str
    candidate_pr_merged: bool
    candidate_artifact_id: str
    candidate_artifact_digest: str
    source_sha256: str
    wheel_sha256: str
    standard_ci_passed: bool
    architecture_validation_passed: bool
    candidate_validation_passed: bool
    exact_artifact_validation_passed: bool
    drive_migration_ledger_complete: bool
    drive_migration_ledger_sha256: str | None
    live_authority_readback_complete: bool
    required_integrations_ready: bool
    v650_rollback_restored: bool
    v650_rollback_evidence_reconciled: bool
    v650_rollback_evidence_sha256: str | None
    review_record_url: str
    decision_record_url: str
    exact_package_authorization_id: str | None
    provider_writes_during_validation: int


@dataclass(frozen=True, slots=True)
class FinalControllerReceipt:
    transaction_id: str
    status: ControlStatus
    evidence_digest: str
    final_version: Literal["7.0.0"]
    final_source_commit: str
    planned_actions: tuple[str, ...]
    blockers: tuple[str, ...]
    provider_writes: int
    publication_performed: bool
    tag_created: bool
    authority_activated: bool
    drive_retired: bool


@dataclass(frozen=True, slots=True)
class PostPublicationEvidence:
    final_version: str
    final_tag: str
    final_source_commit: str
    published_release_readable: bool
    immutable_tag_points_to_final_source: bool
    publication_checksums_passed: bool
    source_sha256_matches_identity: bool
    wheel_sha256_matches_identity: bool
    clean_install_passed: bool
    v650_rollback_restored: bool
    v620_historical_rollback_restored: bool
    live_authority_readback_complete: bool
    provider_writes_during_verification: int


@dataclass(frozen=True, slots=True)
class PostPublicationReceipt:
    transaction_id: str
    status: ControlStatus
    evidence_digest: str
    blockers: tuple[str, ...]
    verified_actions: tuple[str, ...]
    provider_writes: int
    publication_performed: bool
    authority_activated: bool
    drive_retired: bool


@dataclass(frozen=True, slots=True)
class AuthorityActivationEvidence:
    final_version: str
    final_tag: str
    final_source_commit: str
    post_publication_verification_passed: bool
    release_index_digest: str
    authority_record_digest: str
    active_manifest_digest: str
    notion_system_state_readback_passed: bool
    integration_inventory_readback_passed: bool
    v650_rollback_restored: bool
    exact_package_authorization_id: str | None
    provider_writes_during_activation_validation: int


@dataclass(frozen=True, slots=True)
class AuthorityActivationReceipt:
    transaction_id: str
    status: ControlStatus
    evidence_digest: str
    blockers: tuple[str, ...]
    planned_actions: tuple[str, ...]
    provider_writes: int
    activation_performed: bool
    drive_retired: bool


def compile_final_controller(
    evidence: FinalPackageEvidence,
    *,
    transaction_id: str,
) -> FinalControllerReceipt:
    """Compile a non-publishing final controller bound to one exact package."""
    _require_transaction_id(transaction_id)
    blockers: list[str] = []
    if evidence.candidate_version != "7.0.0rc1":
        blockers.append("candidate version must be 7.0.0rc1")
    _append_invalid_sha(blockers, "candidate commit", evidence.candidate_commit, 40)
    _append_invalid_sha(blockers, "final source commit", evidence.final_source_commit, 40)
    _append_invalid_sha(
        blockers,
        "candidate artifact digest",
        evidence.candidate_artifact_digest,
        64,
    )
    _append_invalid_sha(blockers, "source SHA-256", evidence.source_sha256, 64)
    _append_invalid_sha(blockers, "wheel SHA-256", evidence.wheel_sha256, 64)
    if not evidence.candidate_artifact_id.strip():
        blockers.append("candidate artifact ID is required")
    gates = {
        "candidate PR merge": evidence.candidate_pr_merged,
        "standard CI": evidence.standard_ci_passed,
        "architecture validation": evidence.architecture_validation_passed,
        "candidate validation": evidence.candidate_validation_passed,
        "exact-artifact Full Validation": evidence.exact_artifact_validation_passed,
        "Drive migration ledger": evidence.drive_migration_ledger_complete,
        "live authority readback": evidence.live_authority_readback_complete,
        "required integrations": evidence.required_integrations_ready,
        "v6.5 rollback restoration": evidence.v650_rollback_restored,
        "v6.5 rollback evidence reconciliation": (
            evidence.v650_rollback_evidence_reconciled
        ),
    }
    blockers.extend(f"{name} has not passed" for name, passed in gates.items() if not passed)
    if evidence.drive_migration_ledger_complete:
        if evidence.drive_migration_ledger_sha256 is None:
            blockers.append("Drive migration ledger digest is required")
        else:
            _append_invalid_sha(
                blockers,
                "Drive migration ledger digest",
                evidence.drive_migration_ledger_sha256,
                64,
            )
    if evidence.v650_rollback_evidence_reconciled:
        if evidence.v650_rollback_evidence_sha256 is None:
            blockers.append("v6.5 rollback evidence digest is required")
        else:
            _append_invalid_sha(
                blockers,
                "v6.5 rollback evidence digest",
                evidence.v650_rollback_evidence_sha256,
                64,
            )
    elif evidence.v650_rollback_evidence_sha256 is not None:
        blockers.append(
            "v6.5 rollback evidence digest cannot replace reconciliation"
        )
    if not _valid_url(evidence.review_record_url):
        blockers.append("governed review record URL is required")
    if not _valid_url(evidence.decision_record_url):
        blockers.append("governed decision record URL is required")
    if not evidence.exact_package_authorization_id:
        blockers.append("exact-package Ryan authorization is required")
    if evidence.provider_writes_during_validation:
        blockers.append("candidate or final-controller validation performed provider writes")
    planned_actions = (
        "freeze the exact final 7.0.0 source commit",
        "bind the final package to source, wheel, artifact, ledger, review, and decision digests",
        "bind the immutable v6.5 rollback package to reconciled exception evidence",
        "validate the single final publication controller without publishing",
        "publish immutable v7.0.0 tag and GitHub Release only after exact authorization",
        "independently read back all published assets and checksums",
        "retain immutable v6.5.0 as immediate rollback",
    )
    return FinalControllerReceipt(
        transaction_id=transaction_id,
        status="blocked" if blockers else "ready",
        evidence_digest=sha256_digest(asdict(evidence)),
        final_version="7.0.0",
        final_source_commit=evidence.final_source_commit,
        planned_actions=planned_actions,
        blockers=tuple(blockers),
        provider_writes=0,
        publication_performed=False,
        tag_created=False,
        authority_activated=False,
        drive_retired=False,
    )


def verify_post_publication(
    evidence: PostPublicationEvidence,
    *,
    transaction_id: str,
) -> PostPublicationReceipt:
    """Validate an independently downloaded publication without changing authority."""
    _require_transaction_id(transaction_id)
    blockers: list[str] = []
    if evidence.final_version != "7.0.0" or evidence.final_tag != "v7.0.0":
        blockers.append("published identity must be Atlas ROS v7.0.0")
    _append_invalid_sha(blockers, "final source commit", evidence.final_source_commit, 40)
    gates = {
        "published release readability": evidence.published_release_readable,
        "immutable tag target": evidence.immutable_tag_points_to_final_source,
        "publication checksums": evidence.publication_checksums_passed,
        "source identity": evidence.source_sha256_matches_identity,
        "wheel identity": evidence.wheel_sha256_matches_identity,
        "clean installation": evidence.clean_install_passed,
        "v6.5 rollback restoration": evidence.v650_rollback_restored,
        "v6.2 historical rollback restoration": evidence.v620_historical_rollback_restored,
        "live authority readback": evidence.live_authority_readback_complete,
    }
    blockers.extend(f"{name} has not passed" for name, passed in gates.items() if not passed)
    if evidence.provider_writes_during_verification:
        blockers.append("post-publication verification performed provider writes")
    verified_actions = (
        "download every immutable v7.0.0 release asset",
        "verify publication and nested evidence checksums",
        "verify final source and wheel hashes against final identity",
        "install the exact published wheel in a clean environment",
        "restore v6.5.0 and v6.2.0 from immutable GitHub assets",
        "read back the final tag target and release metadata",
    )
    return PostPublicationReceipt(
        transaction_id=transaction_id,
        status="blocked" if blockers else "ready",
        evidence_digest=sha256_digest(asdict(evidence)),
        blockers=tuple(blockers),
        verified_actions=verified_actions,
        provider_writes=0,
        publication_performed=False,
        authority_activated=False,
        drive_retired=False,
    )


def compile_authority_activation(
    evidence: AuthorityActivationEvidence,
    *,
    transaction_id: str,
) -> AuthorityActivationReceipt:
    """Compile but never execute the exact v7 authority-activation transaction."""
    _require_transaction_id(transaction_id)
    blockers: list[str] = []
    if evidence.final_version != "7.0.0" or evidence.final_tag != "v7.0.0":
        blockers.append("activation identity must be Atlas ROS v7.0.0")
    _append_invalid_sha(blockers, "final source commit", evidence.final_source_commit, 40)
    for name, value in (
        ("Release Index digest", evidence.release_index_digest),
        ("authority record digest", evidence.authority_record_digest),
        ("active manifest digest", evidence.active_manifest_digest),
    ):
        _append_invalid_sha(blockers, name, value, 64)
    gates = {
        "post-publication verification": evidence.post_publication_verification_passed,
        "Notion System State readback": evidence.notion_system_state_readback_passed,
        "Integration Inventory readback": evidence.integration_inventory_readback_passed,
        "v6.5 rollback restoration": evidence.v650_rollback_restored,
    }
    blockers.extend(f"{name} has not passed" for name, passed in gates.items() if not passed)
    if not evidence.exact_package_authorization_id:
        blockers.append("exact-package Ryan authorization is required")
    if evidence.provider_writes_during_activation_validation:
        blockers.append("authority-activation validation performed provider writes")
    planned_actions = (
        "atomically activate the canonical GitHub authority record",
        "replace the generated GitHub Release Index with the exact v7 identity",
        "update the version-neutral Notion System State",
        "read back the manifest-resolved Integration Inventory",
        "confirm v6.5.0 as the immediate immutable rollback",
        "record activation review evidence without retiring Google Drive",
    )
    return AuthorityActivationReceipt(
        transaction_id=transaction_id,
        status="blocked" if blockers else "ready",
        evidence_digest=sha256_digest(asdict(evidence)),
        blockers=tuple(blockers),
        planned_actions=planned_actions,
        provider_writes=0,
        activation_performed=False,
        drive_retired=False,
    )


def _require_transaction_id(transaction_id: str) -> None:
    if not transaction_id.strip():
        raise FinalReleaseControlError("an exact release transaction ID is required")


def _append_invalid_sha(
    blockers: list[str],
    field: str,
    value: str,
    length: int,
) -> None:
    if len(value) != length or any(character not in "0123456789abcdef" for character in value):
        blockers.append(f"{field} is not a lowercase {length}-character hexadecimal digest")


def _valid_url(value: str) -> bool:
    return value.startswith("https://") and len(value) > len("https://")


__all__ = [
    "AuthorityActivationEvidence",
    "AuthorityActivationReceipt",
    "FinalControllerReceipt",
    "FinalPackageEvidence",
    "FinalReleaseControlError",
    "PostPublicationEvidence",
    "PostPublicationReceipt",
    "compile_authority_activation",
    "compile_final_controller",
    "verify_post_publication",
]
