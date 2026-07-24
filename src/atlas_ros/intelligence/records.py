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
    CLAIM = "claim_record"
    ASSUMPTION = "assumption_record"
    INFERENCE_RULE = "inference_rule"
    INFERENCE_TRACE = "inference_trace"
    GOVERNANCE_POLICY = "governance_policy_record"
    POLICY_EVALUATION = "policy_evaluation_record"
    DECISION_GOVERNANCE = "decision_governance_record"


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


class ClaimType(StrEnum):
    FACT = "fact"
    INTERPRETATION = "interpretation"
    CONSTRAINT = "constraint"
    OUTCOME = "outcome"


class AssumptionStatus(StrEnum):
    VERIFIED = "verified"
    PARTIAL = "partial"
    UNVERIFIED = "unverified"
    REJECTED = "rejected"


class ClaimRecord(CanonicalRecord):
    KIND: ClassVar[RecordKind] = RecordKind.CLAIM

    kind: Literal[RecordKind.CLAIM] = RecordKind.CLAIM
    statement: str = Field(min_length=1)
    claim_type: ClaimType = ClaimType.FACT
    confidence: Probability
    validation_status: ValidationStatus
    evidence_refs: tuple[RecordRef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_claim_references(self) -> Self:
        if any(ref.kind is not RecordKind.EVIDENCE for ref in self.evidence_refs):
            raise ValueError("claim evidence_refs must reference evidence envelopes")
        return self


class AssumptionRecord(CanonicalRecord):
    KIND: ClassVar[RecordKind] = RecordKind.ASSUMPTION

    kind: Literal[RecordKind.ASSUMPTION] = RecordKind.ASSUMPTION
    assumption: str = Field(min_length=1)
    confidence: Probability
    status: AssumptionStatus = AssumptionStatus.UNVERIFIED
    evidence_refs: tuple[RecordRef, ...] = ()
    claim_refs: tuple[RecordRef, ...] = ()

    @model_validator(mode="after")
    def validate_assumption_references(self) -> Self:
        if any(ref.kind is not RecordKind.EVIDENCE for ref in self.evidence_refs):
            raise ValueError("assumption evidence_refs must reference evidence envelopes")
        if any(ref.kind is not RecordKind.CLAIM for ref in self.claim_refs):
            raise ValueError("assumption claim_refs must reference claim records")
        if self.status is AssumptionStatus.VERIFIED and not (self.evidence_refs or self.claim_refs):
            raise ValueError("verified assumptions require evidence or claim references")
        return self


class InferenceMethod(StrEnum):
    DEDUCTIVE = "deductive"
    INDUCTIVE = "inductive"
    ABDUCTIVE = "abductive"


class InferenceStep(BaseModel):
    model_config = ConfigDict(frozen=True)

    sequence: int = Field(ge=1)
    premise_ref: RecordRef
    description: str = Field(min_length=1)
    confidence: Probability
    validation_status: ValidationStatus


class InferenceRule(CanonicalRecord):
    KIND: ClassVar[RecordKind] = RecordKind.INFERENCE_RULE

    kind: Literal[RecordKind.INFERENCE_RULE] = RecordKind.INFERENCE_RULE
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    method: InferenceMethod
    minimum_premises: int = Field(default=1, ge=1)
    reliability: Probability
    active: bool = True


class InferenceTraceRecord(CanonicalRecord):
    KIND: ClassVar[RecordKind] = RecordKind.INFERENCE_TRACE

    kind: Literal[RecordKind.INFERENCE_TRACE] = RecordKind.INFERENCE_TRACE
    rule_ref: RecordRef
    premise_refs: tuple[RecordRef, ...] = Field(min_length=1)
    conclusion_ref: RecordRef
    steps: tuple[InferenceStep, ...] = Field(min_length=1)
    confidence: Probability
    validation_status: ValidationStatus
    valid: bool
    explanation: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_inference_references(self) -> Self:
        if self.rule_ref.kind is not RecordKind.INFERENCE_RULE:
            raise ValueError("rule_ref must reference an inference rule")
        if self.conclusion_ref.kind is not RecordKind.CLAIM:
            raise ValueError("conclusion_ref must reference a claim record")

        permitted = {
            RecordKind.CLAIM,
            RecordKind.ASSUMPTION,
            RecordKind.INFERENCE_TRACE,
        }
        if any(ref.kind not in permitted for ref in self.premise_refs):
            raise ValueError("premise_refs must reference claims, assumptions, or inference traces")

        if len(self.premise_refs) != len(set(self.premise_refs)):
            raise ValueError("inference premise references must be unique")

        sequences = tuple(step.sequence for step in self.steps)
        expected = tuple(range(1, len(self.steps) + 1))
        if sequences != expected:
            raise ValueError("inference step sequence must be contiguous")

        if tuple(step.premise_ref for step in self.steps) != self.premise_refs:
            raise ValueError("inference steps must correspond to premise_refs")

        if self.validation_status is ValidationStatus.REJECTED and self.valid:
            raise ValueError("rejected inference traces cannot be valid")

        return self


class DecisionDisposition(StrEnum):
    ALLOW = "allow"
    ABSTAIN = "abstain"
    ESCALATE = "escalate"
    REQUEST_EVIDENCE = "request_evidence"
    REQUEST_CLARIFICATION = "request_clarification"
    DENY = "deny"
    DEFER = "defer"


class PolicyEvaluationOutcome(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"


class GovernancePolicyRecord(CanonicalRecord):
    KIND: ClassVar[RecordKind] = RecordKind.GOVERNANCE_POLICY

    kind: Literal[RecordKind.GOVERNANCE_POLICY] = RecordKind.GOVERNANCE_POLICY
    policy_key: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    failure_disposition: DecisionDisposition
    priority: int = Field(default=100, ge=0)
    parameters: dict[str, str | int | float | bool] = Field(default_factory=dict)
    active: bool = True


class PolicyEvaluationRecord(CanonicalRecord):
    KIND: ClassVar[RecordKind] = RecordKind.POLICY_EVALUATION

    kind: Literal[RecordKind.POLICY_EVALUATION] = RecordKind.POLICY_EVALUATION
    policy_ref: RecordRef
    subject_ref: RecordRef
    outcome: PolicyEvaluationOutcome
    disposition: DecisionDisposition
    reason: str = Field(min_length=1)
    evidence_refs: tuple[RecordRef, ...] = ()
    confidence: Probability

    @model_validator(mode="after")
    def validate_policy_evaluation(self) -> Self:
        if self.policy_ref.kind is not RecordKind.GOVERNANCE_POLICY:
            raise ValueError("policy_ref must reference a governance policy")
        if self.subject_ref.kind not in {
            RecordKind.RECOMMENDATION,
            RecordKind.CONTEXT,
            RecordKind.DECISION,
            RecordKind.INFERENCE_TRACE,
        }:
            raise ValueError(
                "subject_ref must reference a recommendation, context, decision, or inference trace"
            )
        if any(ref.kind is not RecordKind.EVIDENCE for ref in self.evidence_refs):
            raise ValueError("policy evaluation evidence_refs must reference evidence envelopes")
        if self.outcome is PolicyEvaluationOutcome.PASS:
            if self.disposition is not DecisionDisposition.ALLOW:
                raise ValueError("passing policy evaluations must use ALLOW disposition")
        elif self.outcome is PolicyEvaluationOutcome.NOT_APPLICABLE:
            if self.disposition is not DecisionDisposition.ALLOW:
                raise ValueError("not-applicable policy evaluations must use ALLOW disposition")
        elif self.disposition is DecisionDisposition.ALLOW:
            raise ValueError("failed policy evaluations cannot use ALLOW disposition")

        required_links = {
            self.policy_ref,
            self.subject_ref,
            *self.evidence_refs,
        }
        if not required_links.issubset(set(self.links)):
            raise ValueError(
                "policy evaluation links must include policy, subject, and evidence references"
            )
        return self


class DecisionGovernanceRecord(CanonicalRecord):
    KIND: ClassVar[RecordKind] = RecordKind.DECISION_GOVERNANCE

    kind: Literal[RecordKind.DECISION_GOVERNANCE] = RecordKind.DECISION_GOVERNANCE
    context_ref: RecordRef
    recommendation_ref: RecordRef | None = None
    policy_evaluation_refs: tuple[RecordRef, ...] = Field(min_length=1)
    disposition: DecisionDisposition
    permitted: bool
    explanation: str = Field(min_length=1)
    evidence_refs: tuple[RecordRef, ...] = ()

    @model_validator(mode="after")
    def validate_decision_governance(self) -> Self:
        if self.context_ref.kind is not RecordKind.CONTEXT:
            raise ValueError("context_ref must reference a context snapshot")
        if (
            self.recommendation_ref is not None
            and self.recommendation_ref.kind is not RecordKind.RECOMMENDATION
        ):
            raise ValueError("recommendation_ref must reference a recommendation record")
        if any(ref.kind is not RecordKind.POLICY_EVALUATION for ref in self.policy_evaluation_refs):
            raise ValueError("policy_evaluation_refs must reference policy evaluation records")
        if len(self.policy_evaluation_refs) != len(set(self.policy_evaluation_refs)):
            raise ValueError("policy evaluation references must be unique")
        if any(ref.kind is not RecordKind.EVIDENCE for ref in self.evidence_refs):
            raise ValueError("governance evidence_refs must reference evidence envelopes")
        if self.permitted != (self.disposition is DecisionDisposition.ALLOW):
            raise ValueError("permitted must be true only for ALLOW disposition")

        direct_refs = {
            self.context_ref,
            *self.policy_evaluation_refs,
            *self.evidence_refs,
        }
        if self.recommendation_ref is not None:
            direct_refs.add(self.recommendation_ref)
        if not direct_refs.issubset(set(self.links)):
            raise ValueError("decision governance links must include all governed references")
        return self


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
        if (
            self.recommendation_ref
            and self.recommendation_ref.kind is not RecordKind.RECOMMENDATION
        ):
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
    | ClaimRecord
    | AssumptionRecord
    | InferenceRule
    | InferenceTraceRecord
    | GovernancePolicyRecord
    | PolicyEvaluationRecord
    | DecisionGovernanceRecord
)

_RECORD_TYPES: dict[RecordKind, type[CanonicalRecord]] = {
    RecordKind.EVIDENCE: EvidenceEnvelope,
    RecordKind.CONTEXT: ContextSnapshot,
    RecordKind.PREDICTION: PredictionRecord,
    RecordKind.RECOMMENDATION: RecommendationRecord,
    RecordKind.DECISION: DecisionRecord,
    RecordKind.LEARNING: LearningEvent,
    RecordKind.CLAIM: ClaimRecord,
    RecordKind.ASSUMPTION: AssumptionRecord,
    RecordKind.INFERENCE_RULE: InferenceRule,
    RecordKind.INFERENCE_TRACE: InferenceTraceRecord,
    RecordKind.GOVERNANCE_POLICY: GovernancePolicyRecord,
    RecordKind.POLICY_EVALUATION: PolicyEvaluationRecord,
    RecordKind.DECISION_GOVERNANCE: DecisionGovernanceRecord,
}


def parse_record(payload: dict[str, Any]) -> CanonicalRecordType:
    kind_value = payload.get("kind")
    if not isinstance(kind_value, str):
        raise ValueError("Record payload is missing a valid 'kind' field")

    kind = RecordKind(kind_value)
    return _RECORD_TYPES[kind].model_validate(payload)  # type: ignore[return-value]
