from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from atlas_ros.intelligence.claim_graph import (
    ClaimAssessmentEngine,
    ClaimRelation,
    ClaimRelationType,
)
from atlas_ros.intelligence.reasoning import (
    DecisionCriterion,
    GovernedReasoningEngine,
    OptionAssessment,
    ReasoningRequest,
)
from atlas_ros.intelligence.record_store import (
    SQLiteIntelligenceRecordStore,
)
from atlas_ros.intelligence.records import (
    AssumptionRecord,
    AssumptionStatus,
    AuthorityLevel,
    ClaimRecord,
    ContextSnapshot,
    EvidenceEnvelope,
    ValidationStatus,
    parse_record,
)

NOW = datetime(2026, 7, 22, 14, 0, tzinfo=UTC)
HASH = "sha256:" + "a" * 64


def evidence(n: int) -> EvidenceEnvelope:
    return EvidenceEnvelope(
        record_id=UUID(f"00000000-0000-4000-a000-{n:012d}"),
        created_at=NOW,
        statement=f"Evidence {n}",
        source_authority=AuthorityLevel.PRIMARY,
        confidence=0.98,
        observed_at=NOW,
        validation_status=ValidationStatus.VERIFIED,
        source_locator=f"source:{n}",
        source_content_hash=HASH,
        citation=f"citation:{n}",
    )


def claim(
    n: int,
    item: EvidenceEnvelope,
    *,
    confidence: float = 0.95,
    status: ValidationStatus = ValidationStatus.VERIFIED,
) -> ClaimRecord:
    return ClaimRecord(
        record_id=UUID(f"00000000-0000-4000-b000-{n:012d}"),
        created_at=NOW,
        statement=f"Claim {n}",
        confidence=confidence,
        validation_status=status,
        evidence_refs=(item.ref(),),
    )


def test_claim_record_round_trip() -> None:
    item = evidence(1)
    record = claim(1, item)

    parsed = parse_record(record.model_dump(mode="json"))

    assert parsed == record
    assert parsed.verify_integrity()


def test_verified_assumption_requires_support() -> None:
    with pytest.raises(
        ValidationError,
        match="verified assumptions require evidence or claim references",
    ):
        AssumptionRecord(
            created_at=NOW,
            assumption="Rollback is available.",
            confidence=0.90,
            status=AssumptionStatus.VERIFIED,
        )


def test_equal_claim_conflict_remains_unresolved() -> None:
    item = evidence(1)
    supporting = claim(1, item)
    contradicting = claim(2, item)
    analyzer = ClaimAssessmentEngine()

    assessments, conflicts = analyzer.analyze(
        option_names=("deploy",),
        claims={
            supporting.ref(): supporting,
            contradicting.ref(): contradicting,
        },
        relations=(
            ClaimRelation(
                source_ref=supporting.ref(),
                relation=ClaimRelationType.SUPPORTS,
                target_option="deploy",
                rationale="Supports deployment.",
            ),
            ClaimRelation(
                source_ref=contradicting.ref(),
                relation=ClaimRelationType.CONTRADICTS,
                target_option="deploy",
                rationale="Contradicts deployment.",
            ),
        ),
    )

    assert assessments["deploy"].unresolved_conflict
    assert conflicts[0].resolved_by is None


def test_stronger_claim_resolves_conflict() -> None:
    item = evidence(1)
    supporting = claim(1, item, confidence=0.98)
    contradicting = claim(
        2,
        item,
        confidence=0.55,
        status=ValidationStatus.PARTIAL,
    )
    analyzer = ClaimAssessmentEngine()

    assessments, conflicts = analyzer.analyze(
        option_names=("deploy",),
        claims={
            supporting.ref(): supporting,
            contradicting.ref(): contradicting,
        },
        relations=(
            ClaimRelation(
                source_ref=supporting.ref(),
                relation=ClaimRelationType.SUPPORTS,
                target_option="deploy",
                rationale="Validated claim supports deployment.",
            ),
            ClaimRelation(
                source_ref=contradicting.ref(),
                relation=ClaimRelationType.CONTRADICTS,
                target_option="deploy",
                rationale="Weak claim contradicts deployment.",
            ),
        ),
    )

    assert not assessments["deploy"].unresolved_conflict
    assert conflicts[0].resolved_by == supporting.ref()


