"""Attended authorization and exact-plan execution with mandatory readback."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from atlas_ros.capabilities.interfaces import ProposedExecutionPlan
from atlas_ros.contracts.execution.transaction import (
    AuthorizedExecutionPlan,
    ExecutedOperationReceipt,
    ExecutionTransactionReceipt,
    ProviderReadbackReceipt,
    ProviderWriteReceipt,
)
from atlas_ros.ports.execution import ExecutionJournalPort, ProviderExecutionPort


class ExecutionBoundaryError(RuntimeError):
    """Raised when authorization or adapter behavior violates an exact boundary."""


@dataclass(frozen=True, slots=True)
class AttendedAuthorizationService:
    """Convert one unblocked proposed plan into an immutable authorized plan."""

    def authorize(
        self,
        plan: ProposedExecutionPlan,
        *,
        authorization_id: str,
        authorized_at: datetime | None = None,
    ) -> AuthorizedExecutionPlan:
        if not authorization_id.strip():
            raise ExecutionBoundaryError("an explicit attended authorization ID is required")
        if plan.blockers:
            raise ExecutionBoundaryError("a blocked execution plan cannot be authorized")
        if not plan.operations:
            raise ExecutionBoundaryError("an empty execution plan cannot be authorized")
        authorized = AuthorizedExecutionPlan.create(
            authorization_id=authorization_id,
            operations=plan.operations,
            authorized_at=authorized_at,
        )
        if authorized.plan_digest != plan.plan_digest:
            raise ExecutionBoundaryError(
                "authorized plan digest does not match the proposed execution plan"
            )
        return authorized


@dataclass(frozen=True, slots=True)
class AttendedExecutionService:
    """Execute exactly one immutable authorized plan and verify every provider write."""

    port: ProviderExecutionPort
    journal: ExecutionJournalPort | None = None

    def execute(
        self,
        plan: AuthorizedExecutionPlan,
        *,
        transaction_id: str,
    ) -> ExecutionTransactionReceipt:
        if not transaction_id.strip():
            raise ExecutionBoundaryError("an exact execution transaction ID is required")
        if self.journal is not None:
            self.journal.begin(plan, transaction_id=transaction_id)

        receipts: list[ExecutedOperationReceipt] = []
        current_operation_id: str | None = None
        try:
            for operation in plan.operations:
                current_operation_id = operation.operation_id
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
                if self.journal is not None:
                    self.journal.record_write(
                        operation,
                        write,
                        transaction_id=transaction_id,
                    )
                readback = self.port.readback(write)
                self._validate_readback(write, readback)
                if self.journal is not None:
                    self.journal.record_readback(
                        readback,
                        transaction_id=transaction_id,
                    )
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
        except Exception as error:
            if self.journal is not None:
                self.journal.fail(
                    transaction_id=transaction_id,
                    operation_id=current_operation_id,
                    reason=str(error),
                )
            raise

        receipt = ExecutionTransactionReceipt(
            transaction_id=transaction_id,
            authorization_id=plan.authorization_id,
            plan_digest=plan.plan_digest,
            operation_receipts=tuple(receipts),
            provider_writes=sum(receipt.changed for receipt in receipts),
        )
        if self.journal is not None:
            self.journal.complete(receipt)
        return receipt

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
