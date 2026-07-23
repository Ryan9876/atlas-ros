from datetime import UTC, datetime, timedelta

import pytest

from atlas_ros.intelligence.benchmark_scoring import BenchmarkScoringEngine
from atlas_ros.intelligence.records import (
    AuthorityLevel,
    ContextSnapshot,
    EvidenceEnvelope,
    ValidationStatus,
)

NOW = datetime(2026, 7, 22, 12, 0, tzinfo=UTC)
HASH = "sha256:" + "a" * 64


def evidence(
    *,
    authority: AuthorityLevel,
    confidence: float,
    validation: ValidationStatus,
    observed_at: datetime = NOW,
    locator: str = "source",
    citation: str = "citation",
) -> EvidenceEnvelope:
    return EvidenceEnvelope(
        created_at=NOW,
        statement="Benchmark evidence",
        source_authority=authority,
        confidence=confidence,
        observed_at=observed_at,
        validation_status=validation,
        source_locator=locator,
        source_content_hash=HASH,
        citation=citation,
    )


def context(
    evidence_records: tuple[EvidenceEnvelope, ...],
    *,
    constraints: tuple[str, ...] = ("production",),
    authorities: tuple[str, ...] = ("policy",),
) -> ContextSnapshot:
    return ContextSnapshot(
        created_at=NOW,
        active_objective="Choose governed response",
        constraints=constraints,
        environment={"domain": "risk"},
        available_authorities=authorities,
        decision_horizon="current evaluation",
        session_lineage=("case-1",),
        evidence_refs=tuple(item.ref() for item in evidence_records),
    )


def test_strong_evidence_produces_strong_governed_scores() -> None:
    records = (
        evidence(
            authority=AuthorityLevel.PRIMARY,
            confidence=0.98,
            validation=ValidationStatus.VERIFIED,
        ),
        evidence(
            authority=AuthorityLevel.AUTHORITATIVE_APPLICATION,
            confidence=0.94,
            validation=ValidationStatus.VERIFIED,
        ),
        evidence(
            authority=AuthorityLevel.GOVERNED_INTERNAL,
            confidence=0.90,
            validation=ValidationStatus.VERIFIED,
        ),
    )
    engine = BenchmarkScoringEngine()
    signals = engine.analyze(
        records,
        context(records),
        evaluated_at=NOW,
    )

    assert signals.authority_strength > 0.90
    assert signals.validation_strength == 1.0
    assert signals.corroboration == 1.0
    assert signals.evidence_support > 0.85
    assert signals.governance_fit > 0.85
    assert signals.unsupported_risk < 0.20


def test_weak_rejected_evidence_favors_abstention() -> None:
    records = (
        evidence(
            authority=AuthorityLevel.UNVERIFIED,
            confidence=0.20,
            validation=ValidationStatus.REJECTED,
            locator="",
            citation="",
        ),
    )
    engine = BenchmarkScoringEngine()
    signals = engine.analyze(
        records,
        context(records, constraints=(), authorities=()),
        evaluated_at=NOW,
    )
    options = engine.build_options(
        governed_label="act",
        evidence_refs=tuple(item.ref() for item in records),
        signals=signals,
    )

    governed, abstain = options

    assert signals.rejected_evidence_ratio == 1.0
    assert governed.scores["evidence_support"] < 0.20
    assert governed.scores["unsupported_risk"] > 0.80
    assert abstain.scores["governance_fit"] > governed.scores["governance_fit"]


def test_more_corroborating_evidence_increases_support() -> None:
    first = evidence(
        authority=AuthorityLevel.GOVERNED_INTERNAL,
        confidence=0.80,
        validation=ValidationStatus.PARTIAL,
    )
    second = evidence(
        authority=AuthorityLevel.GOVERNED_INTERNAL,
        confidence=0.80,
        validation=ValidationStatus.PARTIAL,
    )
    third = evidence(
        authority=AuthorityLevel.GOVERNED_INTERNAL,
        confidence=0.80,
        validation=ValidationStatus.PARTIAL,
    )
    engine = BenchmarkScoringEngine()

    one_signal = engine.analyze(
        (first,),
        context((first,)),
        evaluated_at=NOW,
    )
    three_signal = engine.analyze(
        (first, second, third),
        context((first, second, third)),
        evaluated_at=NOW,
    )

    assert three_signal.corroboration > one_signal.corroboration
    assert three_signal.evidence_support > one_signal.evidence_support


def test_stale_evidence_reduces_freshness_and_actionability() -> None:
    current = evidence(
        authority=AuthorityLevel.PRIMARY,
        confidence=0.95,
        validation=ValidationStatus.VERIFIED,
    )
    stale = evidence(
        authority=AuthorityLevel.PRIMARY,
        confidence=0.95,
        validation=ValidationStatus.VERIFIED,
        observed_at=NOW - timedelta(days=365),
    )
    engine = BenchmarkScoringEngine()

    current_signals = engine.analyze(
        (current,),
        context((current,)),
        evaluated_at=NOW,
    )
    stale_signals = engine.analyze(
        (stale,),
        context((stale,)),
        evaluated_at=NOW,
    )

    assert current_signals.freshness == pytest.approx(1.0)
    assert stale_signals.freshness == pytest.approx(0.0)
    assert stale_signals.actionability < current_signals.actionability


def test_incomplete_context_reduces_actionability() -> None:
    record = evidence(
        authority=AuthorityLevel.PRIMARY,
        confidence=0.95,
        validation=ValidationStatus.VERIFIED,
    )
    engine = BenchmarkScoringEngine()

    complete = context((record,))
    incomplete = ContextSnapshot(
        created_at=NOW,
        active_objective="Choose governed response",
        decision_horizon="current evaluation",
        evidence_refs=(record.ref(),),
    )

    complete_signals = engine.analyze(
        (record,),
        complete,
        evaluated_at=NOW,
    )
    incomplete_signals = engine.analyze(
        (record,),
        incomplete,
        evaluated_at=NOW,
    )

    assert incomplete_signals.context_completeness < (complete_signals.context_completeness)
    assert incomplete_signals.actionability < complete_signals.actionability
