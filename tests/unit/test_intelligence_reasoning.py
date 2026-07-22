from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from atlas_ros.intelligence.reasoning import (
    CriterionDirection,
    DecisionCriterion,
    GovernedReasoningEngine,
    OptionAssessment,
    ReasoningRequest,
)
from atlas_ros.intelligence.record_store import SQLiteIntelligenceRecordStore
from atlas_ros.intelligence.records import (
    AuthorityLevel,
    ContextSnapshot,
    EvidenceEnvelope,
    ValidationStatus,
)

NOW = datetime(2026, 7, 22, 6, 0, tzinfo=UTC)
HASH = "sha256:" + "a" * 64


def evidence(n: int, *, confidence: float = 0.9, authority: AuthorityLevel = AuthorityLevel.PRIMARY, status: ValidationStatus = ValidationStatus.VERIFIED):
    return EvidenceEnvelope(record_id=UUID(f"00000000-0000-4000-9000-{n:012d}"), created_at=NOW, statement=f"Evidence {n}", source_authority=authority, confidence=confidence, observed_at=NOW, validation_status=status, source_content_hash=HASH)


def setup(tmp_path: Path):
    store = SQLiteIntelligenceRecordStore(tmp_path / "records.db")
    store.initialize()
    ev1, ev2 = evidence(1), evidence(2, authority=AuthorityLevel.GOVERNED_INTERNAL)
    ctx = ContextSnapshot(record_id=UUID("00000000-0000-4000-9000-000000000003"), created_at=NOW, active_objective="Choose implementation approach", decision_horizon="current milestone", evidence_refs=(ev1.ref(), ev2.ref()))
    store.append_many((ev1, ev2, ctx))
    return store, ev1, ev2, ctx


def request(ev1, ev2, ctx, margin=0.05):
    return ReasoningRequest(
        objective="Choose implementation approach",
        context_ref=ctx.ref(),
        criteria=(DecisionCriterion(name="benefit", weight=2), DecisionCriterion(name="risk", weight=1, direction=CriterionDirection.MINIMIZE)),
        options=(
            OptionAssessment(option="phased", scores={"benefit": .9, "risk": .2}, expected_benefit="Controlled delivery", expected_risk="Longer schedule", evidence_refs=(ev1.ref(), ev2.ref())),
            OptionAssessment(option="big bang", scores={"benefit": .7, "risk": .8}, expected_benefit="Fast completion", expected_risk="High change risk", evidence_refs=(ev1.ref(),)),
        ),
        minimum_recommendation_margin=margin,
    )


def test_engine_selects_evidence_supported_option(tmp_path: Path):
    store, ev1, ev2, ctx = setup(tmp_path)
    outcome = GovernedReasoningEngine(store).evaluate(request(ev1, ev2, ctx), created_at=NOW)
    assert not outcome.trace.abstained
    assert outcome.trace.selected_option == "phased"
    assert outcome.recommendation is not None
    assert outcome.recommendation.recommendation == "phased"
    assert outcome.recommendation.verify_integrity()
    assert outcome.trace.ranked_options[0].adjusted_score > outcome.trace.ranked_options[1].adjusted_score
    assert GovernedReasoningEngine.decision_quality(outcome.trace) > 0.5


def test_engine_abstains_when_margin_is_insufficient(tmp_path: Path):
    store, ev1, ev2, ctx = setup(tmp_path)
    outcome = GovernedReasoningEngine(store).evaluate(request(ev1, ev2, ctx, margin=.9), created_at=NOW)
    assert outcome.trace.abstained
    assert outcome.recommendation is None
    assert GovernedReasoningEngine.decision_quality(outcome.trace) <= .5


def test_rejected_or_low_confidence_evidence_blocks_recommendation(tmp_path: Path):
    store = SQLiteIntelligenceRecordStore(tmp_path / "records.db")
    store.initialize()
    weak = evidence(4, confidence=.2, status=ValidationStatus.REJECTED)
    ctx = ContextSnapshot(record_id=UUID("00000000-0000-4000-9000-000000000005"), created_at=NOW, active_objective="test", decision_horizon="now", evidence_refs=(weak.ref(),))
    store.append_many((weak, ctx))
    req = ReasoningRequest(objective="test", context_ref=ctx.ref(), criteria=(DecisionCriterion(name="value", weight=1),), options=(
        OptionAssessment(option="a", scores={"value": .9}, expected_benefit="a", expected_risk="a", evidence_refs=(weak.ref(),)),
        OptionAssessment(option="b", scores={"value": .1}, expected_benefit="b", expected_risk="b", evidence_refs=(weak.ref(),)),
    ))
    outcome = GovernedReasoningEngine(store).evaluate(req, created_at=NOW)
    assert outcome.trace.abstained
    assert all(not item.usable for item in outcome.trace.evidence)


def test_request_rejects_missing_scores_and_duplicates(tmp_path: Path):
    store, ev1, ev2, ctx = setup(tmp_path)
    with pytest.raises(ValidationError, match="score every criterion"):
        ReasoningRequest(objective="x", context_ref=ctx.ref(), criteria=(DecisionCriterion(name="a", weight=1), DecisionCriterion(name="b", weight=1)), options=(
            OptionAssessment(option="one", scores={"a": .5}, expected_benefit="x", expected_risk="x", evidence_refs=(ev1.ref(),)),
            OptionAssessment(option="two", scores={"a": .5, "b": .5}, expected_benefit="x", expected_risk="x", evidence_refs=(ev2.ref(),)),
        ))
    with pytest.raises(ValidationError, match="option names must be unique"):
        ReasoningRequest(objective="x", context_ref=ctx.ref(), criteria=(DecisionCriterion(name="a", weight=1),), options=(
            OptionAssessment(option="same", scores={"a": .5}, expected_benefit="x", expected_risk="x", evidence_refs=(ev1.ref(),)),
            OptionAssessment(option="same", scores={"a": .6}, expected_benefit="x", expected_risk="x", evidence_refs=(ev2.ref(),)),
        ))


def test_option_scores_are_bounded(tmp_path: Path):
    store, ev1, _, _ = setup(tmp_path)
    with pytest.raises(ValidationError, match="between 0.0 and 1.0"):
        OptionAssessment(option="bad", scores={"value": 2}, expected_benefit="x", expected_risk="x", evidence_refs=(ev1.ref(),))
