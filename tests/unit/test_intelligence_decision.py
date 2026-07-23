from datetime import UTC, datetime
from pathlib import Path

from atlas_ros.intelligence.decision import (
    DecisionOutcome,
    GovernedDecisionPipeline,
)
from atlas_ros.intelligence.decision_governance import (
    default_governance_policies,
)
from atlas_ros.intelligence.reasoning import (
    CriterionDirection,
    DecisionCriterion,
    OptionAssessment,
    ReasoningRequest,
)
from atlas_ros.intelligence.record_store import (
    SQLiteIntelligenceRecordStore,
)
from atlas_ros.intelligence.records import (
    AuthorityLevel,
    ContextSnapshot,
    DecisionDisposition,
    EvidenceEnvelope,
    GovernancePolicyRecord,
    PolicyEvaluationOutcome,
    ValidationStatus,
)

NOW = datetime(2026, 7, 22, 23, 0, tzinfo=UTC)
HASH = "sha256:" + "c" * 64


def build_decision_case(
    tmp_path: Path,
    *,
    proceed_benefit: float = 0.90,
    defer_benefit: float = 0.20,
    proceed_risk: float = 0.10,
    defer_risk: float = 0.80,
    minimum_recommendation_margin: float = 0.01,
) -> tuple[
    SQLiteIntelligenceRecordStore,
    ReasoningRequest,
    tuple[GovernancePolicyRecord, ...],
]:
    store = SQLiteIntelligenceRecordStore(tmp_path / "records.db")
    store.initialize()

    evidence = EvidenceEnvelope(
        created_at=NOW,
        statement="Current authority supports the proposed action.",
        source_authority=AuthorityLevel.PRIMARY,
        confidence=0.95,
        observed_at=NOW,
        validation_status=ValidationStatus.VERIFIED,
        source_locator="authority://current",
        source_content_hash=HASH,
        citation="current authority",
    )

    context = ContextSnapshot(
        created_at=NOW,
        active_objective="Choose a governed action",
        constraints=("production",),
        environment={
            "human_approval": "",
            "unsupported_assumption_count": "0",
        },
        available_authorities=("current authority",),
        decision_horizon="current decision",
        evidence_refs=(evidence.ref(),),
    )

    policies = default_governance_policies(created_at=NOW)

    store.append_many(
        (
            evidence,
            context,
            *policies,
        )
    )

    request = ReasoningRequest(
        objective="Choose the best-supported governed action.",
        context_ref=context.ref(),
        criteria=(
            DecisionCriterion(
                name="benefit",
                weight=1.0,
                direction=CriterionDirection.MAXIMIZE,
            ),
            DecisionCriterion(
                name="risk",
                weight=1.0,
                direction=CriterionDirection.MINIMIZE,
            ),
        ),
        options=(
            OptionAssessment(
                option="proceed",
                scores={
                    "benefit": proceed_benefit,
                    "risk": proceed_risk,
                },
                expected_benefit="Deliver the capability",
                expected_risk="Controlled implementation risk",
                evidence_refs=(evidence.ref(),),
            ),
            OptionAssessment(
                option="defer",
                scores={
                    "benefit": defer_benefit,
                    "risk": defer_risk,
                },
                expected_benefit="Provide more review time",
                expected_risk="Delay delivery",
                evidence_refs=(evidence.ref(),),
            ),
        ),
        minimum_evidence_confidence=0.10,
        minimum_recommendation_margin=minimum_recommendation_margin,
    )

    return store, request, policies


def evaluate_pipeline(
    store: SQLiteIntelligenceRecordStore,
    request: ReasoningRequest,
    policies: tuple[GovernancePolicyRecord, ...],
) -> DecisionOutcome:
    return GovernedDecisionPipeline(store).evaluate(
        request,
        policy_refs=tuple(policy.ref() for policy in policies),
        created_at=NOW,
    )


def test_pipeline_returns_complete_decision_outcome(
    tmp_path: Path,
) -> None:
    store, request, policies = build_decision_case(tmp_path)

    outcome = evaluate_pipeline(
        store,
        request,
        policies,
    )

    assert isinstance(outcome, DecisionOutcome)
    assert outcome.reasoning.trace.objective == request.objective
    assert outcome.governance.governance.context_ref == request.context_ref
    assert len(outcome.policy_evaluations) == len(policies)


