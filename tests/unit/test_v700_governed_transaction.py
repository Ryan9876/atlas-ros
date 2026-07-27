from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from atlas_ros.adapters.local_sqlite import SQLiteExecutionJournal
from atlas_ros.application.execution import AttendedExecutionService, ExecutionBoundaryError
from atlas_ros.application.transaction import GovernedExecutionTransactionService
from atlas_ros.capabilities.interfaces import ProposedExecutionPlan
from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.contracts.execution.transaction import (
    AuthorizedExecutionPlan,
    PlannedProviderOperation,
    ProviderReadbackReceipt,
    ProviderWriteReceipt,
)
from atlas_ros.kernel.container import (
    KernelConfig,
    KernelPermissionError,
    RuntimeKernel,
    RuntimeMode,
)


@dataclass
class FakeProvider:
    calls: list[str] = field(default_factory=list)

    def write(
        self,
        operation: PlannedProviderOperation,
        *,
        authorization_id: str,
        transaction_id: str,
    ) -> ProviderWriteReceipt:
        self.calls.append(f"write:{operation.operation_id}")
        return ProviderWriteReceipt(
            operation_id=operation.operation_id,
            provider=operation.provider,
            provider_record_id=f"record-{operation.operation_id}",
            idempotency_key=operation.idempotency_key,
            write_digest=operation.payload_digest,
            changed=True,
        )

    def readback(self, receipt: ProviderWriteReceipt) -> ProviderReadbackReceipt:
        self.calls.append(f"readback:{receipt.operation_id}")
        return ProviderReadbackReceipt(
            operation_id=receipt.operation_id,
            provider_record_id=receipt.provider_record_id,
            readback_digest=receipt.write_digest,
        )


def policy(path: Path) -> Path:
    path.write_text(
        "schema_version: '1.0'\n"
        "policy_id: atlas.test\n"
        "lifecycle: active\n"
        "rules:\n"
        "  - test_rule\n",
        encoding="utf-8",
    )
    return path


def kernel(tmp_path: Path, mode: RuntimeMode = RuntimeMode.PRODUCTION) -> RuntimeKernel:
    return RuntimeKernel.compose(
        KernelConfig(
            release_version="7.0.0rc1",
            source_commit="a" * 40,
            initializer_version="7.0",
            contract_catalog_digest="b" * 64,
            capability_catalog_digest="c" * 64,
            mode=mode,
        ),
        [policy(tmp_path / "policy.yaml")],
        (),
    )


def operation() -> PlannedProviderOperation:
    return PlannedProviderOperation(
        operation_id="operation-1",
        sequence=0,
        provider="todoist",
        action="create",
        target="Work/Active Projects",
        payload_digest=sha256_digest({"title": "Governed checkpoint"}),
        idempotency_key="capture-1:0",
    )


def proposed(*, blockers: tuple[str, ...] = (), digest: str | None = None) -> ProposedExecutionPlan:
    operations = (operation(),)
    return ProposedExecutionPlan(
        plan_id="plan-1",
        source_graph_digest="d" * 64,
        operations=operations,
        blockers=blockers,
        plan_digest=(
            digest
            or AuthorizedExecutionPlan.create(
                authorization_id="authorization-1",
                operations=operations,
            ).plan_digest
        ),
    )


def test_governed_transaction_completes_readback_and_reconciliation(
    tmp_path: Path,
) -> None:
    provider = FakeProvider()
    journal = SQLiteExecutionJournal(tmp_path / "atlas.sqlite3")
    service = GovernedExecutionTransactionService(
        kernel(tmp_path),
        AttendedExecutionService(provider, journal),
    )

    result = service.execute(
        proposed(),
        authorization_id="authorization-1",
        transaction_id="transaction-1",
    )

    assert result.authorized_plan.authorization_id == "authorization-1"
    assert result.execution_receipt.provider_writes == 1
    assert result.reconciliation.complete is True
    assert result.reconciliation.matched_operation_ids == ("operation-1",)
    assert journal.snapshot("transaction-1").state == "completed"


def test_simulation_mode_blocks_before_provider_or_journal_write(tmp_path: Path) -> None:
    provider = FakeProvider()
    database = tmp_path / "atlas.sqlite3"
    service = GovernedExecutionTransactionService(
        kernel(tmp_path, RuntimeMode.SIMULATION),
        AttendedExecutionService(provider, SQLiteExecutionJournal(database)),
    )

    with pytest.raises(KernelPermissionError, match="never permits provider writes"):
        service.execute(
            proposed(),
            authorization_id="authorization-1",
            transaction_id="transaction-1",
        )

    assert provider.calls == []
    with pytest.raises(KeyError):
        SQLiteExecutionJournal(database).snapshot("transaction-1")


def test_blocked_plan_cannot_reach_provider(tmp_path: Path) -> None:
    provider = FakeProvider()
    service = GovernedExecutionTransactionService(
        kernel(tmp_path),
        AttendedExecutionService(
            provider,
            SQLiteExecutionJournal(tmp_path / "atlas.sqlite3"),
        ),
    )

    with pytest.raises(ExecutionBoundaryError, match="blocked"):
        service.execute(
            proposed(blockers=("approval_required",)),
            authorization_id="authorization-1",
            transaction_id="transaction-1",
        )

    assert provider.calls == []


def test_proposed_plan_digest_mismatch_cannot_reach_provider(tmp_path: Path) -> None:
    provider = FakeProvider()
    service = GovernedExecutionTransactionService(
        kernel(tmp_path),
        AttendedExecutionService(
            provider,
            SQLiteExecutionJournal(tmp_path / "atlas.sqlite3"),
        ),
    )

    with pytest.raises(ExecutionBoundaryError, match="digest"):
        service.execute(
            proposed(digest="f" * 64),
            authorization_id="authorization-1",
            transaction_id="transaction-1",
        )

    assert provider.calls == []
