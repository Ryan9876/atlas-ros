from __future__ import annotations

from uuid import uuid4

import pytest

from atlas_ros.contracts.execution_v2 import (
    DuplicateFinding,
    ExecutionPlanV2,
    ExecutionStepV2,
    HorizonState,
    ProjectedObjectType,
    ProjectionDecision,
    ProjectionDecisionStatus,
    ProjectionTestResult,
    RepresentationMatch,
    RepresentationMatchKind,
    TaskBudgetResult,
)
from atlas_ros.contracts.migrations.v6_execution_plan import (
    ExecutionPlanMigrationError,
    migrate_execution_plan_v2,
)
from atlas_ros.contracts.models import deterministic_digest
from atlas_ros.contracts.semantic_v1 import (
    SemanticConditionResult,
    SemanticFidelityResultV1,
    SemanticRole,
)


def source_plan() -> ExecutionPlanV2:
    candidate_id = "candidate-1"
    test = ProjectionTestResult(
        condition="advances_primary_outcome",
        passed=True,
        reason_code="passed",
    )
    duplicate = DuplicateFinding(candidate_id=candidate_id)
    representation = RepresentationMatch(
        candidate_id=candidate_id,
        outcome=RepresentationMatchKind.NONE,
    )
    decision_values = {
        "candidate_id": candidate_id,
        "status": ProjectionDecisionStatus.PROJECT_SUBTASK,
        "projected_object_type": ProjectedObjectType.SUBTASK,
        "sequence": 1,
        "projection_rationale": "This is the next executable checkpoint.",
        "task_projection_test": (test,),
        "horizon": HorizonState.CURRENT,
        "duplicate_result": duplicate,
        "existing_representation_result": representation,
        "policy_version": "v2",
    }
    unsigned_decision = ProjectionDecision.model_construct(
        **decision_values,
        decision_digest="0" * 64,
    )
    decision = ProjectionDecision.model_validate(
        {
            **unsigned_decision.model_dump(mode="json"),
            "decision_digest": deterministic_digest(unsigned_decision.digest_payload()),
        }
    )
    step = ExecutionStepV2(
        step_id="step-1",
        title="Complete the checkpoint",
        objective="Complete the next governed checkpoint.",
        done_when="The checkpoint has verified evidence.",
        sequence=1,
        source_candidate_id=candidate_id,
        source_provenance=("source/1",),
        horizon=HorizonState.CURRENT,
        projection_rationale="The action is current and independently executable.",
    )
    values = {
        "plan_id": "plan-1",
        "action_id": "action-1",
        "correlation_id": uuid4(),
        "source_management_reference": "management/1",
        "source_management_digest": "a" * 64,
        "planner_policy_version": "v2",
        "destination_intent": "Todoist Work",
        "projected_steps": (step,),
        "projection_decisions": (decision,),
        "task_budget": TaskBudgetResult(candidate_count=1, projected_subtask_count=1),
        "candidate_set_digest": "b" * 64,
    }
    unsigned = ExecutionPlanV2.model_construct(**values, plan_digest="0" * 64)
    return ExecutionPlanV2.model_validate(
        {
            **unsigned.model_dump(mode="json"),
            "plan_digest": deterministic_digest(unsigned.digest_payload()),
        }
    )


def fidelity() -> SemanticFidelityResultV1:
    condition = SemanticConditionResult(
        condition="primary_outcome_preserved",
        passed=True,
        reason_code="passed",
    )
    values = {
        "primary_outcome_reference": "outcome/1",
        "conditions": (condition,),
        "passed": True,
        "review_required": False,
        "business_plan_fingerprint": "c" * 64,
    }
    unsigned = SemanticFidelityResultV1.model_construct(
        **values,
        result_digest="0" * 64,
    )
    return SemanticFidelityResultV1.model_validate(
        {
            **unsigned.model_dump(mode="json"),
            "result_digest": deterministic_digest(unsigned.digest_payload()),
        }
    )


def test_v2_to_v3_migration_requires_explicit_semantic_evidence() -> None:
    migrated = migrate_execution_plan_v2(
        source_plan(),
        semantic_fidelity=fidelity(),
        semantic_roles={"candidate-1": SemanticRole.CURRENT_BUSINESS_ACTION},
        instruction_roles={"candidate-1": "current_action"},
        primary_outcome_reference="outcome/1",
    )

    assert migrated.contract_version == 3
    assert migrated.source_component == "planning.semantic_execution"
    assert migrated.projected_steps[0].semantic_role is SemanticRole.CURRENT_BUSINESS_ACTION
    assert migrated.projection_decisions[0].source_instruction_role == "current_action"
    assert migrated.verify_digest()
    assert migrated.authorized is False


def test_v2_to_v3_migration_rejects_missing_semantic_role() -> None:
    with pytest.raises(ExecutionPlanMigrationError, match="missing semantic roles"):
        migrate_execution_plan_v2(
            source_plan(),
            semantic_fidelity=fidelity(),
            semantic_roles={},
            instruction_roles={"candidate-1": "current_action"},
            primary_outcome_reference="outcome/1",
        )


def test_v2_to_v3_migration_rejects_tampered_source_digest() -> None:
    plan = source_plan().model_copy(update={"plan_digest": "f" * 64})

    with pytest.raises(ExecutionPlanMigrationError, match="digest"):
        migrate_execution_plan_v2(
            plan,
            semantic_fidelity=fidelity(),
            semantic_roles={"candidate-1": SemanticRole.CURRENT_BUSINESS_ACTION},
            instruction_roles={"candidate-1": "current_action"},
            primary_outcome_reference="outcome/1",
        )
