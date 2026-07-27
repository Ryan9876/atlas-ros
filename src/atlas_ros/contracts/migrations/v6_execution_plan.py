"""Explicit, fail-closed migration from Execution Plan V2 to V3.

This compatibility module is excluded from the v7 production runtime. Callers must
supply the semantic roles and fidelity result introduced by the V3 contract; the
migration never infers those values or authorizes execution.
"""

from __future__ import annotations

from collections.abc import Mapping

from atlas_ros.contracts.execution_v2 import (
    ExecutionPlanV2,
    ExecutionStepV2,
    ProjectionDecision,
    ProjectionDecisionStatus,
)
from atlas_ros.contracts.execution_v3 import (
    ExecutionPlanV3,
    ExecutionStepV3,
    ProjectionDecisionV3,
)
from atlas_ros.contracts.models import deterministic_digest
from atlas_ros.contracts.semantic_v1 import SemanticFidelityResultV1, SemanticRole


class ExecutionPlanMigrationError(ValueError):
    """Raised when V2 evidence cannot be represented safely in V3."""


_STATUS_MAP = {
    ProjectionDecisionStatus.PROJECT_PARENT: "project_parent",
    ProjectionDecisionStatus.PROJECT_SUBTASK: "project_subtask",
    ProjectionDecisionStatus.RETAIN_IN_MANAGEMENT: "retain_in_management",
    ProjectionDecisionStatus.DEFER_FUTURE_HORIZON: "defer_future_horizon",
    ProjectionDecisionStatus.WITHHOLD_NOT_OWNED: "withhold_not_owned",
    ProjectionDecisionStatus.WITHHOLD_NOT_READY: "withhold_not_ready",
    ProjectionDecisionStatus.REVIEW_REQUIRED: "review_required",
    ProjectionDecisionStatus.SUPPRESS_DUPLICATE: "retain_in_management",
    ProjectionDecisionStatus.SUPPRESS_EXISTING: "retain_in_management",
    ProjectionDecisionStatus.WITHHOLD_ALREADY_COMPLETE: "retain_in_management",
    ProjectionDecisionStatus.WITHHOLD_NOT_EXECUTION_OBJECT: "retain_in_management",
    ProjectionDecisionStatus.WITHHOLD_UNRESOLVED: "review_required",
}


def migrate_execution_plan_v2(
    plan: ExecutionPlanV2,
    *,
    semantic_fidelity: SemanticFidelityResultV1,
    semantic_roles: Mapping[str, SemanticRole],
    instruction_roles: Mapping[str, str],
    primary_outcome_reference: str,
) -> ExecutionPlanV3:
    """Migrate verified V2 evidence only when all V3 semantic inputs are explicit."""
    if not plan.verify_digest():
        raise ExecutionPlanMigrationError("source Execution Plan V2 digest is invalid")
    if not primary_outcome_reference.strip():
        raise ExecutionPlanMigrationError("primary outcome reference is required")
    if semantic_fidelity.primary_outcome_reference != primary_outcome_reference:
        raise ExecutionPlanMigrationError(
            "semantic-fidelity result disagrees with the primary outcome reference"
        )
    candidate_ids = {
        decision.candidate_id for decision in plan.projection_decisions
    } | {step.source_candidate_id for step in plan.projected_steps}
    missing_roles = sorted(candidate_ids - set(semantic_roles))
    missing_instruction_roles = sorted(candidate_ids - set(instruction_roles))
    if missing_roles:
        raise ExecutionPlanMigrationError(
            "missing semantic roles for: " + ", ".join(missing_roles)
        )
    if missing_instruction_roles:
        raise ExecutionPlanMigrationError(
            "missing instruction roles for: " + ", ".join(missing_instruction_roles)
        )

    parent = _migrate_parent(plan.parent_outcome)
    steps = tuple(
        _migrate_step(step, semantic_roles[step.source_candidate_id])
        for step in plan.projected_steps
    )
    decisions = tuple(
        _migrate_decision(
            decision,
            semantic_role=semantic_roles[decision.candidate_id],
            instruction_role=instruction_roles[decision.candidate_id],
            primary_outcome_reference=primary_outcome_reference,
        )
        for decision in plan.projection_decisions
    )
    if not semantic_fidelity.passed and (parent is not None or steps):
        raise ExecutionPlanMigrationError(
            "semantic-fidelity failures cannot migrate projected execution objects"
        )

    provisional = ExecutionPlanV3.model_construct(
        contract_version=3,
        plan_id=plan.plan_id,
        action_id=plan.action_id,
        correlation_id=plan.correlation_id,
        created_at=plan.created_at,
        source_component="planning.semantic_execution",
        source_management_reference=plan.source_management_reference,
        source_management_digest=plan.source_management_digest,
        planner_policy_version=plan.planner_policy_version,
        parent_outcome=parent,
        destination_intent=plan.destination_intent,
        projected_steps=steps,
        projection_decisions=decisions,
        deferred_candidates=plan.deferred_candidates,
        retained_management_items=plan.retained_management_items,
        semantic_fidelity=semantic_fidelity,
        human_decision_requirements=plan.human_decision_requirements,
        authorized=False,
        candidate_set_digest=plan.candidate_set_digest,
        plan_digest="0" * 64,
    )
    payload = provisional.model_dump(mode="json", exclude={"created_at", "plan_digest"})
    return ExecutionPlanV3.model_validate(
        {
            **provisional.model_dump(mode="json"),
            "plan_digest": deterministic_digest(payload),
        }
    )


