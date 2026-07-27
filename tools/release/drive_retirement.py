"""Fail-closed Drive-retirement planning and simulation controller.

This tool never calls Google Drive.  It validates the evidence that a separately
authorized adapter must supply, and produces deterministic transaction receipts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Literal

Mode = Literal["inventory", "verify", "prepare-retirement", "retire", "verify-retirement"]


class RetirementPreconditionError(ValueError):
    """Raised when a destructive retirement request lacks required evidence."""


@dataclass(frozen=True)
class RetirementEvidence:
    v7_active: bool
    v650_rollback_restored: bool
    v7_post_promotion_readback: bool
    unresolved_authoritative_items: int
    current_drive_dependencies: int
    drive_integration_retired: bool = False


@dataclass(frozen=True)
class RetirementReceipt:
    mode: Mode
    status: Literal["prepared", "simulated", "verified"]
    transaction_id: str
    evidence_digest: str
    destructive_actions_performed: int
    notes: tuple[str, ...]


def run(mode: Mode, evidence: RetirementEvidence, *, transaction_id: str) -> RetirementReceipt:
    """Validate a retirement phase without performing provider actions.

    The real provider adapter may execute only after this controller returns a
    prepared receipt for retire, and must bind its readback to the same evidence
    digest and transaction identifier.
    """
    if not transaction_id:
        raise RetirementPreconditionError("an exact retirement transaction ID is required")
    digest = _digest(evidence)
    if mode == "inventory":
        return _receipt(mode, "simulated", transaction_id, digest, "inventory captured")
    if mode == "verify":
        _require_migration_complete(evidence)
        return _receipt(mode, "verified", transaction_id, digest, "migration evidence verified")
    if mode == "prepare-retirement":
        _require_retirement_ready(evidence)
        return _receipt(mode, "prepared", transaction_id, digest, "retirement is authorized to prepare")
    if mode == "retire":
        _require_retirement_ready(evidence)
        return _receipt(
            mode,
            "prepared",
            transaction_id,
            digest,
            "provider execution intentionally requires an authorized adapter",
        )
    if mode == "verify-retirement":
        _require_migration_complete(evidence)
        if not evidence.drive_integration_retired:
            raise RetirementPreconditionError("Drive integration retirement readback has not passed")
        return _receipt(mode, "verified", transaction_id, digest, "retirement readback verified")
    raise RetirementPreconditionError(f"unsupported retirement mode: {mode}")


def _require_migration_complete(evidence: RetirementEvidence) -> None:
    if evidence.unresolved_authoritative_items:
        raise RetirementPreconditionError("Drive migration ledger has unresolved authoritative items")
    if evidence.current_drive_dependencies:
        raise RetirementPreconditionError("current source or operating records still depend on Drive")


def _require_retirement_ready(evidence: RetirementEvidence) -> None:
    if not evidence.v7_active:
        raise RetirementPreconditionError("v7 must be Active before Drive retirement")
    if not evidence.v650_rollback_restored:
        raise RetirementPreconditionError("v6.5 rollback restoration must pass before retirement")
    if not evidence.v7_post_promotion_readback:
        raise RetirementPreconditionError("v7 post-promotion readback must pass before retirement")
    _require_migration_complete(evidence)


def _receipt(
    mode: Mode,
    status: Literal["prepared", "simulated", "verified"],
    transaction_id: str,
    digest: str,
    note: str,
) -> RetirementReceipt:
    return RetirementReceipt(
        mode=mode,
        status=status,
        transaction_id=transaction_id,
        evidence_digest=digest,
        destructive_actions_performed=0,
        notes=(note,),
    )


def _digest(evidence: RetirementEvidence) -> str:
    encoded = json.dumps(asdict(evidence), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()
