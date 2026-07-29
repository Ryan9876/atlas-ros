"""Deterministic continuous work-state intelligence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from atlas_ros.contracts.advisory_v1 import MissingDataIndicator
from atlas_ros.contracts.operational_awareness import (
    EffectiveWorkState,
    EvidenceConflictV1,
    FreshnessState,
    NormalizedOperationalRecordV1,
    OperationalSnapshotV1,
    WorkStateEstimateV1,
)
from atlas_ros.policy.operational_awareness import OperationalAwarenessPolicy

from ..common import confidence_for, freshness_for, record_evidence


@dataclass(frozen=True, slots=True)
class WorkStateIntelligence:
    policy: OperationalAwarenessPolicy

    def estimate_all(
        self,
        snapshot: OperationalSnapshotV1,
        *,
        evaluated_at: datetime | None = None,
    ) -> tuple[WorkStateEstimateV1, ...]:
        now = evaluated_at or datetime.fromisoformat(snapshot.generated_time)
        record_map = {
            item.record_ref.canonical_record_id: item for item in snapshot.normalized_records
        }
        conflicts_by_record = {
            record.record_ref.canonical_record_id: tuple(
                conflict
                for conflict in snapshot.contradictions
                if any(
                    observation.record_reference.canonical_record_id
                    == record.record_ref.canonical_record_id
                    for observation in conflict.conflicting_observations
                )
            )
            for record in snapshot.normalized_records
        }
        return tuple(
            self.estimate(
                record,
                record_map=record_map,
                conflicts=conflicts_by_record[record.record_ref.canonical_record_id],
                evaluated_at=now,
            )
            for record in snapshot.normalized_records
        )

    def estimate(
        self,
        record: NormalizedOperationalRecordV1,
        *,
        record_map: dict[str, NormalizedOperationalRecordV1],
        conflicts: tuple[EvidenceConflictV1, ...] = (),
        evaluated_at: datetime | None = None,
    ) -> WorkStateEstimateV1:
        now = evaluated_at or datetime.now(UTC)
        typed_conflicts = conflicts
        freshness = freshness_for(
            record,
            policy=self.policy,
            evaluated_at=now,
            contradicted=bool(typed_conflicts),
        )
        missing: list[MissingDataIndicator] = []
        open_children = tuple(
            child_id
            for child_id in record.child_ids
            if child_id in record_map
            and not (record_map[child_id].completed or record_map[child_id].cancelled)
        )
        if self.policy.completion.require_definition_of_done and not record.definition_of_done:
            missing.append(
                MissingDataIndicator(
                    field_name="definition_of_done",
                    reason="completion criteria are not defined",
                    material=True,
                )
            )
        state = self._determine_state(record, open_children, bool(typed_conflicts))
        if state == EffectiveWorkState.COMPLETED and missing:
            state = EffectiveWorkState.AWAITING_VALIDATION
        evidence = (
            record_evidence(
                record,
                field="observed_state",
                value=record.observed_state,
                freshness=freshness,
                observed_at=now,
            ),
            record_evidence(
                record,
                field="completion_evidence",
                value=record.completion_evidence,
                freshness=freshness,
                observed_at=now,
            ),
            record_evidence(
                record,
                field="blockers",
                value=record.blockers,
                freshness=freshness,
                observed_at=now,
            ),
        )
        confidence = confidence_for(
            policy=self.policy,
            freshness=freshness,
            missing=tuple(missing),
            contradiction_count=len(typed_conflicts),
            rationale="derived from authoritative normalized evidence and compiled policy",
        )
        recommendation: str | None = None
        if typed_conflicts:
            recommendation = "Resolve contradictory authoritative completion or state evidence."
        elif freshness.state in {FreshnessState.STALE, FreshnessState.UNVERIFIABLE}:
            recommendation = "Verify the current state with the authoritative record owner."
        elif state == EffectiveWorkState.AWAITING_VALIDATION:
            recommendation = "Verify all Definition of Done criteria and approval evidence."
        return WorkStateEstimateV1.create(
            record_reference=record.record_ref,
            effective_state=state,
            directly_observed_state=record.observed_state,
            confidence=confidence,
            freshness=freshness,
            evidence=evidence,
            conflicting_evidence=typed_conflicts,
            last_meaningful_update=record.updated_at,
            last_verified_time=record.updated_at,
            expected_next_transition=self._expected_transition(state),
            missing_information=tuple(missing),
            verification_recommendation=recommendation,
            downstream_work_affected=open_children,
        )

    def _determine_state(
        self,
        record: NormalizedOperationalRecordV1,
        open_children: tuple[str, ...],
        conflicted: bool,
    ) -> EffectiveWorkState:
        if record.cancelled:
            return EffectiveWorkState.CANCELLED
        if conflicted:
            return EffectiveWorkState.AWAITING_VALIDATION
        if record.blockers:
            return EffectiveWorkState.BLOCKED
        if (
            record.technically_complete
            and record.approval_required
            and not record.approval_received
        ):
            return EffectiveWorkState.AWAITING_VALIDATION
        completion_ready = (
            record.completed
            and (
                not self.policy.completion.require_completion_evidence
                or bool(record.completion_evidence)
            )
            and (not self.policy.completion.require_closed_children or not open_children)
            and (
                not self.policy.completion.require_approval_when_declared
                or not record.approval_required
                or record.approval_received
            )
        )
        if completion_ready:
            return EffectiveWorkState.COMPLETED
        if record.completed or record.technically_complete:
            return EffectiveWorkState.AWAITING_VALIDATION
        if record.received_evidence and record.delegated:
            return EffectiveWorkState.REVIEW
        if record.delegated:
            return EffectiveWorkState.DELEGATED
        mapped = self.policy.state_mappings.get(record.observed_state.strip().lower())
        if mapped is not None:
            return mapped
        if record.dependencies:
            return EffectiveWorkState.WAITING
        if record.definition_of_done:
            return EffectiveWorkState.READY
        return EffectiveWorkState.NOT_STARTED

    @staticmethod
    def _expected_transition(state: EffectiveWorkState) -> str | None:
        mapping = {
            EffectiveWorkState.NOT_STARTED: "ready",
            EffectiveWorkState.READY: "active",
            EffectiveWorkState.ACTIVE: "technically_complete",
            EffectiveWorkState.WAITING: "active_or_blocked",
            EffectiveWorkState.BLOCKED: "active_after_blocker_resolution",
            EffectiveWorkState.DELEGATED: "review_when_evidence_received",
            EffectiveWorkState.REVIEW: "approved_or_rework",
            EffectiveWorkState.AWAITING_VALIDATION: "completed_after_verification",
            EffectiveWorkState.AWAITING_DECISION: "active_after_decision",
            EffectiveWorkState.TECHNICALLY_COMPLETE: "awaiting_validation",
        }
        return mapping.get(state)
