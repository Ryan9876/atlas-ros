from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from statistics import fmean
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from atlas_ros.intelligence.record_store import SQLiteIntelligenceRecordStore
from atlas_ros.intelligence.records import LearningEvent, RecordRef


class ProposalStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
    ROLLED_BACK = "rolled_back"


class UpdateType(StrEnum):
    CONFIDENCE_ADJUSTMENT = "confidence_adjustment"
    PATTERN_UPDATE = "pattern_update"
    POLICY_THRESHOLD = "policy_threshold"


class LearningPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    minimum_events: int = Field(default=3, ge=1)
    minimum_mean_confidence_gain: float = Field(default=0.02, ge=0.0, le=1.0)
    maximum_confidence_step: float = Field(default=0.10, gt=0.0, le=1.0)
    require_human_approval: bool = True


class PatternUpdateProposal(BaseModel):
    model_config = ConfigDict(frozen=True)

    proposal_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    update_type: UpdateType
    target: str = Field(min_length=1)
    current_value: float | str
    proposed_value: float | str
    rationale: str = Field(min_length=1)
    evidence_refs: tuple[RecordRef, ...] = Field(min_length=1)
    source_event_refs: tuple[RecordRef, ...] = Field(min_length=1)
    expected_quality_gain: float = Field(ge=0.0, le=1.0)
    risk: str = Field(min_length=1)
    status: ProposalStatus = ProposalStatus.DRAFT
    approved_by: str | None = None
    approved_at: datetime | None = None

    @model_validator(mode="after")
    def approval_consistency(self) -> PatternUpdateProposal:
        approved = self.status in {ProposalStatus.APPROVED, ProposalStatus.APPLIED, ProposalStatus.ROLLED_BACK}
        if approved != bool(self.approved_by and self.approved_at):
            raise ValueError("approved status requires approval identity and timestamp")
        return self


class AppliedUpdate(BaseModel):
    model_config = ConfigDict(frozen=True)

    update_id: UUID = Field(default_factory=uuid4)
    proposal_id: UUID
    applied_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    target: str = Field(min_length=1)
    prior_value: float | str
    applied_value: float | str
    rollback_token: str = Field(min_length=1)
    rolled_back_at: datetime | None = None


class LearningQualityReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_count: int = Field(ge=0)
    eligible_count: int = Field(ge=0)
    eligibility_rate: float = Field(ge=0.0, le=1.0)
    mean_confidence_gain: float
    proposal_count: int = Field(ge=0)
    approval_rate: float = Field(ge=0.0, le=1.0)
    rollback_rate: float = Field(ge=0.0, le=1.0)
    quality_score: float = Field(ge=0.0, le=1.0)


@dataclass(frozen=True)
class ProposalOutcome:
    proposal: PatternUpdateProposal | None
    reason: str


