from __future__ import annotations

from collections import defaultdict
from enum import StrEnum
from typing import Any

from atlas_ros.contracts import (
    ErrorClassification,
    ProviderName,
    ProviderOperation,
    ProviderOperationResult,
    ProviderOperationType,
    deterministic_digest,
)
from atlas_ros.orchestration.ports import ProviderExecutionError


class FaultMode(StrEnum):
    SUCCESS = "success"
    TIMEOUT_BEFORE_APPLY = "timeout_before_apply"
    TIMEOUT_AFTER_APPLY = "timeout_after_apply"
    RATE_LIMIT = "rate_limit"
    SERVER_FAILURE = "server_failure"
    VALIDATION_FAILURE = "validation_failure"
    PERMISSION_FAILURE = "permission_failure"
    MALFORMED_RESPONSE = "malformed_response"
    READBACK_MISMATCH = "readback_mismatch"
    HIERARCHY_CORRUPTION = "hierarchy_corruption"
    DUPLICATE_RESPONSE = "duplicate_response"
    SCHEMA_DRIFT = "schema_drift"
    COMPENSATION_FAILURE = "compensation_failure"


class FakeExecutionProvider:
    """Deterministic fault-injection provider; never reaches a live service."""

    def __init__(
        self,
        provider_name: ProviderName,
        faults: dict[str, tuple[FaultMode, ...]] | None = None,
    ) -> None:
        self.provider_name = provider_name
        self.faults = faults or {}
        self.attempts: dict[str, int] = defaultdict(int)
        self.objects: dict[str, str] = {}
        self.operation_log: list[str] = []
        self.compensation_log: list[str] = []

    def execute_operation(
        self,
        operation: ProviderOperation,
        context: dict[str, Any],
        *,
        attempt: int,
        simulation: bool = False,
    ) -> ProviderOperationResult:
        del context
        if operation.provider != self.provider_name:
            raise ProviderExecutionError(
                ErrorClassification.VALIDATION_FAILURE,
                "fake provider received mismatched provider operation",
            )
        self.attempts[operation.operation_id] += 1
        if simulation:
            return ProviderOperationResult(
                operation_id=operation.operation_id,
                provider=operation.provider,
                operation_type=operation.operation_type,
                attempt=attempt,
                evidence={"simulation": "true"},
            )
        modes = self.faults.get(operation.operation_id, ())
        mode = modes[min(attempt - 1, len(modes) - 1)] if modes else FaultMode.SUCCESS
        object_id = (
            f"{operation.provider.value}-{deterministic_digest(operation.idempotency_key)[:12]}"
        )
        if mode == FaultMode.TIMEOUT_BEFORE_APPLY:
            raise ProviderExecutionError(
                ErrorClassification.RETRYABLE_TIMEOUT,
                "provider timeout before apply",
            )
        if mode == FaultMode.TIMEOUT_AFTER_APPLY:
            self.objects[operation.idempotency_key] = object_id
            raise ProviderExecutionError(
                ErrorClassification.RETRYABLE_TIMEOUT,
                "provider timeout after apply",
                uncertain_apply=True,
            )
        if mode == FaultMode.RATE_LIMIT:
            raise ProviderExecutionError(
                ErrorClassification.RETRYABLE_RATE_LIMIT,
                "provider rate limit",
            )
        if mode == FaultMode.SERVER_FAILURE:
            raise ProviderExecutionError(
                ErrorClassification.RETRYABLE_PROVIDER_5XX,
                "provider server failure",
            )
        if mode == FaultMode.VALIDATION_FAILURE:
            raise ProviderExecutionError(
                ErrorClassification.VALIDATION_FAILURE,
                "provider validation failure",
            )
        if mode == FaultMode.PERMISSION_FAILURE:
            raise ProviderExecutionError(
                ErrorClassification.PERMISSION_FAILURE,
                "provider permission failure",
            )
        if mode == FaultMode.SCHEMA_DRIFT:
            raise ProviderExecutionError(
                ErrorClassification.SCHEMA_MISMATCH,
                "provider schema drift",
            )
        if mode in {
            FaultMode.MALFORMED_RESPONSE,
            FaultMode.READBACK_MISMATCH,
            FaultMode.HIERARCHY_CORRUPTION,
            FaultMode.DUPLICATE_RESPONSE,
        }:
            raise ProviderExecutionError(
                ErrorClassification.READBACK_MISMATCH,
                f"provider verification failure: {mode}",
            )
        self.operation_log.append(operation.operation_id)
        self.objects.setdefault(operation.idempotency_key, object_id)
        writes = {
            ProviderOperationType.UPSERT_PARENT,
            ProviderOperationType.UPSERT_CHILD,
            ProviderOperationType.MOVE_GROUP,
            ProviderOperationType.UPSERT_RECORD,
            ProviderOperationType.WRITE_LINK,
        }
        return ProviderOperationResult(
            operation_id=operation.operation_id,
            provider=operation.provider,
            operation_type=operation.operation_type,
            attempt=attempt,
            applied=operation.operation_type in writes,
            readback_verified=True,
            provider_object_references=(self.objects[operation.idempotency_key],),
        )

    def readback_before_retry(
        self,
        operation: ProviderOperation,
        context: dict[str, Any],
    ) -> ProviderOperationResult | None:
        del context
        object_id = self.objects.get(operation.idempotency_key)
        if object_id is None:
            return None
        return ProviderOperationResult(
            operation_id=operation.operation_id,
            provider=operation.provider,
            operation_type=operation.operation_type,
            attempt=self.attempts[operation.operation_id],
            applied=True,
            readback_verified=True,
            provider_object_references=(object_id,),
            evidence={"recovered_by_readback": "true"},
        )

    def compensate_operation(
        self,
        operation: ProviderOperation,
        context: dict[str, Any],
        *,
        attempt: int,
    ) -> ProviderOperationResult:
        del context
        modes = self.faults.get(operation.operation_id, ())
        if FaultMode.COMPENSATION_FAILURE in modes:
            raise ProviderExecutionError(
                ErrorClassification.UNKNOWN_REVIEW,
                "compensation failure",
            )
        self.compensation_log.append(operation.operation_id)
        self.objects.pop(operation.idempotency_key, None)
        return ProviderOperationResult(
            operation_id=operation.operation_id,
            provider=operation.provider,
            operation_type=operation.operation_type,
            attempt=attempt,
            readback_verified=True,
            evidence={"compensated": "true"},
        )
