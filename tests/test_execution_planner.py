from uuid import uuid4

import pytest
from pydantic import ValidationError

from atlas_ros.contracts import ExecutionPlan, ManagementPackage
from atlas_ros.domain.models import Action
from atlas_ros.planning import ExecutionPlanner, ExecutionPlanningPolicy
from atlas_ros.planning.decomposition import DecompositionService


def management(
    *,
    owner: str = "Ryan",
    decision_points: list[str] | None = None,
    outcome: str = "A reviewed operating plan exists",
) -> ManagementPackage:
    return ManagementPackage(
        correlation_id=uuid4(),
        source_component="engines.management_structure",
        responsibility="Lead the operating review",
        desired_outcome=outcome,
        owner=owner,
        workstream="Leadership & Team",
        decision_points=decision_points or [],
    )


def test_execution_planner_projects_one_parent_and_progressive_horizon() -> None:
    package = management()
    plan = ExecutionPlanner().plan(
        package,
        action_id="A-1",
        destination="Work/Leadership & Team",
        candidate_steps=("Prepare agenda", "Review metrics", "Confirm actions", "Publish notes"),
    )
    assert plan.objective == package.desired_outcome
    assert [step.title for step in plan.steps] == [
        "Prepare agenda",
        "Review metrics",
        "Confirm actions",
    ]
    assert plan.authorized is False
    assert plan.review_required is False
    assert plan.non_projection_reasons == []


def test_duplicate_and_existing_representations_do_not_increase_task_count() -> None:
    plan = ExecutionPlanner().plan(
        management(),
        action_id="A-2",
        destination="Work/Leadership & Team",
        candidate_steps=(
            "Prepare agenda",
            "prepare-agenda",
            "Review metrics",
            "Review metrics",
        ),
        existing_representations=("review metrics",),
    )
    assert [step.title for step in plan.steps] == ["Prepare agenda"]


def test_existing_parent_representation_withholds_duplicate_projection() -> None:
    package = management()
    plan = ExecutionPlanner().plan(
        package,
        action_id="A-3",
        destination="Work/Leadership & Team",
        candidate_steps=("Prepare agenda",),
        existing_representations=(package.desired_outcome,),
    )
    assert plan.steps == []
    assert plan.non_projection_reasons == ["An equivalent execution representation already exists."]


def test_non_ryan_owner_and_unresolved_decisions_fail_closed() -> None:
    plan = ExecutionPlanner().plan(
        management(owner="Tina", decision_points=["Confirm audience"]),
        action_id="A-4",
        destination="Work/Leadership & Team",
        candidate_steps=("Prepare agenda",),
    )
    assert plan.steps == []
    assert len(plan.non_projection_reasons) == 2


def test_more_than_five_candidates_requires_review_and_no_projection() -> None:
    plan = ExecutionPlanner().plan(
        management(),
        action_id="A-5",
        destination="Work/Leadership & Team",
        candidate_steps=tuple(f"Step {index}" for index in range(1, 7)),
    )
    assert plan.review_required is True
    assert plan.steps == []
    assert "review threshold" in plan.non_projection_reasons[0]


def test_planner_policy_validation_and_authorization_boundary() -> None:
    with pytest.raises(ValueError, match="review_threshold"):
        ExecutionPlanningPolicy(max_steps=4, review_threshold=3)
    with pytest.raises(ValidationError, match="cannot authorize"):
        ExecutionPlan(
            source_component="planning.execution",
            action_id="A-6",
            objective="Complete the work",
            destination="Work",
            authorized=True,
        )


def test_w03a_preserves_pattern_subtask_behavior_through_compatibility_policy() -> None:
    service = DecompositionService()
    action = Action(
        id="A-7",
        title="Investigate service degradation",
        owner="Ryan",
        definition_of_done="Root cause is documented",
        execution_ready=True,
        delegation_reviewed=True,
    )
    expected = service.select_pattern(action.title)[1]
    assert service.readiness(action).proposed_subtasks == expected
