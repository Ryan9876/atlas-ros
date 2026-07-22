from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any, ClassVar, Literal, Self
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

Probability = Annotated[float, Field(ge=0.0, le=1.0)]

class RecordKind(StrEnum):
    EVIDENCE = "evidence_envelope"
    CONTEXT = "context_snapshot"
    PREDICTION = "prediction_record"
    RECOMMENDATION = "recommendation_record"
    DECISION = "decision_record"
    LEARNING = "learning_event"


class LifecycleState(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    EXPIRED = "expired"
    RETRACTED = "retracted"


class AuthorityLevel(StrEnum):
    PRIMARY = "primary"
    AUTHORITATIVE_APPLICATION = "authoritative_application"
    GOVERNED_INTERNAL = "governed_internal"
    USER_PROVIDED = "user_provided"
    INFERRED = "inferred"
    UNVERIFIED = "unverified"


class ValidationStatus(StrEnum):
    VERIFIED = "verified"
    PARTIAL = "partial"
    UNVERIFIED = "unverified"
    REJECTED = "rejected"


class RecordRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    record_id: UUID
    kind: RecordKind
    integrity_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class ProvenanceHop(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str = Field(min_length=1)
    authority: AuthorityLevel
    observed_at: datetime
    locator: str = ""
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    validation_status: ValidationStatus = ValidationStatus.UNVERIFIED


class CanonicalRecord(BaseModel):
    """Immutable, content-addressed base contract for v5 intelligence records."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    KIND: ClassVar[RecordKind]
    CURRENT_SCHEMA_VERSION: ClassVar[str] = "1.0.0"

    record_id: UUID = Field(default_factory=uuid4)
    kind: RecordKind
    schema_version: str = Field(default="1.0.0", pattern=r"^\d+\.\d+\.\d+$")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE
    supersedes: RecordRef | None = None
    provenance: tuple[ProvenanceHop, ...] = ()
    links: tuple[RecordRef, ...] = ()
    integrity_hash: str = ""

    @model_validator(mode="after")
    def validate_identity_and_integrity(self) -> Self:
        if self.kind is not self.KIND:
            raise ValueError(f"kind must be {self.KIND.value}")
        expected = self.compute_integrity_hash()
        if self.integrity_hash and self.integrity_hash != expected:
            raise ValueError("integrity hash mismatch")
        if not self.integrity_hash:
            object.__setattr__(self, "integrity_hash", expected)
        return self

    def canonical_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"integrity_hash"})

    def canonical_json(self) -> str:
        return json.dumps(
            self.canonical_payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )

    def compute_integrity_hash(self) -> str:
        digest = hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()
        return f"sha256:{digest}"

    def verify_integrity(self) -> bool:
        return self.integrity_hash == self.compute_integrity_hash()

    def ref(self) -> RecordRef:
        return RecordRef(
            record_id=self.record_id,
            kind=self.kind,
            integrity_hash=self.integrity_hash,
        )


class EvidenceEnvelope(CanonicalRecord):
    KIND: ClassVar[RecordKind] = RecordKind.EVIDENCE

    kind: Literal[RecordKind.EVIDENCE] = RecordKind.EVIDENCE
    statement: str = Field(min_length=1)
    source_authority: AuthorityLevel
    confidence: Probability
    observed_at: datetime
    validation_status: ValidationStatus
    source_locator: str = ""
    source_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    citation: str = ""


class ContextSnapshot(CanonicalRecord):
    KIND: ClassVar[RecordKind] = RecordKind.CONTEXT

    kind: Literal[RecordKind.CONTEXT] = RecordKind.CONTEXT
    active_objective: str = Field(min_length=1)
    constraints: tuple[str, ...] = ()
    user_state: dict[str, str] = Field(default_factory=dict)
    environment: dict[str, str] = Field(default_factory=dict)
    available_authorities: tuple[str, ...] = ()
    decision_horizon: str = Field(min_length=1)
    session_lineage: tuple[str, ...] = ()
    evidence_refs: tuple[RecordRef, ...] = ()

    @model_validator(mode="after")
    def evidence_references_only(self) -> Self:
        if any(ref.kind is not RecordKind.EVIDENCE for ref in self.evidence_refs):
            raise ValueError("context evidence_refs must reference evidence envelopes")
        return self


class PredictionRecord(CanonicalRecord):
    KIND: ClassVar[RecordKind] = RecordKind.PREDICTION

    kind: Literal[RecordKind.PREDICTION] = RecordKind.PREDICTION
    prediction: str = Field(min_length=1)
    probability: Probability
    confidence_low: Probability
    confidence_high: Probability
    assumptions: tuple[str, ...] = ()
    expires_at: datetime
    evidence_refs: tuple[RecordRef, ...] = Field(min_length=1)
    actual_outcome: str | None = None
    calibration_error: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_prediction(self) -> Self:
        if not self.confidence_low <= self.probability <= self.confidence_high:
            raise ValueError("probability must fall inside confidence interval")
        if self.expires_at <= self.created_at:
            raise ValueError("prediction expiration must be after creation")
        if any(ref.kind is not RecordKind.EVIDENCE for ref in self.evidence_refs):
            raise ValueError("prediction evidence_refs must reference evidence envelopes")
        if (self.actual_outcome is None) != (self.calibration_error is None):
            raise ValueError("actual outcome and calibration error must be recorded together")
        return self


class RecommendationOption(BaseModel):
    model_config = ConfigDict(frozen=True)

    option: str = Field(min_length=1)
    expected_benefit: str = Field(min_length=1)
    expected_risk: str = Field(min_length=1)


class RecommendationRecord(CanonicalRecord):
    KIND: ClassVar[RecordKind] = RecordKind.RECOMMENDATION

    kind: Literal[RecordKind.RECOMMENDATION] = RecordKind.RECOMMENDATION
    recommendation: str = Field(min_length=1)
    alternatives: tuple[RecommendationOption, ...] = Field(min_length=1)
    rationale: str = Field(min_length=1)
    expected_benefit: str = Field(min_length=1)
    expected_risk: str = Field(min_length=1)
    confidence: Probability
    evidence_refs: tuple[RecordRef, ...] = Field(min_length=1)
    context_ref: RecordRef

    @model_validator(mode="after")
    def validate_recommendation_references(self) -> Self:
        if self.context_ref.kind is not RecordKind.CONTEXT:
            raise ValueError("context_ref must reference a context snapshot")
        if any(ref.kind is not RecordKind.EVIDENCE for ref in self.evidence_refs):
            raise ValueError("recommendation evidence_refs must reference evidence envelopes")
        return self


class DecisionRecord(CanonicalRecord):
    KIND: ClassVar[RecordKind] = RecordKind.DECISION

    kind: Literal[RecordKind.DECISION] = RecordKind.DECISION
    decision: str = Field(min_length=1)
    decision_owner: str = Field(min_length=1)
    selected_option: str = Field(min_length=1)
    expected_outcome: str = Field(min_length=1)
    success_metrics: tuple[str, ...] = Field(min_length=1)
    recommendation_ref: RecordRef | None = None
    evidence_refs: tuple[RecordRef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_decision_references(self) -> Self:
        if self.recommendation_ref and self.recommendation_ref.kind is not RecordKind.RECOMMENDATION:
            raise ValueError("recommendation_ref must reference a recommendation record")
        if any(ref.kind is not RecordKind.EVIDENCE for ref in self.evidence_refs):
            raise ValueError("decision evidence_refs must reference evidence envelopes")
        return self


class LearningEvent(CanonicalRecord):
    KIND: ClassVar[RecordKind] = RecordKind.LEARNING

    kind: Literal[RecordKind.LEARNING] = RecordKind.LEARNING
    observed_outcome: str = Field(min_length=1)
    prediction_ref: RecordRef | None = None
    decision_ref: RecordRef | None = None
    delta_analysis: str = Field(min_length=1)
    confidence_before: Probability
    confidence_after: Probability
    pattern_updates: tuple[str, ...] = ()
    model_version: str = Field(min_length=1)
    learning_eligible: bool
    eligibility_reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_learning_references(self) -> Self:
        if self.prediction_ref and self.prediction_ref.kind is not RecordKind.PREDICTION:
            raise ValueError("prediction_ref must reference a prediction record")
        if self.decision_ref and self.decision_ref.kind is not RecordKind.DECISION:
            raise ValueError("decision_ref must reference a decision record")
        if not self.prediction_ref and not self.decision_ref:
            raise ValueError("learning event must reference a prediction or decision")
        if not self.learning_eligible and self.pattern_updates:
            raise ValueError("ineligible learning events cannot update patterns")
        return self


CanonicalRecordType = (
    EvidenceEnvelope
    | ContextSnapshot
    | PredictionRecord
    | RecommendationRecord
    | DecisionRecord
    | LearningEvent
)

_RECORD_TYPES: dict[RecordKind, type[CanonicalRecord]] = {
    RecordKind.EVIDENCE: EvidenceEnvelope,
    RecordKind.CONTEXT: ContextSnapshot,
    RecordKind.PREDICTION: PredictionRecord,
    RecordKind.RECOMMENDATION: RecommendationRecord,
    RecordKind.DECISION: DecisionRecord,
    RecordKind.LEARNING: LearningEvent,
}


def parse_record(payload: dict[str, Any]) -> CanonicalRecordType:
    kind_value = payload.get("kind")
    if not isinstance(kind_value, str):
        raise ValueError("Record payload is missing a valid 'kind' field")

    kind = RecordKind(kind_value)
    return _RECORD_TYPES[kind].model_validate(payload)  # type: ignore[return-value]
