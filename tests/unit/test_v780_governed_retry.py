from __future__ import annotations

from typing import Any

from atlas_ros.adapters.errors import parse_retry_after
from atlas_ros.contracts import (
    ErrorClassification,
    ProviderName,
    ProviderOperation,
    ProviderOperationResult,
    ProviderOperationType,
    TransactionStateV2,
    deterministic_digest,
)
from atlas_ros.orchestration import (
    ExecutionOrchestratorV2,
    FakeExecutionProvider,
    FaultMode,
    GovernedRetryPolicy,
    ProviderExecutionError,
)


def operation() -> ProviderOperation:
    operation_id = "todoist:1:upsert_parent"
    return ProviderOperation(
        operation_id=operation_id,
        provider=ProviderName.TODOIST,
        operation_type=ProviderOperationType.UPSERT_PARENT,
        sequence=1,
        payload={"value": 1},
        idempotency_key=deterministic_digest({"operation_id": operation_id}),
    )


def command_and_authorization(op: ProviderOperation):
    plan_digest = deterministic_digest({"plan": "retry", "revision": 1})
    authorization = ExecutionOrchestratorV2.issue_authorization(
        plan_id="plan-retry",
        plan_digest=plan_digest,
        action_id="A-RETRY",
        correlation_id="correlation-retry",
        operations=(op,),
        reason="Attended retry test",
        attended_confirmation_evidence="Ryan selected the exact retry test action.",
    )
    command = ExecutionOrchestratorV2.build_command(
        plan_id="plan-retry",
        plan_digest=plan_digest,
        action_id="A-RETRY",
        correlation_id="correlation-retry",
        authorization=authorization,
        operations=(op,),
    )
    return command, authorization


def test_governed_backoff_calls_injected_sleeper_and_is_journaled() -> None:
    op = operation()
    provider = FakeExecutionProvider(
        ProviderName.TODOIST,
        {op.operation_id: (FaultMode.RATE_LIMIT, FaultMode.SUCCESS)},
    )
    delays: list[float] = []
    orchestrator = ExecutionOrchestratorV2(
        (provider,),
        retry_policy=GovernedRetryPolicy(
            maximum_attempts=2,
            backoff_seconds=(0.0, 1.5),
            maximum_delay_seconds=10.0,
        ),
        sleeper=delays.append,
    )
    command, authorization = command_and_authorization(op)

    transaction, receipt = orchestrator.execute(command, authorization)

    assert transaction.state == TransactionStateV2.VERIFIED
    assert receipt.attempt_counts[op.operation_id] == 2
    assert delays == [1.5]
    scheduled = next(entry for entry in transaction.journal if entry.event_type == "retry_scheduled")
    assert "delay_seconds=1.5" in scheduled.result
    assert "delay_source=governed_backoff" in scheduled.result


class RetryAfterProvider(FakeExecutionProvider):
    def execute_operation(
        self,
        operation: ProviderOperation,
        context: dict[str, Any],
        *,
        attempt: int,
        simulation: bool = False,
    ) -> ProviderOperationResult:
        if attempt == 1:
            self.attempts[operation.operation_id] += 1
            raise ProviderExecutionError(
                ErrorClassification.RETRYABLE_RATE_LIMIT,
                "provider rate limit",
                retry_after_seconds=120.0,
            )
        return super().execute_operation(
            operation,
            context,
            attempt=attempt,
            simulation=simulation,
        )


def test_valid_retry_after_is_bounded_and_preferred() -> None:
    op = operation()
    provider = RetryAfterProvider(ProviderName.TODOIST)
    delays: list[float] = []
    orchestrator = ExecutionOrchestratorV2(
        (provider,),
        retry_policy=GovernedRetryPolicy(
            maximum_attempts=2,
            backoff_seconds=(0.0, 2.0),
            maximum_delay_seconds=5.0,
        ),
        sleeper=delays.append,
    )
    command, authorization = command_and_authorization(op)

    transaction, _ = orchestrator.execute(command, authorization)

    assert delays == [5.0]
    scheduled = next(entry for entry in transaction.journal if entry.event_type == "retry_scheduled")
    assert "delay_source=provider_retry_after" in scheduled.result


def test_retry_after_parser_rejects_malformed_values() -> None:
    assert parse_retry_after("15") == 15.0
    assert parse_retry_after(" 0 ") == 0.0
    assert parse_retry_after("-1") is None
    assert parse_retry_after("tomorrow") is None
    assert parse_retry_after("Wed, 21 Oct 2015 07:28:00 GMT") is None
