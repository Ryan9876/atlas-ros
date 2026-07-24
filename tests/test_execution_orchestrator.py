from uuid import uuid4

import pytest

from atlas_ros.adapters.todoist import FakeTodoistAdapter
from atlas_ros.adapters.todoist_execution import TodoistExecutionAdapter
from atlas_ros.domain.models import Action
from atlas_ros.orchestration import (
    ExecutionAuthorization,
    ExecutionOrchestrator,
    ExecutionRequest,
)
from atlas_ros.workflows.w03_todoist import TodoistService, task_description


def request() -> ExecutionRequest:
    return ExecutionRequest(
        correlation_id=uuid4(),
        action_id="A-1",
        existing_task_id="",
        title="Prepare operating review",
        description=task_description(
            "Prepare operating review",
            "The operating review is complete and verified.",
        ),
        project="Work",
        section="",
        labels=(),
        subtasks=("Gather inputs", "Review decisions"),
        subtask_descriptions=(
            task_description("Gather inputs", "Gather inputs is completed and verified."),
            task_description("Review decisions", "Review decisions is completed and verified."),
        ),
    )


def test_orchestrator_requires_explicit_authorization() -> None:
    orchestrator = ExecutionOrchestrator(TodoistExecutionAdapter(FakeTodoistAdapter()))
    with pytest.raises(PermissionError, match="explicit confirmation"):
        orchestrator.execute(request(), ExecutionAuthorization(confirmed=False))


def test_orchestrator_sequences_adapter_operations_and_emits_verified_receipt() -> None:
    provider = FakeTodoistAdapter()
    orchestrator = ExecutionOrchestrator(TodoistExecutionAdapter(provider))
    transaction, receipt = orchestrator.execute(
        request(),
        ExecutionAuthorization(confirmed=True),
    )
    assert transaction.state.value == "verified"
    assert receipt.applied is True
    assert receipt.readback_verified is True
    assert receipt.provider == "todoist"
    assert receipt.provider_object_id == transaction.provider_object_id
    children = provider.list_tasks(parent_id=receipt.provider_object_id)
    assert sorted(child.content for child in children) == [
        "01 — Gather inputs",
        "02 — Review decisions",
    ]


def test_provider_adapter_does_not_accept_authorization_or_planning_inputs() -> None:
    adapter = TodoistExecutionAdapter(FakeTodoistAdapter())
    target = adapter.resolve_target("Work", "", ())
    assert target.project_id == "work"
    assert not hasattr(adapter, "authorize")
    assert not hasattr(adapter, "plan")


def test_legacy_w03_apply_delegates_and_preserves_return_contract() -> None:
    provider = FakeTodoistAdapter()
    service = TodoistService(provider)
    action = Action(
        id="A-1",
        title="Prepare operating review",
        owner="Ryan",
        definition_of_done="The operating review is complete and verified.",
        execution_ready=True,
        delegation_reviewed=True,
    )
    result = service.apply(action, confirmed=True)
    assert result.dry_run is False
    assert result.task_id
    assert service.last_receipt is not None
    assert service.last_receipt.readback_verified is True


def test_orchestrator_wraps_provider_failure_without_false_receipt() -> None:
    class FailingProvider(FakeTodoistAdapter):
        def create_task(self, **kwargs):  # type: ignore[no-untyped-def]
            raise ValueError("provider unavailable")

    orchestrator = ExecutionOrchestrator(TodoistExecutionAdapter(FailingProvider()))
    with pytest.raises(RuntimeError, match="execution transaction"):
        orchestrator.execute(request(), ExecutionAuthorization(confirmed=True))
