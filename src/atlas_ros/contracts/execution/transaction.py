"""Immutable attended-execution contracts for exact provider transactions."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from atlas_ros.contracts.digests import sha256_digest


class PlannedProviderOperation(BaseModel):
    """One exact provider operation produced by the sole planning authority."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    operation_id: str = Field(min_length=1, max_length=128)
    sequence: int = Field(ge=0)
    provider: str = Field(min_length=1, max_length=64)
    action: str = Field(min_length=1, max_length=64)
    target: str = Field(min_length=1, max_length=512)
    payload_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    idempotency_key: str = Field(min_length=1, max_length=256)


class ProposedExecutionPlan(BaseModel):
    """A provider-neutral plan produced before attended authorization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_id: Literal["atlas.proposed-execution-plan"] = (
        "atlas.proposed-execution-plan"
    )
    schema_version: Literal["1.0"] = "1.0"
    plan_id: str = Field(min_length=1, max_length=128)
    source_graph_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    operations: tuple[PlannedProviderOperation, ...] = ()
    blockers: tuple[str, ...] = ()
    plan_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(
        cls,
        *,
        plan_id: str,
        source_graph_digest: str,
        operations: tuple[PlannedProviderOperation, ...] = (),
        blockers: tuple[str, ...] = (),
    ) -> ProposedExecutionPlan:
        return cls(
            plan_id=plan_id,
            source_graph_digest=source_graph_digest,
            operations=operations,
            blockers=blockers,
            plan_digest=sha256_digest(_operations_payload(operations)),
        )

    @model_validator(mode="after")
    def validate_plan(self) -> ProposedExecutionPlan:
        _validate_operation_set(self.operations, label="proposed")
        if not self.operations and not self.blockers:
            raise ValueError("proposed plan requires operations or blockers")
        if len(set(self.blockers)) != len(self.blockers):
            raise ValueError("proposed plan contains duplicate blockers")
        if sha256_digest(_operations_payload(self.operations)) != self.plan_digest:
            raise ValueError("proposed plan digest does not match operations")
        return self


class AuthorizedExecutionPlan(BaseModel):
    """An immutable execution plan that has received attended authorization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_id: Literal["atlas.authorized-execution-plan"] = (
        "atlas.authorized-execution-plan"
    )
    schema_version: Literal["1.0"] = "1.0"
    authorization_id: str = Field(min_length=1, max_length=256)
    plan_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    operations: tuple[PlannedProviderOperation, ...] = Field(min_length=1)
    authorized_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def create(
        cls,
        *,
        authorization_id: str,
        operations: tuple[PlannedProviderOperation, ...],
        authorized_at: datetime | None = None,
    ) -> AuthorizedExecutionPlan:
        payload = _operations_payload(operations)
        values: dict[str, Any] = {
            "authorization_id": authorization_id,
            "plan_digest": sha256_digest(payload),
            "operations": operations,
        }
        if authorized_at is not None:
            values["authorized_at"] = authorized_at
        return cls.model_validate(values)

    @model_validator(mode="after")
    def validate_plan(self) -> AuthorizedExecutionPlan:
        _validate_operation_set(self.operations, label="authorized")
        if sha256_digest(_operations_payload(self.operations)) != self.plan_digest:
            raise ValueError("authorized plan digest does not match operations")
        return self


class ProviderWriteReceipt(BaseModel):
    """Provider-neutral write result returned before independent readback."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    operation_id: str
    provider: str
    provider_record_id: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    write_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    changed: bool


class ProviderReadbackReceipt(BaseModel):
    """Independent provider readback for one completed write operation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    operation_id: str
    provider_record_id: str = Field(min_length=1)
    readback_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class ExecutedOperationReceipt(BaseModel):
    """Bound write and readback evidence for one authorized operation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    operation_id: str
    provider: str
    provider_record_id: str
    idempotency_key: str
    write_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    readback_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    changed: bool

    @model_validator(mode="after")
    def verify_readback(self) -> ExecutedOperationReceipt:
        if self.write_digest != self.readback_digest:
            raise ValueError("provider readback does not match the completed write")
        return self


class ExecutionTransactionReceipt(BaseModel):
    """Completion evidence for an exact attended provider transaction."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_id: Literal["atlas.execution-transaction-receipt"] = (
        "atlas.execution-transaction-receipt"
    )
    schema_version: Literal["1.0"] = "1.0"
    transaction_id: str = Field(min_length=1, max_length=256)
    authorization_id: str = Field(min_length=1, max_length=256)
    plan_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_receipts: tuple[ExecutedOperationReceipt, ...] = Field(min_length=1)
    provider_writes: int = Field(ge=0)
    completion_state: Literal["completed"] = "completed"
    completed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_receipt(self) -> ExecutionTransactionReceipt:
        operation_ids = tuple(receipt.operation_id for receipt in self.operation_receipts)
        if len(set(operation_ids)) != len(operation_ids):
            raise ValueError("transaction receipt contains duplicate operation IDs")
        changed_count = sum(receipt.changed for receipt in self.operation_receipts)
        if self.provider_writes != changed_count:
            raise ValueError("provider write count does not match operation receipts")
        return self


def _validate_operation_set(
    operations: tuple[PlannedProviderOperation, ...],
    *,
    label: str,
) -> None:
    sequences = tuple(operation.sequence for operation in operations)
    if sequences != tuple(range(len(operations))):
        raise ValueError(f"{label} operations must use contiguous canonical sequence")
    operation_ids = tuple(operation.operation_id for operation in operations)
    if len(set(operation_ids)) != len(operation_ids):
        raise ValueError(f"{label} plan contains duplicate operation IDs")
    idempotency_keys = tuple(operation.idempotency_key for operation in operations)
    if len(set(idempotency_keys)) != len(idempotency_keys):
        raise ValueError(f"{label} plan contains duplicate idempotency keys")


def _operations_payload(
    operations: tuple[PlannedProviderOperation, ...],
) -> list[dict[str, Any]]:
    return [operation.model_dump(mode="json") for operation in operations]
