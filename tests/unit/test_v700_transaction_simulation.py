from __future__ import annotations

from dataclasses import replace

from tools.release.transaction_simulation import (
    PromotionSimulationEvidence,
    RollbackSimulationEvidence,
    simulate_promotion,
    simulate_rollback,
)


def promotion_evidence(**overrides: object) -> PromotionSimulationEvidence:
    values: dict[str, object] = {
        "candidate_version": "7.0.0rc1",
        "candidate_commit": "a" * 40,
        "candidate_artifact_id": "artifact-1",
        "candidate_artifact_digest": "b" * 64,
        "candidate_source_sha256": "c" * 64,
        "candidate_wheel_sha256": "d" * 64,
        "standard_ci_passed": True,
        "architecture_validation_passed": True,
        "candidate_validation_passed": True,
        "exact_artifact_validation_passed": True,
        "active_v650_restored": True,
        "rollback_v620_restored": True,
        "performance_gate_passed": True,
        "drive_migration_ledger_complete": True,
        "required_integrations_ready": True,
        "provider_writes_during_validation": 0,
    }
    values.update(overrides)
    return PromotionSimulationEvidence(**values)  # type: ignore[arg-type]


def rollback_evidence(**overrides: object) -> RollbackSimulationEvidence:
    values: dict[str, object] = {
        "target_version": "6.5.0",
        "target_commit": "e" * 40,
        "target_tag": "v6.5.0",
        "target_release_readable": True,
        "target_checksums_passed": True,
        "target_clean_install_passed": True,
        "target_restoration_passed": True,
        "current_candidate_deactivation_reversible": True,
        "provider_writes_during_simulation": 0,
    }
    values.update(overrides)
    return RollbackSimulationEvidence(**values)  # type: ignore[arg-type]


def test_promotion_simulation_is_ready_only_when_every_gate_passes() -> None:
    receipt = simulate_promotion(
        promotion_evidence(),
        transaction_id="promotion-simulation-1",
    )

    assert receipt.status == "ready"
    assert receipt.blockers == ()
    assert receipt.provider_writes == 0
    assert receipt.destructive_actions_performed == 0


def test_promotion_simulation_records_missing_exact_artifact_and_ledger() -> None:
    receipt = simulate_promotion(
        promotion_evidence(
            exact_artifact_validation_passed=False,
            drive_migration_ledger_complete=False,
        ),
        transaction_id="promotion-simulation-1",
    )

    assert receipt.status == "blocked"
    assert "exact-artifact Full Validation has not passed" in receipt.blockers
    assert "Drive migration ledger has not passed" in receipt.blockers


def test_promotion_simulation_blocks_any_validation_provider_write() -> None:
    receipt = simulate_promotion(
        replace(promotion_evidence(), provider_writes_during_validation=1),
        transaction_id="promotion-simulation-1",
    )

    assert receipt.status == "blocked"
    assert "candidate validation performed provider writes" in receipt.blockers


def test_rollback_simulation_is_bound_to_immutable_v650() -> None:
    ready = simulate_rollback(
        rollback_evidence(),
        transaction_id="rollback-simulation-1",
    )
    wrong_target = simulate_rollback(
        rollback_evidence(target_version="6.2.0", target_tag="v6.2.0"),
        transaction_id="rollback-simulation-2",
    )

    assert ready.status == "ready"
    assert ready.provider_writes == 0
    assert wrong_target.status == "blocked"
    assert "rollback target must be immutable v6.5.0" in wrong_target.blockers
