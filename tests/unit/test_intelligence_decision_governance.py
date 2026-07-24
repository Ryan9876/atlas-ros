from datetime import UTC, datetime
from pathlib import Path

import pytest

from atlas_ros.intelligence.decision_governance import (
    CONTRADICTION_CHECK,
    MAXIMUM_UNSUPPORTED_ASSUMPTIONS,
    MINIMUM_AUTHORITY,
    MINIMUM_EVIDENCE_CONFIDENCE,
    MINIMUM_RECOMMENDATION_MARGIN,
    REQUIRED_HUMAN_APPROVAL,
    GovernanceOutcome,
    GovernedDecisionEngine,
    PolicyResult,
    default_governance_policies,
)
from atlas_ros.intelligence.reasoning import (
    CriterionDirection,
    DecisionCriterion,
    GovernedReasoningEngine,
    OptionAssessment,
    ReasoningOutcome,
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
    RecommendationRecord,
    ValidationStatus,
)

NOW = datetime(2026, 7, 22, 22, 0, tzinfo=UTC)
HASH = "sha256:" + "b" * 64


def build_reasoning_case(
    tmp_path: Path,
    *,
    evidence_confidence: float = 0.95,
    evidence_authority: AuthorityLevel = AuthorityLevel.PRIMARY,
    human_approval: str = "",
    unsupported_assumption_count: str = "0",
    proceed_benefit: float = 0.90,
    defer_benefit: float = 0.20,
    proceed_risk: float = 0.10,
    defer_risk: float = 0.80,
    minimum_reasoning_margin: float = 0.01,
) -> tuple[
    SQLiteIntelligenceRecordStore,
    ContextSnapshot,
    tuple[GovernancePolicyRecord, ...],
    ReasoningOutcome,
]:
    store = SQLiteIntelligenceRecordStore(tmp_path / "records.db")
    store.initialize()

    evidence = EvidenceEnvelope(
        created_at=NOW,
        statement="Current authority supports the governed action.",
        source_authority=evidence_authority,
        confidence=evidence_confidence,
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
            "human_approval": human_approval,
            "unsupported_assumption_count": unsupported_assumption_count,
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
        minimum_recommendation_margin=minimum_reasoning_margin,
    )

    reasoning = GovernedReasoningEngine(store).evaluate(
        request,
        created_at=NOW,
    )

    return store, context, policies, reasoning


def policy_by_key(
    policies: tuple[GovernancePolicyRecord, ...],
    policy_key: str,
) -> GovernancePolicyRecord:
    return next(policy for policy in policies if policy.policy_key == policy_key)


def govern(
    store: SQLiteIntelligenceRecordStore,
    context: ContextSnapshot,
    policies: tuple[GovernancePolicyRecord, ...],
    reasoning: ReasoningOutcome,
) -> GovernanceOutcome:
    return GovernedDecisionEngine(store).evaluate(
        reasoning_outcome=reasoning,
        context_ref=context.ref(),
        policy_refs=tuple(policy.ref() for policy in policies),
        created_at=NOW,
    )


def test_all_default_policies_allow_strong_reasoning(
    tmp_path: Path,
) -> None:
    store, context, policies, reasoning = build_reasoning_case(tmp_path)

    outcome = govern(
        store,
        context,
        policies,
        reasoning,
    )

    assert outcome.governance.disposition is DecisionDisposition.ALLOW
    assert outcome.governance.permitted
    assert len(outcome.evaluations) == 6
    assert all(
        evaluation.outcome is PolicyEvaluationOutcome.PASS for evaluation in outcome.evaluations
    )


def test_governance_records_persist_and_resolve(
    tmp_path: Path,
) -> None:
    store, context, policies, reasoning = build_reasoning_case(tmp_path)
    outcome = govern(
        store,
        context,
        policies,
        reasoning,
    )

    assert isinstance(reasoning.recommendation, RecommendationRecord)

    store.append_many(
        (
            reasoning.recommendation,
            *outcome.evaluations,
            outcome.governance,
        )
    )

    assert store.resolve(outcome.governance.ref()) == outcome.governance

    for evaluation in outcome.evaluations:
        assert store.resolve(evaluation.ref()) == evaluation


def test_required_human_approval_escalates_when_missing(
    tmp_path: Path,
) -> None:
    store, context, _, reasoning = build_reasoning_case(
        tmp_path,
        human_approval="",
    )

    policy = GovernancePolicyRecord(
        created_at=NOW,
        policy_key=REQUIRED_HUMAN_APPROVAL,
        name="Required human approval",
        description="Explicit human approval is required.",
        failure_disposition=DecisionDisposition.ESCALATE,
        priority=10,
        parameters={"required": True},
    )
    store.append(policy)

    outcome = govern(
        store,
        context,
        (policy,),
        reasoning,
    )

    assert outcome.governance.disposition is DecisionDisposition.ESCALATE
    assert not outcome.governance.permitted
    assert outcome.evaluations[0].outcome is PolicyEvaluationOutcome.FAIL


