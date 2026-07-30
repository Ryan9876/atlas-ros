"""SQLite retry and evidence journal for attended execution transactions.

The database stores provider-neutral transaction metadata and digests only. It is
not a canonical business, planning, release, or authorization authority.
"""

from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from atlas_ros.contracts.execution.transaction import (
    AuthorizedExecutionPlan,
    ExecutionTransactionReceipt,
    PlannedProviderOperation,
    ProviderReadbackReceipt,
    ProviderWriteReceipt,
)


class ExecutionJournalError(RuntimeError):
    """Raised when local journal state contradicts the authorized transaction."""


@dataclass(frozen=True, slots=True)
class JournalTransactionSnapshot:
    transaction_id: str
    authorization_id: str
    plan_digest: str
    state: str
    provider_writes: int
    failure_reason: str | None
    operation_states: tuple[tuple[str, str], ...]


class SQLiteExecutionJournal:
    """Durable, idempotent local journal with private POSIX file modes."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._secure_database_files()
        self._initialize()
        self._secure_database_files()

    def _secure_database_files(self) -> None:
        """Restore 0700 directory and 0600 database/WAL/SHM modes on POSIX."""
        if os.name != "posix":
            return
        self.path.parent.chmod(0o700)
        for candidate in (
            self.path,
            Path(f"{self.path}-wal"),
            Path(f"{self.path}-shm"),
        ):
            try:
                candidate.chmod(0o600)
            except FileNotFoundError:
                continue

    def begin(self, plan: AuthorizedExecutionPlan, *, transaction_id: str) -> None:
        if not transaction_id.strip():
            raise ExecutionJournalError("transaction ID is required")
        now = _now()
        with self._connection() as connection:
            existing = connection.execute(
                "SELECT authorization_id, plan_digest, state FROM execution_transactions "
                "WHERE transaction_id = ?",
                (transaction_id,),
            ).fetchone()
            if existing is not None:
                if existing[:2] != (plan.authorization_id, plan.plan_digest):
                    raise ExecutionJournalError(
                        "existing transaction identity disagrees with authorized plan"
                    )
                if existing[2] == "completed":
                    raise ExecutionJournalError("completed transaction cannot be executed again")
                self._verify_existing_operations(connection, transaction_id, plan)
                connection.execute(
                    "UPDATE execution_transactions SET state = 'prepared', failure_reason = NULL, "
                    "updated_at = ? WHERE transaction_id = ?",
                    (now, transaction_id),
                )
                return
            connection.execute(
                "INSERT INTO execution_transactions "
                "(transaction_id, authorization_id, plan_digest, state, provider_writes, "
                "failure_reason, receipt_json, created_at, updated_at) "
                "VALUES (?, ?, ?, 'prepared', 0, NULL, NULL, ?, ?)",
                (transaction_id, plan.authorization_id, plan.plan_digest, now, now),
            )
            connection.executemany(
                "INSERT INTO execution_operations "
                "(transaction_id, operation_id, sequence, provider, action, target, "
                "payload_digest, idempotency_key, state, attempts, provider_record_id, "
                "write_digest, readback_digest, changed, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'prepared', 0, NULL, NULL, NULL, NULL, ?)",
                [
                    (
                        transaction_id,
                        operation.operation_id,
                        operation.sequence,
                        operation.provider,
                        operation.action,
                        operation.target,
                        operation.payload_digest,
                        operation.idempotency_key,
                        now,
                    )
                    for operation in plan.operations
                ],
            )

    def record_write(
        self,
        operation: PlannedProviderOperation,
        receipt: ProviderWriteReceipt,
        *,
        transaction_id: str,
    ) -> None:
        if receipt.operation_id != operation.operation_id:
            raise ExecutionJournalError("write receipt operation ID mismatch")
        if receipt.provider != operation.provider:
            raise ExecutionJournalError("write receipt provider mismatch")
        if receipt.idempotency_key != operation.idempotency_key:
            raise ExecutionJournalError("write receipt idempotency key mismatch")
        with self._connection() as connection:
            row = self._operation_row(connection, transaction_id, operation.operation_id)
            expected = (
                operation.sequence,
                operation.provider,
                operation.action,
                operation.target,
                operation.payload_digest,
                operation.idempotency_key,
            )
            if row != expected:
                raise ExecutionJournalError(
                    "journaled operation metadata disagrees with authorized operation"
                )
            connection.execute(
                "UPDATE execution_operations SET state = 'written', attempts = attempts + 1, "
                "provider_record_id = ?, write_digest = ?, changed = ?, updated_at = ? "
                "WHERE transaction_id = ? AND operation_id = ?",
                (
                    receipt.provider_record_id,
                    receipt.write_digest,
                    int(receipt.changed),
                    _now(),
                    transaction_id,
                    operation.operation_id,
                ),
            )
            connection.execute(
                "UPDATE execution_transactions SET state = 'executing', updated_at = ? "
                "WHERE transaction_id = ?",
                (_now(), transaction_id),
            )

    def record_readback(
        self,
        receipt: ProviderReadbackReceipt,
        *,
        transaction_id: str,
    ) -> None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT provider_record_id, write_digest, state FROM execution_operations "
                "WHERE transaction_id = ? AND operation_id = ?",
                (transaction_id, receipt.operation_id),
            ).fetchone()
            if row is None:
                raise ExecutionJournalError("readback references an unknown operation")
            if row[2] != "written":
                raise ExecutionJournalError("readback requires a recorded provider write")
            if row[0] != receipt.provider_record_id:
                raise ExecutionJournalError("readback provider record ID mismatch")
            if row[1] != receipt.readback_digest:
                raise ExecutionJournalError("readback digest does not match recorded write")
            connection.execute(
                "UPDATE execution_operations SET state = 'verified', readback_digest = ?, "
                "updated_at = ? WHERE transaction_id = ? AND operation_id = ?",
                (receipt.readback_digest, _now(), transaction_id, receipt.operation_id),
            )

    def fail(
        self,
        *,
        transaction_id: str,
        operation_id: str | None,
        reason: str,
    ) -> None:
        with self._connection() as connection:
            connection.execute(
                "UPDATE execution_transactions SET state = 'failed', failure_reason = ?, "
                "updated_at = ? WHERE transaction_id = ?",
                (reason[:4000], _now(), transaction_id),
            )
            if operation_id is not None:
                connection.execute(
                    "UPDATE execution_operations SET state = 'failed', updated_at = ? "
                    "WHERE transaction_id = ? AND operation_id = ?",
                    (_now(), transaction_id, operation_id),
                )

    def complete(self, receipt: ExecutionTransactionReceipt) -> None:
        with self._connection() as connection:
            transaction = connection.execute(
                "SELECT authorization_id, plan_digest FROM execution_transactions "
                "WHERE transaction_id = ?",
                (receipt.transaction_id,),
            ).fetchone()
            if transaction is None:
                raise ExecutionJournalError("completion references an unknown transaction")
            if transaction != (receipt.authorization_id, receipt.plan_digest):
                raise ExecutionJournalError("completion receipt identity mismatch")
            states = connection.execute(
                "SELECT operation_id, state FROM execution_operations "
                "WHERE transaction_id = ? ORDER BY sequence",
                (receipt.transaction_id,),
            ).fetchall()
            if not states or any(state != "verified" for _, state in states):
                raise ExecutionJournalError(
                    "transaction cannot complete before every operation is verified"
                )
            receipt_ids = tuple(item.operation_id for item in receipt.operation_receipts)
            if receipt_ids != tuple(operation_id for operation_id, _ in states):
                raise ExecutionJournalError("completion receipt operation set mismatch")
            connection.execute(
                "UPDATE execution_transactions SET state = 'completed', provider_writes = ?, "
                "failure_reason = NULL, receipt_json = ?, updated_at = ? "
                "WHERE transaction_id = ?",
                (
                    receipt.provider_writes,
                    json.dumps(receipt.model_dump(mode="json"), sort_keys=True),
                    _now(),
                    receipt.transaction_id,
                ),
            )

    def snapshot(self, transaction_id: str) -> JournalTransactionSnapshot:
        with self._connection() as connection:
            transaction = connection.execute(
                "SELECT authorization_id, plan_digest, state, provider_writes, failure_reason "
                "FROM execution_transactions WHERE transaction_id = ?",
                (transaction_id,),
            ).fetchone()
            if transaction is None:
                raise KeyError(transaction_id)
            operations = connection.execute(
                "SELECT operation_id, state FROM execution_operations "
                "WHERE transaction_id = ? ORDER BY sequence",
                (transaction_id,),
            ).fetchall()
        return JournalTransactionSnapshot(
            transaction_id=transaction_id,
            authorization_id=transaction[0],
            plan_digest=transaction[1],
            state=transaction[2],
            provider_writes=transaction[3],
            failure_reason=transaction[4],
            operation_states=tuple((item[0], item[1]) for item in operations),
        )

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode = WAL;
                CREATE TABLE IF NOT EXISTS execution_transactions (
                    transaction_id TEXT PRIMARY KEY,
                    authorization_id TEXT NOT NULL,
                    plan_digest TEXT NOT NULL,
                    state TEXT NOT NULL,
                    provider_writes INTEGER NOT NULL,
                    failure_reason TEXT,
                    receipt_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS execution_operations (
                    transaction_id TEXT NOT NULL,
                    operation_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    provider TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target TEXT NOT NULL,
                    payload_digest TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    state TEXT NOT NULL,
                    attempts INTEGER NOT NULL,
                    provider_record_id TEXT,
                    write_digest TEXT,
                    readback_digest TEXT,
                    changed INTEGER,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (transaction_id, operation_id),
                    UNIQUE (provider, idempotency_key),
                    FOREIGN KEY (transaction_id) REFERENCES execution_transactions(transaction_id)
                );
                """
            )

    def _verify_existing_operations(
        self,
        connection: sqlite3.Connection,
        transaction_id: str,
        plan: AuthorizedExecutionPlan,
    ) -> None:
        rows = connection.execute(
            "SELECT operation_id, sequence, provider, action, target, payload_digest, "
            "idempotency_key FROM execution_operations WHERE transaction_id = ? "
            "ORDER BY sequence",
            (transaction_id,),
        ).fetchall()
        expected = [
            (
                operation.operation_id,
                operation.sequence,
                operation.provider,
                operation.action,
                operation.target,
                operation.payload_digest,
                operation.idempotency_key,
            )
            for operation in plan.operations
        ]
        if rows != expected:
            raise ExecutionJournalError(
                "existing transaction operations disagree with authorized plan"
            )

    @staticmethod
    def _operation_row(
        connection: sqlite3.Connection,
        transaction_id: str,
        operation_id: str,
    ) -> tuple[Any, ...]:
        row = connection.execute(
            "SELECT sequence, provider, action, target, payload_digest, idempotency_key "
            "FROM execution_operations WHERE transaction_id = ? AND operation_id = ?",
            (transaction_id, operation_id),
        ).fetchone()
        if row is None:
            raise ExecutionJournalError("write references an unknown operation")
        return tuple(row)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA foreign_keys = ON")
        self._secure_database_files()
        try:
            yield connection
            connection.commit()
            self._secure_database_files()
        except Exception:
            connection.rollback()
            self._secure_database_files()
            raise
        finally:
            self._secure_database_files()
            connection.close()
            self._secure_database_files()


def _now() -> str:
    return datetime.now(UTC).isoformat()
