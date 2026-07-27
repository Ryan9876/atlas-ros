"""Attended exact-plan execution with mandatory provider readback."""

from __future__ import annotations

from dataclasses import dataclass

from atlas_ros.contracts.execution.transaction import (
    AuthorizedExecutionPlan,
    ExecutedOperationReceipt,
    ExecutionTransactionReceipt,
    ProviderReadbackReceipt,
    ProviderWriteReceipt,
)
from atlas_ros.ports.execution import ProviderExecutionPort


class ExecutionBoundaryError(RuntimeError):
    """Raised when an adapter result violates the authorized execution boundary."""


@dataclass(frozen=True)
class AttendedExecutionService:
    """Execute exactly one immutable authorized plan and verify every provider write."""

    port: ProviderExecutionPort

    def execute(
        self,
        plan: AuthorizedExecutionPlan,
        *,
        transaction_id: str,
    ) -> ExecutionTransactionReceipt:
        if not transaction_id.strip():
            raise ExecutionBoundaryError("an exact execution transaction ID is required")

        receipts: list[ExecutedOperationReceipt] = []
        for operation in plan.operations:
            write = self.port.write(
                operation,
                authorization_id=plan.authorization_id,
                transaction_id=transaction_id,
            )
            self._validate_write(
                operation.operation_id,
                operation.provider,
                operation.idempotency_key,
                write,
            )
            readback = self.port.readback(write)
            self._validate_readback(write, readback)
            receipts.append(
                ExecutedOperationReceipt(
                    operation_id=operation.operation_id,
                    provider=operation.provider,
                    provider_record_id=write.provider_record_id,
                    idempotency_key=operation.idempotency_key,
                    write_digest=write.write_digest,
                    readback_digest=readback.readback_digest,
                    changed=write.changed,
                )
            )

        return ExecutionTransactionReceipt(
            transaction_id=transaction_id,
            authorization_id=plan.authorization_id,
            plan_digest=plan.plan_digest,
            operation_receipts=tuple(receipts),
            provider_writes=sum(receipt.changed for receipt in receipts),
        )

    @staticmethod
    def _validate_write(
        operation_id: str,
        provider: str,
        idempotency_key: str,
        receipt: ProviderWriteReceipt,
    ) -> None:
        if receipt.operation_id != operation_id:
            raise ExecutionBoundaryError("adapter returned a different operation ID")
        if receipt.provider != provider:
            raise ExecutionBoundaryError("adapter returned a different provider")
        if receipt.idempotency_key != idempotency_key:
            raise ExecutionBoundaryError("adapter changed the idempotency key")

    @staticmethod
    def _validate_readback(
        write: ProviderWriteReceipt,
        readback: ProviderReadbackReceipt,
    ) -> None:
        if readback.operation_id != write.operation_id:
            raise ExecutionBoundaryError("readback returned a different operation ID")
        if readback.provider_record_id != write.provider_record_id:
            raise ExecutionBoundaryError("readback returned a different provider record")
        if readback.readback_digest != write.write_digest:
            raise ExecutionBoundaryError("provider readback does not match the completed write")
