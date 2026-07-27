from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from atlas_ros.adapters.local_sqlite import ExecutionJournalError, SQLiteExecutionJournal
from atlas_ros.application.execution import AttendedExecutionService, ExecutionBoundaryError
from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.contracts.execution.transaction import (
    AuthorizedExecutionPlan,
    PlannedProviderOperation,
    ProviderReadbackReceipt,
    ProviderWriteReceipt,
)


@dataclass
class FakeProvider:
    tamper_readback: bool = False
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
            readback_digest=("f" * 64 if self.tamper_readback else receipt.write_digest),
        )


def operation(sequence: int, *, payload: str = "sensitive payload") -> PlannedProviderOperation:
    return PlannedProviderOperation(
        operation_id=f"operation-{sequence}",
        sequence=sequence,
        provider="todoist",
        action="create",
        target="Work/Active Projects",
        payload_digest=sha256_digest(payload),
        idempotency_key=f"capture-1:{sequence}",
    )


def plan(*operations: PlannedProviderOperation) -> AuthorizedExecutionPlan:
    return AuthorizedExecutionPlan.create(
        authorization_id="authorization-1",
        operations=operations or (operation(0), operation(1)),
    )


def test_journal_completes_only_after_verified_readback(tmp_path: Path) -> None:
    journal = SQLiteExecutionJournal(tmp_path / "state/atlas.sqlite3")
    provider = FakeProvider()

    receipt = AttendedExecutionService(provider, journal).execute(
        plan(), transaction_id="transaction-1"
    )
    snapshot = journal.snapshot("transaction-1")

    assert receipt.provider_writes == 2
    assert snapshot.state == "completed"
    assert snapshot.provider_writes == 2
    assert snapshot.operation_states == (
        ("operation-0", "verified"),
        ("operation-1", "verified"),
    )


def test_journal_prevents_reexecution_of_completed_transaction(tmp_path: Path) -> None:
    journal = SQLiteExecutionJournal(tmp_path / "atlas.sqlite3")
    provider = FakeProvider()
    service = AttendedExecutionService(provider, journal)
    authorized = plan()
    service.execute(authorized, transaction_id="transaction-1")
    call_count = len(provider.calls)

    with pytest.raises(ExecutionJournalError, match="completed"):
        service.execute(authorized, transaction_id="transaction-1")

    assert len(provider.calls) == call_count


def test_journal_retains_failure_and_allows_exact_retry(tmp_path: Path) -> None:
    journal = SQLiteExecutionJournal(tmp_path / "atlas.sqlite3")
    authorized = plan(operation(0))

    with pytest.raises(ExecutionBoundaryError, match="readback"):
        AttendedExecutionService(FakeProvider(tamper_readback=True), journal).execute(
            authorized,
            transaction_id="transaction-1",
        )
    failed = journal.snapshot("transaction-1")
    assert failed.state == "failed"
    assert failed.failure_reason is not None

    receipt = AttendedExecutionService(FakeProvider(), journal).execute(
        authorized,
        transaction_id="transaction-1",
    )

    assert receipt.provider_writes == 1
    assert journal.snapshot("transaction-1").state == "completed"


def test_journal_rejects_transaction_identity_substitution(tmp_path: Path) -> None:
    journal = SQLiteExecutionJournal(tmp_path / "atlas.sqlite3")
    first = plan(operation(0))
    journal.begin(first, transaction_id="transaction-1")
    different = AuthorizedExecutionPlan.create(
        authorization_id="authorization-2",
        operations=(
            PlannedProviderOperation(
                operation_id="other",
                sequence=0,
                provider="todoist",
                action="create",
                target="Personal",
                payload_digest="a" * 64,
                idempotency_key="other:0",
            ),
        ),
    )

    with pytest.raises(ExecutionJournalError, match="identity"):
        journal.begin(different, transaction_id="transaction-1")


def test_journal_stores_digests_not_raw_payload_content(tmp_path: Path) -> None:
    database = tmp_path / "atlas.sqlite3"
    journal = SQLiteExecutionJournal(database)
    secret = "do not persist this raw capture text"
    AttendedExecutionService(FakeProvider(), journal).execute(
        plan(operation(0, payload=secret)),
        transaction_id="transaction-1",
    )

    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT payload_digest, target FROM execution_operations"
        ).fetchall()
    assert rows == [(sha256_digest(secret), "Work/Active Projects")]
    assert secret.encode() not in database.read_bytes()


def test_adapter_package_import_does_not_load_provider_clients() -> None:
    import sys

    for module_name in tuple(sys.modules):
        if module_name.startswith("atlas_ros.adapters"):
            del sys.modules[module_name]
    import atlas_ros.adapters  # noqa: F401

    assert "atlas_ros.adapters.notion" not in sys.modules
    assert "atlas_ros.adapters.todoist" not in sys.modules
    assert "atlas_ros.adapters.keychain" not in sys.modules
