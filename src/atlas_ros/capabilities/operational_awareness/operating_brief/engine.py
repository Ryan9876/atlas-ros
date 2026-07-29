"""Deterministic exception-based operating brief generation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from atlas_ros.contracts.advisory_v1 import (
    ConfidenceAssessment,
    ProvenanceRecord,
    ValueOrigin,
)
from atlas_ros.contracts.operational_awareness import (
    BriefItemV1,
    CommitmentAssessmentV1,
    EffectiveWorkState,
    FollowUpDisposition,
    FreshnessState,
    MaterialChangeV1,
    Materiality,
    OperatingBriefV1,
    OperationalSnapshotV1,
    WorkStateEstimateV1,
)
from atlas_ros.policy.operational_awareness import OperationalAwarenessPolicy


@dataclass(frozen=True, slots=True)
class OperatingBriefService:
    policy: OperationalAwarenessPolicy

    def generate(
        self,
        current: OperationalSnapshotV1,
        estimates: tuple[WorkStateEstimateV1, ...],
        commitments: tuple[CommitmentAssessmentV1, ...],
        *,
        previous: OperationalSnapshotV1 | None = None,
        generated_at: datetime | None = None,
    ) -> OperatingBriefV1:
        now = generated_at or datetime.fromisoformat(current.generated_time)
        items: list[BriefItemV1] = []
        seen: set[str] = set()
        estimate_by_id = {
            item.record_reference.canonical_record_id: item for item in estimates
        }
        commitment_by_id = {
            item.commitment_id.removeprefix("commitment:"): item for item in commitments
        }
        records = sorted(
            current.normalized_records,
            key=lambda record: (
                record.priority,
                record.due_date or "9999-12-31",
                record.record_ref.canonical_record_id,
            ),
        )
        for record in records:
            record_id = record.record_ref.canonical_record_id
            estimate = estimate_by_id[record_id]
            candidate = self._item_for(record_id, record, estimate, commitment_by_id.get(record_id))
            if candidate is None or record_id in seen:
                continue
            items.append(candidate)
            seen.add(record_id)
        ranked = tuple(
            BriefItemV1.create(
                item_id=item.item_id,
                record_reference=item.record_reference,
                conclusion=item.conclusion,
                item_type=item.item_type,
                rank=index + 1,
                materiality=item.materiality,
                evidence_refs=item.evidence_refs,
                confidence=item.confidence,
            )
            for index, item in enumerate(sorted(items, key=self._rank_key))
        )
        budget = self.policy.brief.item_budget
        selected = ranked[:budget]
        overflow = max(0, len(ranked) - len(selected))
        head = selected[0] if selected else None
        remaining = selected[1:] if head is not None else selected
        changes = self._changes(previous, current, now)
        return OperatingBriefV1.create(
            highest_value_next_action=head,
            decisions_requiring_ryan=tuple(
                item for item in remaining if item.item_type == "decision"
            ),
            new_or_worsened_blockers=tuple(
                item for item in remaining if item.item_type == "blocker"
            ),
            delegated_work_requiring_follow_up=tuple(
                item for item in remaining if item.item_type == "delegated_follow_up"
            ),
            overdue_or_at_risk_commitments=tuple(
                item for item in remaining if item.item_type == "commitment_risk"
            ),
            stale_or_contradictory_work_state=tuple(
                item for item in remaining if item.item_type == "state_warning"
            ),
            material_completions=tuple(
                item for item in remaining if item.item_type == "completion"
            ),
            significant_changes=changes,
            safe_to_ignore_summary=(
                "Unchanged normal work was omitted."
                if selected
                else "No material exceptions were detected; unchanged work can be ignored."
            ),
            overflow_summary=f"{overflow} additional material item(s) summarized by count.",
            source_snapshot_references=tuple(
                item
                for item in (
                    (previous.snapshot_id if previous else None),
                    current.snapshot_id,
                )
                if item
            ),
        )

    def _item_for(
        self,
        record_id: str,
        record: object,
        estimate: WorkStateEstimateV1,
        commitment: CommitmentAssessmentV1 | None,
    ) -> BriefItemV1 | None:
        from atlas_ros.contracts.operational_awareness import NormalizedOperationalRecordV1

        if not isinstance(record, NormalizedOperationalRecordV1):
            return None
        item_type: str | None = None
        conclusion: str | None = None
        materiality = Materiality.MEDIUM
        if estimate.effective_state == EffectiveWorkState.AWAITING_DECISION:
            item_type = "decision"
            conclusion = f"Decision required for {record.title}."
            materiality = Materiality.HIGH
        elif estimate.effective_state == EffectiveWorkState.BLOCKED:
            item_type = "blocker"
            conclusion = f"{record.title} is blocked: {', '.join(record.blockers)}."
            materiality = Materiality.CRITICAL if record.priority == 1 else Materiality.HIGH
        elif commitment and commitment.follow_up_disposition in {
            FollowUpDisposition.APPROPRIATE,
            FollowUpDisposition.DEADLINE_AT_RISK,
            FollowUpDisposition.ESCALATION,
        }:
            item_type = (
                "delegated_follow_up"
                if commitment.commitment_type.value == "delegated_outcome"
                else "commitment_risk"
            )
            conclusion = f"Follow-up is required for {record.title}."
            materiality = Materiality.HIGH
        elif estimate.freshness.state in {
            FreshnessState.STALE,
            FreshnessState.CONTRADICTED,
            FreshnessState.UNVERIFIABLE,
        }:
            item_type = "state_warning"
            conclusion = (
                f"Verify {record.title}; its current state is "
                f"{estimate.freshness.state.value}."
            )
            materiality = Materiality.HIGH
        elif estimate.effective_state == EffectiveWorkState.COMPLETED:
            item_type = "completion"
            conclusion = f"{record.title} is materially complete."
            materiality = Materiality.MEDIUM
        if item_type is None or conclusion is None:
            return None
        evidence_refs = tuple(item.evidence_id for item in estimate.evidence)
        return BriefItemV1.create(
            item_id=f"brief-item:{record_id}:{item_type}",
            record_reference=record.record_ref,
            conclusion=conclusion,
            item_type=item_type,
            rank=1,
            materiality=materiality,
            evidence_refs=evidence_refs,
            confidence=estimate.confidence,
        )

    @staticmethod
    def _rank_key(item: BriefItemV1) -> tuple[int, int, str]:
        type_rank = {
            "decision": 1,
            "blocker": 1,
            "commitment_risk": 2,
            "delegated_follow_up": 2,
            "state_warning": 4,
            "completion": 5,
        }
        materiality_rank = {
            Materiality.CRITICAL: 0,
            Materiality.HIGH: 1,
            Materiality.MEDIUM: 2,
            Materiality.LOW: 3,
        }
        return (
            type_rank.get(item.item_type, 9),
            materiality_rank[item.materiality],
            item.record_reference.canonical_record_id,
        )

    @staticmethod
    def _changes(
        previous: OperationalSnapshotV1 | None,
        current: OperationalSnapshotV1,
        now: datetime,
    ) -> tuple[MaterialChangeV1, ...]:
        if previous is None:
            return ()
        old = {
            item.record_ref.canonical_record_id: item for item in previous.normalized_records
        }
        changes: list[MaterialChangeV1] = []
        for record in current.normalized_records:
            prior = old.get(record.record_ref.canonical_record_id)
            if prior is None:
                previous_value: object = None
                current_value: object = record.observed_state
            elif prior.record_digest == record.record_digest:
                continue
            else:
                previous_value = prior.observed_state
                current_value = record.observed_state
            changes.append(
                MaterialChangeV1.create(
                    record_reference=record.record_ref,
                    previous_value=previous_value,
                    current_value=current_value,
                    change_time=now.astimezone(UTC).isoformat(),
                    materiality=Materiality.HIGH if record.priority == 1 else Materiality.MEDIUM,
                    reason_it_matters="the effective work state or supporting evidence changed",
                    downstream_effect=(
                        "next-action projection may change" if record.child_ids else None
                    ),
                    confidence=ConfidenceAssessment(
                        score=1.0,
                        rationale="deterministic digest comparison",
                    ),
                    provenance=(
                        ProvenanceRecord(
                            source_ref=record.record_ref.canonical_url
                            or record.record_ref.canonical_record_id,
                            origin=ValueOrigin.OBSERVED,
                            observed_at=now.isoformat(),
                        ),
                    ),
                )
            )
        return tuple(changes)
