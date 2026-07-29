"""Evidence-ranked execution context and resumption assembly."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from atlas_ros.contracts.advisory_v1 import ConfidenceAssessment
from atlas_ros.contracts.operational_awareness import (
    EffectiveWorkState,
    ExecutionContextPackV1,
    FreshnessState,
    OperationalSnapshotV1,
    ResumptionPointV1,
    WorkStateEstimateV1,
)
from atlas_ros.policy.operational_awareness import OperationalAwarenessPolicy


@dataclass(frozen=True, slots=True)
class ExecutionContextService:
    policy: OperationalAwarenessPolicy

    def build(
        self,
        snapshot: OperationalSnapshotV1,
        estimates: tuple[WorkStateEstimateV1, ...],
        *,
        record_id: str,
    ) -> ExecutionContextPackV1:
        records = {
            item.record_ref.canonical_record_id: item for item in snapshot.normalized_records
        }
        record = records.get(record_id)
        if record is None:
            raise KeyError(f"unknown operational record: {record_id}")
        estimate = next(
            item for item in estimates if item.record_reference.canonical_record_id == record_id
        )
        parent = records.get(record.record_ref.parent_record_id or "")
        children = tuple(records[item] for item in record.child_ids if item in records)
        relevant = [record]
        if parent is not None:
            relevant.append(parent)
        relevant.extend(children)
        evidence_refs = tuple(
            item.record_ref.canonical_url or item.record_ref.canonical_record_id
            for item in relevant[: self.policy.context.evidence_limit]
        )
        resumption = self.resume(snapshot, estimates, record_id=record_id)
        stale_warning = (
            f"Context is {estimate.freshness.state.value}; verify before consequential action."
            if estimate.freshness.state
            in {FreshnessState.STALE, FreshnessState.CONTRADICTED, FreshnessState.UNVERIFIABLE}
            else None
        )
        completed_work = tuple(child.title for child in children if child.completed)
        remaining_work = tuple(
            child.title for child in children if not child.completed and not child.cancelled
        )
        return ExecutionContextPackV1.create(
            target_work_item=record.record_ref,
            desired_outcome=record.expected_outcome or record.title,
            why_it_matters=str(
                record.extra.get("why_it_matters") or "Advances the persistent outcome."
            ),
            effective_work_state=estimate.effective_state,
            confidence=estimate.confidence,
            freshness=estimate.freshness,
            most_recent_material_change=record.updated_at,
            prior_decisions=tuple(str(item) for item in record.extra.get("prior_decisions", ())),
            completed_work=completed_work,
            remaining_work=remaining_work,
            current_blocker_or_dependency=record.blockers + record.dependencies,
            delegated_work=tuple(
                child.title for child in children if child.delegated
            ),
            stakeholders=tuple(
                item
                for item in (
                    record.owner,
                    record.responsible_party,
                    record.accountable_party,
                )
                if item
            ),
            relevant_records_and_evidence=evidence_refs,
            unresolved_questions=tuple(
                str(item) for item in record.extra.get("unresolved_questions", ())
            ),
            recommended_next_action=self._next_action(record, estimate.effective_state),
            resumption_point=resumption,
            stale_context_warning=stale_warning,
            redaction_warning=(
                "Some evidence was redacted; interpretation may be incomplete."
                if record.extra.get("redacted")
                else None
            ),
        )

    def resume(
        self,
        snapshot: OperationalSnapshotV1,
        estimates: tuple[WorkStateEstimateV1, ...],
        *,
        record_id: str,
    ) -> ResumptionPointV1:
        record = next(
            item
            for item in snapshot.normalized_records
            if item.record_ref.canonical_record_id == record_id
        )
        estimate = next(
            item for item in estimates if item.record_reference.canonical_record_id == record_id
        )
        stopped = record.extra.get("where_execution_stopped")
        evidence = tuple(str(item) for item in record.extra.get("resumption_evidence", ()))
        if stopped and evidence:
            return ResumptionPointV1.create(
                where_execution_stopped=str(stopped),
                last_confirmed_action=_optional_text(record.extra.get("last_confirmed_action")),
                conclusion_reached=_optional_text(record.extra.get("conclusion_reached")),
                unresolved_question=_optional_text(record.extra.get("unresolved_question")),
                next_concrete_action=_optional_text(record.extra.get("next_action"))
                or self._next_action(record, estimate.effective_state),
                source_evidence=evidence,
                confidence=estimate.confidence,
                generated_time=snapshot.generated_time,
                unknown_reason=None,
                minimum_verification_required=None,
            )
        return ResumptionPointV1.create(
            where_execution_stopped=None,
            last_confirmed_action=None,
            conclusion_reached=None,
            unresolved_question=None,
            next_concrete_action=None,
            source_evidence=(),
            confidence=ConfidenceAssessment(
                score=0.0,
                rationale="insufficient evidence to reconstruct the resumption point",
            ),
            generated_time=snapshot.generated_time,
            unknown_reason="resumption evidence is insufficient",
            minimum_verification_required=(
                "Review the latest authoritative update or execution receipt."
            ),
        )

    @staticmethod
    def _next_action(record: object, state: EffectiveWorkState) -> str | None:
        from atlas_ros.contracts.operational_awareness import NormalizedOperationalRecordV1

        if not isinstance(record, NormalizedOperationalRecordV1):
            return None
        explicit = _optional_text(record.extra.get("next_action"))
        if explicit:
            return explicit
        if state == EffectiveWorkState.BLOCKED:
            return "Resolve or escalate the named blocker."
        if state == EffectiveWorkState.DELEGATED:
            return "Review the agreed checkpoint and follow up when due."
        if state == EffectiveWorkState.REVIEW:
            return "Review the received evidence against the Definition of Done."
        if state == EffectiveWorkState.AWAITING_VALIDATION:
            return "Verify completion and approval evidence."
        if state == EffectiveWorkState.COMPLETED:
            return None
        return "Advance the next incomplete Ryan-owned checkpoint."


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
