from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import ContractKind, deterministic_digest
from .semantic_v1 import SemanticFidelityResultV1, SemanticRole


class ExecutionCandidateV3(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal[3] = 3
    candidate_id: str = Field(min_length=1, max_length=256)
    correlation_id: UUID
    source_management_reference: str = Field(min_length=1, max_length=500)
    title: str = Field(min_length=1, max_length=500)
    proposed_objective: str = Field(min_length=1, max_length=10_000)
    done_when: str = Field(min_length=1, max_length=10_000)
    owner: str = Field(default="", max_length=200)
    semantic_role: SemanticRole
    horizon: Literal["current", "next", "conditional", "future", "blocked"]
    primary_outcome_reference: str = Field(min_length=1, max_length=500)
    source_instruction_role: str = Field(min_length=1, max_length=100)
    semantic_provenance: tuple[str, ...] = ()
    execution_ready: bool = False
    trigger: str = Field(default="", max_length=2_000)
    candidate_digest: str = Field(min_length=64, max_length=64)

    def digest_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"candidate_digest"})

    def verify_digest(self) -> bool:
        return self.candidate_digest == deterministic_digest(self.digest_payload())


class ProjectionDecisionV3(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal[3] = 3
    candidate_id: str = Field(min_length=1, max_length=256)
    semantic_role: SemanticRole
    status: Literal[
        "project_parent",
        "project_subtask",
        "retain_in_management",
        "defer_future_horizon",
        "withhold_not_owned",
        "withhold_not_ready",
        "review_required",
    ]
    projected_object_type: Literal["none", "parent", "subtask"] = "none"
    sequence: int | None = Field(default=None, ge=1)
    primary_outcome_reference: str = Field(min_length=1, max_length=500)
    source_instruction_role: str = Field(min_length=1, max_length=100)
    advances_primary_outcome: bool
    rationale: str = Field(min_length=1, max_length=2_000)
    semantic_fidelity_conditions: tuple[str, ...] = ()
    review_required: bool = False
    decision_digest: str = Field(min_length=64, max_length=64)

    def digest_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"decision_digest"})

    def verify_digest(self) -> bool:
        return self.decision_digest == deterministic_digest(self.digest_payload())


class ExecutionStepV3(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    step_id: str = Field(min_length=1, max_length=256)
    title: str = Field(min_length=1, max_length=500)
    objective: str = Field(min_length=1, max_length=10_000)
    done_when: str = Field(min_length=1, max_length=10_000)
    sequence: int = Field(ge=1)
    source_candidate_id: str = Field(min_length=1, max_length=256)
    semantic_role: SemanticRole
    semantic_provenance: tuple[str, ...] = ()


class ExecutionPlanV3(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal[3] = 3
    contract_kind: ContractKind = ContractKind.EXECUTION_PLAN
    plan_id: str = Field(min_length=1, max_length=256)
    action_id: str = Field(min_length=1, max_length=256)
    correlation_id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source_component: Literal["planning.semantic_execution"] = "planning.semantic_execution"
    source_management_reference: str = Field(min_length=1, max_length=500)
    source_management_digest: str = Field(min_length=64, max_length=64)
    planner_policy_version: str = Field(min_length=1, max_length=100)
    parent_outcome: ExecutionStepV3 | None = None
    destination_intent: str = Field(min_length=1, max_length=200)
    projected_steps: tuple[ExecutionStepV3, ...] = ()
    projection_decisions: tuple[ProjectionDecisionV3, ...]
    deferred_candidates: tuple[str, ...] = ()
    retained_management_items: tuple[str, ...] = ()
    semantic_fidelity: SemanticFidelityResultV1
    human_decision_requirements: tuple[str, ...] = ()
    authorized: Literal[False] = False
    candidate_set_digest: str = Field(min_length=64, max_length=64)
    plan_digest: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_plan(self) -> ExecutionPlanV3:
        sequence = [step.sequence for step in self.projected_steps]
        if sequence != list(range(1, len(sequence) + 1)):
            raise ValueError("execution steps must use contiguous one-based sequence")
        if not self.semantic_fidelity.passed and (self.parent_outcome or self.projected_steps):
            raise ValueError("semantic-fidelity failures cannot project execution objects")
        if not all(decision.verify_digest() for decision in self.projection_decisions):
            raise ValueError("projection decision digest verification failed")
        return self

    def digest_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"created_at", "plan_digest"})

    def verify_digest(self) -> bool:
        return self.plan_digest == deterministic_digest(self.digest_payload())
