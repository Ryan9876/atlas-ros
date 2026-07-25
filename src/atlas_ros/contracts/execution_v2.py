from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import ContractKind, ExecutionPlan, ExecutionStep, deterministic_digest


class CandidateType(StrEnum):
    PARENT_OUTCOME = "parent_outcome"
    EXECUTABLE_ACTION = "independently_executable_action"
    CHECKLIST = "checklist_candidate"
    DECISION = "decision"
    APPROVAL = "approval"
    EVIDENCE = "evidence_requirement"
    GOVERNANCE = "governance_requirement"
    DEPENDENCY = "dependency"
    RISK_RESPONSE = "risk_response"
    CONDITIONAL_FUTURE = "conditional_future_action"
    REFERENCE = "reference_information"


class HorizonState(StrEnum):
    CURRENT = "current"
    NEXT = "next"
    CONDITIONAL = "conditional"
    FUTURE = "future"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    NOT_APPLICABLE = "not_applicable"


class CompletionState(StrEnum):
    OUTSTANDING = "outstanding"
    COMPLETE = "complete"
    RECURRING = "recurring"
    UNKNOWN = "unknown"


class ProjectionDecisionStatus(StrEnum):
    PROJECT_PARENT = "project_parent"
    PROJECT_SUBTASK = "project_subtask"
    RETAIN_IN_MANAGEMENT = "retain_in_management"
    DEFER_FUTURE_HORIZON = "defer_future_horizon"
    SUPPRESS_DUPLICATE = "suppress_duplicate"
    SUPPRESS_EXISTING = "suppress_existing_representation"
    WITHHOLD_NOT_OWNED = "withhold_not_owned"
    WITHHOLD_NOT_READY = "withhold_not_ready"
    WITHHOLD_UNRESOLVED = "withhold_unresolved"
    WITHHOLD_ALREADY_COMPLETE = "withhold_already_complete"
    WITHHOLD_NOT_EXECUTION_OBJECT = "withhold_not_execution_object"
    REVIEW_REQUIRED = "review_required"


class ProjectedObjectType(StrEnum):
    NONE = "none"
    PARENT = "parent"
    SUBTASK = "subtask"


class RepresentationMatchKind(StrEnum):
    EXACT_PARENT = "exact_existing_parent"
    EXACT_SUBTASK = "exact_existing_subtask"
    EQUIVALENT_OPEN = "equivalent_open_representation"
    EQUIVALENT_COMPLETED = "equivalent_completed_representation"
    RELATED = "related_but_non_equivalent"
    NONE = "no_match"
    AMBIGUOUS = "ambiguous_match_requiring_review"


class ProjectionTestResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    condition: str = Field(min_length=1, max_length=100)
    passed: bool
    reason_code: str = Field(min_length=1, max_length=100)
    detail: str = Field(default="", max_length=2_000)


class ExecutionCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal[2] = 2
    candidate_id: str = Field(min_length=1, max_length=256)
    correlation_id: UUID
    source_management_reference: str = Field(min_length=1, max_length=500)
    candidate_type: CandidateType
    title: str = Field(min_length=1, max_length=500)
    proposed_objective: str = Field(min_length=1, max_length=10_000)
    done_when: str = Field(default="", max_length=10_000)
    owner: str = Field(default="", max_length=200)
    responsibility_domain: str = Field(default="", max_length=200)
    workstream: str = Field(default="", max_length=200)
    source_section: str = Field(default="", max_length=200)
    source_item_id: str = Field(default="", max_length=256)
    source_provenance: tuple[str, ...] = ()
    dependency_references: tuple[str, ...] = ()
    trigger: str = Field(default="", max_length=2_000)
    trigger_satisfied: bool = False
    completion_state: CompletionState = CompletionState.OUTSTANDING
    execution_ready: bool = False
    earliest_executable_horizon: HorizonState = HorizonState.CURRENT
    existing_representation_hints: tuple[str, ...] = ()
    confidence: float = Field(default=1.0, ge=0, le=1)
    assumptions: tuple[str, ...] = ()
    ambiguities: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    can_remain_embedded: bool = False
    improves_execution_clarity: bool = True
    independently_executable: bool = True
    recurrence_required: bool = False
    candidate_digest: str = Field(min_length=64, max_length=64)

    def digest_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"candidate_digest"})

    def verify_digest(self) -> bool:
        return self.candidate_digest == deterministic_digest(self.digest_payload())


class ExistingRepresentation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    representation_id: str = Field(min_length=1, max_length=256)
    representation_type: Literal["parent", "subtask", "execution_object"]
    title: str = Field(min_length=1, max_length=500)
    objective: str = Field(default="", max_length=10_000)
    done_when: str = Field(default="", max_length=10_000)
    owner: str = Field(default="", max_length=200)
    workstream: str = Field(default="", max_length=200)
    state: Literal["open", "completed", "cancelled"]
    parent_reference: str = Field(default="", max_length=256)
    source_action_id: str = Field(default="", max_length=256)
    canonical_signature: str = Field(default="", max_length=64)
    last_verified_at: datetime
    provenance: tuple[str, ...] = ()


