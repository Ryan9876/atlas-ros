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
