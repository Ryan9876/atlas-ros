"""Shared deterministic operational-awareness helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from atlas_ros.contracts.advisory_v1 import (
    ConfidenceAssessment,
    MissingDataIndicator,
    ProvenanceRecord,
    ValueOrigin,
)
from atlas_ros.contracts.operational_awareness import (
    AuthorityLevel,
    FreshnessAssessmentV1,
    FreshnessState,
    NormalizedOperationalRecordV1,
    OperationalEvidenceV1,
)
from atlas_ros.policy.operational_awareness import OperationalAwarenessPolicy


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def freshness_for(
    record: NormalizedOperationalRecordV1,
    *,
    policy: OperationalAwarenessPolicy,
    evaluated_at: datetime,
    contradicted: bool = False,
) -> FreshnessAssessmentV1:
    source_time = parse_time(record.updated_at)
    if contradicted:
        state = FreshnessState.CONTRADICTED
        rationale = "material evidence is contradictory"
        age_days: float | None = None
    elif source_time is None:
        state = FreshnessState.UNVERIFIABLE
        rationale = "the authoritative source time is unavailable"
        age_days = None
    else:
        age_days = max(0.0, (evaluated_at - source_time).total_seconds() / 86_400)
        if age_days <= policy.freshness_days.current:
            state = FreshnessState.CURRENT
            rationale = "evidence is within the current threshold"
        elif age_days <= policy.freshness_days.aging:
            state = FreshnessState.AGING
            rationale = "evidence is aging but not stale"
        else:
            state = FreshnessState.STALE
            rationale = "evidence exceeds the stale threshold"
    return FreshnessAssessmentV1.create(
        state=state,
        evaluated_at=evaluated_at.isoformat(),
        source_time=record.updated_at,
        age_days=age_days,
        threshold_days=float(policy.freshness_days.stale),
        rationale=rationale,
    )


def record_evidence(
    record: NormalizedOperationalRecordV1,
    *,
    field: str,
    value: Any,
    freshness: FreshnessAssessmentV1,
    observed_at: datetime,
) -> OperationalEvidenceV1:
    return OperationalEvidenceV1.create(
        evidence_id=f"{record.record_ref.canonical_record_id}:{field}",
        record_reference=record.record_ref,
        observed_fact=field,
        observed_value=value,
        observation_time=observed_at.isoformat(),
        source_time=record.updated_at,
        value_origin=ValueOrigin.OBSERVED,
        authority_level=(
            AuthorityLevel.EXECUTION
            if record.record_ref.authoritative_system.value == "todoist"
            else AuthorityLevel.AUTHORITATIVE_DYNAMIC
        ),
        freshness=freshness,
        provenance=(
            ProvenanceRecord(
                source_ref=(
                    record.record_ref.canonical_url
                    or record.record_ref.canonical_record_id
                ),
                origin=ValueOrigin.OBSERVED,
                observed_at=observed_at.isoformat(),
            ),
        ),
        redaction_state="not_redacted",
    )


def confidence_for(
    *,
    policy: OperationalAwarenessPolicy,
    freshness: FreshnessAssessmentV1,
    missing: tuple[MissingDataIndicator, ...] = (),
    contradiction_count: int = 0,
    rationale: str,
) -> ConfidenceAssessment:
    score = policy.confidence.base
    score -= sum(
        policy.confidence.missing_material_penalty
        if item.material
        else policy.confidence.unverified_penalty
        for item in missing
    )
    score -= contradiction_count * policy.confidence.contradiction_penalty
    if freshness.state == FreshnessState.STALE:
        score -= policy.confidence.stale_penalty
    elif freshness.state == FreshnessState.UNVERIFIABLE:
        score -= policy.confidence.unverified_penalty
    elif freshness.state == FreshnessState.CONTRADICTED:
        score -= policy.confidence.contradiction_penalty
    return ConfidenceAssessment(
        score=max(0.0, min(1.0, score)),
        rationale=rationale,
        missing_data=missing,
    )
