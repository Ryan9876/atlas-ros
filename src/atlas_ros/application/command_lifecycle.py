"""Attended command-lifecycle coordination through canonical planning."""
from __future__ import annotations

from dataclasses import dataclass

from atlas_ros.capabilities.operational_awareness.command_lifecycle import (
    AtlasCommandParser,
    CommandLifecycleService,
    TaskUpdateLifecycleNormalizer,
)
from atlas_ros.capabilities.operational_awareness.command_lifecycle.natural_delegation import (
    bind_natural_delegation_identities,
    bind_natural_delegation_plan,
)
from atlas_ros.contracts.execution.transaction import ProposedExecutionPlan
from atlas_ros.contracts.operational_awareness import (
    AtlasCommandV1,
    CommandExecutionReceiptV1,
    CommandInterpretationV1,
    CommandSourceRefV1,
    OperationalSnapshotV1,
    TaskUpdateLifecycleNormalizationV1,
    TodoistLifecyclePlanV1,
)
from atlas_ros.policy.operational_awareness import OperationalAwarenessPolicy
from atlas_ros.ports.lifecycle_planning import LifecyclePlanCompilerPort


@dataclass(frozen=True, slots=True)
class CommandLifecycleResult:
    command: AtlasCommandV1
    normalization: TaskUpdateLifecycleNormalizationV1 | None
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
        normalization: TaskUpdateLifecycleNormalizationV1 | None = None
        if source.source_command_text.lstrip().lower().startswith("@atlas"):
            command = AtlasCommandParser(self.policy).parse(source)
        else:
            normalization = TaskUpdateLifecycleNormalizer(self.policy).normalize(
                source,
                snapshot,
            )
            normalization = bind_natural_delegation_identities(
                normalization,
                snapshot,
            )
            command = normalization.proposed_command
        service = CommandLifecycleService(self.policy)
        interpretation = service.interpret(command, snapshot)
        lifecycle: TodoistLifecyclePlanV1 | None = None
        canonical: ProposedExecutionPlan | None = None
        operation_ids: tuple[str, ...] = ()
        if not interpretation.blockers:
            lifecycle = service.plan(interpretation, snapshot)
            if normalization is not None:
                lifecycle = bind_natural_delegation_plan(lifecycle)
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
            normalization=normalization,
            interpretation=interpretation,
            lifecycle_plan=lifecycle,
            canonical_plan=canonical,
            receipt=receipt,
        )
