from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import deterministic_digest


class ConfidenceSubject(StrEnum):
    INTENT_PARTITION = "intent_partition_confidence"
    PLANNING_MODEL = "planning_model_confidence"
    CLASSIFICATION = "classification_confidence"
    RESPONSIBILITY_RESOLUTION = "responsibility_resolution_confidence"
    ROUTING = "routing_confidence"
    SEMANTIC_FIDELITY = "semantic_fidelity_confidence"


class ConfidenceDimensionV1(BaseModel):
    """One independently governed confidence dimension."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    subject: ConfidenceSubject
    confidence: float = Field(ge=0, le=1)
    evidence_basis: tuple[str, ...] = ()
    affects_execution_eligibility: bool
    requires_attended_review: bool
    related_dimensions: tuple[ConfidenceSubject, ...] = ()
    material: bool = True

    @model_validator(mode="after")
    def validate_review_effect(self) -> ConfidenceDimensionV1:
        if self.requires_attended_review and not self.affects_execution_eligibility:
            raise ValueError("an attended-review confidence dimension must affect eligibility")
        return self


class CoherenceConditionResultV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    condition: str = Field(min_length=1, max_length=100)
    passed: bool
    reason_code: str = Field(min_length=1, max_length=100)
    detail: str = Field(default="", max_length=2_000)
    material: bool = True


class ReasoningCoherenceResultV1(BaseModel):
    """Provider-independent evidence that one reasoning conclusion is internally coherent."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal[1] = 1
    primary_business_outcome: str = Field(min_length=1, max_length=10_000)
    planning_model_id: str = Field(min_length=1, max_length=200)
    confidence_dimensions: tuple[ConfidenceDimensionV1, ...]
    conditions: tuple[CoherenceConditionResultV1, ...]
    passed: bool
    review_required: bool
    resolved_classification: str = Field(min_length=1, max_length=100)
    resolved_destination: str = Field(min_length=1, max_length=200)
    resolved_responsibility_domain: str = Field(min_length=1, max_length=100)
    resolved_workstream: str = Field(min_length=1, max_length=200)
    low_confidence_dimensions: tuple[ConfidenceSubject, ...] = ()
    explanation: str = Field(min_length=1, max_length=4_000)
    provider_writes: Literal[0] = 0
    result_digest: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_summary(self) -> ReasoningCoherenceResultV1:
        material_pass = all(condition.passed for condition in self.conditions if condition.material)
        if self.passed != material_pass:
            raise ValueError("reasoning coherence summary does not match material conditions")
        if self.review_required == self.passed:
            raise ValueError("coherence review is required exactly when a material condition fails")
        dimension_subjects = [dimension.subject for dimension in self.confidence_dimensions]
        if len(dimension_subjects) != len(set(dimension_subjects)):
            raise ValueError("confidence dimensions must have unique subjects")
        return self

    def digest_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"result_digest"})

    def verify_digest(self) -> bool:
        return self.result_digest == deterministic_digest(self.digest_payload())


class BenchmarkMode(StrEnum):
    PROVIDER_FREE_SEMANTIC = "provider_free_semantic"
    SHADOW_ORCHESTRATION = "shadow_orchestration"
    ATTENDED_PROVIDER_CANARY = "attended_provider_canary"


class BenchmarkExecutionPolicyV1(BaseModel):
    """Governed benchmark lifecycle policy with provider-free execution as the default."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal[1] = 1
    mode: BenchmarkMode = BenchmarkMode.PROVIDER_FREE_SEMANTIC
    provider_writes_allowed: bool = False
    exact_object_budget: int = Field(default=0, ge=0)
    explicit_authorization_required: bool = False
    provider_readback_required: bool = False
    reconciliation_required: bool = False
    record_strategy: Literal["review_record", "operational_record"] = "review_record"
    policy_digest: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_mode(self) -> BenchmarkExecutionPolicyV1:
        if self.mode in {
            BenchmarkMode.PROVIDER_FREE_SEMANTIC,
            BenchmarkMode.SHADOW_ORCHESTRATION,
        }:
            if self.provider_writes_allowed or self.exact_object_budget:
                raise ValueError("provider-free and shadow benchmarks cannot write provider objects")
            if self.explicit_authorization_required:
                raise ValueError("zero-write benchmark modes do not require provider authorization")
        else:
            if not self.provider_writes_allowed or self.exact_object_budget <= 0:
                raise ValueError("attended canaries require a positive exact object budget")
            if not (
                self.explicit_authorization_required
                and self.provider_readback_required
                and self.reconciliation_required
            ):
                raise ValueError("attended canaries require authorization, readback, and reconciliation")
        return self

    def digest_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"policy_digest"})

    def verify_digest(self) -> bool:
        return self.policy_digest == deterministic_digest(self.digest_payload())


class HorizonEvidenceV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scope_and_success_approved: bool = False
    technical_owner_confirmed: bool = False
    low_risk_targets_confirmed: bool = False
    controls_and_rollback_approved: bool = False
    technical_execution_complete: bool = False
    evidence_complete: bool = False
    go_no_go_decision: Literal["go", "no_go", "pending"] = "pending"


class HorizonPromotionProposalV1(BaseModel):
    """Provider-free proposal for the next attended horizon transition."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal[1] = 1
    current_checkpoint: str = Field(min_length=1, max_length=500)
    proposed_transition: Literal[
        "retain_scope_checkpoint",
        "retain_owner_and_targets_checkpoint",
        "retain_controls_checkpoint",
        "authorize_delegated_execution",
        "collect_execution_evidence",
        "propose_go_no_go_review",
        "retain_expansion_for_separate_approval",
        "close_without_expansion",
    ]
    eligible: bool
    attended_authorization_required: Literal[True] = True
    provider_writes: Literal[0] = 0
    rationale: str = Field(min_length=1, max_length=2_000)
    retained_future_outcomes: tuple[str, ...] = ()
    proposal_digest: str = Field(min_length=64, max_length=64)

    def digest_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"proposal_digest"})

    def verify_digest(self) -> bool:
        return self.proposal_digest == deterministic_digest(self.digest_payload())
