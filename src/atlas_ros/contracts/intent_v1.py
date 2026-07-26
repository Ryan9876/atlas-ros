from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import deterministic_digest


class InstructionRole(StrEnum):
    PRIMARY_BUSINESS_OUTCOME = "primary_business_outcome"
    CURRENT_BUSINESS_ACTION = "current_business_action"
    DELEGATED_ACTION = "delegated_action"
    CONDITIONAL_ACTION = "conditional_action"
    EVALUATION_CONTEXT = "evaluation_context"
    AUDIT_REQUIREMENT = "audit_requirement"
    EXECUTION_CONSTRAINT = "execution_constraint"
    REFERENCE_CONTEXT = "reference_context"


class IntentPartitionV1(BaseModel):
    """Provider-independent separation of business intent from control-plane instructions."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal[1] = 1
    correlation_id: UUID = Field(default_factory=uuid4)
    primary_business_outcome: str = Field(default="", max_length=10_000)
    current_business_actions: tuple[str, ...] = ()
    delegated_actions: tuple[str, ...] = ()
    conditional_actions: tuple[str, ...] = ()
    evaluation_context: tuple[str, ...] = ()
    audit_requirements: tuple[str, ...] = ()
    execution_constraints: tuple[str, ...] = ()
    reference_context: tuple[str, ...] = ()
    source_clauses: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    confidence: float = Field(ge=0, le=1)
    ambiguities: tuple[str, ...] = ()
    requires_human_decision: bool = False
    partition_digest: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_partition(self) -> IntentPartitionV1:
        if self.requires_human_decision and not self.ambiguities:
            raise ValueError("human decision requires an intent-partition ambiguity")
        if not self.primary_business_outcome and not self.requires_human_decision:
            raise ValueError("an unambiguous intent partition requires a primary outcome")
        return self

    def digest_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"partition_digest"})

    def verify_digest(self) -> bool:
        return self.partition_digest == deterministic_digest(self.digest_payload())