class ExistingRepresentationIndex(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    representations: tuple[ExistingRepresentation, ...] = ()
    verified_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source_digest: str = Field(default="", max_length=64)


class RepresentationMatch(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: str
    outcome: RepresentationMatchKind
    representation_ids: tuple[str, ...] = ()
    rationale: str = Field(default="", max_length=2_000)


class DuplicateFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: str
    matched_candidate_id: str = ""
    layer: str = Field(default="none", max_length=100)
    duplicate: bool = False
    ambiguous: bool = False
    rationale: str = Field(default="", max_length=2_000)


class ProjectionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: str
    status: ProjectionDecisionStatus
    projected_object_type: ProjectedObjectType = ProjectedObjectType.NONE
    parent_relationship: str = ""
    sequence: int | None = Field(default=None, ge=1)
    projection_rationale: str = ""
    non_projection_reasons: tuple[str, ...] = ()
    task_projection_test: tuple[ProjectionTestResult, ...]
    horizon: HorizonState
    duplicate_result: DuplicateFinding
    existing_representation_result: RepresentationMatch
    review_required: bool = False
    human_decision_required: bool = False
    evidence: tuple[str, ...] = ()
    policy_version: str = Field(min_length=1, max_length=100)
    decision_digest: str = Field(min_length=64, max_length=64)

    def digest_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"decision_digest"})

    def verify_digest(self) -> bool:
        return self.decision_digest == deterministic_digest(self.digest_payload())


class ExecutionStepV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    step_id: str = Field(min_length=1, max_length=256)
    title: str = Field(min_length=1, max_length=500)
    objective: str = Field(min_length=1, max_length=10_000)
    done_when: str = Field(min_length=1, max_length=10_000)
    sequence: int = Field(ge=1)
    dependencies: tuple[str, ...] = ()
    source_candidate_id: str = Field(min_length=1, max_length=256)
    source_provenance: tuple[str, ...] = ()
    horizon: HorizonState
    projection_rationale: str = Field(min_length=1, max_length=2_000)


class TaskBudgetResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_count: int = Field(ge=0)
    projected_subtask_count: int = Field(ge=0)
    default_limit: int = Field(default=3, ge=0)
    review_threshold: int = Field(default=5, ge=1)
    expanded_budget_used: bool = False
    rationale: str = ""
    compression_alternatives: tuple[str, ...] = ()
    multiple_parent_outcomes: bool = False


class ExecutionPlanV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal[2] = 2
    contract_kind: ContractKind = ContractKind.EXECUTION_PLAN
    plan_id: str = Field(min_length=1, max_length=256)
    action_id: str = Field(min_length=1, max_length=256)
    correlation_id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source_component: Literal["planning.execution"] = "planning.execution"
    source_management_reference: str = Field(min_length=1, max_length=500)
    source_management_digest: str = Field(min_length=64, max_length=64)
    planner_policy_version: str = Field(min_length=1, max_length=100)
    parent_outcome: ExecutionStepV2 | None = None
    destination_intent: str = Field(min_length=1, max_length=200)
    projected_steps: tuple[ExecutionStepV2, ...] = ()
    projection_decisions: tuple[ProjectionDecision, ...]
    deferred_candidates: tuple[str, ...] = ()
    retained_management_items: tuple[str, ...] = ()
    duplicate_findings: tuple[DuplicateFinding, ...] = ()
    existing_representation_findings: tuple[RepresentationMatch, ...] = ()
    horizon_summary: dict[str, int] = Field(default_factory=dict)
    task_budget: TaskBudgetResult
    decomposition_review_status: Literal["not_required", "required", "approved"] = (
        "not_required"
    )
    human_decision_requirements: tuple[str, ...] = ()
    projection_explanation: str = ""
    non_projection_explanations: tuple[str, ...] = ()
    candidate_set_digest: str = Field(min_length=64, max_length=64)
    authorized: Literal[False] = False
    plan_digest: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_plan(self) -> ExecutionPlanV2:
        sequence = [step.sequence for step in self.projected_steps]
        if sequence != list(range(1, len(sequence) + 1)):
            raise ValueError("execution steps must use contiguous one-based sequence")
        if self.decomposition_review_status == "required" and self.projected_steps:
            raise ValueError("review-gated plans cannot project ordinary subtasks")
        if not all(decision.verify_digest() for decision in self.projection_decisions):
            raise ValueError("projection decision digest verification failed")
        return self

    def digest_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"created_at", "plan_digest"})

    def verify_digest(self) -> bool:
        return self.plan_digest == deterministic_digest(self.digest_payload())

    def project_v1(self) -> ExecutionPlan:
        if self.decomposition_review_status == "required" or self.human_decision_requirements:
            raise ValueError("unsafe lossy Execution Plan V2 projection")
        parent = self.parent_outcome
        if parent is None:
            raise ValueError("unsafe lossy Execution Plan V2 projection")
        return ExecutionPlan(
            correlation_id=self.correlation_id,
            created_at=self.created_at,
            source_component=self.source_component,
            action_id=self.action_id,
            objective=parent.objective,
            destination=self.destination_intent,
            steps=[
                ExecutionStep(
                    step_id=step.step_id,
                    title=step.title,
                    done_when=step.done_when,
                    sequence=step.sequence,
                )
                for step in self.projected_steps
            ],
            authorized=False,
            projection_explanation=self.projection_explanation,
            non_projection_reasons=list(self.non_projection_explanations),
            review_required=False,
        )
