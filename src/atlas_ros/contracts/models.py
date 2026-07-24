from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ContractKind(StrEnum):
    CAPTURE = "capture"
    REASONING = "reasoning"
    KNOWLEDGE = "knowledge"
    MANAGEMENT = "management"
    EXECUTION_PLAN = "execution_plan"
    EXECUTION_RECEIPT = "execution_receipt"
    RECONCILIATION = "reconciliation"


class ContractEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal[1] = 1
    contract_kind: ContractKind
    correlation_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source_component: str = Field(min_length=1, max_length=200)


class CaptureEnvelope(ContractEnvelope):
    contract_kind: ContractKind = ContractKind.CAPTURE
    content: str = Field(min_length=1, max_length=100_000)
    source: str = Field(default="unknown", min_length=1, max_length=200)
    context: dict[str, Any] = Field(default_factory=dict)


class ReasoningPackage(ContractEnvelope):
    contract_kind: ContractKind = ContractKind.REASONING
    classification: str = Field(min_length=1, max_length=100)
    destination: str = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    rationale: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    requires_human_decision: bool = False


class EvidenceSignal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    category: str = Field(min_length=1, max_length=100)
    signal: str = Field(min_length=1, max_length=500)
    weight: float = Field(gt=0, le=10)
    source: str = Field(default="capture", min_length=1, max_length=100)


class ReasoningPackageV2(BaseModel):
    """Responsibility-aware reasoning contract with explicit v1 compatibility projection."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal[2] = 2
    contract_kind: ContractKind = ContractKind.REASONING
    correlation_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source_component: str = Field(min_length=1, max_length=200)
    classification: str = Field(min_length=1, max_length=100)
    destination: str = Field(min_length=1, max_length=200)
    responsibility_domain: str = Field(min_length=1, max_length=100)
    desired_outcome: str = Field(min_length=1, max_length=10_000)
    workstream: str = Field(min_length=1, max_length=200)
    activity_summary: str = Field(min_length=1, max_length=1_000)
    operating_context: str = Field(default="", max_length=100)
    operating_context_confidence: float = Field(default=0, ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    decisive_evidence: list[EvidenceSignal] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    challenge_status: str = Field(default="unchallenged", min_length=1, max_length=100)
    fallback_reason: str = Field(default="", max_length=1_000)
    requires_human_decision: bool = False

    @model_validator(mode="after")
    def validate_context_confidence(self) -> ReasoningPackageV2:
        if not self.operating_context and self.operating_context_confidence != 0:
            raise ValueError("operating-context confidence requires an operating context")
        if self.requires_human_decision and not (self.ambiguities or self.fallback_reason):
            raise ValueError("human-decision reasoning requires ambiguity or fallback evidence")
        return self

    def project_v1(self) -> ReasoningPackage:
        return ReasoningPackage(
            correlation_id=self.correlation_id,
            created_at=self.created_at,
            source_component=self.source_component,
            classification=self.classification,
            destination=self.destination,
            confidence=self.confidence,
            rationale=list(self.rationale),
            ambiguities=list(self.ambiguities),
            requires_human_decision=self.requires_human_decision,
        )


class ClassificationChallenge(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    challenge_id: str = Field(min_length=1, max_length=256)
    correlation_id: UUID
    status: Literal["accepted", "challenged", "corrected", "unresolved"]
    reason: str = Field(min_length=1, max_length=2_000)
    corrected_responsibility_domain: str = Field(default="", max_length=100)
    corrected_workstream: str = Field(default="", max_length=200)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_correction(self) -> ClassificationChallenge:
        if self.status == "corrected":
            if not self.corrected_responsibility_domain or not self.corrected_workstream:
                raise ValueError("corrected challenges require responsibility and workstream")
        elif self.corrected_responsibility_domain or self.corrected_workstream:
            raise ValueError("correction fields require corrected challenge status")
        return self


class ClassificationChallengeReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    challenge_id: str = Field(min_length=1, max_length=256)
    correlation_id: UUID
    applied: bool
    idempotent_replay: bool = False
    prior_status: str = Field(min_length=1, max_length=100)
    resulting_status: str = Field(min_length=1, max_length=100)
    evidence: dict[str, str] = Field(default_factory=dict)


class KnowledgePackage(ContractEnvelope):
    contract_kind: ContractKind = ContractKind.KNOWLEDGE
    module_ids: list[str] = Field(default_factory=list)
    facts: dict[str, Any] = Field(default_factory=dict)
    unresolved_questions: list[str] = Field(default_factory=list)


class ManagementPackage(ContractEnvelope):
    contract_kind: ContractKind = ContractKind.MANAGEMENT
    responsibility: str = Field(min_length=1, max_length=500)
    desired_outcome: str = Field(min_length=1, max_length=10_000)
    owner: str = ""
    workstream: str = ""
    decision_points: list[str] = Field(default_factory=list)


class ExecutionStep(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    step_id: str = Field(min_length=1, max_length=256)
    title: str = Field(min_length=1, max_length=500)
    done_when: str = Field(min_length=1, max_length=10_000)
    sequence: int = Field(ge=1)
    provider_metadata: dict[str, str] = Field(default_factory=dict)


class ExecutionPlan(ContractEnvelope):
    contract_kind: ContractKind = ContractKind.EXECUTION_PLAN
    action_id: str = Field(min_length=1, max_length=256)
    objective: str = Field(min_length=1, max_length=10_000)
    destination: str = Field(min_length=1, max_length=200)
    steps: list[ExecutionStep] = Field(default_factory=list)
    authorized: bool = False
    projection_explanation: str = ""
    non_projection_reasons: list[str] = Field(default_factory=list)
    review_required: bool = False

    @model_validator(mode="after")
    def validate_step_sequence(self) -> ExecutionPlan:
        sequence = [step.sequence for step in self.steps]
        if sequence != list(range(1, len(sequence) + 1)):
            raise ValueError("execution steps must use contiguous one-based sequence")
        if self.authorized:
            raise ValueError("execution planner cannot authorize provider writes")
        return self


class ExecutionReceipt(ContractEnvelope):
    contract_kind: ContractKind = ContractKind.EXECUTION_RECEIPT
    action_id: str = Field(min_length=1, max_length=256)
    provider: str = Field(min_length=1, max_length=100)
    provider_object_id: str = Field(min_length=1, max_length=500)
    applied: bool
    readback_verified: bool
    evidence: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_verified_apply(self) -> ExecutionReceipt:
        if self.applied and not self.readback_verified:
            raise ValueError("applied execution requires verified readback")
        return self


class ReconciliationResult(ContractEnvelope):
    contract_kind: ContractKind = ContractKind.RECONCILIATION
    object_id: str = Field(min_length=1, max_length=500)
    consistent: bool
    mismatches: list[str] = Field(default_factory=list)
    checkpoint_advanced: bool = False

    @model_validator(mode="after")
    def prevent_unsafe_checkpoint(self) -> ReconciliationResult:
        if self.checkpoint_advanced and (not self.consistent or self.mismatches):
            raise ValueError("checkpoint cannot advance with reconciliation mismatches")
        return self
