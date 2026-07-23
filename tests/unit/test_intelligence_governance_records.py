from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from atlas_ros.intelligence.record_store import (
    ReferenceResolutionError,
    SQLiteIntelligenceRecordStore,
)
from atlas_ros.intelligence.records import (
    AuthorityLevel,
    ContextSnapshot,
    DecisionDisposition,
    DecisionGovernanceRecord,
    EvidenceEnvelope,
    GovernancePolicyRecord,
    PolicyEvaluationOutcome,
    PolicyEvaluationRecord,
    RecommendationOption,
    RecommendationRecord,
    RecordKind,
    ValidationStatus,
    parse_record,
)

NOW = datetime(2026, 7, 22, 21, 0, tzinfo=UTC)
HASH = "sha256:" + "a" * 64


def evidence() -> EvidenceEnvelope:
    return EvidenceEnvelope(
        created_at=NOW,
        statement="Current authority supports the recommendation.",
        source_authority=AuthorityLevel.PRIMARY,
        confidence=0.98,
        observed_at=NOW,
        validation_status=ValidationStatus.VERIFIED,
        source_locator="authority://current",
        source_content_hash=HASH,
        citation="current authority",
    )


def context(item: EvidenceEnvelope) -> ContextSnapshot:
    return ContextSnapshot(
        created_at=NOW,
        active_objective="Govern a recommendation",
        decision_horizon="current decision",
        evidence_refs=(item.ref(),),
    )


def recommendation(
    item: EvidenceEnvelope,
    snapshot: ContextSnapshot,
) -> RecommendationRecord:
    return RecommendationRecord(
        created_at=NOW,
        recommendation="Proceed",
        alternatives=(
            RecommendationOption(
                option="Defer",
                expected_benefit="More validation time",
                expected_risk="Delayed delivery",
            ),
        ),
        rationale="Current governed evidence supports proceeding.",
        expected_benefit="Controlled delivery",
        expected_risk="Implementation risk",
        confidence=0.92,
        evidence_refs=(item.ref(),),
        context_ref=snapshot.ref(),
    )


def policy() -> GovernancePolicyRecord:
    return GovernancePolicyRecord(
        created_at=NOW,
        policy_key="minimum-evidence-confidence",
        name="Minimum evidence confidence",
        description="Recommendations require sufficient evidence confidence.",
        failure_disposition=DecisionDisposition.REQUEST_EVIDENCE,
        parameters={"minimum_confidence": 0.80},
    )


def test_governance_records_round_trip_and_persist(tmp_path: Path) -> None:
    item = evidence()
    snapshot = context(item)
    rec = recommendation(item, snapshot)
    rule = policy()

    evaluation = PolicyEvaluationRecord(
        created_at=NOW,
        policy_ref=rule.ref(),
        subject_ref=rec.ref(),
        outcome=PolicyEvaluationOutcome.PASS,
        disposition=DecisionDisposition.ALLOW,
        reason="Recommendation confidence exceeds the policy threshold.",
        evidence_refs=(item.ref(),),
        confidence=0.98,
        links=(rule.ref(), rec.ref(), item.ref()),
    )
    governance = DecisionGovernanceRecord(
        created_at=NOW,
        context_ref=snapshot.ref(),
        recommendation_ref=rec.ref(),
        policy_evaluation_refs=(evaluation.ref(),),
        disposition=DecisionDisposition.ALLOW,
        permitted=True,
        explanation="All active governance policies passed.",
        evidence_refs=(item.ref(),),
        links=(
            snapshot.ref(),
            rec.ref(),
            evaluation.ref(),
            item.ref(),
        ),
    )

    for record in (rule, evaluation, governance):
        assert parse_record(record.model_dump(mode="json")) == record
        assert record.verify_integrity()

    store = SQLiteIntelligenceRecordStore(tmp_path / "records.db")
    store.initialize()
    store.append_many((item, snapshot, rec, rule, evaluation, governance))

    assert store.resolve(rule.ref()) == rule
    assert store.resolve(evaluation.ref()) == evaluation
    assert store.resolve(governance.ref()) == governance
    assert governance.kind is RecordKind.DECISION_GOVERNANCE


def test_failed_policy_cannot_allow_action() -> None:
    item = evidence()
    snapshot = context(item)
    rec = recommendation(item, snapshot)
    rule = policy()

    with pytest.raises(
        ValidationError,
        match="failed policy evaluations cannot use ALLOW",
    ):
        PolicyEvaluationRecord(
            created_at=NOW,
            policy_ref=rule.ref(),
            subject_ref=rec.ref(),
            outcome=PolicyEvaluationOutcome.FAIL,
            disposition=DecisionDisposition.ALLOW,
            reason="Invalid permissive failure.",
            evidence_refs=(item.ref(),),
            confidence=0.50,
            links=(rule.ref(), rec.ref(), item.ref()),
        )


def test_governance_permitted_matches_disposition() -> None:
    item = evidence()
    snapshot = context(item)
    rec = recommendation(item, snapshot)
    rule = policy()
    evaluation = PolicyEvaluationRecord(
        created_at=NOW,
        policy_ref=rule.ref(),
        subject_ref=rec.ref(),
        outcome=PolicyEvaluationOutcome.FAIL,
        disposition=DecisionDisposition.ESCALATE,
        reason="Human approval is required.",
        evidence_refs=(item.ref(),),
        confidence=0.90,
        links=(rule.ref(), rec.ref(), item.ref()),
    )

    with pytest.raises(
        ValidationError,
        match="permitted must be true only for ALLOW",
    ):
        DecisionGovernanceRecord(
            created_at=NOW,
            context_ref=snapshot.ref(),
            recommendation_ref=rec.ref(),
            policy_evaluation_refs=(evaluation.ref(),),
            disposition=DecisionDisposition.ESCALATE,
            permitted=True,
            explanation="Invalid permitted state.",
            evidence_refs=(item.ref(),),
            links=(
                snapshot.ref(),
                rec.ref(),
                evaluation.ref(),
                item.ref(),
            ),
        )


def test_store_rejects_unresolved_governance_links(tmp_path: Path) -> None:
    item = evidence()
    snapshot = context(item)
    rec = recommendation(item, snapshot)
    rule = policy()
    evaluation = PolicyEvaluationRecord(
        created_at=NOW,
        policy_ref=rule.ref(),
        subject_ref=rec.ref(),
        outcome=PolicyEvaluationOutcome.PASS,
        disposition=DecisionDisposition.ALLOW,
        reason="Policy passed.",
        evidence_refs=(item.ref(),),
        confidence=0.95,
        links=(rule.ref(), rec.ref(), item.ref()),
    )

    store = SQLiteIntelligenceRecordStore(tmp_path / "records.db")
    store.initialize()

    with pytest.raises(ReferenceResolutionError, match="unresolved reference"):
        store.append_many((evaluation,))
