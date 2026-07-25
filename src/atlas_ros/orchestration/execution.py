from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID, uuid4

from atlas_ros.contracts import (
    LEGAL_TRANSITIONS,
    ErrorClassification,
    ExecutionAuthorizationV2,
    ExecutionCommandV2,
    ExecutionReceipt,
    ExecutionReceiptV2,
    ExecutionTransactionV2,
    ProviderName,
    ProviderOperation,
    ProviderOperationResult,
    ProviderOperationType,
    RecoveryInstruction,
    TransactionJournalEntry,
    TransactionStateV2,
    deterministic_digest,
    stable_id,
)
from atlas_ros.orchestration.ports import (
    ExecutionProviderPort,
    LegacyTodoistExecutionPort,
    ProviderExecutionError,
)


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

    def __init__(self, adapter: LegacyTodoistExecutionPort) -> None:
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
            raise RuntimeError(
                f"execution transaction {transaction.transaction_id} failed"
            ) from exc

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


@dataclass(frozen=True)
class GovernedRetryPolicy:
    maximum_attempts: int = 3
    backoff_seconds: tuple[float, ...] = (0.0, 0.25, 1.0)

    def __post_init__(self) -> None:
        if self.maximum_attempts < 1 or self.maximum_attempts > 5:
            raise ValueError("retry attempts must remain between one and five")
        if len(self.backoff_seconds) < self.maximum_attempts:
            raise ValueError("retry policy requires one governed delay per attempt")


@dataclass(frozen=True)
class ExecutionEvent:
    event_type: str
    correlation_id: str
    transaction_id: str
    command_id: str
    plan_digest: str
    authorization_digest: str
    operation_id: str = ""
    provider: str = ""
    attempt: int = 0
    state: str = ""
    result_code: str = ""
    receipt_digest: str = ""


@dataclass
class InMemoryExecutionStore:
    transactions: dict[str, ExecutionTransactionV2] = field(default_factory=dict)
    receipts: dict[str, ExecutionReceiptV2] = field(default_factory=dict)
    active_commands: set[str] = field(default_factory=set)