def _migrate_parent(step: ExecutionStepV2 | None) -> ExecutionStepV3 | None:
    if step is None:
        return None
    return ExecutionStepV3(
        step_id=step.step_id,
        title=step.title,
        objective=step.objective,
        done_when=step.done_when,
        sequence=step.sequence,
        source_candidate_id=step.source_candidate_id,
        semantic_role=SemanticRole.PARENT_BUSINESS_OUTCOME,
        semantic_provenance=step.source_provenance,
    )


def _migrate_step(step: ExecutionStepV2, semantic_role: SemanticRole) -> ExecutionStepV3:
    if semantic_role not in {
        SemanticRole.CURRENT_BUSINESS_ACTION,
        SemanticRole.DELEGATED_ACTION,
        SemanticRole.CONDITIONAL_ACTION,
    }:
        raise ExecutionPlanMigrationError(
            f"projected step has a non-executable semantic role: {step.source_candidate_id}"
        )
    return ExecutionStepV3(
        step_id=step.step_id,
        title=step.title,
        objective=step.objective,
        done_when=step.done_when,
        sequence=step.sequence,
        source_candidate_id=step.source_candidate_id,
        semantic_role=semantic_role,
        semantic_provenance=step.source_provenance,
    )


def _migrate_decision(
    decision: ProjectionDecision,
    *,
    semantic_role: SemanticRole,
    instruction_role: str,
    primary_outcome_reference: str,
) -> ProjectionDecisionV3:
    try:
        status = _STATUS_MAP[decision.status]
    except KeyError as error:
        raise ExecutionPlanMigrationError(
            f"unsupported V2 projection status: {decision.status}"
        ) from error
    rationale = decision.projection_rationale or "; ".join(decision.non_projection_reasons)
    if not rationale:
        rationale = "Preserved by explicit V2-to-V3 compatibility migration."
    fidelity_conditions = tuple(
        result.condition for result in decision.task_projection_test if result.passed
    )
    payload = {
        "contract_version": 3,
        "candidate_id": decision.candidate_id,
        "semantic_role": semantic_role,
        "status": status,
        "projected_object_type": decision.projected_object_type.value,
        "sequence": decision.sequence,
        "primary_outcome_reference": primary_outcome_reference,
        "source_instruction_role": instruction_role,
        "advances_primary_outcome": status in {"project_parent", "project_subtask"},
        "rationale": rationale,
        "semantic_fidelity_conditions": fidelity_conditions,
        "review_required": decision.review_required or status == "review_required",
    }
    return ProjectionDecisionV3.model_validate(
        {**payload, "decision_digest": deterministic_digest(payload)}
    )
