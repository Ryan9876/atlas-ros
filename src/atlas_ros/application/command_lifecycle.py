"""Attended command-lifecycle coordination through canonical planning."""
from __future__ import annotations

from dataclasses import dataclass

from atlas_ros.capabilities.operational_awareness.command_lifecycle import (
    AtlasCommandParser,
    CommandLifecycleService,
)
from atlas_ros.contracts.execution.transaction import ProposedExecutionPlan
from atlas_ros.contracts.operational_awareness import (
    AtlasCommandV1,
    CommandExecutionReceiptV1,
    CommandInterpretationV1,
    CommandSourceRefV1,
    OperationalSnapshotV1,
    TodoistLifecyclePlanV1,
)
from atlas_ros.policy.operational_awareness import OperationalAwarenessPolicy
from atlas_ros.ports.lifecycle_planning import LifecyclePlanCompilerPort


@dataclass(frozen=True, slots=True)
class CommandLifecycleResult:
    command: AtlasCommandV1
    interpretation: CommandInterpretationV1
    lifecycle_plan: TodoistLifecyclePlanV1 | None
    canonical_plan: ProposedExecutionPlan | None
    receipt: CommandExecutionReceiptV1


@dataclass(frozen=True, slots=True)
class CommandLifecycleCoordinator:
    """Interpret explicit intent and prepare an exact, unexecuted plan."""

    policy: OperationalAwarenessPolicy
    planner: LifecyclePlanCompilerPort

    def prepare(
        self,
        source: CommandSourceRefV1,
        snapshot: OperationalSnapshotV1,
    ) -> CommandLifecycleResult:
        command = AtlasCommandParser(self.policy).parse(source)
        service = CommandLifecycleService(self.policy)
        interpretation = service.interpret(command, snapshot)
        lifecycle: TodoistLifecyclePlanV1 | None = None
        canonical: ProposedExecutionPlan | None = None
        operation_ids: tuple[str, ...] = ()
        if not interpretation.blockers:
            lifecycle = service.plan(interpretation, snapshot)
            canonical = self.planner.compile(lifecycle)
            operation_ids = tuple(item.operation_id for item in canonical.operations)
        receipt = CommandExecutionReceiptV1.create(
            command_digest=command.command_digest,
            interpretation_digest=interpretation.interpretation_digest,
            lifecycle_plan_digest=(lifecycle.plan_digest if lifecycle else "0" * 64),
            canonical_plan_digest=(canonical.plan_digest if canonical else None),
            authorization_id=None,
            operation_identities=operation_ids,
            readback_digests=(),
            provider_write_count=0,
            completion_state="planned_not_executed" if canonical else "blocked",
        )
        return CommandLifecycleResult(
            command=command,
            interpretation=interpretation,
            lifecycle_plan=lifecycle,
            canonical_plan=canonical,
            receipt=receipt,
        )
