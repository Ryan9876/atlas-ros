"""Delegation and commitment intelligence contracts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from atlas_ros.contracts.advisory_v1 import ConfidenceAssessment, ProvenanceRecord

from .base import (
    AcceptanceState,
    CommitmentType,
    DigestBoundModel,
    EffectiveWorkState,
    FollowUpDisposition,
)
from .evidence import FreshnessAssessmentV1, OperationalEvidenceV1
from .records import OperationalRecordRefV1


class CommitmentCandidateV1(DigestBoundModel):
    digest_field = "candidate_digest"

    contract_id: Literal["atlas.commitment-candidate"] = "atlas.commitment-candidate"
    schema_version: Literal["1.0"] = "1.0"
    candidate_id: str = Field(min_length=1, max_length=512)
    original_source: str = Field(min_length=1, max_length=2_000)
    proposed_commitment_type: CommitmentType
    obligated_party: str | None = Field(default=None, max_length=300)
    accountable_party: str | None = Field(default=None, max_length=300)
    requested_outcome: str = Field(min_length=1, max_length=5_000)
    proposed_due_date: str | None = None
    proposed_checkpoint: str | None = None
    confidence: ConfidenceAssessment
    ambiguity: tuple[str, ...] = ()
    provenance: tuple[ProvenanceRecord, ...]
    candidate_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> CommitmentCandidateV1:
        return cls(candidate_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_candidate(self) -> CommitmentCandidateV1:
        if not self.provenance:
            raise ValueError("commitment candidate requires provenance")
        if not self.verify_digest():
            raise ValueError("commitment candidate digest mismatch")
        return self


class CommitmentAssessmentV1(DigestBoundModel):
    digest_field = "assessment_digest"

    contract_id: Literal["atlas.commitment-assessment"] = "atlas.commitment-assessment"
    schema_version: Literal["1.0"] = "1.0"
    commitment_id: str = Field(min_length=1, max_length=512)
    commitment_type: CommitmentType
    responsible_party: str | None = Field(default=None, max_length=300)
    accountable_party: str | None = Field(default=None, max_length=300)
    acceptance_status: AcceptanceState
    delivery_status: EffectiveWorkState
    expected_outcome: str = Field(min_length=1, max_length=5_000)
    completion_criteria: tuple[str, ...] = ()
    assigned_date: str | None = None
    delivery_due_date: str | None = None
    next_checkpoint: str | None = None
    last_meaningful_update: str | None = None
    last_verified_time: str | None = None
    expected_evidence: tuple[str, ...] = ()
    received_evidence: tuple[OperationalEvidenceV1, ...] = ()
    active_blockers: tuple[str, ...] = ()
    follow_up_disposition: FollowUpDisposition
    escalation_disposition: str | None = None
    confidence: ConfidenceAssessment
    freshness: FreshnessAssessmentV1
    related_action_record: OperationalRecordRefV1 | None = None
    related_portfolio_project: OperationalRecordRefV1 | None = None
    provenance: tuple[ProvenanceRecord, ...]
    assessment_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> CommitmentAssessmentV1:
        return cls(assessment_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_assessment(self) -> CommitmentAssessmentV1:
        if not self.provenance:
            raise ValueError("commitment assessment requires provenance")
        if (
            self.acceptance_status == AcceptanceState.UNCONFIRMED
            and self.delivery_status == EffectiveWorkState.COMPLETED
        ):
            raise ValueError("unconfirmed commitment cannot be concluded completed")
        if not self.verify_digest():
            raise ValueError("commitment assessment digest mismatch")
        return self
