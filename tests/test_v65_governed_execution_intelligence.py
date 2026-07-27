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
        FrameworkRuleV65("retention", "retain seven years", AuthorityTier.ORGANIZATION_POLICY, "4", "policy", True),
    ))
    assert result.rules[0].tier is AuthorityTier.ORGANIZATION_POLICY
    with pytest.raises(AdvisoryError, match="conflicting_rule"):
        composer.compose((
            FrameworkRuleV65("retention", "one year", AuthorityTier.PREFERENCE, "1", "pref"),
            FrameworkRuleV65("retention", "seven years", AuthorityTier.ORGANIZATION_POLICY, "4", "policy", True),
        ))


def test_minimum_path_keeps_mandatory_controls_and_orders_dependencies() -> None:
    plan = MinimumEffectivePathPlannerV65().plan((
        PathStepV65("scope", "Scope", mandatory=True),
        PathStepV65("approve", "Approve", ("scope",), mandatory=True, gate="human"),
        PathStepV65("pilot", "Pilot", ("approve",)),
    ), ("pilot",))
    assert tuple(step.step_id for step in plan.steps) == ("scope", "approve", "pilot")
    assert "unknown:approve:risk" in plan.blockers


def test_minimum_path_rejects_cycles_and_missing_prerequisites() -> None:
    with pytest.raises(AdvisoryError, match="cyclic"):
        MinimumEffectivePathPlannerV65().plan((
            PathStepV65("one", "One", ("two",)),
            PathStepV65("two", "Two", ("one",)),
        ), ("one",))
    with pytest.raises(AdvisoryError, match="missing"):
        MinimumEffectivePathPlannerV65().plan((PathStepV65("one", "One", ("missing",)),), ("one",))


def test_execution_intelligence_requires_evidence_and_is_idempotent() -> None:
    record = ExecutionRecordV65("record-1")
    ready = record.transition(ExecutionEventV65("one", ExecutionStateV65.PENDING, ExecutionStateV65.READY, idempotency_key="ready"))
    active = ready.transition(ExecutionEventV65("two", ExecutionStateV65.READY, ExecutionStateV65.IN_PROGRESS))
    with pytest.raises(AdvisoryError, match="completion_requires_evidence"):
        active.transition(ExecutionEventV65("three", ExecutionStateV65.IN_PROGRESS, ExecutionStateV65.SUCCEEDED))
    complete = active.transition(ExecutionEventV65("four", ExecutionStateV65.IN_PROGRESS, ExecutionStateV65.SUCCEEDED, ("receipt-1",)))
    assert complete.state is ExecutionStateV65.SUCCEEDED
    assert ready.transition(ExecutionEventV65("again", ExecutionStateV65.READY, ExecutionStateV65.IN_PROGRESS, idempotency_key="ready")) is ready


def test_presentation_separates_claim_types_and_sanitizes_markup() -> None:
    view = ExecutionPresenterV65().render(
        facts=("Readback passed",), actions=("No provider write",), warnings=("<unsafe>",),
        blockers=(), assumptions=(), next_steps=("Review",), audit_refs=("V65-1",),
    )
    assert "## Verified facts" in view.executive
    assert "<unsafe>" not in view.executive
    assert "<unsafe>" not in view.technical
    assert "unsafe" in view.technical


def test_scenario_is_deterministic_and_has_no_provider_writes() -> None:
    baseline = ScenarioV65("baseline", {"window": "one hour"}, {"risk": "low"})
    alternative = ScenarioV65("alternative", {"window": "two hours"}, {"risk": "medium"}, ("review change",))
    first = ScenarioIntelligenceV65().compare(baseline, alternative)
    second = ScenarioIntelligenceV65().compare(baseline, alternative)
    assert first.digest == second.digest
    assert first.changed_assumptions == ("window",)
    assert first.provider_writes == 0
