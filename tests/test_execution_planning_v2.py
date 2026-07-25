from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from hypothesis import given
from hypothesis import strategies as st

from atlas_ros.contracts import (
    CandidateType,
    CompletionState,
    ExecutionCandidate,
    ExistingRepresentation,
    ExistingRepresentationIndex,
    HorizonState,
    ManagementPackageV2,
    ManagementSection,
    ProjectionDecisionStatus,
    RepresentationMatchKind,
    deterministic_digest,
)
from atlas_ros.orchestration import ExecutionCommandFactory
from atlas_ros.planning import (
    DuplicateAnalyzer,
    ExecutionCandidateExtractor,
    ExecutionPlanner,
    ExecutionPlanningPolicy,
    ProgressiveHorizonPolicy,
)


def management(
    *,
    sections: tuple[ManagementSection, ...] = (),
    lifecycle: str = "structurally_complete",
    owner: str = "Ryan",
) -> ManagementPackageV2:
    arguments: dict[str, Any] = {
        "correlation_id": uuid4(),
        "artifact_id": "team-operating-model:test",
        "artifact_type": "team_operating_model",
        "planning_model_id": "team-operating-model",
        "planning_model_version": "2.0.0",
        "source_reasoning_reference": "reasoning/v3/test",
        "source_knowledge_reference": "knowledge/v2/test",
        "responsibility": "Lead the operating review",
        "desired_outcome": "A reviewed operating plan is approved and recorded",
        "owner": owner,
        "workstream": "Leadership & Team",
        "sections": sections,
        "section_provenance": {section.section_id: section.provenance for section in sections},
        "section_completeness": {section.section_id: section.completeness for section in sections},
        "completion_evidence_requirements": (
            "The operating plan is approved and stored in its authoritative location",
        ),
        "lifecycle_status": lifecycle,
        "planning_registry_digest": "1" * 64,
        "module_registry_digest": "2" * 64,
        "configuration_digest": "3" * 64,
    }
    unsigned = ManagementPackageV2(package_digest="0" * 64, **arguments)
    return ManagementPackageV2(
        **arguments,
        package_digest=deterministic_digest(unsigned.digest_payload()),
    )


def candidate(
    candidate_id: str,
    *,
    candidate_type: CandidateType = CandidateType.EXECUTABLE_ACTION,
    title: str | None = None,
    objective: str | None = None,
    done_when: str | None = None,
    owner: str = "Ryan",
    horizon: HorizonState = HorizonState.CURRENT,
    execution_ready: bool = True,
    completion_state: CompletionState = CompletionState.OUTSTANDING,
    ambiguities: tuple[str, ...] = (),
    can_remain_embedded: bool = False,
    improves_execution_clarity: bool = True,
    independently_executable: bool = True,
    source_item_id: str | None = None,
    trigger_satisfied: bool = False,
    recurrence_required: bool = False,
    dependencies: tuple[str, ...] = (),
) -> ExecutionCandidate:
    name = title or f"Complete action {candidate_id}"
    values: dict[str, Any] = {
        "candidate_id": candidate_id,
        "correlation_id": CORRELATION_ID,
        "source_management_reference": "management-package/v2/test",
        "candidate_type": candidate_type,
        "title": name,
        "proposed_objective": objective or f"Deliver outcome for {name}",
        "done_when": done_when or f"Evidence for {name} is approved and recorded",
        "owner": owner,
        "responsibility_domain": "Network Services",
        "workstream": "Operations",
        "source_section": "actions",
        "source_item_id": source_item_id or candidate_id,
        "source_provenance": ("module:test",),
        "dependency_references": dependencies,
        "execution_ready": execution_ready,
        "earliest_executable_horizon": horizon,
        "completion_state": completion_state,
        "ambiguities": ambiguities,
        "can_remain_embedded": can_remain_embedded,
        "improves_execution_clarity": improves_execution_clarity,
        "independently_executable": independently_executable,
        "trigger_satisfied": trigger_satisfied,
        "recurrence_required": recurrence_required,
    }
    unsigned = ExecutionCandidate(candidate_digest="0" * 64, **values)
    return ExecutionCandidate(
        **values,
        candidate_digest=deterministic_digest(unsigned.digest_payload()),
    )


