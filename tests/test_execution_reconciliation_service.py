from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

from atlas_ros.services.execution_reconciliation import ExecutionReconciliationService
from atlas_ros.workflows.w04_reconciliation import (
    ReconciliationPlan,
    ReconciliationResult,
    TodoistReconciliationService,
)


class MemoryStateStore:
    def __init__(self) -> None:
        self.value = datetime(2026, 7, 23, tzinfo=UTC)

    def checkpoint(self) -> datetime:
        return self.value

    def set_checkpoint(self, value: datetime) -> None:
        self.value = value


def service_with_state() -> tuple[ExecutionReconciliationService, MemoryStateStore]:
    service = object.__new__(ExecutionReconciliationService)
    state = MemoryStateStore()
    service.state_store = state
    return service, state


def empty_plan(*, conflicts: tuple[str, ...] = ()) -> ReconciliationPlan:
    return ReconciliationPlan(
        generated_at=datetime(2026, 7, 24, tzinfo=UTC),
        mutations=(),
        conflicts=conflicts,
    )


def test_conflicts_restore_checkpoint() -> None:
    service, state = service_with_state()
    original = state.checkpoint()

    def legacy_apply(*args: object, **kwargs: object) -> ReconciliationResult:
        state.set_checkpoint(datetime(2026, 7, 24, tzinfo=UTC))
        return ReconciliationResult(1, 0, 1, 0, 0)

    with patch.object(TodoistReconciliationService, "apply", side_effect=legacy_apply):
        result = service.apply(empty_plan(conflicts=("conflict",)), confirmed=True)
    assert result.conflicts == 1
    assert state.checkpoint() == original


def test_consistent_result_advances_canonical_checkpoint() -> None:
    service, _ = service_with_state()
    with patch.object(
        TodoistReconciliationService,
        "apply",
        return_value=ReconciliationResult(2, 2, 0, 0, 2),
    ):
        outcome = service.apply_with_contract(empty_plan(), confirmed=True)
    assert outcome.canonical.consistent is True
    assert outcome.canonical.checkpoint_advanced is True
    assert outcome.canonical.mismatches == []


def test_conflict_result_is_fail_closed() -> None:
    service, _ = service_with_state()
    with patch.object(
        TodoistReconciliationService,
        "apply",
        return_value=ReconciliationResult(1, 0, 1, 0, 0),
    ):
        outcome = service.apply_with_contract(
            empty_plan(conflicts=("task-1: concurrent field conflict",)),
            confirmed=True,
        )
    assert outcome.canonical.consistent is False
    assert outcome.canonical.checkpoint_advanced is False
    assert outcome.canonical.mismatches == ["task-1: concurrent field conflict"]
