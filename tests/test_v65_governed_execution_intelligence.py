from __future__ import annotations

import pytest

from atlas_ros.engines.governed_execution_v65 import (
    AdvisoryError,
    AuthorityTier,
    ExecutionEventV65,
    ExecutionPresenterV65,
    ExecutionRecordV65,
    ExecutionStateV65,
    FrameworkRuleV65,
    GovernedFrameworkComposerV65,
    MinimumEffectivePathPlannerV65,
    PathStepV65,
    ScenarioIntelligenceV65,
    ScenarioV65,
)


def test_framework_precedence_is_deterministic_and_conflicts_fail_closed() -> None:
    composer = GovernedFrameworkComposerV65()
    result = composer.compose((
        FrameworkRuleV65("retention", "retain seven years", AuthorityTier.PREFERENCE, "1", "pref"),
        FrameworkRuleV65(
            "retention",
            "retain seven years",
            AuthorityTier.ORGANIZATION_POLICY,
            "4",
            "policy",
            True,
        ),
    ))
    assert result.rules[0].tier is AuthorityTier.ORGANIZATION_POLICY
    assert result.provenance == ("retention@4:policy",)
    with pytest.raises(AdvisoryError, match="conflicting_rule"):
        composer.compose((
            FrameworkRuleV65("retention", "one year", AuthorityTier.PREFERENCE, "1", "pref"),
            FrameworkRuleV65(
                "retention",
                "seven years",
                AuthorityTier.ORGANIZATION_POLICY,
                "4",
                "policy",
                True,
            ),
        ))


def test_framework_rejects_missing_and_cyclic_dependencies() -> None:
    composer = GovernedFrameworkComposerV65()
    with pytest.raises(AdvisoryError, match="missing_framework_dependency"):
        composer.compose((
            FrameworkRuleV65(
                "retention",
                "retain",
                AuthorityTier.ORGANIZATION_POLICY,
                "1",
                "policy",
                requires=("unknown",),
            ),
        ))
    with pytest.raises(AdvisoryError, match="cyclic_framework_dependencies"):
        composer.compose((
            FrameworkRuleV65(
                "one", "one", AuthorityTier.ORGANIZATION_POLICY, "1", "policy", requires=("two",)
            ),
            FrameworkRuleV65(
                "two", "two", AuthorityTier.ORGANIZATION_POLICY, "1", "policy", requires=("one",)
            ),
        ))


def test_minimum_path_keeps_mandatory_controls_and_orders_dependencies() -> None:
    plan = MinimumEffectivePathPlannerV65().plan((
        PathStepV65("scope", "Scope", mandatory=True),
        PathStepV65(
            "approve",
            "Approve",
            ("scope",),
            mandatory=True,
            gate="human",
            evidence_required=("approval-receipt",),
        ),
        PathStepV65("pilot", "Pilot", ("approve",)),
    ), ("pilot",))
    assert tuple(step.step_id for step in plan.steps) == ("scope", "approve", "pilot")
    assert "unknown:approve:risk" in plan.blockers
    assert plan.required_evidence == ("approval-receipt",)


def test_minimum_path_rejects_cycles_missing_prerequisites_and_unrecoverable_side_effects() -> None:
    planner = MinimumEffectivePathPlannerV65()
    with pytest.raises(AdvisoryError, match="cyclic"):
        planner.plan((
            PathStepV65("one", "One", ("two",)),
            PathStepV65("two", "Two", ("one",)),
        ), ("one",))
    with pytest.raises(AdvisoryError, match="missing"):
        planner.plan((PathStepV65("one", "One", ("missing",)),), ("one",))
    with pytest.raises(AdvisoryError, match="side_effect_requires_rollback"):
        PathStepV65("change", "Change", side_effect=True)


def test_execution_intelligence_requires_evidence_readback_and_is_replayable() -> None:
    record = ExecutionRecordV65("record-1")
    ready_event = ExecutionEventV65(
        "one", ExecutionStateV65.PENDING, ExecutionStateV65.READY, idempotency_key="ready"
    )
    ready = record.transition(ready_event)
    assert ready.transition(ready_event) is ready
    active = ready.transition(
        ExecutionEventV65("two", ExecutionStateV65.READY, ExecutionStateV65.IN_PROGRESS)
    )
    with pytest.raises(AdvisoryError, match="completion_requires_evidence"):
        active.transition(
            ExecutionEventV65("three", ExecutionStateV65.IN_PROGRESS, ExecutionStateV65.SUCCEEDED)
        )
    with pytest.raises(AdvisoryError, match="completion_requires_readback"):
        active.transition(
            ExecutionEventV65(
                "four", ExecutionStateV65.IN_PROGRESS, ExecutionStateV65.SUCCEEDED, ("receipt-1",)
            )
        )
    complete_event = ExecutionEventV65(
        "five",
        ExecutionStateV65.IN_PROGRESS,
        ExecutionStateV65.SUCCEEDED,
        ("receipt-1",),
        readback_refs=("readback-1",),
    )
    complete = active.transition(complete_event)
    assert complete.state is ExecutionStateV65.SUCCEEDED
    assert complete.receipts == ("readback-1", "receipt-1")
    assert ExecutionRecordV65.replay("record-1", complete.events).audit_digest() == complete.audit_digest()