CORRELATION_ID = uuid4()


def candidates(count: int) -> tuple[ExecutionCandidate, ...]:
    return (
        candidate("parent", candidate_type=CandidateType.PARENT_OUTCOME),
        *(candidate(f"child-{index}") for index in range(1, count + 1)),
    )


def test_command_factory_preserves_exact_plan_without_adding_work() -> None:
    plan = ExecutionPlanner().plan_v2(
        management(),
        action_id="A-command",
        destination_intent="Work/Operations",
        candidates=candidates(2),
    )
    operations = ExecutionCommandFactory.todoist_operations(
        plan,
        project="Work",
        section="Operations",
    )
    child_operations = [
        operation
        for operation in operations
        if operation.operation_type.value == "upsert_child"
    ]
    assert len(child_operations) == len(plan.projected_steps) == 2
    assert [operation.sequence for operation in operations] == list(
        range(1, len(operations) + 1)
    )
    assert child_operations[0].payload["objective"] == plan.projected_steps[0].objective
    assert child_operations[0].payload["done_when"] == plan.projected_steps[0].done_when


def test_command_factory_creates_no_placeholder_for_zero_subtasks() -> None:
    plan = ExecutionPlanner().plan_v2(
        management(),
        action_id="A-zero",
        destination_intent="Work/Operations",
        candidates=candidates(0),
    )
    operations = ExecutionCommandFactory.todoist_operations(
        plan,
        project="Work",
        section="Operations",
    )
    assert all(operation.operation_type.value != "upsert_child" for operation in operations)


def test_command_factory_builds_only_explicit_notion_operations() -> None:
    plan = ExecutionPlanner().plan_v2(
        management(),
        action_id="A-notion",
        destination_intent="Work/Operations",
        candidates=candidates(0),
    )
    operations = ExecutionCommandFactory.notion_operations(
        plan,
        identity="A-notion",
        properties={"Action ID": "A-notion"},
    )
    assert [operation.operation_type.value for operation in operations] == [
        "find_record",
        "upsert_record",
        "verify_record",
    ]


def test_command_factory_rejects_tampered_plan() -> None:
    plan = ExecutionPlanner().plan_v2(
        management(),
        action_id="A-tampered",
        destination_intent="Work/Operations",
        candidates=candidates(0),
    ).model_copy(update={"plan_digest": "0" * 64})
    with pytest.raises(ValueError, match="digest"):
        ExecutionCommandFactory.todoist_operations(
            plan,
            project="Work",
            section="Operations",
        )


def test_extractor_is_deterministic_and_does_not_turn_sections_into_tasks() -> None:
    action = {
        "candidate_id": "action-1",
        "candidate_type": "independently_executable_action",
        "title": "Review the operating plan",
        "objective": "Complete the operating-plan review",
        "done_when": "Review outcomes are approved and recorded",
        "owner": "Ryan",
        "execution_ready": True,
    }
    base = management(
        sections=(
            ManagementSection(
                section_id="actions",
                title="Actions",
                content={"execution_candidates": [action]},
                provenance=("module:actions",),
                completeness="complete",
            ),
        )
    )
    expanded = management(
        sections=(
            *base.sections,
            ManagementSection(
                section_id="governance",
                title="Governance",
                content={"rules": ["review quarterly"], "notes": ["context only"]},
                provenance=("module:governance",),
                completeness="complete",
            ),
        )
    )
    first = ExecutionCandidateExtractor().extract(base)
    second = ExecutionCandidateExtractor().extract(base)
    additional_detail = ExecutionCandidateExtractor().extract(expanded)
    executable = {
        CandidateType.PARENT_OUTCOME,
        CandidateType.EXECUTABLE_ACTION,
        CandidateType.RISK_RESPONSE,
    }
    assert first.candidate_set_digest == second.candidate_set_digest
    assert sum(item.candidate_type in executable for item in first.candidates) == 2
    assert sum(item.candidate_type in executable for item in additional_detail.candidates) == 2
    assert all(item.verify_digest() for item in first.candidates)


