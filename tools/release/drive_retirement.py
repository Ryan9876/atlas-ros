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
