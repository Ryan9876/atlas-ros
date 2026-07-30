"""V7.8.0 governed retry hardening for attended execution orchestration.

Provider adapters remain single-attempt transports. This module keeps delay selection,
sleeping, evidence, and uncertain-write readback in the orchestration layer.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

from atlas_ros.adapters.errors import AdapterError
from atlas_ros.contracts import (
    ExecutionAuthorizationV2,
    ExecutionCommandV2,
    ProviderOperation,
    ProviderOperationResult,
    TransactionJournalEntry,
    TransactionStateV2,
)
from atlas_ros.orchestration.execution import ExecutionEvent
from atlas_ros.orchestration.execution import ExecutionOrchestratorV2 as _BaseOrchestrator
from atlas_ros.orchestration.execution import GovernedRetryPolicy as _BaseRetryPolicy
from atlas_ros.orchestration.execution import InMemoryExecutionStore
from atlas_ros.orchestration.ports import ExecutionProviderPort, ProviderExecutionError


@dataclass(frozen=True)
class GovernedRetryPolicy(_BaseRetryPolicy):
    """Bounded retry policy owned exclusively by governed orchestration."""

    maximum_delay_seconds: float = 60.0
    allow_provider_retry_after: bool = True

    def __post_init__(self) -> None:
        super().__post_init__()
        if any(delay < 0 for delay in self.backoff_seconds):
            raise ValueError("retry delays cannot be negative")
        if self.maximum_delay_seconds < 0:
            raise ValueError("maximum retry delay cannot be negative")

    def delay_for(
        self,
        *,
        failed_attempt: int,
        retry_after_seconds: float | None,
    ) -> tuple[float, str]:
        """Choose a deterministic bounded delay for the next governed attempt."""
        if (
            self.allow_provider_retry_after
            and retry_after_seconds is not None
            and retry_after_seconds >= 0
        ):
            return min(retry_after_seconds, self.maximum_delay_seconds), "provider_retry_after"
        index = min(failed_attempt, len(self.backoff_seconds) - 1)
        return min(self.backoff_seconds[index], self.maximum_delay_seconds), "governed_backoff"


class ExecutionOrchestratorV2(_BaseOrchestrator):
    """Execution orchestrator with injectable, journaled, bounded retry delays."""

    def __init__(
        self,
        providers: tuple[ExecutionProviderPort, ...],
        *,
        retry_policy: GovernedRetryPolicy | None = None,
        store: InMemoryExecutionStore | None = None,
        event_sink: Callable[[ExecutionEvent], None] | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        super().__init__(
            providers,
            retry_policy=retry_policy or GovernedRetryPolicy(),
            store=store,
            event_sink=event_sink,
        )
        self._sleeper = sleeper

    @staticmethod
    def _retry_after(exc: ProviderExecutionError) -> float | None:
        if exc.retry_after_seconds is not None:
            return exc.retry_after_seconds
        cause = exc.__cause__
        return cause.retry_after_seconds if isinstance(cause, AdapterError) else None

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
        policy = cast(GovernedRetryPolicy, self._retry_policy)
        for attempt in range(1, policy.maximum_attempts + 1):
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
                if not exc.classification.retryable or attempt >= policy.maximum_attempts:
                    raise
                delay, delay_source = policy.delay_for(
                    failed_attempt=attempt,
                    retry_after_seconds=self._retry_after(exc),
                )
                state = self._transition(
                    entries,
                    command,
                    transaction_id,
                    state,
                    TransactionStateV2.RETRY_PENDING,
                    operation=operation,
                    attempt=attempt,
                    event_type="retry_scheduled",
                    result=(
                        f"{exc}; delay_seconds={delay:g}; delay_source={delay_source}; "
                        f"next_attempt={attempt + 1}"
                    ),
                    error=exc.classification,
                    retry_eligible=True,
                )
                if not simulation and delay > 0:
                    self._sleeper(delay)
                state = self._transition(
                    entries,
                    command,
                    transaction_id,
                    state,
                    TransactionStateV2.APPLYING,
                    operation=operation,
                    attempt=attempt + 1,
                    event_type="retry_started",
                    result=f"governed attempt {attempt + 1} after {delay:g}s {delay_source}",
                )
        raise AssertionError("bounded retry loop exited unexpectedly")
