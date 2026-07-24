from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID, uuid4

from atlas_ros.adapters.todoist_execution import TodoistExecutionAdapter
from atlas_ros.contracts import ExecutionReceipt


class TransactionState(StrEnum):
    PREPARED = "prepared"
    APPLYING = "applying"
    VERIFIED = "verified"
    FAILED = "failed"


@dataclass(frozen=True)
class ExecutionAuthorization:
    confirmed: bool
    actor: str = "Ryan"
    reason: str = "Explicit attended confirmation"


@dataclass(frozen=True)
class ExecutionRequest:
    correlation_id: UUID
    action_id: str
    existing_task_id: str
    title: str
    description: str
    project: str
    section: str
    labels: tuple[str, ...]
    subtasks: tuple[str, ...]
    subtask_descriptions: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.action_id.strip() or not self.title.strip() or not self.description.strip():
            raise ValueError("execution request requires action id, title, and description")
        if len(self.subtasks) != len(self.subtask_descriptions):
            raise ValueError("subtask titles and descriptions must have equal length")


@dataclass(frozen=True)
class ExecutionTransaction:
    transaction_id: UUID
    action_id: str
    state: TransactionState
    provider_object_id: str = ""
    error: str = ""


class ExecutionOrchestrator:
    """Owns attended authorization, sequencing, transaction state, and receipts."""

    def __init__(self, adapter: TodoistExecutionAdapter) -> None:
        self._adapter = adapter

    def execute(
        self,
        request: ExecutionRequest,
        authorization: ExecutionAuthorization,
    ) -> tuple[ExecutionTransaction, ExecutionReceipt]:
        if not authorization.confirmed:
            raise PermissionError("explicit confirmation is required")
        transaction_id = uuid4()
        try:
            target = self._adapter.resolve_target(
                request.project,
                request.section,
                request.labels,
            )
            parent = self._adapter.upsert_parent(
                action_id=request.action_id,
                existing_task_id=request.existing_task_id,
                title=request.title,
                description=request.description,
                target=target,
            )
            existing = self._adapter.children_by_content(parent.id)
            expected_titles: list[str] = []
            for index, (raw_title, description) in enumerate(
                zip(request.subtasks, request.subtask_descriptions, strict=True),
                1,
            ):
                title = f"{index:02d} — {raw_title}"
                expected_titles.append(title)
                self._adapter.upsert_child(
                    action_id=request.action_id,
                    parent_id=parent.id,
                    project_id=target.project_id,
                    sequence=index,
                    raw_title=raw_title,
                    description=description,
                    existing=existing.get(title),
                )
            self._adapter.verify_tree(parent.id, expected_titles)
        except Exception as exc:
            transaction = ExecutionTransaction(
                transaction_id=transaction_id,
                action_id=request.action_id,
                state=TransactionState.FAILED,
                error=str(exc),
            )
            raise RuntimeError(f"execution transaction {transaction.transaction_id} failed") from exc

        transaction = ExecutionTransaction(
            transaction_id=transaction_id,
            action_id=request.action_id,
            state=TransactionState.VERIFIED,
            provider_object_id=parent.id,
        )
        receipt = ExecutionReceipt(
            correlation_id=request.correlation_id,
            source_component="orchestration.execution",
            action_id=request.action_id,
            provider="todoist",
            provider_object_id=parent.id,
            applied=True,
            readback_verified=True,
            evidence={
                "transaction_id": str(transaction_id),
                "authorization_actor": authorization.actor,
                "authorization_reason": authorization.reason,
                "subtask_count": str(len(request.subtasks)),
            },
        )
        return transaction, receipt

    def move_group(
        self,
        task_id: str,
        target_section_id: str,
        authorization: ExecutionAuthorization,
    ) -> ExecutionTransaction:
        if not authorization.confirmed:
            raise PermissionError("explicit confirmation is required")
        transaction_id = uuid4()
        try:
            self._adapter.move_group(task_id, target_section_id)
        except Exception as exc:
            raise RuntimeError(f"execution transaction {transaction_id} failed") from exc
        return ExecutionTransaction(
            transaction_id=transaction_id,
            action_id=task_id,
            state=TransactionState.VERIFIED,
            provider_object_id=task_id,
        )
