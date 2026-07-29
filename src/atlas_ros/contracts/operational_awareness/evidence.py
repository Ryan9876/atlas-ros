"""Evidence, freshness, and contradiction contracts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from atlas_ros.contracts.advisory_v1 import ProvenanceRecord, ValueOrigin
from atlas_ros.contracts.digests import sha256_digest

from .base import AuthorityLevel, DigestBoundModel, FreshnessState, Materiality
from .records import OperationalRecordRefV1


class FreshnessAssessmentV1(DigestBoundModel):
    digest_field = "assessment_digest"

    contract_id: Literal["atlas.freshness-assessment"] = "atlas.freshness-assessment"
    schema_version: Literal["1.0"] = "1.0"
    state: FreshnessState
    evaluated_at: str
    source_time: str | None = None
    age_days: float | None = Field(default=None, ge=0)
    threshold_days: float | None = Field(default=None, ge=0)
    rationale: str = Field(min_length=1, max_length=2_000)
    assessment_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> FreshnessAssessmentV1:
        return cls(assessment_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_digest(self) -> FreshnessAssessmentV1:
        if not self.verify_digest():
            raise ValueError("freshness assessment digest mismatch")
        return self


class OperationalEvidenceV1(DigestBoundModel):
    digest_field = "evidence_digest"

    contract_id: Literal["atlas.operational-evidence"] = "atlas.operational-evidence"
    schema_version: Literal["1.0"] = "1.0"
    evidence_id: str = Field(min_length=1, max_length=512)
    record_reference: OperationalRecordRefV1
    observed_fact: str = Field(min_length=1, max_length=500)
    observed_value: Any
    observation_time: str
    source_time: str | None = None
    value_origin: ValueOrigin
    authority_level: AuthorityLevel
    freshness: FreshnessAssessmentV1
    provenance: tuple[ProvenanceRecord, ...]
    redaction_state: str = Field(default="not_redacted", max_length=100)
    evidence_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> OperationalEvidenceV1:
        return cls(evidence_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_digest(self) -> OperationalEvidenceV1:
        if not self.provenance:
            raise ValueError("operational evidence requires provenance")
        if not self.verify_digest():
            raise ValueError("operational evidence digest mismatch")
        return self


class EvidenceConflictV1(DigestBoundModel):
    digest_field = "conflict_digest"

    contract_id: Literal["atlas.evidence-conflict"] = "atlas.evidence-conflict"
    schema_version: Literal["1.0"] = "1.0"
    conflicting_observations: tuple[OperationalEvidenceV1, ...] = Field(min_length=2)
    affected_field: str = Field(min_length=1, max_length=500)
    authority_comparison: str = Field(min_length=1, max_length=2_000)
    materiality: Materiality
    safe_resolution: str | None = Field(default=None, max_length=2_000)
    required_verification_or_decision: str = Field(min_length=1, max_length=2_000)
    conflict_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> EvidenceConflictV1:
        return cls(conflict_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_conflict(self) -> EvidenceConflictV1:
        if not self.verify_digest():
            raise ValueError("evidence conflict digest mismatch")
        return self
