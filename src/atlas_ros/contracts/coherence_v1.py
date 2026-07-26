from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import deterministic_digest


ConfidenceDimensionName = Literal[
    "intent_partition",
    "planning_model",
    "classification",
    "responsibility_resolution",
    "routing",
    "semantic_fidelity",
]


class BenchmarkMode(StrEnum):
    PROVIDER_FREE = "provider_free"
    SHADOW_ORCHESTRATION = "shadow_orchestration"
    ATTENDED_PROVIDER_CANARY = "attended_provider_canary"


class ConfidenceDimensionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal[1] = 1
    dimension: ConfidenceDimensionName
    subject: str = Field(min_length=1, max_length=500)
    score: float = Field(ge=0, le=1)
    evidence_basis: tuple[str, ...] = ()
    affects_execution_eligibility: bool
    requires_attended_review: bool
    relationship: tuple[str, ...] = ()


class CoherenceConditionResultV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    condition: str = Field(min_length=1, max_length=100)
    passed: bool
    material: bool
    reason_code: str = Field(min_length=1, max_length=100)
    detail: str = Field(default="", max_length=2_000)


class ReasoningCoherenceResultV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal[1] = 1
    conditions: tuple[CoherenceConditionResultV1, ...]
    passed: bool
    review_required: bool
    material_contradictions: tuple[str, ...] = ()
    non_blocking_findings: tuple[str, ...] = ()
    user_facing_summary: str = Field(min_length=1, max_length=3_000)
    result_digest: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_result(self) -> ReasoningCoherenceResultV1:
        expected = all(item.passed for item in self.conditions if item.material)
        if self.passed != expected:
            raise ValueError("coherence summary does not match material conditions")
        if self.review_required == self.passed:
            raise ValueError("coherence review is required exactly when material coherence fails")
        return self

    def digest_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"result_digest"})

    def verify_digest(self) -> bool:
        return self.result_digest == deterministic_digest(self.digest_payload())


class BenchmarkExecutionPolicyV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal[1] = 1
    mode: BenchmarkMode = BenchmarkMode.PROVIDER_FREE
    provider_writes_allowed: bool = False
    explicit_authorization_required: bool = False
    object_budget: int = Field(default=0, ge=0)
    provider_readback_required: bool = False
    reconciliation_required: bool = False

    @classmethod
    def for_mode(
        cls, mode: BenchmarkMode, *, object_budget: int = 0
    ) -> BenchmarkExecutionPolicyV1:
        if mode is BenchmarkMode.ATTENDED_PROVIDER_CANARY:
            if object_budget < 1:
                raise ValueError("attended provider canary requires an explicit object budget")
            return cls(
                mode=mode,
                provider_writes_allowed=True,
                explicit_authorization_required=True,
                object_budget=object_budget,
                provider_readback_required=True,
                reconciliation_required=True,
            )
        return cls(mode=mode)


class HorizonPromotionProposalV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal[1] = 1
    current_stage: str = Field(min_length=1, max_length=100)
    proposed_stage: str = Field(min_length=1, max_length=100)
    proposed_action: str = Field(min_length=1, max_length=500)
    eligible: bool
    attended_authorization_required: bool = True
    provider_writes: Literal[0] = 0
    rationale: str = Field(min_length=1, max_length=2_000)
