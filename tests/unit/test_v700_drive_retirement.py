from __future__ import annotations

import pytest

from tools.release.drive_retirement import (
    RetirementEvidence,
    RetirementPreconditionError,
    run,
)


def ready_evidence(*, retired: bool = False) -> RetirementEvidence:
    return RetirementEvidence(
        v7_active=True,
        v650_rollback_restored=True,
        v7_post_promotion_readback=True,
        unresolved_authoritative_items=0,
        current_drive_dependencies=0,
        drive_integration_retired=retired,
    )


def test_retirement_prepare_is_fail_closed_until_all_evidence_passes() -> None:
    with pytest.raises(RetirementPreconditionError, match="v7 must be Active"):
        run(
            "prepare-retirement",
            RetirementEvidence(False, True, True, 0, 0),
            transaction_id="retire-7.0.0",
        )


def test_retire_mode_is_simulation_only_and_never_performs_deletion() -> None:
    receipt = run("retire", ready_evidence(), transaction_id="retire-7.0.0")
    assert receipt.status == "prepared"
    assert receipt.destructive_actions_performed == 0


def test_retirement_readback_requires_integration_retired() -> None:
    with pytest.raises(RetirementPreconditionError, match="readback"):
        run("verify-retirement", ready_evidence(), transaction_id="retire-7.0.0")
    receipt = run(
        "verify-retirement",
        ready_evidence(retired=True),
        transaction_id="retire-7.0.0",
    )
    assert receipt.status == "verified"
