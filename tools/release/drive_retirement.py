"""Fail-closed Drive-retirement planning and simulation controller.

This tool never calls Google Drive. It validates checksum-bound ledger evidence
that a separately authorized adapter must supply, and produces deterministic
transaction receipts.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Literal

from tools.release.drive_migration_ledger import DriveMigrationLedger

Mode = Literal[
    "inventory",
    "verify",
    "prepare-retirement",
    "retire",
    "verify-retirement",
]


class RetirementPreconditionError(ValueError):
    """Raised when a destructive retirement request lacks required evidence."""


@dataclass(frozen=True)
class RetirementEvidence:
    v7_active: bool
    v650_rollback_restored: bool
    v7_post_promotion_readback: bool
    migration_ledger_sha256: str
    migration_complete_for_promotion: bool
    migration_ready_for_retirement: bool
    unresolved_authoritative_items: int
    current_drive_dependencies: int
    drive_integration_retired: bool = False

    @classmethod
    def from_ledger(
        cls,
        ledger: DriveMigrationLedger,
        *,
        v7_active: bool,
        v650_rollback_restored: bool,
        v7_post_promotion_readback: bool,
        drive_integration_retired: bool = False,
    ) -> RetirementEvidence:
        """Derive all migration counts and state from one checksum-bound ledger."""
        return cls(
            v7_active=v7_active,
            v650_rollback_restored=v650_rollback_restored,
            v7_post_promotion_readback=v7_post_promotion_readback,
            migration_ledger_sha256=ledger.ledger_sha256,
            migration_complete_for_promotion=ledger.complete_for_promotion_readiness,
            migration_ready_for_retirement=ledger.ready_for_post_promotion_retirement,
            unresolved_authoritative_items=ledger.unresolved_authoritative_items,
            current_drive_dependencies=ledger.staged_current_dependencies,
            drive_integration_retired=drive_integration_retired,
        )


@dataclass(frozen=True)
class RetirementReceipt:
    mode: Mode
    status: Literal["prepared", "simulated", "verified"]
    transaction_id: str
    evidence_digest: str
    migration_ledger_sha256: str
    destructive_actions_performed: int
    notes: tuple[str, ...]


def run(
    mode: Mode,
    evidence: RetirementEvidence,
    *,
    transaction_id: str,
) -> RetirementReceipt:
    """Validate a retirement phase without performing provider actions."""
    if not transaction_id:
        raise RetirementPreconditionError(
            "an exact retirement transaction ID is required"
        )
    _require_ledger_digest(evidence.migration_ledger_sha256)
    digest = _digest(evidence)
    if mode == "inventory":
        return _receipt(
            mode,
            "simulated",
            transaction_id,
            digest,
            evidence.migration_ledger_sha256,
            "checksum-bound inventory captured",
        )
    if mode == "verify":
        _require_promotion_migration_ready(evidence)
        return _receipt(
            mode,
            "verified",
            transaction_id,
            digest,
            evidence.migration_ledger_sha256,
            "promotion migration evidence verified",
        )
    if mode == "prepare-retirement":
        _require_retirement_ready(evidence)
        return _receipt(
            mode,
            "prepared",
            transaction_id,
            digest,
            evidence.migration_ledger_sha256,
            "retirement is authorized to prepare",
        )
    if mode == "retire":
        _require_retirement_ready(evidence)
        return _receipt(
            mode,
            "prepared",
            transaction_id,
            digest,
            evidence.migration_ledger_sha256,
            "provider execution intentionally requires an authorized adapter",
        )
    if mode == "verify-retirement":
        _require_retirement_ready(evidence)
        if not evidence.drive_integration_retired:
            raise RetirementPreconditionError(
                "Drive integration retirement readback has not passed"
            )
        return _receipt(
            mode,
            "verified",
            transaction_id,
            digest,
            evidence.migration_ledger_sha256,
            "retirement readback verified",
        )
    raise RetirementPreconditionError(f"unsupported retirement mode: {mode}")


def _require_promotion_migration_ready(evidence: RetirementEvidence) -> None:
    if not evidence.migration_complete_for_promotion:
        raise RetirementPreconditionError(
            "Drive migration ledger is not complete for promotion readiness"
        )
    if evidence.unresolved_authoritative_items:
        raise RetirementPreconditionError(
            "Drive migration ledger has unresolved authoritative items"
        )


def _require_retirement_ready(evidence: RetirementEvidence) -> None:
    if not evidence.v7_active:
        raise RetirementPreconditionError("v7 must be Active before Drive retirement")
    if not evidence.v650_rollback_restored:
        raise RetirementPreconditionError(
            "v6.5 rollback restoration must pass before retirement"
        )
    if not evidence.v7_post_promotion_readback:
        raise RetirementPreconditionError(
            "v7 post-promotion readback must pass before retirement"
        )
    _require_promotion_migration_ready(evidence)
    if not evidence.migration_ready_for_retirement:
        raise RetirementPreconditionError(
            "Drive migration ledger is not ready for post-promotion retirement"
        )
    if evidence.current_drive_dependencies:
        raise RetirementPreconditionError(
            "current source or operating records still depend on Drive"
        )


def _receipt(
    mode: Mode,
    status: Literal["prepared", "simulated", "verified"],
    transaction_id: str,
    digest: str,
    migration_ledger_sha256: str,
    note: str,
) -> RetirementReceipt:
    return RetirementReceipt(
        mode=mode,
        status=status,
        transaction_id=transaction_id,
        evidence_digest=digest,
        migration_ledger_sha256=migration_ledger_sha256,
        destructive_actions_performed=0,
        notes=(note,),
    )


def _require_ledger_digest(value: str) -> None:
    if len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise RetirementPreconditionError(
            "migration ledger SHA-256 is missing or invalid"
        )


def _digest(evidence: RetirementEvidence) -> str:
    encoded = json.dumps(
        asdict(evidence), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


@dataclass(frozen=True)
class DriveRetirementAuthorization:
    """Exact attended authorization for a future Drive retirement transaction."""

    authorization_id: str
    transaction_id: str
    dependency_inventory_sha256: str
    historical_inventory_sha256: str
    exclusion_review_sha256: str
    account_scope: str
    credential_scope_sha256: str
    object_budget: int
    byte_budget: int
    exact_target_ids: tuple[str, ...]
    content_deletion_authorized: bool = False
    credential_revocation_authorized: bool = False
    connector_removal_authorized: bool = False


@dataclass(frozen=True)
class DriveRetirementPreflight:
    """Read-only evidence required before a retirement transaction can exist."""

    dependency_inventory_sha256: str
    historical_inventory_sha256: str
    exclusion_review_sha256: str
    zero_current_dependencies: bool
    historical_inventory_complete: bool
    exclusion_review_complete: bool
    rollback_restoration_passed: bool
    post_promotion_readback_passed: bool
    account_scope: str
    credential_scope_sha256: str
    target_ids: tuple[str, ...]
    object_count: int
    byte_count: int


@dataclass(frozen=True)
class DriveRetirementSimulationReceipt:
    """Non-destructive exact-transaction simulation evidence."""

    transaction_id: str
    authorization_id: str
    preflight_digest: str
    authorized_actions: tuple[str, ...]
    exact_target_ids: tuple[str, ...]
    object_count: int
    byte_count: int
    provider_writes: int
    destructive_actions: int
    status: Literal["simulated"] = "simulated"


def simulate_retirement_transaction(
    preflight: DriveRetirementPreflight,
    authorization: DriveRetirementAuthorization,
) -> DriveRetirementSimulationReceipt:
    """Validate an exact future transaction without contacting Google Drive."""
    _validate_retirement_transaction(preflight, authorization)
    actions: list[str] = []
    if authorization.content_deletion_authorized:
        actions.append("content_deletion")
    if authorization.credential_revocation_authorized:
        actions.append("credential_revocation")
    if authorization.connector_removal_authorized:
        actions.append("connector_removal")
    return DriveRetirementSimulationReceipt(
        transaction_id=authorization.transaction_id,
        authorization_id=authorization.authorization_id,
        preflight_digest=_digest_dataclass(preflight),
        authorized_actions=tuple(actions),
        exact_target_ids=authorization.exact_target_ids,
        object_count=preflight.object_count,
        byte_count=preflight.byte_count,
        provider_writes=0,
        destructive_actions=0,
    )


def _validate_retirement_transaction(
    preflight: DriveRetirementPreflight,
    authorization: DriveRetirementAuthorization,
) -> None:
    for value, label in (
        (preflight.dependency_inventory_sha256, "dependency inventory"),
        (preflight.historical_inventory_sha256, "historical inventory"),
        (preflight.exclusion_review_sha256, "exclusion review"),
        (preflight.credential_scope_sha256, "credential scope"),
    ):
        _require_ledger_digest(value)
        if not value:
            raise RetirementPreconditionError(f"{label} digest is required")
    if not preflight.zero_current_dependencies:
        raise RetirementPreconditionError("current Drive dependencies remain")
    if not preflight.historical_inventory_complete:
        raise RetirementPreconditionError("historical Drive inventory is incomplete")
    if not preflight.exclusion_review_complete:
        raise RetirementPreconditionError("Drive exclusion review is incomplete")
    if not preflight.rollback_restoration_passed:
        raise RetirementPreconditionError("rollback restoration has not passed")
    if not preflight.post_promotion_readback_passed:
        raise RetirementPreconditionError("post-promotion readback has not passed")
    if not authorization.authorization_id or not authorization.transaction_id:
        raise RetirementPreconditionError("exact authorization and transaction IDs are required")
    if authorization.dependency_inventory_sha256 != preflight.dependency_inventory_sha256:
        raise RetirementPreconditionError("authorization dependency inventory does not match")
    if authorization.historical_inventory_sha256 != preflight.historical_inventory_sha256:
        raise RetirementPreconditionError("authorization historical inventory does not match")
    if authorization.exclusion_review_sha256 != preflight.exclusion_review_sha256:
        raise RetirementPreconditionError("authorization exclusion review does not match")
    if authorization.account_scope != preflight.account_scope:
        raise RetirementPreconditionError("authorization account scope does not match")
    if authorization.credential_scope_sha256 != preflight.credential_scope_sha256:
        raise RetirementPreconditionError("authorization credential scope does not match")
    if set(authorization.exact_target_ids) != set(preflight.target_ids):
        raise RetirementPreconditionError("authorization target set does not match preflight")
    if preflight.object_count != len(preflight.target_ids):
        raise RetirementPreconditionError("preflight object count does not match target set")
    if preflight.object_count > authorization.object_budget:
        raise RetirementPreconditionError("Drive retirement object budget would be exceeded")
    if preflight.byte_count > authorization.byte_budget:
        raise RetirementPreconditionError("Drive retirement byte budget would be exceeded")
    if not any(
        (
            authorization.content_deletion_authorized,
            authorization.credential_revocation_authorized,
            authorization.connector_removal_authorized,
        )
    ):
        raise RetirementPreconditionError("authorization contains no retirement action")


def _digest_dataclass(value: object) -> str:
    encoded = json.dumps(asdict(value), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return sha256(encoded).hexdigest()
