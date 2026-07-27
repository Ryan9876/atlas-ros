from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from atlas_ros.application.execution import AttendedExecutionService, ExecutionBoundaryError
from atlas_ros.contracts.execution.transaction import (
    AuthorizedExecutionPlan,
    PlannedProviderOperation,
    ProviderReadbackReceipt,
    ProviderWriteReceipt,
)
from atlas_ros.kernel.digests import sha256_digest


@dataclass
class FakeExecutionPort:
    tamper_write_operation: bool = False
    tamper_readback: bool = False
    calls: list[str] = field(default_factory=list)

    def write(
        self,
        operation: PlannedProviderOperation,
        *,
        authorization_id: str,
        transaction_id: str,
    ) -> ProviderWriteReceipt:
        self.calls.append(f"write:{operation.operation_id}:{authorization_id}:{transaction_id}")
        operation_id = "different" if self.tamper_write_operation else operation.operation_id
        return ProviderWriteReceipt(
            operation_id=operation_id,
            provider=operation.provider,
            provider_record_id=f"record-{operation.operation_id}",
            idempotency_key=operation.idempotency_key,
            write_digest=operation.payload_digest,
            changed=True,
        )

    def readback(self, receipt: ProviderWriteReceipt) -> ProviderReadbackReceipt:
        self.calls.append(f"readback:{receipt.operation_id}")
        digest = "f" * 64 if self.tamper_readback else receipt.write_digest
        return ProviderReadbackReceipt(
            operation_id=receipt.operation_id,
            provider_record_id=receipt.provider_record_id,
            readback_digest=digest,
        )


def operation(sequence: int) -> PlannedProviderOperation:
    return PlannedProviderOperation(
        operation_id=f"operation-{sequence}",
        sequence=sequence,
        provider="todoist",
        action="create",
        target="Work/Active Projects",
        payload_digest=sha256_digest({"sequence": sequence}),
        idempotency_key=f"capture-1:{sequence}",
    )


def plan() -> AuthorizedExecutionPlan:
    return AuthorizedExecutionPlan.create(
        authorization_id="authorization-1",
        operations=(operation(0), operation(1)),
    )


def test_attended_execution_uses_exact_order_and_mandatory_readback() -> None:
    port = FakeExecutionPort()
    receipt = AttendedExecutionService(port).execute(plan(), transaction_id="transaction-1")

    assert receipt.provider_writes == 2
    assert [item.operation_id for item in receipt.operation_receipts] == [
        "operation-0",
        "operation-1",
    ]
    assert port.calls == [
        "write:operation-0:authorization-1:transaction-1",
        "readback:operation-0",
        "write:operation-1:authorization-1:transaction-1",
        "readback:operation-1",
    ]


def test_attended_execution_rejects_adapter_operation_substitution() -> None:
    with pytest.raises(ExecutionBoundaryError, match="different operation ID"):
        AttendedExecutionService(FakeExecutionPort(tamper_write_operation=True)).execute(
            plan(), transaction_id="transaction-1"
        )


def test_attended_execution_rejects_readback_mismatch() -> None:
    with pytest.raises(ExecutionBoundaryError, match="does not match"):
        AttendedExecutionService(FakeExecutionPort(tamper_readback=True)).execute(
            plan(), transaction_id="transaction-1"
        )


def test_authorized_plan_rejects_noncanonical_sequence() -> None:
    with pytest.raises(ValueError, match="canonical sequence"):
        AuthorizedExecutionPlan.create(
            authorization_id="authorization-1",
            operations=(operation(1),),
        )
