from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .coherence_v1 import ConfidenceDimensionV1, ReasoningCoherenceResultV1
from .intent_v1 import IntentPartitionV1
from .models import (
    ContractKind,
    EvidenceSignal,
    ManagementPackageV2,
    PlanningModelCandidate,
    ReasoningPackageV3,
    deterministic_digest,
)


class SemanticRole(StrEnum):
    PARENT_BUSINESS_OUTCOME = "parent_business_outcome"
    CURRENT_BUSINESS_ACTION = "current_business_action"
    DELEGATED_ACTION = "delegated_action"
    CONDITIONAL_ACTION = "conditional_action"
    EVALUATION_ONLY = "evaluation_only"
    AUDIT_ONLY = "audit_only"
    PROVIDER_CONTROL = "provider_control"
    REFERENCE_ONLY = "reference_only"


class ReasoningPackageV4(BaseModel):
    """Reasoning contract with first-class semantic intent partitioning."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal[4] = 4
    contract_kind: ContractKind = ContractKind.REASONING
    correlation_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source_component: str = Field(min_length=1, max_length=200)
    classification: str = Field(min_length=1, max_length=100)
    destination: str = Field(min_length=1, max_length=200)
    responsibility_domain: str = Field(min_length=1, max_length=100)
    workstream: str = Field(min_length=1, max_length=200)
    activity_summary: str = Field(min_length=1, max_length=1_000)
    operating_context: str = Field(default="", max_length=100)
    operating_context_confidence: float = Field(default=0, ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    decisive_evidence: tuple[EvidenceSignal, ...] = ()
    rationale: tuple[str, ...] = ()
    challenge_status: str = Field(default="unchallenged", min_length=1, max_length=100)
    normalized_intent: str = Field(min_length=1, max_length=10_000)
    management_pattern: str = Field(min_length=1, max_length=200)
    candidate_planning_models: tuple[PlanningModelCandidate, ...]
    selected_planning_model_id: str = Field(min_length=1, max_length=200)
    selected_planning_model_version_constraint: str = Field(default="*", max_length=100)
    selection_method: Literal["inferred", "user_selected", "policy_selected"]
    selection_confidence: float = Field(ge=0, le=1)
    selection_rationale: str = Field(min_length=1, max_length=2_000)
    alternatives_considered: tuple[str, ...] = ()
    planning_assumptions: tuple[str, ...] = ()
    planning_constraints: tuple[str, ...] = ()
    known_stakeholders: tuple[str, ...] = ()
    known_inputs: dict[str, Any] = Field(default_factory=dict)
    primary_business_outcome: str = Field(default="", max_length=10_000)
    current_business_actions: tuple[str, ...] = ()
    delegated_actions: tuple[str, ...] = ()
    conditional_actions: tuple[str, ...] = ()
    evaluation_context: tuple[str, ...] = ()
    audit_requirements: tuple[str, ...] = ()
    execution_constraints: tuple[str, ...] = ()
    reference_context: tuple[str, ...] = ()
    intent_partition_confidence: float = Field(ge=0, le=1)
    intent_partition_ambiguities: tuple[str, ...] = ()
    intent_partition_digest: str = Field(min_length=64, max_length=64)
    unresolved_planning_questions: tuple[str, ...] = ()
    requires_human_decision: bool = False
    confidence_dimensions: tuple[ConfidenceDimensionV1, ...] = ()
    coherence_result: ReasoningCoherenceResultV1 | None = None
    user_facing_summary: str = Field(default="", max_length=3_000)

    @model_validator(mode="after")
    def validate_selection_and_intent(self) -> ReasoningPackageV4:
        candidates = {candidate.model_id for candidate in self.candidate_planning_models}
        if self.selected_planning_model_id not in candidates:
            raise ValueError("selected planning model must be a declared candidate")
        if self.requires_human_decision and not (
            self.intent_partition_ambiguities or self.unresolved_planning_questions
        ):
            raise ValueError("human decision requires a governed ambiguity")
        if not self.requires_human_decision and not self.primary_business_outcome:
            raise ValueError("semantic reasoning requires a primary business outcome")
        if self.coherence_result is not None and not self.coherence_result.verify_digest():
            raise ValueError("reasoning coherence digest verification failed")
        if (
            self.coherence_result is not None
            and self.coherence_result.review_required
            and not self.requires_human_decision
        ):
            raise ValueError("coherence review requirement must fail closed")
        return self

    @classmethod
    def from_v3(
        cls,
        reasoning: ReasoningPackageV3,
        partition: IntentPartitionV1,
        *,
        responsibility_domain: str,
        workstream: str,
        activity_summary: str,
        confidence: float,
        operating_context: str = "",
        operating_context_confidence: float = 0,
        decisive_evidence: tuple[EvidenceSignal, ...] = (),
        rationale: tuple[str, ...] = (),
        challenge_status: str = "unchallenged",
    ) -> ReasoningPackageV4:
        questions = tuple(
            dict.fromkeys(
                (*reasoning.unresolved_planning_questions, *partition.ambiguities)
            )
        )
        return cls(
            correlation_id=reasoning.correlation_id,
            created_at=reasoning.created_at,
            source_component="engines.management_reasoning",
            classification=reasoning.classification,
            destination=reasoning.destination,
            responsibility_domain=responsibility_domain,
            workstream=workstream,
            activity_summary=activity_summary,
            operating_context=operating_context,
            operating_context_confidence=operating_context_confidence,
            confidence=confidence,
            decisive_evidence=decisive_evidence,
            rationale=rationale,
            challenge_status=challenge_status,
            normalized_intent=reasoning.normalized_intent,
            management_pattern=reasoning.management_pattern,
            candidate_planning_models=reasoning.candidate_planning_models,
            selected_planning_model_id=reasoning.selected_planning_model_id,
            selected_planning_model_version_constraint=(
                reasoning.selected_planning_model_version_constraint
            ),
            selection_method=reasoning.selection_method,
            selection_confidence=reasoning.selection_confidence,
            selection_rationale=reasoning.selection_rationale,
            alternatives_considered=reasoning.alternatives_considered,
            planning_assumptions=reasoning.planning_assumptions,
            planning_constraints=reasoning.planning_constraints,
            known_stakeholders=reasoning.known_stakeholders,
            known_inputs=dict(reasoning.known_inputs),
            primary_business_outcome=partition.primary_business_outcome,
            current_business_actions=partition.current_business_actions,
            delegated_actions=partition.delegated_actions,
            conditional_actions=partition.conditional_actions,
            evaluation_context=partition.evaluation_context,
            audit_requirements=partition.audit_requirements,
            execution_constraints=partition.execution_constraints,
            reference_context=partition.reference_context,
            intent_partition_confidence=partition.confidence,
            intent_partition_ambiguities=partition.ambiguities,
            intent_partition_digest=partition.partition_digest,
            unresolved_planning_questions=questions,
            requires_human_decision=(
                reasoning.requires_human_decision or partition.requires_human_decision
            ),
        )

    def project_v3(self) -> ReasoningPackageV3:
        if self.requires_human_decision or not self.primary_business_outcome:
            raise ValueError("unsafe lossy Reasoning Package V4 projection")
        inputs = {
            **self.known_inputs,
            "desired_outcome": self.primary_business_outcome,
            "primary_business_outcome": self.primary_business_outcome,
            "current_business_actions": self.current_business_actions,
            "delegated_actions": self.delegated_actions,
            "conditional_actions": self.conditional_actions,
            "evaluation_context": self.evaluation_context,
            "audit_requirements": self.audit_requirements,
            "execution_constraints": self.execution_constraints,
        }
        return ReasoningPackageV3(
            correlation_id=self.correlation_id,
            created_at=self.created_at,
            source_component=self.source_component,
            classification=self.classification,
            destination=self.destination,
            normalized_intent=self.primary_business_outcome,
            management_pattern=self.management_pattern,
            candidate_planning_models=self.candidate_planning_models,
            selected_planning_model_id=self.selected_planning_model_id,
            selected_planning_model_version_constraint=(
                self.selected_planning_model_version_constraint
            ),
            selection_method=self.selection_method,
            selection_confidence=self.selection_confidence,
            selection_rationale=self.selection_rationale,
            alternatives_considered=self.alternatives_considered,
            planning_assumptions=self.planning_assumptions,
            planning_constraints=self.planning_constraints,
            known_stakeholders=self.known_stakeholders,
            known_inputs=inputs,
            unresolved_planning_questions=(),
            requires_human_decision=False,
        )


class ManagementActionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    action_id: str = Field(min_length=1, max_length=256)
    title: str = Field(min_length=1, max_length=500)
    objective: str = Field(min_length=1, max_length=10_000)
    done_when: str = Field(min_length=1, max_length=10_000)
    owner: str = Field(default="", max_length=200)
    semantic_role: SemanticRole
    horizon: Literal["current", "next", "conditional", "future", "blocked"]
    source_instruction_role: str = Field(min_length=1, max_length=100)
    semantic_provenance: tuple[str, ...] = ()
    execution_ready: bool = False
    trigger: str = Field(default="", max_length=2_000)


class ManagementPackageV3(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal[3] = 3
    contract_kind: ContractKind = ContractKind.MANAGEMENT
    correlation_id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source_component: str = "engines.management_structure"
    artifact_id: str = Field(min_length=1, max_length=256)
    artifact_type: str = Field(min_length=1, max_length=200)
    planning_model_id: str = Field(min_length=1, max_length=200)
    planning_model_version: str = Field(min_length=1, max_length=100)
    source_reasoning_reference: str = Field(min_length=1, max_length=500)
    source_knowledge_reference: str = Field(min_length=1, max_length=500)
    responsibility: str = Field(min_length=1, max_length=2_000)
    primary_outcome: str = Field(min_length=1, max_length=10_000)
    primary_outcome_done_when: str = Field(min_length=1, max_length=10_000)
    owner: str = Field(default="", max_length=200)
    workstream: str = Field(default="", max_length=200)
    execution_candidates: tuple[ManagementActionV1, ...] = ()
    delegated_outcomes: tuple[ManagementActionV1, ...] = ()
    conditional_outcomes: tuple[ManagementActionV1, ...] = ()
    evaluation_context: tuple[str, ...] = ()
    audit_requirements: tuple[str, ...] = ()
    execution_constraints: tuple[str, ...] = ()
    reference_context: tuple[str, ...] = ()
    confidence_dimensions: tuple[ConfidenceDimensionV1, ...] = ()
    reasoning_coherence: ReasoningCoherenceResultV1 | None = None
    user_facing_summary: str = Field(default="", max_length=3_000)
    semantic_provenance: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    assumptions: tuple[str, ...] = ()
    unresolved_items: tuple[str, ...] = ()
    lifecycle_status: Literal["draft", "decision_required", "structurally_complete"]
    planning_registry_digest: str = Field(min_length=64, max_length=64)
    module_registry_digest: str = Field(min_length=64, max_length=64)
    configuration_digest: str = Field(min_length=64, max_length=64)
    intent_partition_digest: str = Field(min_length=64, max_length=64)
    package_digest: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_coherence(self) -> ManagementPackageV3:
        if self.reasoning_coherence is not None and not self.reasoning_coherence.verify_digest():
            raise ValueError("management reasoning coherence digest verification failed")
        if (
            self.reasoning_coherence is not None
            and self.reasoning_coherence.review_required
            and self.lifecycle_status == "structurally_complete"
        ):
            raise ValueError("management package cannot be complete when coherence requires review")
        return self

    def digest_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"created_at", "package_digest"})

    def verify_digest(self) -> bool:
        return self.package_digest == deterministic_digest(self.digest_payload())

    def project_v2(self) -> ManagementPackageV2:
        if self.lifecycle_status != "structurally_complete":
            raise ValueError("unsafe lossy Management Package V3 projection")
        execution_items = [
            {
                "candidate_id": action.action_id,
                "candidate_type": "independently_executable_action",
                "title": action.title,
                "objective": action.objective,
                "done_when": action.done_when,
                "owner": action.owner,
                "horizon": action.horizon,
                "execution_ready": action.execution_ready,
                "provenance": action.semantic_provenance,
            }
            for action in self.execution_candidates
        ]
        from .models import ManagementSection, ValidationResult

        section = ManagementSection(
            section_id="semantic-execution",
            title="Semantic execution",
            content={"execution_candidates": execution_items},
            provenance=(f"intent-partition/{self.intent_partition_digest}",),
            completeness="complete",
        )
        arguments: dict[str, Any] = {
            "correlation_id": self.correlation_id,
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "planning_model_id": self.planning_model_id,
            "planning_model_version": self.planning_model_version,
            "source_reasoning_reference": self.source_reasoning_reference,
            "source_knowledge_reference": self.source_knowledge_reference,
            "responsibility": self.responsibility,
            "desired_outcome": self.primary_outcome,
            "owner": self.owner,
            "workstream": self.workstream,
            "sections": (section,),
            "section_provenance": {"semantic-execution": section.provenance},
            "section_completeness": {"semantic-execution": "complete"},
            "assumptions": self.assumptions,
            "unresolved_items": (),
            "decision_points": (),
            "governance_requirements": (),
            "required_approvals": (),
            "escalation_requirements": (),
            "completion_evidence_requirements": (self.primary_outcome_done_when,),
            "validation_results": (
                ValidationResult(
                    rule="semantic_intent_separation",
                    passed=True,
                    detail="Business execution is separated from control-plane evidence.",
                ),
            ),
            "lifecycle_status": "structurally_complete",
            "planning_registry_digest": self.planning_registry_digest,
            "module_registry_digest": self.module_registry_digest,
            "configuration_digest": self.configuration_digest,
        }
        unsigned = ManagementPackageV2(package_digest="0" * 64, **arguments)
        return ManagementPackageV2(
            **arguments,
            package_digest=deterministic_digest(unsigned.digest_payload()),
        )


class SemanticConditionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    condition: str = Field(min_length=1, max_length=100)
    passed: bool
    reason_code: str = Field(min_length=1, max_length=100)
    detail: str = Field(default="", max_length=2_000)


class SemanticFidelityResultV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal[1] = 1
    primary_outcome_reference: str = Field(min_length=1, max_length=500)
    conditions: tuple[SemanticConditionResult, ...]
    passed: bool
    review_required: bool
    business_plan_fingerprint: str = Field(min_length=64, max_length=64)
    result_digest: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_result(self) -> SemanticFidelityResultV1:
        if self.passed != all(condition.passed for condition in self.conditions):
            raise ValueError("semantic fidelity summary does not match condition results")
        if self.review_required == self.passed:
            raise ValueError("semantic review is required exactly when fidelity fails")
        return self

    def digest_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"result_digest"})

    def verify_digest(self) -> bool:
        return self.result_digest == deterministic_digest(self.digest_payload())
