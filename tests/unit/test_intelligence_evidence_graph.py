from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from atlas_ros.intelligence.evidence_graph import (
    EvidenceGraphAnalyzer,
    EvidenceRelation,
    EvidenceRelationType,
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
    AuthorityLevel,
    ContextSnapshot,
    EvidenceEnvelope,
    ValidationStatus,
)

NOW = datetime(2026, 7, 22, 12, 0, tzinfo=UTC)
HASH = "sha256:" + "a" * 64


def evidence(
    n: int,
    *,
    authority: AuthorityLevel = AuthorityLevel.PRIMARY,
    confidence: float = 0.95,
    status: ValidationStatus = ValidationStatus.VERIFIED,
) -> EvidenceEnvelope:
    return EvidenceEnvelope(
        record_id=UUID(f"00000000-0000-4000-9000-{n:012d}"),
        created_at=NOW,
        statement=f"Evidence {n}",
        source_authority=authority,
        confidence=confidence,
        observed_at=NOW,
        validation_status=status,
        source_locator=f"source:{n}",
        source_content_hash=HASH,
        citation=f"citation:{n}",
    )


def test_support_increases_graph_multiplier() -> None:
    supporting = evidence(1)
    analyzer = EvidenceGraphAnalyzer()

    assessments, conflicts = analyzer.analyze(
        option_names=("act",),
        evidence={supporting.ref(): supporting},
        relations=(
            EvidenceRelation(
                source_ref=supporting.ref(),
                relation=EvidenceRelationType.SUPPORTS,
                target_option="act",
                rationale="Primary authority supports action.",
            ),
        ),
    )

    result = assessments["act"]

    assert result.support_strength > 0.90
    assert result.contradiction_strength == 0.0
    assert result.graph_multiplier > 0.90
    assert not result.unresolved_conflict
    assert conflicts == ()


def test_equal_authority_conflict_remains_unresolved() -> None:
    supporting = evidence(1)
    contradicting = evidence(2)
    analyzer = EvidenceGraphAnalyzer()

    assessments, conflicts = analyzer.analyze(
        option_names=("act",),
        evidence={
            supporting.ref(): supporting,
            contradicting.ref(): contradicting,
        },
        relations=(
            EvidenceRelation(
                source_ref=supporting.ref(),
                relation=EvidenceRelationType.SUPPORTS,
                target_option="act",
                rationale="Supports action.",
            ),
            EvidenceRelation(
                source_ref=contradicting.ref(),
                relation=EvidenceRelationType.CONTRADICTS,
                target_option="act",
                rationale="Contradicts action.",
            ),
        ),
    )

    assert assessments["act"].unresolved_conflict
    assert len(conflicts) == 1
    assert conflicts[0].resolved_by is None


def test_primary_authority_resolves_weaker_contradiction() -> None:
    supporting = evidence(
        1,
        authority=AuthorityLevel.PRIMARY,
        confidence=0.98,
    )
    contradicting = evidence(
        2,
        authority=AuthorityLevel.INFERRED,
        confidence=0.60,
        status=ValidationStatus.PARTIAL,
    )
    analyzer = EvidenceGraphAnalyzer()

    assessments, conflicts = analyzer.analyze(
        option_names=("act",),
        evidence={
            supporting.ref(): supporting,
            contradicting.ref(): contradicting,
        },
        relations=(
            EvidenceRelation(
                source_ref=supporting.ref(),
                relation=EvidenceRelationType.SUPPORTS,
                target_option="act",
                rationale="Primary authority supports action.",
            ),
            EvidenceRelation(
                source_ref=contradicting.ref(),
                relation=EvidenceRelationType.CONTRADICTS,
                target_option="act",
                rationale="Inferred evidence contradicts action.",
            ),
        ),
    )

    assert not assessments["act"].unresolved_conflict
    assert conflicts[0].resolved_by == supporting.ref()


def test_supersession_removes_obsolete_contradiction() -> None:
    current = evidence(1)
    obsolete = evidence(2)
    analyzer = EvidenceGraphAnalyzer()

    assessments, conflicts = analyzer.analyze(
        option_names=("act",),
        evidence={
            current.ref(): current,
            obsolete.ref(): obsolete,
        },
        relations=(
            EvidenceRelation(
                source_ref=current.ref(),
                relation=EvidenceRelationType.SUPPORTS,
                target_option="act",
                rationale="Current authority supports action.",
            ),
            EvidenceRelation(
                source_ref=obsolete.ref(),
                relation=EvidenceRelationType.CONTRADICTS,
                target_option="act",
                rationale="Obsolete authority contradicts action.",
            ),
            EvidenceRelation(
                source_ref=current.ref(),
                target_ref=obsolete.ref(),
                relation=EvidenceRelationType.SUPERSEDES,
                target_option="act",
                rationale="Current authority supersedes obsolete source.",
            ),
        ),
    )

    result = assessments["act"]

    assert obsolete.ref() not in result.contradicting_refs
    assert not result.unresolved_conflict
    assert conflicts == ()


