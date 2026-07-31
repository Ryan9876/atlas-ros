"""Attended composite ingress reconciliation contracts.

The composite coordinator joins Universal Inbox review and Todoist execution/comment
review without merging their authority or write paths. It is planning-only.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.reconciliation.service import ReconciliationPlan, TodoistReconciliationService


class ReconciliationScope(StrEnum):
    COMPOSITE = "composite"
    UNIVERSAL_INBOX_ONLY = "universal-inbox-only"
    TODOIST_ONLY = "todoist-only"
    TODOIST_TASK = "todoist-task"


@dataclass(frozen=True, slots=True)
class ReconciliationInvocation:
    scope: ReconciliationScope
    task_selector: str = ""


@dataclass(frozen=True, slots=True)
class UniversalInboxDryRun:
    records_inspected: int
    proposed_mutations: tuple[dict[str, object], ...] = ()
    blocked: tuple[str, ...] = ()
    ignored: tuple[str, ...] = ()

    @property
    def plan_digest(self) -> str:
        return sha256_digest(
            {
                "records_inspected": self.records_inspected,
                "proposed_mutations": self.proposed_mutations,
                "blocked": self.blocked,
                "ignored": self.ignored,
            }
        )


class UniversalInboxPlanner(Protocol):
    def plan(self) -> UniversalInboxDryRun: ...


@dataclass(frozen=True, slots=True)
class CompositeIngressPlan:
    invocation: ReconciliationInvocation
    universal_inbox: UniversalInboxDryRun | None
    todoist: ReconciliationPlan | None

    @property
    def sources_checked(self) -> tuple[str, ...]:
        sources: list[str] = []
        if self.universal_inbox is not None:
            sources.append("universal-inbox")
        if self.todoist is not None:
            sources.append("todoist")
        return tuple(sources)

    @property
    def plan_digest(self) -> str:
        return sha256_digest(
            {
                "scope": self.invocation.scope.value,
                "task_selector": self.invocation.task_selector,
                "universal_inbox": (
                    self.universal_inbox.plan_digest if self.universal_inbox else None
                ),
                "todoist": self.todoist.plan_digest if self.todoist else None,
            }
        )


@dataclass(frozen=True, slots=True)
class CompositeIngressReconciler:
    universal_inbox: UniversalInboxPlanner
    todoist: TodoistReconciliationService

    def plan(self, invocation: ReconciliationInvocation) -> CompositeIngressPlan:
        inbox_plan: UniversalInboxDryRun | None = None
        todoist_plan: ReconciliationPlan | None = None
        if invocation.scope in {
            ReconciliationScope.COMPOSITE,
            ReconciliationScope.UNIVERSAL_INBOX_ONLY,
        }:
            inbox_plan = self.universal_inbox.plan()
        if invocation.scope in {
            ReconciliationScope.COMPOSITE,
            ReconciliationScope.TODOIST_ONLY,
            ReconciliationScope.TODOIST_TASK,
        }:
            todoist_plan = self.todoist.plan(
                task_id=(
                    invocation.task_selector
                    if invocation.scope == ReconciliationScope.TODOIST_TASK
                    else ""
                )
            )
        return CompositeIngressPlan(
            invocation=invocation,
            universal_inbox=inbox_plan,
            todoist=todoist_plan,
        )


def parse_reconciliation_invocation(text: str) -> ReconciliationInvocation:
    """Resolve attended natural-language invocation aliases deterministically."""

    normalized = " ".join(text.strip().casefold().split())
    if normalized in {"reconcile ros", "reconcile ros inbox"}:
        return ReconciliationInvocation(ReconciliationScope.COMPOSITE)
    if normalized == "reconcile universal inbox only":
        return ReconciliationInvocation(ReconciliationScope.UNIVERSAL_INBOX_ONLY)
    if normalized == "reconcile todoist only":
        return ReconciliationInvocation(ReconciliationScope.TODOIST_ONLY)
    prefix = "reconcile "
    if normalized.startswith(prefix):
        selector = text.strip()[len(prefix) :].strip()
        if selector:
            return ReconciliationInvocation(
                ReconciliationScope.TODOIST_TASK,
                task_selector=selector,
            )
    raise ValueError("unrecognized reconciliation invocation")
