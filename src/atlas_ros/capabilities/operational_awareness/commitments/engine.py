"""Delegation and commitment intelligence without silent writes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from atlas_ros.contracts.advisory_v1 import (
    ConfidenceAssessment,
    ProvenanceRecord,
    ValueOrigin,
)
from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.contracts.operational_awareness import (
    AcceptanceState,
    CommitmentAssessmentV1,
    CommitmentCandidateV1,
    CommitmentType,
    EffectiveWorkState,
    FollowUpDisposition,
    FreshnessState,
    NormalizedOperationalRecordV1,
    OperationalSnapshotV1,
    WorkStateEstimateV1,
)
from atlas_ros.policy.operational_awareness import OperationalAwarenessPolicy

from ..common import confidence_for, freshness_for, parse_time, record_evidence


@dataclass(frozen=True, slots=True)
class CommitmentIntelligence:
    policy: OperationalAwarenessPolicy

    def assess_all(
        self,
        snapshot: OperationalSnapshotV1,
        estimates: tuple[WorkStateEstimateV1, ...],
        *,
        evaluated_at: datetime | None = None,
    ) -> tuple[CommitmentAssessmentV1, ...]:
        now = evaluated_at or datetime.fromisoformat(snapshot.generated_time)
        estimates_by_id = {
            item.record_reference.canonical_record_id: item for item in estimates
        }
        results: list[CommitmentAssessmentV1] = []
        for record in snapshot.normalized_records:
            commitment_type = self._commitment_type(record)
            if commitment_type is None:
                continue
            results.append(
                self.assess(
                    record,
                    commitment_type=commitment_type,
                    estimate=estimates_by_id[record.record_ref.canonical_record_id],
                    evaluated_at=now,
                )
            )
        return tuple(results)

    def candidate_from_text(
        self,
        text: str,
        *,
        source_ref: str,
        observed_at: datetime | None = None,
    ) -> CommitmentCandidateV1:
        now = observed_at or datetime.now(UTC)
        lowered = text.lower()
        explicit = any(token in lowered for token in ("i will", "i'll", "please provide", "agreed"))
        candidate_type = (
            CommitmentType.RYAN_OWNED
            if "i will" in lowered or "i'll" in lowered
            else CommitmentType.UNCONFIRMED_CONVERSATIONAL
        )
        ambiguity = () if explicit else ("language does not prove acceptance or obligation",)
        return CommitmentCandidateV1.create(
            candidate_id=(
                "commitment-candidate:"
                f"{sha256_digest({'source_ref': source_ref, 'text': text})[:24]}"
            ),
            original_source=text,
            proposed_commitment_type=candidate_type,
            obligated_party="Ryan" if candidate_type == CommitmentType.RYAN_OWNED else None,
            accountable_party="Ryan" if candidate_type == CommitmentType.RYAN_OWNED else None,
            requested_outcome=text.strip(),
            proposed_due_date=None,
            proposed_checkpoint=None,
            confidence=ConfidenceAssessment(
                score=0.9 if explicit else 0.4,
                rationale=(
                    "explicit commitment language detected"
                    if explicit
                    else "ambiguous language retained as a candidate"
                ),
            ),
            ambiguity=ambiguity,
            provenance=(
                ProvenanceRecord(
                    source_ref=source_ref,
                    origin=ValueOrigin.OBSERVED,
                    observed_at=now.isoformat(),
                ),
            ),
        )

    def assess(
        self,
        record: NormalizedOperationalRecordV1,
        *,
        commitment_type: CommitmentType,
        estimate: WorkStateEstimateV1,
        evaluated_at: datetime,
    ) -> CommitmentAssessmentV1:
        freshness = freshness_for(record, policy=self.policy, evaluated_at=evaluated_at)
        checkpoint_time = parse_time(record.checkpoint)
        now = evaluated_at.astimezone(UTC)
        overdue = checkpoint_time is not None and checkpoint_time < now
        if estimate.effective_state == EffectiveWorkState.COMPLETED:
            follow_up = FollowUpDisposition.COMPLETED
        elif record.acceptance_status == AcceptanceState.UNCONFIRMED:
            follow_up = FollowUpDisposition.VERIFICATION
        elif overdue:
            follow_up = FollowUpDisposition.DEADLINE_AT_RISK
        elif record.checkpoint and freshness.state in {FreshnessState.AGING, FreshnessState.STALE}:
            follow_up = FollowUpDisposition.APPROPRIATE
        elif record.checkpoint:
            follow_up = FollowUpDisposition.PREMATURE
        else:
            follow_up = FollowUpDisposition.NONE
        evidence = tuple(
            record_evidence(
                record,
                field="received_evidence",
                value=value,
                freshness=freshness,
                observed_at=evaluated_at,
            )
            for value in record.received_evidence
        )
        confidence = confidence_for(
            policy=self.policy,
            freshness=freshness,
            rationale="commitment state synthesized from authoritative management records",
        )
        return CommitmentAssessmentV1.create(
            commitment_id=f"commitment:{record.record_ref.canonical_record_id}",
            commitment_type=commitment_type,
            responsible_party=record.responsible_party,
            accountable_party=record.accountable_party or record.owner,
            acceptance_status=record.acceptance_status,
            delivery_status=estimate.effective_state,
            expected_outcome=record.expected_outcome or record.title,
            completion_criteria=record.definition_of_done,
            assigned_date=str(record.extra.get("assigned_date") or "") or None,
            delivery_due_date=record.due_date,
            next_checkpoint=record.checkpoint,
            last_meaningful_update=record.updated_at,
            last_verified_time=record.updated_at,
            expected_evidence=tuple(
                str(item) for item in record.extra.get("expected_evidence", ())
            ),
            received_evidence=evidence,
            active_blockers=record.blockers,
            follow_up_disposition=follow_up,
            escalation_disposition=(
                "consider escalation after verification"
                if follow_up == FollowUpDisposition.DEADLINE_AT_RISK
                else None
            ),
            confidence=confidence,
            freshness=freshness,
            related_action_record=(
                record.record_ref
                if record.record_ref.record_type.value == "action_record"
                else None
            ),
            related_portfolio_project=None,
            provenance=(
                ProvenanceRecord(
                    source_ref=record.record_ref.canonical_url
                    or record.record_ref.canonical_record_id,
                    origin=ValueOrigin.OBSERVED,
                    observed_at=evaluated_at.isoformat(),
                ),
            ),
        )

    @staticmethod
    def _commitment_type(record: NormalizedOperationalRecordV1) -> CommitmentType | None:
        explicit = str(record.extra.get("commitment_type") or "")
        if explicit:
            try:
                return CommitmentType(explicit)
            except ValueError:
                return CommitmentType.UNCONFIRMED_CONVERSATIONAL
        if record.delegated:
            return CommitmentType.DELEGATED_OUTCOME
        if record.responsible_party == "Ryan":
            return CommitmentType.RYAN_OWNED
        if record.dependencies:
            return CommitmentType.WAITING_DEPENDENCY
        return None