@pytest.mark.parametrize("count", [0, 1, 2, 3])
def test_default_budget_projects_zero_to_three_subtasks(count: int) -> None:
    plan = ExecutionPlanner().plan_v2(
        management(),
        action_id=f"A-{count}",
        destination_intent="Work/Operations",
        candidates=candidates(count),
    )
    assert len(plan.projected_steps) == count
    assert plan.task_budget.expanded_budget_used is False
    assert plan.decomposition_review_status == "not_required"
    assert plan.authorized is False
    assert plan.verify_digest()


@pytest.mark.parametrize("count", [4, 5])
def test_four_or_five_subtasks_require_explicit_budget_rationale(count: int) -> None:
    plan = ExecutionPlanner().plan_v2(
        management(),
        action_id=f"A-{count}",
        destination_intent="Work/Operations",
        candidates=candidates(count),
    )
    assert len(plan.projected_steps) == count
    assert plan.task_budget.expanded_budget_used is True
    assert "governed four-or-five-step allowance" in plan.task_budget.rationale


def test_more_than_five_is_review_gate_not_authorization() -> None:
    plan = ExecutionPlanner().plan_v2(
        management(),
        action_id="A-6",
        destination_intent="Work/Operations",
        candidates=candidates(6),
    )
    assert plan.decomposition_review_status == "required"
    assert plan.projected_steps == ()
    assert all(
        decision.status is ProjectionDecisionStatus.REVIEW_REQUIRED
        for decision in plan.projection_decisions[1:]
    )
    assert plan.authorized is False
    assert plan.task_budget.compression_alternatives


@pytest.mark.parametrize(
    ("changed", "expected"),
    [
        ({"owner": "Tina"}, ProjectionDecisionStatus.WITHHOLD_NOT_OWNED),
        (
            {"execution_ready": False},
            ProjectionDecisionStatus.WITHHOLD_NOT_READY,
        ),
        (
            {"ambiguities": ("Confirm the audience",)},
            ProjectionDecisionStatus.WITHHOLD_UNRESOLVED,
        ),
        (
            {"completion_state": CompletionState.COMPLETE},
            ProjectionDecisionStatus.WITHHOLD_ALREADY_COMPLETE,
        ),
        (
            {"horizon": HorizonState.FUTURE},
            ProjectionDecisionStatus.DEFER_FUTURE_HORIZON,
        ),
        (
            {
                "candidate_type": CandidateType.GOVERNANCE,
                "can_remain_embedded": True,
            },
            ProjectionDecisionStatus.WITHHOLD_NOT_EXECUTION_OBJECT,
        ),
    ],
)
def test_projection_test_explains_every_non_projection(
    changed: dict[str, Any],
    expected: ProjectionDecisionStatus,
) -> None:
    plan = ExecutionPlanner().plan_v2(
        management(),
        action_id="A-withhold",
        destination_intent="Work/Operations",
        candidates=(
            candidate("parent", candidate_type=CandidateType.PARENT_OUTCOME),
            candidate("subject", **changed),
        ),
    )
    decision = next(item for item in plan.projection_decisions if item.candidate_id == "subject")
    assert decision.status is expected
    assert len(decision.task_projection_test) == 14
    assert decision.non_projection_reasons
    assert decision.verify_digest()


def test_layered_duplicate_policy_is_order_independent() -> None:
    first = candidate("one", title="Review Metrics")
    duplicate = candidate(
        "two",
        title="review-metrics",
        objective=first.proposed_objective,
        done_when=first.done_when,
        source_item_id="different",
    )
    forward = DuplicateAnalyzer().analyze((first, duplicate))
    reverse = DuplicateAnalyzer().analyze((duplicate, first))
    assert sum(item.duplicate for item in forward.values()) == 1
    assert sum(item.duplicate for item in reverse.values()) == 1


