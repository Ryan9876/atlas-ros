from __future__ import annotations

from dataclasses import dataclass

from atlas_ros.reconciliation.composite import (
    CompositeIngressReconciler,
    ReconciliationScope,
    UniversalInboxDryRun,
    parse_reconciliation_invocation,
)
from atlas_ros.reconciliation.service import ReconciliationPlan, ReconciliationScopeReport


@dataclass
class InboxPlanner:
    calls: int = 0

    def plan(self) -> UniversalInboxDryRun:
        self.calls += 1
        return UniversalInboxDryRun(records_inspected=2)


@dataclass
class TodoistPlanner:
    calls: list[str]

    def plan(self, *, full: bool = False, task_id: str = "") -> ReconciliationPlan:
        del full
        self.calls.append(task_id)
        return ReconciliationPlan(
            generated_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
            mutations=(),
            scope_report=ReconciliationScopeReport(comments_inspected=1),
        )


def test_composite_aliases_check_inbox_and_todoist() -> None:
    for text in ("Reconcile ROS", "Reconcile ROS inbox"):
        invocation = parse_reconciliation_invocation(text)
        inbox = InboxPlanner()
        todoist = TodoistPlanner([])
        plan = CompositeIngressReconciler(inbox, todoist).plan(invocation)
        assert invocation.scope == ReconciliationScope.COMPOSITE
        assert plan.sources_checked == ("universal-inbox", "todoist")
        assert inbox.calls == 1 and todoist.calls == [""]


def test_scoped_invocations_remain_isolated() -> None:
    inbox = InboxPlanner()
    todoist = TodoistPlanner([])
    reconciler = CompositeIngressReconciler(inbox, todoist)

    inbox_only = reconciler.plan(
        parse_reconciliation_invocation("Reconcile Universal Inbox only")
    )
    assert inbox_only.sources_checked == ("universal-inbox",)
    assert todoist.calls == []

    todoist_only = reconciler.plan(parse_reconciliation_invocation("Reconcile Todoist only"))
    assert todoist_only.sources_checked == ("todoist",)

    scoped = reconciler.plan(parse_reconciliation_invocation("Reconcile parent-123"))
    assert scoped.invocation.scope == ReconciliationScope.TODOIST_TASK
    assert todoist.calls[-1] == "parent-123"