class GovernedLearningEngine:
    """Proposes, approves, applies, and rolls back bounded learning updates."""

    def __init__(self, record_store: SQLiteIntelligenceRecordStore, policy: LearningPolicy | None = None) -> None:
        self.record_store = record_store
        self.policy = policy or LearningPolicy()

    def propose_confidence_adjustment(
        self,
        event_refs: Sequence[RecordRef],
        *,
        target: str,
        current_value: float,
        evidence_refs: Sequence[RecordRef],
        created_at: datetime | None = None,
    ) -> ProposalOutcome:
        events: list[LearningEvent] = []
        for ref in event_refs:
            record = self.record_store.resolve(ref)
            if not isinstance(record, LearningEvent):
                raise ValueError("event_refs must resolve to LearningEvent")
            if record.learning_eligible:
                events.append(record)
        if len(events) < self.policy.minimum_events:
            return ProposalOutcome(None, "insufficient eligible learning events")
        mean_gain = fmean(event.confidence_after - event.confidence_before for event in events)
        if abs(mean_gain) < self.policy.minimum_mean_confidence_gain:
            return ProposalOutcome(None, "observed confidence change below policy threshold")
        bounded = max(-self.policy.maximum_confidence_step, min(self.policy.maximum_confidence_step, mean_gain))
        proposed = max(0.0, min(1.0, current_value + bounded))
        proposal = PatternUpdateProposal(
            created_at=created_at or datetime.now(UTC),
            update_type=UpdateType.CONFIDENCE_ADJUSTMENT,
            target=target,
            current_value=current_value,
            proposed_value=proposed,
            rationale=f"{len(events)} eligible outcomes support bounded confidence adjustment {bounded:+.4f}.",
            evidence_refs=tuple(evidence_refs),
            source_event_refs=tuple(event.ref() for event in events),
            expected_quality_gain=min(1.0, abs(mean_gain)),
            risk="Calibration may regress if the observed sample is not representative.",
        )
        return ProposalOutcome(proposal, "proposal created")

    def approve(self, proposal: PatternUpdateProposal, *, approver: str, approved_at: datetime | None = None) -> PatternUpdateProposal:
        if proposal.status is not ProposalStatus.DRAFT:
            raise ValueError("only draft proposals can be approved")
        return proposal.model_copy(update={
            "status": ProposalStatus.APPROVED,
            "approved_by": approver,
            "approved_at": approved_at or datetime.now(UTC),
        })

    def reject(self, proposal: PatternUpdateProposal) -> PatternUpdateProposal:
        if proposal.status is not ProposalStatus.DRAFT:
            raise ValueError("only draft proposals can be rejected")
        return proposal.model_copy(update={"status": ProposalStatus.REJECTED})

    def apply(self, proposal: PatternUpdateProposal, *, applied_at: datetime | None = None) -> tuple[PatternUpdateProposal, AppliedUpdate]:
        if self.policy.require_human_approval and proposal.status is not ProposalStatus.APPROVED:
            raise PermissionError("approved proposal required before application")
        if proposal.status not in {ProposalStatus.DRAFT, ProposalStatus.APPROVED}:
            raise ValueError("proposal cannot be applied from current status")
        applied = AppliedUpdate(
            proposal_id=proposal.proposal_id,
            applied_at=applied_at or datetime.now(UTC),
            target=proposal.target,
            prior_value=proposal.current_value,
            applied_value=proposal.proposed_value,
            rollback_token=f"rollback:{proposal.proposal_id}",
        )
        return proposal.model_copy(update={"status": ProposalStatus.APPLIED}), applied

    def rollback(self, proposal: PatternUpdateProposal, applied: AppliedUpdate, *, rolled_back_at: datetime | None = None) -> tuple[PatternUpdateProposal, AppliedUpdate]:
        if proposal.status is not ProposalStatus.APPLIED:
            raise ValueError("only applied proposals can be rolled back")
        if applied.proposal_id != proposal.proposal_id:
            raise ValueError("applied update does not match proposal")
        when = rolled_back_at or datetime.now(UTC)
        return (
            proposal.model_copy(update={"status": ProposalStatus.ROLLED_BACK}),
            applied.model_copy(update={"rolled_back_at": when}),
        )

    @staticmethod
    def evaluate(events: Sequence[LearningEvent], proposals: Sequence[PatternUpdateProposal], updates: Sequence[AppliedUpdate]) -> LearningQualityReport:
        eligible = [event for event in events if event.learning_eligible]
        gains = [event.confidence_after - event.confidence_before for event in eligible]
        approved = [p for p in proposals if p.status in {ProposalStatus.APPROVED, ProposalStatus.APPLIED, ProposalStatus.ROLLED_BACK}]
        rolled_back = [u for u in updates if u.rolled_back_at is not None]
        eligibility_rate = len(eligible) / len(events) if events else 0.0
        approval_rate = len(approved) / len(proposals) if proposals else 0.0
        rollback_rate = len(rolled_back) / len(updates) if updates else 0.0
        mean_gain = fmean(gains) if gains else 0.0
        quality = max(0.0, min(1.0, 0.45 * eligibility_rate + 0.35 * max(0.0, mean_gain) + 0.20 * (1.0 - rollback_rate)))
        return LearningQualityReport(
            event_count=len(events), eligible_count=len(eligible), eligibility_rate=eligibility_rate,
            mean_confidence_gain=mean_gain, proposal_count=len(proposals), approval_rate=approval_rate,
            rollback_rate=rollback_rate, quality_score=quality,
        )
