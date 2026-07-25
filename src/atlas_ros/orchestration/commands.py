from __future__ import annotations

from atlas_ros.contracts import (
    ExecutionPlanV2,
    ProviderName,
    ProviderOperation,
    ProviderOperationType,
    deterministic_digest,
)


class ExecutionCommandFactory:
    """Projects an already-governed plan into ordered provider operations."""

    @staticmethod
    def todoist_operations(
        plan: ExecutionPlanV2,
        *,
        project: str,
        section: str,
        labels: tuple[str, ...] = (),
        existing_parent_id: str = "",
    ) -> tuple[ProviderOperation, ...]:
        if not plan.verify_digest():
            raise ValueError("Execution Plan V2 digest verification failed")
        parent = plan.parent_outcome
        if parent is None:
            raise ValueError("Todoist execution requires a planned parent outcome")
        specs: list[tuple[ProviderOperationType, dict[str, object]]] = [
            (
                ProviderOperationType.RESOLVE_TARGET,
                {"project": project, "section": section, "labels": labels},
            ),
            (
                ProviderOperationType.READ_PARENT,
                {"existing_task_id": existing_parent_id},
            ),
            (
                ProviderOperationType.UPSERT_PARENT,
                {
                    "action_id": plan.action_id,
                    "existing_task_id": existing_parent_id,
                    "title": parent.title,
                    "objective": parent.objective,
                    "done_when": parent.done_when,
                },
            ),
            (
                ProviderOperationType.VERIFY_PARENT,
                {
                    "title": parent.title,
                    "objective": parent.objective,
                    "done_when": parent.done_when,
                },
            ),
            (ProviderOperationType.READ_CHILDREN, {}),
        ]
        for step in plan.projected_steps:
            payload = {
                "action_id": plan.action_id,
                "sequence": step.sequence,
                "raw_title": step.title,
                "objective": step.objective,
                "done_when": step.done_when,
            }
            specs.append((ProviderOperationType.UPSERT_CHILD, payload))
            specs.append((ProviderOperationType.VERIFY_CHILD, {"sequence": step.sequence}))
        specs.append(
            (
                ProviderOperationType.VERIFY_HIERARCHY,
                {
                    "expected_titles": tuple(
                        f"{step.sequence:02d} — {step.title}" for step in plan.projected_steps
                    )
                },
            )
        )
        return ExecutionCommandFactory._operations(
            plan.plan_digest,
            plan.action_id,
            ProviderName.TODOIST,
            specs,
        )

    @staticmethod
    def notion_operations(
        plan: ExecutionPlanV2,
        *,
        identity: str,
        properties: dict[str, object],
    ) -> tuple[ProviderOperation, ...]:
        if not plan.verify_digest():
            raise ValueError("Execution Plan V2 digest verification failed")
        specs: list[tuple[ProviderOperationType, dict[str, object]]] = [
            (ProviderOperationType.FIND_RECORD, {"identity": identity}),
            (
                ProviderOperationType.UPSERT_RECORD,
                {"identity": identity, "properties": properties},
            ),
            (
                ProviderOperationType.VERIFY_RECORD,
                {"identity": identity, "properties": properties},
            ),
        ]
        return ExecutionCommandFactory._operations(
            plan.plan_digest,
            plan.action_id,
            ProviderName.NOTION,
            specs,
        )

    @staticmethod
    def _operations(
        plan_digest: str,
        action_id: str,
        provider: ProviderName,
        specs: list[tuple[ProviderOperationType, dict[str, object]]],
    ) -> tuple[ProviderOperation, ...]:
        return tuple(
            ProviderOperation(
                operation_id=f"{provider.value}:{action_id}:{index}:{operation_type.value}",
                provider=provider,
                operation_type=operation_type,
                sequence=index,
                payload=payload,
                idempotency_key=deterministic_digest(
                    {
                        "plan_digest": plan_digest,
                        "action_id": action_id,
                        "provider": provider,
                        "sequence": index,
                        "operation_type": operation_type,
                        "payload": payload,
                    }
                ),
            )
            for index, (operation_type, payload) in enumerate(specs, 1)
        )
