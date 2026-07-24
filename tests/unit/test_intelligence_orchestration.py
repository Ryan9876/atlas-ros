from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from atlas_ros.intelligence.decision import DecisionOutcome
from atlas_ros.intelligence.decision_governance import CONTRADICTION_CHECK
from atlas_ros.intelligence.inference import InferenceOutcome, InferenceRequest
from atlas_ros.intelligence.orchestration import (
    IntelligenceOrchestrator,
    IntelligenceOutcome,
    IntelligenceState,
)
from atlas_ros.intelligence.reasoning import (
    DecisionCriterion,
    OptionAssessment,
    ReasoningOutcome,
    ReasoningRequest,
    ReasoningTrace,
)
from atlas_ros.intelligence.record_store import SQLiteIntelligenceRecordStore
from atlas_ros.intelligence.records import (
    AuthorityLevel,
    ClaimRecord,
    ClaimType,
    ContextSnapshot,
    DecisionDisposition,
    EvidenceEnvelope,
    GovernancePolicyRecord,
    InferenceMethod,
    InferenceRule,
    ValidationStatus,
)

NOW = datetime(2026, 7, 22, 23, 30, tzinfo=UTC)
HASH = "sha256:" + "d" * 64


def reasoning_outcome(
    objective: str = "Select a governed option.",
) -> ReasoningOutcome:
    return ReasoningOutcome(
        trace=ReasoningTrace(
            objective=objective,
            evidence=(),
            claims=(),
            evidence_graph=(),
            claim_graph=(),
            conflicts=(),
            claim_conflicts=(),
            ranked_options=(),
            selected_option=None,
            abstained=True,
            explanation="No decision was produced.",
            uncertainty=1.0,
        ),
        recommendation=None,
    )


def request() -> ReasoningRequest:
    return cast(
        ReasoningRequest,
        SimpleNamespace(objective="Select a governed option."),
    )


def test_initial_state_contains_no_stage_results() -> None:
    state = IntelligenceState()

    assert state.inference is None
    assert state.reasoning is None
    assert state.decision is None
    assert not state.has_inference
    assert not state.has_reasoning
    assert not state.has_decision
    assert not state.completed


def test_state_exposes_completed_stages() -> None:
    inference = cast(InferenceOutcome, SimpleNamespace())
    reasoning = reasoning_outcome()
    decision = cast(
        DecisionOutcome,
        SimpleNamespace(reasoning=reasoning),
    )

    state = IntelligenceState(
        inference=inference,
        reasoning=reasoning,
        decision=decision,
    )

    assert state.inference is inference
    assert state.reasoning is reasoning
    assert state.decision is decision
    assert state.has_inference
    assert state.has_reasoning
    assert state.has_decision
    assert state.completed


def test_decision_requires_reasoning_outcome() -> None:
    decision = cast(
        DecisionOutcome,
        SimpleNamespace(reasoning=reasoning_outcome()),
    )

    with pytest.raises(
        ValueError,
        match="decision state requires a reasoning outcome",
    ):
        IntelligenceState(decision=decision)


def test_decision_must_contain_state_reasoning() -> None:
    state_reasoning = reasoning_outcome("Objective A")
    different_reasoning = reasoning_outcome("Objective B")
    decision = cast(
        DecisionOutcome,
        SimpleNamespace(reasoning=different_reasoning),
    )

    with pytest.raises(
        ValueError,
        match="decision outcome must contain",
    ):
        IntelligenceState(
            reasoning=state_reasoning,
            decision=decision,
        )


def test_intelligence_outcome_exposes_state_results() -> None:
    workflow_request = request()
    inference = cast(InferenceOutcome, SimpleNamespace())
    reasoning = reasoning_outcome()
    decision = cast(
        DecisionOutcome,
        SimpleNamespace(reasoning=reasoning),
    )
    state = IntelligenceState(
        inference=inference,
        reasoning=reasoning,
        decision=decision,
    )

    outcome = IntelligenceOutcome(
        request=workflow_request,
        state=state,
    )

    assert outcome.request is workflow_request
    assert outcome.inference is inference
    assert outcome.reasoning is reasoning
    assert outcome.decision is decision
    assert outcome.completed