class ExecutionOrchestratorV2:
    """Exact-plan authorization, deterministic provider sequencing, and receipts."""

    def __init__(
        self,
        providers: tuple[ExecutionProviderPort, ...],
        *,
        retry_policy: GovernedRetryPolicy | None = None,
        store: InMemoryExecutionStore | None = None,
        event_sink: Callable[[ExecutionEvent], None] | None = None,
    ) -> None:
        self._providers = {provider.provider_name: provider for provider in providers}
        self._retry_policy = retry_policy or GovernedRetryPolicy()
        self._store = store or InMemoryExecutionStore()
        self._event_sink = event_sink

    @staticmethod
    def build_command(
        *,
        plan_id: str,
        plan_digest: str,
        action_id: str,
        correlation_id: str,
        authorization: ExecutionAuthorizationV2,
        operations: tuple[ProviderOperation, ...],
    ) -> ExecutionCommandV2:
        base = {
            "plan_id": plan_id,
            "plan_digest": plan_digest,
            "action_id": action_id,
            "correlation_id": correlation_id,
            "authorization_digest": authorization.authorization_digest,
            "operations": [operation.model_dump(mode="json") for operation in operations],
        }
        command_id = stable_id("command", base)
        idempotency_key = deterministic_digest(
            {
                "command_id": command_id,
                "plan_digest": plan_digest,
                "action_id": action_id,
            }
        )
        provisional = ExecutionCommandV2(
            command_id=command_id,
            execution_plan_id=plan_id,
            execution_plan_digest=plan_digest,
            authorization_id=authorization.authorization_id,
            authorization_digest=authorization.authorization_digest,
            action_id=action_id,
            correlation_id=correlation_id,
            operations=operations,
            idempotency_key=idempotency_key,
            command_digest="0" * 64,
        )
        command_digest = deterministic_digest(provisional.digest_payload())
        return provisional.model_copy(update={"command_digest": command_digest})

    @staticmethod
    def issue_authorization(
        *,
        plan_id: str,
        plan_digest: str,
        action_id: str,
        correlation_id: str,
        operations: tuple[ProviderOperation, ...],
        reason: str,
        attended_confirmation_evidence: str,
        actor_identity: str = "Ryan",
        replay_policy: Literal["one_time", "idempotent_replay"] = "idempotent_replay",
    ) -> ExecutionAuthorizationV2:
        payload: dict[str, Any] = {
            "authorization_id": stable_id(
                "authorization",
                {
                    "plan_id": plan_id,
                    "plan_digest": plan_digest,
                    "action_id": action_id,
                    "correlation_id": correlation_id,
                },
            ),
            "actor_identity": actor_identity,
            "actor_authority": "production_promotion_owner",
            "execution_plan_id": plan_id,
            "execution_plan_digest": plan_digest,
            "action_id": action_id,
            "provider_scope": frozenset(operation.provider for operation in operations),
            "operation_types": frozenset(operation.operation_type for operation in operations),
            "maximum_object_count": len(operations),
            "reason": reason,
            "attended_confirmation_evidence": attended_confirmation_evidence,
            "issued_at": datetime.now(UTC),
            "replay_policy": replay_policy,
            "correlation_id": correlation_id,
        }
        authorization_digest = deterministic_digest(
            ExecutionAuthorizationV2(
                **payload,
                authorization_digest="0" * 64,
            ).digest_payload()
        )
        return ExecutionAuthorizationV2(
            **payload,
            authorization_digest=authorization_digest,
        )

    def simulate(
        self,
        command: ExecutionCommandV2,
        authorization: ExecutionAuthorizationV2,
    ) -> tuple[ExecutionTransactionV2, ExecutionReceiptV2]:
        return self._run(command, authorization, simulation=True)

    def execute(
        self,
        command: ExecutionCommandV2,
        authorization: ExecutionAuthorizationV2,
    ) -> tuple[ExecutionTransactionV2, ExecutionReceiptV2]:
        return self._run(command, authorization, simulation=False)

    def _run(
        self,
        command: ExecutionCommandV2,
        authorization: ExecutionAuthorizationV2,
        *,
        simulation: bool,
    ) -> tuple[ExecutionTransactionV2, ExecutionReceiptV2]:
        if not command.verify_digest():
            raise ValueError("command digest verification failed")
        if (
            command.authorization_id != authorization.authorization_id
            or command.authorization_digest != authorization.authorization_digest
        ):
            raise PermissionError("command authorization reference differs")
        prior_receipt = self._store.receipts.get(command.command_id)
        if prior_receipt is not None and prior_receipt.applied:
            if authorization.replay_policy != "idempotent_replay":
                raise PermissionError("one-time authorization has already been consumed")
            return self._store.transactions[command.command_id], prior_receipt
        if command.command_id in self._store.active_commands:
            raise RuntimeError("duplicate command is already active")
        authorization.validate_for(
            plan_id=command.execution_plan_id,
            plan_digest=command.execution_plan_digest,
            action_id=command.action_id,
            operations=command.operations,
        )
        self._store.active_commands.add(command.command_id)
        transaction_id = stable_id("transaction", command.command_id)
        context: dict[str, Any] = {}
        entries: list[TransactionJournalEntry] = []
        results: list[ProviderOperationResult] = []
        applied: list[str] = []
        recovery: list[RecoveryInstruction] = []
        state = TransactionStateV2.PREPARED
        self._emit("command_prepared", command, authorization, transaction_id, state)
        state = self._transition(
            entries,
            command,
            transaction_id,
            state,
            TransactionStateV2.AUTHORIZATION_VALIDATED,
            event_type="authorization_validated",
            result="accepted",
        )
        try:
            state = self._transition(
                entries,
                command,
                transaction_id,
                state,
                TransactionStateV2.APPLYING,
                event_type="transaction_started",
                result="simulation" if simulation else "started",
            )
            for operation in command.operations:
                provider = self._providers.get(operation.provider)
                if provider is None:
                    raise ProviderExecutionError(
                        ErrorClassification.VALIDATION_FAILURE,
                        f"provider port is not configured: {operation.provider}",
                    )
                result, state = self._apply_with_retry(
                    provider,
                    operation,
                    command,
                    authorization,
                    transaction_id,
                    context,
                    entries,
                    state,
                    simulation=simulation,
                )
                results.append(result)
                if not simulation and result.applied:
                    applied.append(operation.operation_id)
                if operation.operation_type.name.startswith("VERIFY"):
                    state = self._transition(
                        entries,
                        command,
                        transaction_id,
                        state,
                        TransactionStateV2.VERIFYING,
                        operation=operation,
                        attempt=result.attempt,
                        event_type="readback_passed",
                        result="verified",
                        readback_status="passed",
                        references=result.provider_object_references,
                    )
            final_state = (
                TransactionStateV2.VERIFIED if not simulation else TransactionStateV2.SIMULATED
            )
            state = self._transition(
                entries,
                command,
                transaction_id,
                state,
                final_state,
                event_type="transaction_completed",
                result="verified" if not simulation else "simulation_complete",
            )
        except ProviderExecutionError as exc:
            failed_operation = command.operations[len(results)]
            if applied:
                state = self._transition(
                    entries,
                    command,
                    transaction_id,
                    state,
                    TransactionStateV2.PARTIALLY_APPLIED,
                    operation=failed_operation,
                    event_type="provider_operation_failed",
                    result=str(exc),
                    error=exc.classification,
                )
                state, recovery = self._compensate(
                    command,
                    authorization,
                    transaction_id,
                    context,
                    entries,
                    results,
                    state,
                )
            else:
                state = self._transition(
                    entries,
                    command,
                    transaction_id,
                    state,
                    TransactionStateV2.FAILED,
                    operation=failed_operation,
                    event_type="provider_operation_failed",
                    result=str(exc),
                    error=exc.classification,
                )
        finally:
            self._store.active_commands.discard(command.command_id)

        unapplied = (
            ()
            if state == TransactionStateV2.VERIFIED
            else tuple(
                operation.operation_id
                for operation in command.operations
                if operation.operation_id not in applied
            )
        )
        transaction = ExecutionTransactionV2(
            transaction_id=transaction_id,
            command_id=command.command_id,
            correlation_id=command.correlation_id,
            state=state,
            applied_operation_ids=tuple(applied),
            unapplied_operation_ids=unapplied,
            journal=tuple(entries),
            recovery_instructions=tuple(recovery),
        )
        receipt = self._receipt(
            command,
            authorization,
            transaction,
            results,
            simulation=simulation,
        )
        self._store.transactions[command.command_id] = transaction
        self._store.receipts[command.command_id] = receipt
        self._emit(
            "receipt_generated",
            command,
            authorization,
            transaction_id,
            state,
            receipt_digest=receipt.receipt_digest,
        )
        return transaction, receipt

    def _apply_with_retry(
        self,
        provider: ExecutionProviderPort,
        operation: ProviderOperation,
        command: ExecutionCommandV2,
        authorization: ExecutionAuthorizationV2,
        transaction_id: str,
        context: dict[str, Any],
        entries: list[TransactionJournalEntry],
        state: TransactionStateV2,
        *,
        simulation: bool,
    ) -> tuple[ProviderOperationResult, TransactionStateV2]:
        for attempt in range(1, self._retry_policy.maximum_attempts + 1):
            self._emit(
                "provider_operation_started",
                command,
                authorization,
                transaction_id,
                state,
                operation=operation,
                attempt=attempt,
            )
            try:
                result = provider.execute_operation(
                    operation,
                    context,
                    attempt=attempt,
                    simulation=simulation,
                )
                new_state = (
                    TransactionStateV2.VERIFYING
                    if result.readback_verified
                    else TransactionStateV2.APPLYING
                )
                state = self._transition(
                    entries,
                    command,
                    transaction_id,
                    state,
                    new_state,
                    operation=operation,
                    attempt=attempt,
                    event_type="provider_operation_succeeded",
                    result="simulation" if simulation else "succeeded",
                    readback_status=("passed" if result.readback_verified else "not_required"),
                    references=result.provider_object_references,
                )
                return result, state
            except ProviderExecutionError as exc:
                if exc.uncertain_apply:
                    recovered = provider.readback_before_retry(operation, context)
                    if recovered is not None:
                        state = self._transition(
                            entries,
                            command,
                            transaction_id,
                            state,
                            TransactionStateV2.VERIFYING,
                            operation=operation,
                            attempt=attempt,
                            event_type="readback_passed",
                            result="uncertain apply recovered by readback",
                            readback_status="passed",
                            references=recovered.provider_object_references,
                        )
                        return recovered, state
                if (
                    not exc.classification.retryable
                    or attempt >= self._retry_policy.maximum_attempts
                ):
                    raise
                state = self._transition(
                    entries,
                    command,
                    transaction_id,
                    state,
                    TransactionStateV2.RETRY_PENDING,
                    operation=operation,
                    attempt=attempt,
                    event_type="retry_scheduled",
                    result=str(exc),
                    error=exc.classification,
                    retry_eligible=True,
                )
                state = self._transition(
                    entries,
                    command,
                    transaction_id,
                    state,
                    TransactionStateV2.APPLYING,
                    operation=operation,
                    attempt=attempt + 1,
                    event_type="retry_started",
                    result=f"governed attempt {attempt + 1}",
                )
        raise AssertionError("bounded retry loop exited unexpectedly")

    def _compensate(
        self,
        command: ExecutionCommandV2,
        authorization: ExecutionAuthorizationV2,
        transaction_id: str,
        context: dict[str, Any],
        entries: list[TransactionJournalEntry],
        results: list[ProviderOperationResult],
        state: TransactionStateV2,
    ) -> tuple[TransactionStateV2, list[RecoveryInstruction]]:
        compensable = [
            operation
            for operation in command.operations
            if operation.operation_id in {result.operation_id for result in results}
            and operation.compensation_allowed
        ]
        if not compensable:
            instructions = [
                RecoveryInstruction(
                    operation_id=operation.operation_id,
                    provider=operation.provider,
                    instruction=(
                        "Inspect provider readback and resume the same command only "
                        "after safe state is established."
                    ),
                    evidence_reference=transaction_id,
                )
                for operation in command.operations
                if operation.operation_id not in {result.operation_id for result in results}
            ]
            state = self._transition(
                entries,
                command,
                transaction_id,
                state,
                TransactionStateV2.MANUAL_RECOVERY_REQUIRED,
                event_type="manual_recovery_required",
                result="no safe authorized compensation",
            )
            return state, instructions
        state = self._transition(
            entries,
            command,
            transaction_id,
            state,
            TransactionStateV2.COMPENSATING,
            event_type="compensation_started",
            result="started",
        )
        try:
            for operation in reversed(compensable):
                self._providers[operation.provider].compensate_operation(
                    operation,
                    context,
                    attempt=1,
                )
        except ProviderExecutionError:
            instruction = RecoveryInstruction(
                operation_id=operation.operation_id,
                provider=operation.provider,
                instruction="Compensation failed; inspect provider state and recover manually.",
                evidence_reference=transaction_id,
            )
            state = self._transition(
                entries,
                command,
                transaction_id,
                state,
                TransactionStateV2.MANUAL_RECOVERY_REQUIRED,
                operation=operation,
                event_type="manual_recovery_required",
                result="compensation failed",
            )
            return state, [instruction]
        state = self._transition(
            entries,
            command,
            transaction_id,
            state,
            TransactionStateV2.COMPENSATED,
            event_type="compensation_completed",
            result="compensated",
        )
        return state, []

    @staticmethod
    def _transition(
        entries: list[TransactionJournalEntry],
        command: ExecutionCommandV2,
        transaction_id: str,
        prior: TransactionStateV2,
        new: TransactionStateV2,
        *,
        operation: ProviderOperation | None = None,
        attempt: int = 0,
        event_type: str,
        result: str,
        error: ErrorClassification | None = None,
        retry_eligible: bool = False,
        readback_status: str = "not_required",
        references: tuple[str, ...] = (),
    ) -> TransactionStateV2:
        if new not in LEGAL_TRANSITIONS[prior]:
            raise ValueError(f"illegal transaction transition: {prior} -> {new}")
        payload: dict[str, Any] = {
            "transaction_id": transaction_id,
            "command_id": command.command_id,
            "correlation_id": command.correlation_id,
            "sequence": len(entries) + 1,
            "prior_state": prior,
            "new_state": new,
            "operation_id": operation.operation_id if operation else "",
            "provider": operation.provider if operation else None,
            "attempt": attempt,
            "event_type": event_type,
            "result": result[:500],
            "error_classification": error,
            "retry_eligible": retry_eligible,
            "provider_object_references": references,
            "readback_status": readback_status,
            "previous_entry_digest": entries[-1].entry_digest if entries else "",
        }
        entry = TransactionJournalEntry(
            **payload,
            entry_digest=deterministic_digest(
                TransactionJournalEntry(
                    **payload,
                    entry_digest="0" * 64,
                ).digest_payload()
            ),
        )
        entries.append(entry)
        return new

    @staticmethod
    def _receipt(
        command: ExecutionCommandV2,
        authorization: ExecutionAuthorizationV2,
        transaction: ExecutionTransactionV2,
        results: list[ProviderOperationResult],
        *,
        simulation: bool,
    ) -> ExecutionReceiptV2:
        successful = transaction.state == TransactionStateV2.VERIFIED and not simulation
        readbacks = {
            result.operation_id: result.readback_verified
            for result in results
            if next(
                operation
                for operation in command.operations
                if operation.operation_id == result.operation_id
            ).requires_readback
        }
        references = tuple(
            sorted(
                {reference for result in results for reference in result.provider_object_references}
            )
        )
        attempt_counts = {result.operation_id: result.attempt for result in results}
        receipt_id = stable_id("receipt", command.command_id)
        base: dict[str, Any] = {
            "receipt_id": receipt_id,
            "transaction_id": transaction.transaction_id,
            "command_id": command.command_id,
            "action_id": command.action_id,
            "correlation_id": command.correlation_id,
            "execution_plan_id": command.execution_plan_id,
            "execution_plan_digest": command.execution_plan_digest,
            "authorization_id": authorization.authorization_id,
            "authorization_digest": authorization.authorization_digest,
            "actor": authorization.actor_identity,
            "operations_requested": tuple(
                operation.operation_id for operation in command.operations
            ),
            "operations_applied": (
                tuple(operation.operation_id for operation in command.operations)
                if successful
                else transaction.applied_operation_ids
            ),
            "provider_object_references": references,
            "idempotency_digests": tuple(
                operation.idempotency_key for operation in command.operations
            ),
            "attempt_counts": attempt_counts,
            "final_transaction_state": transaction.state,
            "readback_results": readbacks,
            "hierarchy_verified": any(
                operation.operation_type == ProviderOperationType.VERIFY_HIERARCHY
                and operation.operation_id in attempt_counts
                for operation in command.operations
            ),
            "objective_done_when_verified": any(
                operation.operation_type == ProviderOperationType.VERIFY_PARENT
                and operation.operation_id in attempt_counts
                for operation in command.operations
            ),
            "section_routing_verified": any(
                operation.operation_type == ProviderOperationType.RESOLVE_TARGET
                and operation.operation_id in attempt_counts
                for operation in command.operations
            ),
            "notion_link_verified": (
                any(
                    operation.operation_type == ProviderOperationType.VERIFY_RECORD
                    and operation.operation_id in attempt_counts
                    for operation in command.operations
                )
                if any(
                    operation.provider == ProviderName.NOTION for operation in command.operations
                )
                else None
            ),
            "compensation_result": (
                "compensated" if transaction.state == TransactionStateV2.COMPENSATED else ""
            ),
            "recovery_instructions": transaction.recovery_instructions,
            "evidence_digests": tuple(entry.entry_digest for entry in transaction.journal),
            "applied": successful,
            "readback_verified": successful and all(readbacks.values()),
            "simulation": simulation,
        }
        receipt_digest = deterministic_digest(
            ExecutionReceiptV2(**base, receipt_digest="0" * 64).digest_payload()
        )
        return ExecutionReceiptV2(**base, receipt_digest=receipt_digest)

    def _emit(
        self,
        event_type: str,
        command: ExecutionCommandV2,
        authorization: ExecutionAuthorizationV2,
        transaction_id: str,
        state: TransactionStateV2,
        *,
        operation: ProviderOperation | None = None,
        attempt: int = 0,
        receipt_digest: str = "",
    ) -> None:
        if self._event_sink is None:
            return
        self._event_sink(
            ExecutionEvent(
                event_type=event_type,
                correlation_id=command.correlation_id,
                transaction_id=transaction_id,
                command_id=command.command_id,
                plan_digest=command.execution_plan_digest,
                authorization_digest=authorization.authorization_digest,
                operation_id=operation.operation_id if operation else "",
                provider=operation.provider.value if operation else "",
                attempt=attempt,
                state=state.value,
                result_code=event_type,
                receipt_digest=receipt_digest,
            )
        )
