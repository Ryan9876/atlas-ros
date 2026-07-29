"""Canonical exact-operation compilation for command lifecycle plans."""
from __future__ import annotations

from dataclasses import dataclass

from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.contracts.execution.transaction import (
    PlannedProviderOperation,
    ProposedExecutionPlan,
)
from atlas_ros.contracts.operational_awareness import TodoistLifecyclePlanV1


class OperationalLifecyclePlanningError(ValueError):
    """Raised when a lifecycle proposal cannot enter canonical planning safely."""


@dataclass(frozen=True, slots=True)
class OperationalLifecycleExecutionPlanner:
    """The sole compiler from typed lifecycle intent to exact provider operations.

    This component plans only. It never authorizes, invokes adapters, or performs
    readback. Exact payload content remains digest-bound to each operation.
    """

    def compile(self, lifecycle: TodoistLifecyclePlanV1) -> ProposedExecutionPlan:
        if lifecycle.blockers:
            return ProposedExecutionPlan.create(
                plan_id=f"lifecycle:{lifecycle.plan_digest[:24]}",
                source_graph_digest=lifecycle.plan_digest,
                blockers=lifecycle.blockers,
            )
        specs = lifecycle.notion_operations + lifecycle.todoist_operations
        if not specs:
            raise OperationalLifecyclePlanningError("lifecycle plan contains no operations")
        if len(specs) > lifecycle.maximum_object_count:
            raise OperationalLifecyclePlanningError("lifecycle object budget exceeded")
        operations = tuple(
            PlannedProviderOperation(
                operation_id=f"oa:{index}:{spec.operation_digest[:20]}",
                sequence=index,
                provider=spec.provider,
                action=spec.action,
                target=spec.target,
                payload_digest=sha256_digest(spec.payload),
                idempotency_key=spec.idempotency_key,
            )
            for index, spec in enumerate(specs)
        )
        return ProposedExecutionPlan.create(
            plan_id=f"lifecycle:{lifecycle.plan_digest[:24]}",
            source_graph_digest=lifecycle.plan_digest,
            operations=operations,
        )