def test_orchestration_models_are_immutable() -> None:
    state = IntelligenceState()
    outcome = IntelligenceOutcome(
        request=request(),
        state=state,
    )

    with pytest.raises(FrozenInstanceError):
        state.reasoning = reasoning_outcome()  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        outcome.state = IntelligenceState()  # type: ignore[misc]


def test_orchestrator_runs_and_persists_complete_pipeline(tmp_path: Path) -> None:
    store = SQLiteIntelligenceRecordStore(tmp_path / "records.db")
    store.initialize()
    evidence = EvidenceEnvelope(
        created_at=NOW,
        statement="Validated evidence supports the phased option.",
        source_authority=AuthorityLevel.PRIMARY,
        confidence=0.98,
        observed_at=NOW,
        validation_status=ValidationStatus.VERIFIED,
        source_locator="authority://current",
        source_content_hash=HASH,
        citation="current authority",
    )
    premise = ClaimRecord(
        created_at=NOW,
        statement="The phased option satisfies the current authority.",
        claim_type=ClaimType.FACT,
        confidence=0.95,
        validation_status=ValidationStatus.VERIFIED,
        evidence_refs=(evidence.ref(),),
    )
    rule = InferenceRule(
        created_at=NOW,
        name="Governed option support",
        description="A validated premise supports a governed option.",
        method=InferenceMethod.DEDUCTIVE,
        minimum_premises=1,
        reliability=0.95,
    )
    context = ContextSnapshot(
        created_at=NOW,
        active_objective="Choose a governed implementation option",
        decision_horizon="current decision",
        evidence_refs=(evidence.ref(),),
    )
    policy = GovernancePolicyRecord(
        created_at=NOW,
        policy_key=CONTRADICTION_CHECK,
        name="Contradiction check",
        description="Material contradictions require escalation.",
        failure_disposition=DecisionDisposition.ESCALATE,
    )
    store.append_many((evidence, premise, rule, context, policy))

    workflow_request = ReasoningRequest(
        objective="Choose the best-supported governed option.",
        context_ref=context.ref(),
        criteria=(DecisionCriterion(name="benefit", weight=1.0),),
        options=(
            OptionAssessment(
                option="phased",
                scores={"benefit": 0.90},
                expected_benefit="Controlled delivery",
                expected_risk="Longer schedule",
                evidence_refs=(evidence.ref(),),
            ),
            OptionAssessment(
                option="defer",
                scores={"benefit": 0.20},
                expected_benefit="More review time",
                expected_risk="Delayed value",
                evidence_refs=(evidence.ref(),),
            ),
        ),
        minimum_evidence_confidence=0.10,
        minimum_recommendation_margin=0.05,
    )
    inference_request = InferenceRequest(
        rule_ref=rule.ref(),
        premise_refs=(premise.ref(),),
        conclusion_statement="The phased option is supported by governed inference.",
        target_options=("phased",),
    )

    outcome = IntelligenceOrchestrator(store).run(
        workflow_request,
        policy_refs=(policy.ref(),),
        inference=inference_request,
        created_at=NOW,
    )

    assert outcome.completed
    assert outcome.inference is not None
    assert outcome.reasoning is not None
    assert outcome.decision is not None
    assert outcome.decision.permitted
    assert outcome.request.options[0].claim_refs == (outcome.inference.conclusion.ref(),)
    assert outcome.inference.conclusion.ref() in {
        assessment.claim_ref for assessment in outcome.reasoning.trace.claims
    }
    assert store.resolve(outcome.inference.trace.ref()) == outcome.inference.trace
    assert store.resolve(outcome.decision.decision.ref()) == outcome.decision.decision