def test_execution_intelligence_rejects_authority_and_idempotency_ambiguity() -> None:
    with pytest.raises(AdvisoryError, match="provider_free"):
        ExecutionRecordV65("unsafe", authority_execute=True)
    ready = ExecutionRecordV65("record").transition(
        ExecutionEventV65("one", ExecutionStateV65.PENDING, ExecutionStateV65.READY, idempotency_key="a")
    )
    with pytest.raises(AdvisoryError, match="idempotency_key_reused"):
        ready.transition(
            ExecutionEventV65("two", ExecutionStateV65.READY, ExecutionStateV65.IN_PROGRESS, idempotency_key="a")
        )
    assert ready.next_valid_actions() == (ExecutionStateV65.BLOCKED, ExecutionStateV65.IN_PROGRESS)


def test_execution_retry_requires_partial_failure_evidence() -> None:
    active = (
        ExecutionRecordV65("record")
        .transition(ExecutionEventV65("ready", ExecutionStateV65.PENDING, ExecutionStateV65.READY))
        .transition(ExecutionEventV65("start", ExecutionStateV65.READY, ExecutionStateV65.IN_PROGRESS))
    )
    partial = active.transition(
        ExecutionEventV65("partial", ExecutionStateV65.IN_PROGRESS, ExecutionStateV65.PARTIAL_FAILURE)
    )
    resumed = partial.transition(
        ExecutionEventV65(
            "retry",
            ExecutionStateV65.PARTIAL_FAILURE,
            ExecutionStateV65.READY,
            retry_of="partial",
        )
    )
    assert resumed.state is ExecutionStateV65.READY
    with pytest.raises(AdvisoryError, match="retry_requires"):
        active.transition(
            ExecutionEventV65(
                "bad-retry",
                ExecutionStateV65.IN_PROGRESS,
                ExecutionStateV65.PARTIAL_FAILURE,
                retry_of="missing",
            )
        )


def test_presentation_separates_claim_types_redacts_secrets_and_exposes_state() -> None:
    view = ExecutionPresenterV65().render(
        facts=("Readback passed",),
        actions=("No provider write",),
        warnings=("<unsafe> token=abc123",),
        blockers=(),
        assumptions=(),
        decisions=("Human approved review",),
        stale=("Source is stale",),
        conflicts=("Two sources disagree",),
        next_steps=("Review",),
        audit_refs=("V65-1",),
    )
    assert "## Verified facts" in view.executive
    assert "<unsafe>" not in view.executive
    assert "abc123" not in view.executive
    assert "[REDACTED]" in view.executive
    assert "## Stale state" in view.executive
    assert "## Conflicts" in view.executive
    assert view.technical == view.plain_text


def test_scenario_is_deterministic_isolated_and_preserves_comparison_context() -> None:
    baseline = ScenarioV65(
        "baseline",
        {"window": "one hour"},
        {"risk": "low"},
        constraints={"approval": "required"},
        downstream_effects={"customer": "none"},
        uncertainty={"duration": "unknown"},
    )
    alternative = ScenarioV65(
        "alternative",
        {"window": "two hours"},
        {"risk": "medium"},
        ("review change",),
        constraints={"approval": "required", "staff": "two"},
        downstream_effects={"customer": "brief interruption"},
        failure_modes=("rollback delay",),
        uncertainty={"duration": "wide"},
    )
    first = ScenarioIntelligenceV65().compare(baseline, alternative)
    second = ScenarioIntelligenceV65().compare(baseline, alternative)
    assert first.digest == second.digest
    assert first.changed_assumptions == ("window",)
    assert first.changed_constraints == ("staff",)
    assert first.changed_downstream_effects == ("customer",)
    assert first.provider_writes == 0
    assert first.analysis_label == "provider-free counterfactual analysis"
    with pytest.raises(TypeError):
        baseline.assumptions["window"] = "mutated"  # type: ignore[index]
