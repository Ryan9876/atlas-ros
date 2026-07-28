from __future__ import annotations

from dataclasses import replace

import pytest

from tools.release.drive_migration_ledger import compile_ledger
from tools.release.drive_retirement import (
    RetirementEvidence,
    RetirementPreconditionError,
    run,
)


def record(
    drive_id: str,
    *,
    classification: str,
    status: str,
    disposition: str,
    target: str,
    digest: str,
) -> dict[str, object]:
    return {
        "drive_id": drive_id,
        "title": drive_id,
        "mime_type": "text/markdown",
        "size_bytes": 100,
        "modified_time": "2026-07-27T00:00:00Z",
        "owned_by_me": True,
        "shared": False,
        "drive_content_sha256": digest,
        "classification": classification,
        "github_target": target,
        "github_content_sha256": digest,
        "content_equivalent": True,
        "migration_status": status,
        "disposition": disposition,
    }


def retirement_ledger():
    return compile_ledger(
        [
            record(
                "historical-v650",
                classification="historical_authority",
                status="verified",
                disposition="retain_immutable_github",
                target="releases/v6.5.0/source.tar.gz",
                digest="a" * 64,
            ),
            record(
                "duplicate-index",
                classification="duplicate",
                status="verified",
                disposition="eligible_for_retirement",
                target="migration/duplicate-release-index.md",
                digest="b" * 64,
            ),
        ]
    )


def staged_promotion_ledger():
    return compile_ledger(
        [
            record(
                "active-drive-bootstrap",
                classification="current_until_v7_activation",
                status="staged",
                disposition="retire_after_v7_activation",
                target="governance/RELEASE_INDEX.md",
                digest="c" * 64,
            ),
            record(
                "historical-v650",
                classification="historical_authority",
                status="verified",
                disposition="retain_immutable_github",
                target="releases/v6.5.0/source.tar.gz",
                digest="a" * 64,
            ),
        ]
    )


def ready_evidence(*, retired: bool = False) -> RetirementEvidence:
    return RetirementEvidence.from_ledger(
        retirement_ledger(),
        v7_active=True,
        v650_rollback_restored=True,
        v7_post_promotion_readback=True,
        drive_integration_retired=retired,
    )


def test_promotion_migration_verification_allows_staged_current_bootstrap() -> None:
    evidence = RetirementEvidence.from_ledger(
        staged_promotion_ledger(),
        v7_active=False,
        v650_rollback_restored=True,
        v7_post_promotion_readback=False,
    )

    receipt = run("verify", evidence, transaction_id="verify-v7-migration")

    assert receipt.status == "verified"
    assert receipt.migration_ledger_sha256 == staged_promotion_ledger().ledger_sha256


def test_retirement_prepare_is_fail_closed_until_v7_is_active() -> None:
    evidence = replace(ready_evidence(), v7_active=False)

    with pytest.raises(RetirementPreconditionError, match="v7 must be Active"):
        run("prepare-retirement", evidence, transaction_id="retire-7.0.0")


def test_staged_bootstrap_is_not_postpromotion_retirement_evidence() -> None:
    evidence = RetirementEvidence.from_ledger(
        staged_promotion_ledger(),
        v7_active=True,
        v650_rollback_restored=True,
        v7_post_promotion_readback=True,
    )

    with pytest.raises(RetirementPreconditionError, match="not ready"):
        run("prepare-retirement", evidence, transaction_id="retire-7.0.0")


def test_retire_mode_is_simulation_only_and_never_performs_deletion() -> None:
    receipt = run("retire", ready_evidence(), transaction_id="retire-7.0.0")

    assert receipt.status == "prepared"
    assert receipt.destructive_actions_performed == 0
    assert receipt.migration_ledger_sha256 == retirement_ledger().ledger_sha256


def test_retirement_readback_requires_integration_retired() -> None:
    with pytest.raises(RetirementPreconditionError, match="readback"):
        run("verify-retirement", ready_evidence(), transaction_id="retire-7.0.0")
    receipt = run(
        "verify-retirement",
        ready_evidence(retired=True),
        transaction_id="retire-7.0.0",
    )
    assert receipt.status == "verified"


def test_controller_rejects_invalid_ledger_digest() -> None:
    evidence = replace(ready_evidence(), migration_ledger_sha256="invalid")

    with pytest.raises(RetirementPreconditionError, match="SHA-256"):
        run("verify", evidence, transaction_id="verify-v7-migration")