def test_required_human_approval_passes_when_granted(
    tmp_path: Path,
) -> None:
    store, context, _, reasoning = build_reasoning_case(
        tmp_path,
        human_approval="approved",
    )

    policy = GovernancePolicyRecord(
        created_at=NOW,
        policy_key=REQUIRED_HUMAN_APPROVAL,
        name="Required human approval",
        description="Explicit human approval is required.",
        failure_disposition=DecisionDisposition.ESCALATE,
        priority=10,
        parameters={"required": True},
    )
    store.append(policy)

    outcome = govern(
        store,
        context,
        (policy,),
        reasoning,
    )

    assert outcome.governance.disposition is DecisionDisposition.ALLOW
    assert outcome.governance.permitted


def test_low_evidence_confidence_requests_evidence(
    tmp_path: Path,
) -> None:
    store, context, policies, reasoning = build_reasoning_case(
        tmp_path,
        evidence_confidence=0.40,
    )

    policy = policy_by_key(
        policies,
        MINIMUM_EVIDENCE_CONFIDENCE,
    )

    outcome = govern(
        store,
        context,
        (policy,),
        reasoning,
    )

    assert outcome.governance.disposition is DecisionDisposition.REQUEST_EVIDENCE
    assert not outcome.governance.permitted
    assert outcome.evaluations[0].outcome is PolicyEvaluationOutcome.FAIL


def test_low_authority_requests_evidence(
    tmp_path: Path,
) -> None:
    store, context, policies, reasoning = build_reasoning_case(
        tmp_path,
        evidence_authority=AuthorityLevel.UNVERIFIED,
    )

    policy = policy_by_key(
        policies,
        MINIMUM_AUTHORITY,
    )

    outcome = govern(
        store,
        context,
        (policy,),
        reasoning,
    )

    assert outcome.governance.disposition is DecisionDisposition.REQUEST_EVIDENCE
    assert not outcome.governance.permitted


def test_unsupported_assumptions_request_clarification(
    tmp_path: Path,
) -> None:
    store, context, policies, reasoning = build_reasoning_case(
        tmp_path,
        unsupported_assumption_count="2",
    )

    policy = policy_by_key(
        policies,
        MAXIMUM_UNSUPPORTED_ASSUMPTIONS,
    )

    outcome = govern(
        store,
        context,
        (policy,),
        reasoning,
    )

    assert outcome.governance.disposition is DecisionDisposition.REQUEST_CLARIFICATION
    assert not outcome.governance.permitted


def test_policy_priority_determines_final_disposition(
    tmp_path: Path,
) -> None:
    store, context, _, reasoning = build_reasoning_case(
        tmp_path,
        human_approval="",
        unsupported_assumption_count="2",
    )

    approval_policy = GovernancePolicyRecord(
        created_at=NOW,
        policy_key=REQUIRED_HUMAN_APPROVAL,
        name="Required human approval",
        description="Explicit human approval is required.",
        failure_disposition=DecisionDisposition.ESCALATE,
        priority=10,
        parameters={"required": True},
    )
    assumption_policy = GovernancePolicyRecord(
        created_at=NOW,
        policy_key=MAXIMUM_UNSUPPORTED_ASSUMPTIONS,
        name="Maximum unsupported assumptions",
        description="Unsupported assumptions must remain within policy.",
        failure_disposition=DecisionDisposition.REQUEST_CLARIFICATION,
        priority=20,
        parameters={"maximum_count": 0},
    )
    store.append_many(
        (
            approval_policy,
            assumption_policy,
        )
    )

    outcome = govern(
        store,
        context,
        (
            assumption_policy,
            approval_policy,
        ),
        reasoning,
    )

    assert outcome.governance.disposition is DecisionDisposition.ESCALATE
    assert not outcome.governance.permitted
    assert outcome.evaluations[0].policy_ref == approval_policy.ref()
    assert outcome.evaluations[1].policy_ref == assumption_policy.ref()


def test_reasoning_abstention_forces_governance_abstention(
    tmp_path: Path,
) -> None:
    store, context, policies, reasoning = build_reasoning_case(
        tmp_path,
        proceed_benefit=0.51,
        defer_benefit=0.50,
        proceed_risk=0.49,
        defer_risk=0.50,
        minimum_reasoning_margin=0.20,
    )

    policy = policy_by_key(
        policies,
        CONTRADICTION_CHECK,
    )

    outcome = govern(
        store,
        context,
        (policy,),
        reasoning,
    )

    assert reasoning.trace.abstained
    assert reasoning.recommendation is None
    assert outcome.governance.disposition is DecisionDisposition.ABSTAIN
    assert not outcome.governance.permitted
    assert outcome.governance.recommendation_ref is None


