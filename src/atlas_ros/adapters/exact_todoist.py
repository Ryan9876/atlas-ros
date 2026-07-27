"""Exact Todoist execution adapter with checksum-bound payload resolution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypedDict

from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.contracts.execution.transaction import (
    PlannedProviderOperation,
    ProviderReadbackReceipt,
    ProviderWriteReceipt,
)
from atlas_ros.ports.execution import ExecutionPayloadPort
from atlas_ros.ports.todoist import TodoistClientPort, TodoistTaskRecord


class ExactTodoistExecutionError(RuntimeError):
    """Raised when an authorized operation cannot be translated exactly."""


class TodoistCreatePayload(TypedDict):
    content: str
    project_id: str
    section_id: str | None
    parent_id: str | None
    description: str


def todoist_target(
    project_id: str,
    *,
    section_id: str | None = None,
    parent_id: str | None = None,
) -> str:
    """Return the canonical target identity for a Todoist create operation."""
    parts = [f"project:{project_id}"]
    if section_id is not None:
        parts.append(f"section:{section_id}")
    if parent_id is not None:
        parts.append(f"parent:{parent_id}")
    return "/".join(parts)


@dataclass(frozen=True, slots=True)
class ExactTodoistExecutionAdapter:
    """Execute exact Todoist creates; never plan, authorize, or add fields."""

    client: TodoistClientPort
    payloads: ExecutionPayloadPort

    def write(
        self,
        operation: PlannedProviderOperation,
        *,
        authorization_id: str,
        transaction_id: str,
    ) -> ProviderWriteReceipt:
        if not authorization_id.strip() or not transaction_id.strip():
            raise ExactTodoistExecutionError(
                "Todoist execution requires authorization and transaction IDs"
            )
        if operation.provider != "todoist":
            raise ExactTodoistExecutionError(
                "Todoist adapter received an operation for another provider"
            )
        if operation.action != "create":
            raise ExactTodoistExecutionError(
                f"unsupported Todoist execution action: {operation.action}"
            )
        payload = self.payloads.resolve(operation)
        if payload.operation_id != operation.operation_id:
            raise ExactTodoistExecutionError(
                "resolved payload references a different operation"
            )
        if payload.payload_digest != operation.payload_digest:
            raise ExactTodoistExecutionError(
                "resolved payload digest does not match operation"
            )
        values = _validate_create_payload(payload.data)
        expected_target = todoist_target(
            values["project_id"],
            section_id=values["section_id"],
            parent_id=values["parent_id"],
        )
        if operation.target != expected_target:
            raise ExactTodoistExecutionError(
                "Todoist operation target disagrees with exact payload destination"
            )
        task = self.client.create_task(
            content=values["content"],
            project_id=values["project_id"],
            section_id=values["section_id"],
            parent_id=values["parent_id"],
            description=values["description"],
            idempotency_key=operation.idempotency_key,
        )
        return ProviderWriteReceipt(
            operation_id=operation.operation_id,
            provider="todoist",
            provider_record_id=task.id,
            idempotency_key=operation.idempotency_key,
            write_digest=sha256_digest(_task_projection(task)),
            changed=True,
        )

    def readback(self, receipt: ProviderWriteReceipt) -> ProviderReadbackReceipt:
        if receipt.provider != "todoist":
            raise ExactTodoistExecutionError(
                "Todoist readback received a different provider"
            )
        task = self.client.get_task(receipt.provider_record_id)
        return ProviderReadbackReceipt(
            operation_id=receipt.operation_id,
            provider_record_id=task.id,
            readback_digest=sha256_digest(_task_projection(task)),
        )


def _validate_create_payload(payload: dict[str, Any]) -> TodoistCreatePayload:
    allowed = {"content", "project_id", "section_id", "parent_id", "description"}
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ExactTodoistExecutionError(
            "Todoist payload contains unsupported fields: " + ", ".join(unknown)
        )
    content = _required_string(payload, "content")
    project_id = _required_string(payload, "project_id")
    section_id = _optional_string(payload.get("section_id"), "section_id")
    parent_id = _optional_string(payload.get("parent_id"), "parent_id")
    description = payload.get("description", "")
    if not isinstance(description, str):
        raise ExactTodoistExecutionError(
            "Todoist payload description must be a string"
        )
    return {
        "content": content,
        "project_id": project_id,
        "section_id": section_id,
        "parent_id": parent_id,
        "description": description,
    }


def _required_string(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ExactTodoistExecutionError(
            f"Todoist payload requires non-empty {field}"
        )
    return value


def _optional_string(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ExactTodoistExecutionError(
            f"Todoist payload {field} must be a non-empty string or null"
        )
    return value


def _task_projection(task: TodoistTaskRecord) -> dict[str, str | None]:
    return {
        "content": task.content,
        "project_id": task.project_id,
        "section_id": task.section_id,
        "parent_id": task.parent_id,
        "description": task.description,
    }


__all__ = [
    "ExactTodoistExecutionAdapter",
    "ExactTodoistExecutionError",
    "todoist_target",
]