def test_supersedes_requires_target_ref() -> None:
    source = evidence(1)

    with pytest.raises(
        ValidationError,
        match="supersedes relations require target_ref",
    ):
        EvidenceRelation(
            source_ref=source.ref(),
            relation=EvidenceRelationType.SUPERSEDES,
            target_option="act",
            rationale="Supersedes obsolete evidence.",
        )


def test_reasoning_engine_abstains_on_unresolved_conflict(
    tmp_path: Path,
) -> None:
    store = SQLiteIntelligenceRecordStore(tmp_path / "records.db")
    store.initialize()

    supporting = evidence(1)
    contradicting = evidence(2)
    context = ContextSnapshot(
        record_id=UUID("00000000-0000-4000-9000-000000000003"),
        created_at=NOW,
        active_objective="Determine whether to act",
        decision_horizon="current evaluation",
        evidence_refs=(
            supporting.ref(),
            contradicting.ref(),
        ),
    )
    store.append_many((supporting, contradicting, context))

    request = ReasoningRequest(
        objective="Determine whether to act",
        context_ref=context.ref(),
        criteria=(DecisionCriterion(name="value", weight=1.0),),
        options=(
            OptionAssessment(
                option="act",
                scores={"value": 0.95},
                expected_benefit="Resolve the issue.",
                expected_risk="May act incorrectly.",
                evidence_refs=(
                    supporting.ref(),
                    contradicting.ref(),
                ),
            ),
            OptionAssessment(
                option="wait",
                scores={"value": 0.20},
                expected_benefit="Gather more evidence.",
                expected_risk="Delay resolution.",
                evidence_refs=(
                    supporting.ref(),
                    contradicting.ref(),
                ),
            ),
        ),
        evidence_relations=(
            EvidenceRelation(
                source_ref=supporting.ref(),
                relation=EvidenceRelationType.SUPPORTS,
                target_option="act",
                rationale="Supports action.",
            ),
            EvidenceRelation(
                source_ref=contradicting.ref(),
                relation=EvidenceRelationType.CONTRADICTS,
                target_option="act",
                rationale="Contradicts action.",
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
    assert outcome.trace.conflicts
    assert "conflict" in outcome.trace.explanation.casefold()


def test_reasoning_engine_selects_authoritatively_supported_option(
    tmp_path: Path,
) -> None:
    store = SQLiteIntelligenceRecordStore(tmp_path / "records.db")
    store.initialize()

    primary = evidence(
        1,
        authority=AuthorityLevel.PRIMARY,
        confidence=0.98,
    )
    inferred = evidence(
        2,
        authority=AuthorityLevel.INFERRED,
        confidence=0.55,
        status=ValidationStatus.PARTIAL,
    )
    context = ContextSnapshot(
        record_id=UUID("00000000-0000-4000-9000-000000000003"),
        created_at=NOW,
        active_objective="Determine whether to act",
        decision_horizon="current evaluation",
        evidence_refs=(primary.ref(), inferred.ref()),
    )
    store.append_many((primary, inferred, context))

    request = ReasoningRequest(
        objective="Determine whether to act",
        context_ref=context.ref(),
        criteria=(DecisionCriterion(name="value", weight=1.0),),
        options=(
            OptionAssessment(
                option="act",
                scores={"value": 0.90},
                expected_benefit="Resolve the issue.",
                expected_risk="May act incorrectly.",
                evidence_refs=(primary.ref(), inferred.ref()),
            ),
            OptionAssessment(
                option="wait",
                scores={"value": 0.30},
                expected_benefit="Gather more evidence.",
                expected_risk="Delay resolution.",
                evidence_refs=(primary.ref(), inferred.ref()),
            ),
        ),
        evidence_relations=(
            EvidenceRelation(
                source_ref=primary.ref(),
                relation=EvidenceRelationType.SUPPORTS,
                target_option="act",
                rationale="Primary authority supports action.",
            ),
            EvidenceRelation(
                source_ref=inferred.ref(),
                relation=EvidenceRelationType.CONTRADICTS,
                target_option="act",
                rationale="Weak inferred evidence contradicts action.",
            ),
            EvidenceRelation(
                source_ref=primary.ref(),
                relation=EvidenceRelationType.SUPPORTS,
                target_option="wait",
                rationale="Primary evidence remains available.",
            ),
        ),
    )

    outcome = GovernedReasoningEngine(store).evaluate(
        request,
        created_at=NOW,
    )

    assert not outcome.trace.abstained
    assert outcome.trace.selected_option == "act"
    assert outcome.recommendation is not None
    assert outcome.trace.conflicts[0].resolved_by == primary.ref()
    assert "Evidence graph support" in outcome.trace.explanation