def test_existing_open_representation_suppresses_projection() -> None:
    child = candidate("child")
    index = ExistingRepresentationIndex(
        representations=(
            ExistingRepresentation(
                representation_id="existing-1",
                representation_type="subtask",
                title=child.title,
                objective=child.proposed_objective,
                done_when=child.done_when,
                owner="Ryan",
                workstream="Operations",
                state="open",
                last_verified_at=datetime.now(UTC),
            ),
        )
    )
    plan = ExecutionPlanner().plan_v2(
        management(),
        action_id="A-existing",
        destination_intent="Work/Operations",
        candidates=(
            candidate("parent", candidate_type=CandidateType.PARENT_OUTCOME),
            child,
        ),
        existing_index=index,
    )
    decision = plan.projection_decisions[1]
    assert decision.status is ProjectionDecisionStatus.SUPPRESS_EXISTING
    assert (
        decision.existing_representation_result.outcome is RepresentationMatchKind.EQUIVALENT_OPEN
    )


def test_completed_representation_requires_explicit_recurrence() -> None:
    child = candidate("child")
    recurring = candidate("recurring", recurrence_required=True)
    index = ExistingRepresentationIndex(
        representations=(
            ExistingRepresentation(
                representation_id="existing-complete",
                representation_type="subtask",
                title=child.title,
                objective=child.proposed_objective,
                done_when=child.done_when,
                owner="Ryan",
                workstream="Operations",
                state="completed",
                last_verified_at=datetime.now(UTC),
            ),
            ExistingRepresentation(
                representation_id="existing-recurring",
                representation_type="subtask",
                title=recurring.title,
                objective=recurring.proposed_objective,
                done_when=recurring.done_when,
                owner="Ryan",
                workstream="Operations",
                state="completed",
                last_verified_at=datetime.now(UTC),
            ),
        )
    )
    plan = ExecutionPlanner().plan_v2(
        management(),
        action_id="A-recurring",
        destination_intent="Work/Operations",
        candidates=(
            candidate("parent", candidate_type=CandidateType.PARENT_OUTCOME),
            child,
            recurring,
        ),
        existing_index=index,
    )
    statuses = {item.candidate_id: item.status for item in plan.projection_decisions}
    assert statuses["child"] is ProjectionDecisionStatus.SUPPRESS_EXISTING
    assert statuses["recurring"] is ProjectionDecisionStatus.PROJECT_SUBTASK


def test_conditional_horizon_transitions_only_when_trigger_is_true() -> None:
    waiting = candidate(
        "conditional",
        horizon=HorizonState.CONDITIONAL,
        trigger_satisfied=False,
    )
    ready = candidate(
        "conditional-ready",
        horizon=HorizonState.CONDITIONAL,
        trigger_satisfied=True,
    )
    assert ProgressiveHorizonPolicy.effective(waiting) is HorizonState.CONDITIONAL
    assert ProgressiveHorizonPolicy.effective(ready) is HorizonState.CURRENT
    assert (
        ProgressiveHorizonPolicy.transition(waiting, trigger_satisfied=True) is HorizonState.CURRENT
    )


def test_v1_projection_is_safe_only_without_review_or_human_decisions() -> None:
    plan = ExecutionPlanner().plan_v2(
        management(),
        action_id="A-safe-v1",
        destination_intent="Work/Operations",
        candidates=candidates(2),
    )
    projected = plan.project_v1()
    assert projected.authorized is False
    assert [step.title for step in projected.steps] == [
        "Complete action child-1",
        "Complete action child-2",
    ]
    gated = ExecutionPlanner().plan_v2(
        management(),
        action_id="A-unsafe-v1",
        destination_intent="Work/Operations",
        candidates=candidates(6),
    )
    with pytest.raises(ValueError, match="unsafe lossy"):
        gated.project_v1()


def test_observability_is_structured_and_content_safe() -> None:
    events: list[tuple[str, dict[str, str]]] = []
    plan = ExecutionPlanner(event_sink=lambda name, fields: events.append((name, fields))).plan_v2(
        management(),
        action_id="A-events",
        destination_intent="Work/Operations",
        candidates=candidates(1),
    )
    assert plan.verify_digest()
    assert {name for name, _ in events} >= {
        "task_projection_test_passed",
        "candidate_projected",
        "plan_generated",
    }
    assert all("candidate_digest" in fields or "plan_digest" in fields for _, fields in events)
    assert all("done_when" not in fields and "objective" not in fields for _, fields in events)