def test_reasoning_engine_uses_claim_graph(
    tmp_path: Path,
) -> None:
    store = SQLiteIntelligenceRecordStore(tmp_path / "records.db")
    store.initialize()

    item = evidence(1)
    deployment_claim = claim(1, item)
    context = ContextSnapshot(
        record_id=UUID("00000000-0000-4000-c000-000000000001"),
        created_at=NOW,
        active_objective="Determine whether to deploy",
        decision_horizon="current release",
        evidence_refs=(item.ref(),),
    )
    store.append_many((item, deployment_claim, context))

    request = ReasoningRequest(
        objective="Determine whether to deploy",
        context_ref=context.ref(),
        criteria=(DecisionCriterion(name="readiness", weight=1.0),),
        options=(
            OptionAssessment(
                option="deploy",
                scores={"readiness": 0.95},
                expected_benefit="Release validated capability.",
                expected_risk="Deployment failure.",
                evidence_refs=(item.ref(),),
                claim_refs=(deployment_claim.ref(),),
            ),
            OptionAssessment(
                option="wait",
                scores={"readiness": 0.20},
                expected_benefit="Gather more evidence.",
                expected_risk="Delay release.",
                evidence_refs=(item.ref(),),
            ),
        ),
        claim_relations=(
            ClaimRelation(
                source_ref=deployment_claim.ref(),
                relation=ClaimRelationType.SUPPORTS,
                target_option="deploy",
                rationale="Validated readiness claim supports deployment.",
            ),
        ),
    )

    outcome = GovernedReasoningEngine(store).evaluate(
        request,
        created_at=NOW,
    )

    assert not outcome.trace.abstained
    assert outcome.trace.selected_option == "deploy"
    assert outcome.recommendation is not None
    assert outcome.trace.claims
    assert outcome.trace.claim_graph
    assert outcome.trace.ranked_options[0].claim_strength > 0.90


def test_reasoning_engine_abstains_on_claim_conflict(
    tmp_path: Path,
) -> None:
    store = SQLiteIntelligenceRecordStore(tmp_path / "records.db")
    store.initialize()

    item = evidence(1)
    supporting = claim(1, item)
    contradicting = claim(2, item)
    context = ContextSnapshot(
        record_id=UUID("00000000-0000-4000-c000-000000000002"),
        created_at=NOW,
        active_objective="Determine whether to deploy",
        decision_horizon="current release",
        evidence_refs=(item.ref(),),
    )
    store.append_many((item, supporting, contradicting, context))

    request = ReasoningRequest(
        objective="Determine whether to deploy",
        context_ref=context.ref(),
        criteria=(DecisionCriterion(name="readiness", weight=1.0),),
        options=(
            OptionAssessment(
                option="deploy",
                scores={"readiness": 0.95},
                expected_benefit="Release validated capability.",
                expected_risk="Deployment failure.",
                evidence_refs=(item.ref(),),
                claim_refs=(
                    supporting.ref(),
                    contradicting.ref(),
                ),
            ),
            OptionAssessment(
                option="wait",
                scores={"readiness": 0.20},
                expected_benefit="Gather more evidence.",
                expected_risk="Delay release.",
                evidence_refs=(item.ref(),),
            ),
        ),
        claim_relations=(
            ClaimRelation(
                source_ref=supporting.ref(),
                relation=ClaimRelationType.SUPPORTS,
                target_option="deploy",
                rationale="Supports deployment.",
            ),
            ClaimRelation(
                source_ref=contradicting.ref(),
                relation=ClaimRelationType.CONTRADICTS,
                target_option="deploy",
                rationale="Contradicts deployment.",
            ),
        ),
    )

    outcome = GovernedReasoningEngine(store).evaluate(
        request,
        created_at=NOW,
    )

    assert outcome.trace.abstained
    assert outcome.trace.selected_option is None
    assert outcome.recommendation is None
    assert outcome.trace.claim_conflicts