def test_duplicate_policy_references_are_rejected(
    tmp_path: Path,
) -> None:
    store, context, policies, reasoning = build_reasoning_case(tmp_path)
    policy = policies[0]

    with pytest.raises(
        ValueError,
        match="policy references must be unique",
    ):
        GovernedDecisionEngine(store).evaluate(
            reasoning_outcome=reasoning,
            context_ref=context.ref(),
            policy_refs=(
                policy.ref(),
                policy.ref(),
            ),
            created_at=NOW,
        )


def test_inactive_policies_are_ignored(
    tmp_path: Path,
) -> None:
    store, context, _, reasoning = build_reasoning_case(tmp_path)

    active_policy = GovernancePolicyRecord(
        created_at=NOW,
        policy_key=CONTRADICTION_CHECK,
        name="Active contradiction policy",
        description="Reject unresolved contradictions.",
        failure_disposition=DecisionDisposition.ESCALATE,
        priority=10,
        active=True,
    )
    inactive_policy = GovernancePolicyRecord(
        created_at=NOW,
        policy_key=REQUIRED_HUMAN_APPROVAL,
        name="Inactive approval policy",
        description="This inactive policy must be ignored.",
        failure_disposition=DecisionDisposition.ESCALATE,
        priority=1,
        parameters={"required": True},
        active=False,
    )
    store.append_many(
        (
            active_policy,
            inactive_policy,
        )
    )

    outcome = govern(
        store,
        context,
        (
            inactive_policy,
            active_policy,
        ),
        reasoning,
    )

    assert len(outcome.evaluations) == 1
    assert outcome.evaluations[0].policy_ref == active_policy.ref()
    assert outcome.governance.disposition is DecisionDisposition.ALLOW


def test_unsupported_policy_key_is_rejected(
    tmp_path: Path,
) -> None:
    store, context, _, reasoning = build_reasoning_case(tmp_path)

    policy = GovernancePolicyRecord(
        created_at=NOW,
        policy_key="unknown-policy",
        name="Unknown policy",
        description="This policy has no registered evaluator.",
        failure_disposition=DecisionDisposition.DENY,
    )
    store.append(policy)

    with pytest.raises(
        ValueError,
        match="unsupported governance policy",
    ):
        govern(
            store,
            context,
            (policy,),
            reasoning,
        )


def test_custom_policy_evaluator_can_be_registered(
    tmp_path: Path,
) -> None:
    store, context, _, reasoning = build_reasoning_case(tmp_path)

    policy = GovernancePolicyRecord(
        created_at=NOW,
        policy_key="custom-policy",
        name="Custom policy",
        description="A registered custom evaluator controls this policy.",
        failure_disposition=DecisionDisposition.DEFER,
    )
    store.append(policy)

    def custom_evaluator(
        governance_policy: GovernancePolicyRecord,
        reasoning_outcome: ReasoningOutcome,
        snapshot: ContextSnapshot,
    ) -> PolicyResult:
        assert governance_policy.policy_key == "custom-policy"
        assert reasoning_outcome.recommendation is not None
        assert snapshot == context

        return PolicyResult(
            passed=False,
            reason="Custom review is incomplete.",
            confidence=0.75,
        )

    engine = GovernedDecisionEngine(store)
    engine.register_policy_evaluator(
        "custom-policy",
        custom_evaluator,
    )

    outcome = engine.evaluate(
        reasoning_outcome=reasoning,
        context_ref=context.ref(),
        policy_refs=(policy.ref(),),
        created_at=NOW,
    )

    assert outcome.governance.disposition is DecisionDisposition.DEFER
    assert not outcome.governance.permitted
    assert outcome.evaluations[0].confidence == 0.75


def test_replacing_existing_evaluator_requires_explicit_permission(
    tmp_path: Path,
) -> None:
    store, _, _, _ = build_reasoning_case(tmp_path)
    engine = GovernedDecisionEngine(store)

    def replacement(
        policy: GovernancePolicyRecord,
        reasoning: ReasoningOutcome,
        context: ContextSnapshot,
    ) -> PolicyResult:
        del policy, reasoning, context

        return PolicyResult(
            passed=True,
            reason="Replacement evaluator passed.",
            confidence=1.0,
        )

    with pytest.raises(
        ValueError,
        match="already registered",
    ):
        engine.register_policy_evaluator(
            CONTRADICTION_CHECK,
            replacement,
        )

    engine.register_policy_evaluator(
        CONTRADICTION_CHECK,
        replacement,
        replace=True,
    )


def test_minimum_recommendation_margin_policy_passes(
    tmp_path: Path,
) -> None:
    store, context, policies, reasoning = build_reasoning_case(tmp_path)

    policy = policy_by_key(
        policies,
        MINIMUM_RECOMMENDATION_MARGIN,
    )

    outcome = govern(
        store,
        context,
        (policy,),
        reasoning,
    )

    assert outcome.governance.disposition is DecisionDisposition.ALLOW
    assert outcome.evaluations[0].outcome is PolicyEvaluationOutcome.PASS