def test_ambiguous_duplicate_requires_review_without_suppression() -> None:
    inputs = (
        candidate("parent", candidate_type=CandidateType.PARENT_OUTCOME),
        candidate("brief-a", title="Prepare quarterly launch brief"),
        candidate("brief-b", title="Prepare quarterly launch briefing"),
    )
    plan = ExecutionPlanner().plan_v2(
        management(),
        action_id="A-ambiguous",
        destination_intent="Work",
        candidates=inputs,
    )
    decision = next(item for item in plan.projection_decisions if item.candidate_id == "brief-b")
    assert decision.status is ProjectionDecisionStatus.REVIEW_REQUIRED
    assert decision.duplicate_result.ambiguous
    assert decision.human_decision_required


def test_multiple_independent_parent_outcomes_create_separate_plans() -> None:
    inputs = (
        candidate(
            "parent-launch",
            candidate_type=CandidateType.PARENT_OUTCOME,
            title="Launch the service",
        ),
        candidate(
            "parent-train",
            candidate_type=CandidateType.PARENT_OUTCOME,
            title="Train the support team",
        ),
        candidate("launch-step", dependencies=("parent-launch",)),
        candidate("train-step", dependencies=("parent-train",)),
        candidate("unassigned-step"),
    )
    plans = ExecutionPlanner().plan_many_v2(
        management(),
        action_id="A-multiple",
        destination_intent="Work",
        candidates=inputs,
    )
    assert len(plans) == 2
    assert {plan.parent_outcome.source_candidate_id for plan in plans if plan.parent_outcome} == {
        "parent-launch",
        "parent-train",
    }
    assert {step.source_candidate_id for plan in plans for step in plan.projected_steps} == {
        "launch-step",
        "train-step",
    }
    assert all(plan.task_budget.multiple_parent_outcomes for plan in plans)
    assert all(
        "independently valid parent outcomes" in plan.projection_explanation for plan in plans
    )


def test_similar_parent_outcome_is_not_artificially_split() -> None:
    inputs = (
        candidate(
            "parent-a",
            candidate_type=CandidateType.PARENT_OUTCOME,
            title="Approve quarterly release plan",
        ),
        candidate(
            "parent-b",
            candidate_type=CandidateType.PARENT_OUTCOME,
            title="Approve quarterly release planning",
        ),
    )
    plans = ExecutionPlanner().plan_many_v2(
        management(),
        action_id="A-parent-review",
        destination_intent="Work",
        candidates=inputs,
    )
    assert len(plans) == 1


@given(st.lists(st.integers(min_value=1, max_value=3), min_size=1, max_size=8))
def test_duplicate_insertion_never_increases_task_count(values: list[int]) -> None:
    unique = sorted(set(values))
    base = (
        candidate("parent", candidate_type=CandidateType.PARENT_OUTCOME),
        *(candidate(f"child-{value}") for value in unique),
    )
    duplicated = (
        *base,
        *(
            candidate(
                f"duplicate-{value}",
                title=f"Complete action child-{value}",
            )
            for value in values
        ),
    )
    planner = ExecutionPlanner(ExecutionPlanningPolicy(max_steps=10, review_threshold=10))
    first = planner.plan_v2(
        management(),
        action_id="A-base",
        destination_intent="Work",
        candidates=base,
    )
    second = planner.plan_v2(
        management(),
        action_id="A-duplicate",
        destination_intent="Work",
        candidates=duplicated,
    )
    assert len(second.projected_steps) <= len(first.projected_steps)


@given(st.permutations((1, 2, 3)))
def test_candidate_input_order_does_not_change_semantic_plan(order: tuple[int, ...]) -> None:
    inputs = (
        candidate("parent", candidate_type=CandidateType.PARENT_OUTCOME),
        *(candidate(f"child-{value}") for value in order),
    )
    plan = ExecutionPlanner().plan_v2(
        management(),
        action_id="A-order",
        destination_intent="Work",
        candidates=inputs,
    )
    assert [step.source_candidate_id for step in plan.projected_steps] == [
        "child-1",
        "child-2",
        "child-3",
    ]
    assert plan.authorized is False