def test_pipeline_allows_supported_recommendation(
    tmp_path: Path,
) -> None:
    store, request, policies = build_decision_case(tmp_path)

    outcome = evaluate_pipeline(
        store,
        request,
        policies,
    )

    assert outcome.recommendation is not None
    assert outcome.recommendation.recommendation == "proceed"
    assert outcome.disposition is DecisionDisposition.ALLOW
    assert outcome.permitted
    assert all(
        evaluation.outcome is PolicyEvaluationOutcome.PASS
        for evaluation in outcome.policy_evaluations
    )


def test_decision_outcome_properties_expose_nested_results(
    tmp_path: Path,
) -> None:
    store, request, policies = build_decision_case(tmp_path)

    outcome = evaluate_pipeline(
        store,
        request,
        policies,
    )

    assert outcome.recommendation is outcome.reasoning.recommendation
    assert outcome.policy_evaluations is outcome.governance.evaluations
    assert outcome.decision is outcome.governance.governance
    assert outcome.disposition is outcome.decision.disposition
    assert outcome.permitted is outcome.decision.permitted


def test_recommendation_flows_into_governance(
    tmp_path: Path,
) -> None:
    store, request, policies = build_decision_case(tmp_path)

    outcome = evaluate_pipeline(
        store,
        request,
        policies,
    )

    assert outcome.recommendation is not None
    assert outcome.decision.recommendation_ref == outcome.recommendation.ref()

    assert all(
        evaluation.subject_ref == outcome.recommendation.ref()
        for evaluation in outcome.policy_evaluations
    )


def test_abstained_reasoning_produces_abstained_decision(
    tmp_path: Path,
) -> None:
    store, request, policies = build_decision_case(
        tmp_path,
        proceed_benefit=0.51,
        defer_benefit=0.50,
        proceed_risk=0.49,
        defer_risk=0.50,
        minimum_recommendation_margin=0.20,
    )

    outcome = evaluate_pipeline(
        store,
        request,
        policies,
    )

    assert outcome.reasoning.trace.abstained
    assert outcome.recommendation is None
    assert outcome.disposition is DecisionDisposition.ABSTAIN
    assert not outcome.permitted
    assert outcome.decision.recommendation_ref is None


def test_pipeline_preserves_policy_priority_order(
    tmp_path: Path,
) -> None:
    store, request, policies = build_decision_case(tmp_path)

    outcome = evaluate_pipeline(
        store,
        request,
        tuple(reversed(policies)),
    )

    evaluated_policy_refs = tuple(
        evaluation.policy_ref for evaluation in outcome.policy_evaluations
    )
    expected_policy_refs = tuple(
        policy.ref()
        for policy in sorted(
            policies,
            key=lambda policy: (
                policy.priority,
                policy.policy_key,
                str(policy.record_id),
            ),
        )
    )

    assert evaluated_policy_refs == expected_policy_refs


def test_pipeline_is_semantically_deterministic(
    tmp_path: Path,
) -> None:
    store, request, policies = build_decision_case(tmp_path)
    pipeline = GovernedDecisionPipeline(store)
    policy_refs = tuple(policy.ref() for policy in policies)

    first = pipeline.evaluate(
        request,
        policy_refs=policy_refs,
        created_at=NOW,
    )
    second = pipeline.evaluate(
        request,
        policy_refs=policy_refs,
        created_at=NOW,
    )

    assert first.reasoning.trace == second.reasoning.trace
    assert first.disposition is second.disposition
    assert first.permitted == second.permitted

    assert tuple(
        (
            evaluation.policy_ref,
            evaluation.outcome,
            evaluation.disposition,
            evaluation.reason,
            evaluation.confidence,
        )
        for evaluation in first.policy_evaluations
    ) == tuple(
        (
            evaluation.policy_ref,
            evaluation.outcome,
            evaluation.disposition,
            evaluation.reason,
            evaluation.confidence,
        )
        for evaluation in second.policy_evaluations
    )
