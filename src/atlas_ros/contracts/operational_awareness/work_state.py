"""Continuous work-state intelligence contracts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from atlas_ros.contracts.advisory_v1 import ConfidenceAssessment, MissingDataIndicator
from atlas_ros.contracts.digests import sha256_digest

from .base import DigestBoundModel, EffectiveWorkState
from .evidence import EvidenceConflictV1, FreshnessAssessmentV1, OperationalEvidenceV1
from .records import OperationalRecordRefV1


class WorkStateEstimateV1(DigestBoundModel):
    digest_field = "estimate_digest"

    contract_id: Literal["atlas.work-state-estimate"] = "atlas.work-state-estimate"
    schema_version: Literal["1.0"] = "1.0"
    record_reference: OperationalRecordRefV1
    effective_state: EffectiveWorkState
    directly_observed_state: str
    confidence: ConfidenceAssessment
    freshness: FreshnessAssessmentV1
    evidence: tuple[OperationalEvidenceV1, ...]
    conflicting_evidence: tuple[EvidenceConflictV1, ...] = ()
    last_meaningful_update: str | None = None
    last_verified_time: str | None = None
    expected_next_transition: str | None = None
    missing_information: tuple[MissingDataIndicator, ...] = ()
    verification_recommendation: str | None = None
    downstream_work_affected: tuple[str, ...] = ()
    estimate_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> WorkStateEstimateV1:
        return cls(estimate_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_estimate(self) -> WorkStateEstimateV1:
        if not self.evidence:
            raise ValueError("work-state estimate requires supporting evidence")
        if self.conflicting_evidence and self.effective_state == EffectiveWorkState.COMPLETED:
            raise ValueError("materially conflicted work cannot be concluded completed")
        if not self.verify_digest():
            raise ValueError("work-state estimate digest mismatch")
        return self
