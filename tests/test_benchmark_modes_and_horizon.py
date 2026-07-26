import pytest

from atlas_ros.contracts import BenchmarkExecutionPolicyV1, BenchmarkMode
from atlas_ros.planning import HorizonPromotionEngine


def test_provider_free_and_shadow_modes_never_allow_writes() -> None:
    for mode in (BenchmarkMode.PROVIDER_FREE, BenchmarkMode.SHADOW_ORCHESTRATION):
        policy = BenchmarkExecutionPolicyV1.for_mode(mode)
        assert not policy.provider_writes_allowed
        assert policy.object_budget == 0
        assert not policy.explicit_authorization_required


def test_attended_canary_requires_object_budget_and_readback() -> None:
    with pytest.raises(ValueError, match="object budget"):
        BenchmarkExecutionPolicyV1.for_mode(BenchmarkMode.ATTENDED_PROVIDER_CANARY)
    policy = BenchmarkExecutionPolicyV1.for_mode(
        BenchmarkMode.ATTENDED_PROVIDER_CANARY, object_budget=4
    )
    assert policy.provider_writes_allowed
    assert policy.explicit_authorization_required
    assert policy.object_budget == 4
    assert policy.provider_readback_required
    assert policy.reconciliation_required


def test_horizon_sequence_is_provider_free_and_attended() -> None:
    engine = HorizonPromotionEngine()
    cases = [
        ({}, "scope_definition"),
        ({"scope_approved": True}, "ownership_and_targets"),
        (
            {"scope_approved": True, "owner_targets_confirmed": True},
            "controls_and_rollback",
        ),
        (
            {
                "scope_approved": True,
                "owner_targets_confirmed": True,
                "controls_rollback_approved": True,
            },
            "delegated_execution",
        ),
        (
            {
                "scope_approved": True,
                "owner_targets_confirmed": True,
                "controls_rollback_approved": True,
                "execution_evidence_complete": True,
            },
            "conditional_review",
        ),
        (
            {
                "scope_approved": True,
                "owner_targets_confirmed": True,
                "controls_rollback_approved": True,
                "execution_evidence_complete": True,
                "go_decision": True,
            },
            "future_rollout",
        ),
    ]
    defaults = {
        "scope_approved": False,
        "owner_targets_confirmed": False,
        "controls_rollback_approved": False,
        "execution_evidence_complete": False,
        "go_decision": False,
    }
    for overrides, expected in cases:
        proposal = engine.evaluate(**{**defaults, **overrides})
        assert proposal.proposed_stage == expected
        assert proposal.provider_writes == 0
        assert proposal.attended_authorization_required
