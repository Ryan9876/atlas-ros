"""Provider-neutral execution, readback, durability, and permission boundaries."""

from __future__ import annotations

from typing import Protocol

from atlas_ros.contracts.execution.payload import ProviderOperationPayload
from atlas_ros.contracts.execution.transaction import (
    AuthorizedExecutionPlan,
    ExecutionTransactionReceipt,
    PlannedProviderOperation,
    ProviderReadbackReceipt,
    ProviderWriteReceipt,
)


class ProviderWriteGuard(Protocol):
    """Authorize provider-write eligibility without exposing kernel implementation."""

    def require_provider_write_permission(self, authorization_id: str | None) -> None:
        """Fail closed unless the current runtime may execute an attended write."""


class ExecutionPayloadPort(Protocol):
    """Resolve exact operation content without changing the authorized plan."""

    def resolve(self, operation: PlannedProviderOperation) -> ProviderOperationPayload:
        """Return checksum-bound payload content for one planned operation."""


class ProviderExecutionPort(Protocol):
    """Execute one authorized operation and independently read it back."""

    def write(
        self,
        operation: PlannedProviderOperation,
        *,
        authorization_id: str,
        transaction_id: str,
    ) -> ProviderWriteReceipt: ...

    def readback(self, receipt: ProviderWriteReceipt) -> ProviderReadbackReceipt: ...


class ExecutionJournalPort(Protocol):
    """Persist retry and evidence state without becoming business authority."""

    def begin(self, plan: AuthorizedExecutionPlan, *, transaction_id: str) -> None:
        """Durably record the exact authorized transaction before provider writes."""

    def record_write(
        self,
        operation: PlannedProviderOperation,
        receipt: ProviderWriteReceipt,
        *,
        transaction_id: str,
    ) -> None:
        """Record one provider result while the transaction remains incomplete."""

    def record_readback(
        self,
        receipt: ProviderReadbackReceipt,
        *,
        transaction_id: str,
    ) -> None:
        """Record independent provider readback for one operation."""

    def fail(
        self,
        *,
        transaction_id: str,
        operation_id: str | None,
        reason: str,
    ) -> None:
        """Retain failure evidence and leave the transaction retryable."""

    def complete(self, receipt: ExecutionTransactionReceipt) -> None:
        """Mark the transaction complete only after all readbacks pass."""
