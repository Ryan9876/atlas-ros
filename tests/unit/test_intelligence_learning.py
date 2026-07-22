from datetime import UTC, datetime, timedelta

import pytest

from atlas_ros.intelligence.learning import GovernedLearningEngine, LearningPolicy, ProposalStatus
from atlas_ros.intelligence.record_store import SQLiteIntelligenceRecordStore
from atlas_ros.intelligence.records import (
    AuthorityLevel,
    EvidenceEnvelope,
    LearningEvent,
    PredictionRecord,
    ValidationStatus,
)


def seed(tmp_path, gains=(0.1, 0.08, 0.06), eligible=True):
    store = SQLiteIntelligenceRecordStore(tmp_path / "records.db")
    store.initialize()
    now = datetime.now(UTC)
    ev = EvidenceEnvelope(
        statement="source",
        source_authority=AuthorityLevel.PRIMARY,
        confidence=0.9,
        observed_at=now,
        validation_status=ValidationStatus.VERIFIED,
        source_content_hash="sha256:" + "a" * 64,
    )
    store.append(ev)
    pred = PredictionRecord(
        created_at=now,
        prediction="event",
        probability=0.5,
        confidence_low=0.3,
        confidence_high=0.7,
        expires_at=now + timedelta(days=2),
        evidence_refs=(ev.ref(),),
    )
    store.append(pred)
    events = []
    for i, gain in enumerate(gains):
        event = LearningEvent(
            created_at=now + timedelta(hours=i + 1),
            observed_outcome="positive",
            prediction_ref=pred.ref(),
            delta_analysis="resolved",
            confidence_before=0.5,
            confidence_after=max(0, min(1, 0.5 + gain)),
            pattern_updates=(("calibrate",) if eligible else ()),
            model_version="m1",
            learning_eligible=eligible,
            eligibility_reason="valid" if eligible else "invalid",
        )
        store.append(event)
        events.append(event)
    return store, ev, events


def test_proposes_bounded_adjustment(tmp_path):
    store, ev, events = seed(tmp_path)
    engine = GovernedLearningEngine(store, LearningPolicy(maximum_confidence_step=0.05))
    out = engine.propose_confidence_adjustment(
        [e.ref() for e in events], target="forecast:x", current_value=0.5, evidence_refs=[ev.ref()]
    )
    assert out.proposal is not None
    assert out.proposal.proposed_value == pytest.approx(0.55)


def test_insufficient_events_abstains(tmp_path):
    store, ev, events = seed(tmp_path, gains=(0.1,))
    out = GovernedLearningEngine(store).propose_confidence_adjustment(
        [events[0].ref()], target="x", current_value=0.5, evidence_refs=[ev.ref()]
    )
    assert out.proposal is None


def test_ineligible_events_do_not_learn(tmp_path):
    store, ev, events = seed(tmp_path, eligible=False)
    out = GovernedLearningEngine(store).propose_confidence_adjustment(
        [e.ref() for e in events], target="x", current_value=0.5, evidence_refs=[ev.ref()]
    )
    assert out.proposal is None


def test_approval_required(tmp_path):
    store, ev, events = seed(tmp_path)
    engine = GovernedLearningEngine(store)
    proposal = engine.propose_confidence_adjustment(
        [e.ref() for e in events], target="x", current_value=0.5, evidence_refs=[ev.ref()]
    ).proposal
    with pytest.raises(PermissionError):
        engine.apply(proposal)


def test_approve_apply_and_rollback(tmp_path):
    store, ev, events = seed(tmp_path)
    engine = GovernedLearningEngine(store)
    proposal = engine.propose_confidence_adjustment(
        [e.ref() for e in events], target="x", current_value=0.5, evidence_refs=[ev.ref()]
    ).proposal
    approved = engine.approve(proposal, approver="Ryan")
    applied_proposal, update = engine.apply(approved)
    assert applied_proposal.status is ProposalStatus.APPLIED
    rolled, reversed_update = engine.rollback(applied_proposal, update)
    assert rolled.status is ProposalStatus.ROLLED_BACK
    assert reversed_update.rolled_back_at is not None


def test_mismatched_rollback_rejected(tmp_path):
    store, ev, events = seed(tmp_path)
    engine = GovernedLearningEngine(store)
    p1 = engine.approve(
        engine.propose_confidence_adjustment(
            [e.ref() for e in events], target="x", current_value=0.5, evidence_refs=[ev.ref()]
        ).proposal,
        approver="Ryan",
    )
    p2 = engine.approve(
        engine.propose_confidence_adjustment(
            [e.ref() for e in events], target="y", current_value=0.4, evidence_refs=[ev.ref()]
        ).proposal,
        approver="Ryan",
    )
    p1a, u1 = engine.apply(p1)
    with pytest.raises(ValueError):
        engine.rollback(p2.model_copy(update={"status": ProposalStatus.APPLIED}), u1)


def test_quality_report(tmp_path):
    store, ev, events = seed(tmp_path)
    engine = GovernedLearningEngine(store)
    p = engine.approve(
        engine.propose_confidence_adjustment(
            [e.ref() for e in events], target="x", current_value=0.5, evidence_refs=[ev.ref()]
        ).proposal,
        approver="Ryan",
    )
    pa, u = engine.apply(p)
    report = engine.evaluate(events, [pa], [u])
    assert report.eligible_count == 3
    assert report.quality_score > 0
