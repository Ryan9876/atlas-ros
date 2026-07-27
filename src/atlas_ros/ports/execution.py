"""Provider-neutral execution and readback boundary."""

from __future__ import annotations

from typing import Protocol

from atlas_ros.contracts.execution.transaction import (
    PlannedProviderOperation,
    ProviderReadbackReceipt,
    ProviderWriteReceipt,
)


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
