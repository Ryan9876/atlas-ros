"""SQLite retry and evidence journal for attended execution transactions."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from atlas_ros.contracts.execution.transaction import (
    AuthorizedExecutionPlan,
    ExecutionTransactionReceipt,
    PlannedProviderOperation,
    ProviderReadbackReceipt,
    ProviderWriteReceipt,
)


class JournalStateError(RuntimeError):
    """Raised when local durability state contradicts an exact transaction."""


@dataclass(frozen=True, slots=True)
class SQLiteExecutionJournal:
    """Persist retry evidence without becoming release or business authority."""

    path: Path

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode=WAL;
                PRAGMA foreign_keys=ON;
                CREATE TABLE IF NOT EXISTS execution_transactions (
                    transaction_id TEXT PRIMARY KEY,
                    authorization_id TEXT NOT NULL,
                    plan_digest TEXT NOT NULL,
                    status TEXT NOT NULL,
                    current_operation_id TEXT,
                    failure_reason TEXT,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    receipt_json TEXT
                );
                CREATE TABLE IF NOT EXISTS execution_operations (
                    transaction_id TEXT NOT NULL,
                    operation_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    planned_json TEXT NOT NULL,
                    write_json TEXT,
                    readback_json TEXT,
                    status TEXT NOT NULL,
                    PRIMARY KEY (transaction_id, operation_id),
                    FOREIGN KEY (transaction_id)
                        REFERENCES execution_transactions(transaction_id)
                        ON DELETE CASCADE
                );
                """
            )

    def begin(self, plan: AuthorizedExecutionPlan, *, transaction_id: str) -> None:
        """Record an exact transaction and all planned operations before writes."""
        if not transaction_id.strip():
            raise JournalStateError("transaction ID is required")
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT authorization_id, plan_digest, status
                FROM execution_transactions
                WHERE transaction_id = ?
                """,
                (transaction_id,),
            ).fetchone()
            if row is not None:
                authorization_id, plan_digest, status = row
                if authorization_id != plan.authorization_id or plan_digest != plan.plan_digest:
                    raise JournalStateError(
                        "transaction ID is already bound to different authorization evidence"
                    )
                if status == "completed":
                    raise JournalStateError("transaction is already complete")
                return
            connection.execute(
                """
                INSERT INTO execution_transactions (
                    transaction_id,
                    authorization_id,
                    plan_digest,
                    status,
                    started_at
                ) VALUES (?, ?, ?, 'running', ?)
                """,
                (
                    transaction_id,
                    plan.authorization_id,
                    plan.plan_digest,
                    datetime.now(UTC).isoformat(),
                ),
            )
            connection.executemany(
                """
                INSERT INTO execution_operations (
                    transaction_id,
                    operation_id,
                    sequence,
                    planned_json,
                    status
                ) VALUES (?, ?, ?, ?, 'planned')
                """,
                (
                    (
                        transaction_id,
                        operation.operation_id,
                        operation.sequence,
                        operation.model_dump_json(),
                    )
                    for operation in plan.operations
                ),
            )

    def record_write(
        self,
        operation: PlannedProviderOperation,
        receipt: ProviderWriteReceipt,
        *,
        transaction_id: str,
    ) -> None:
        """Persist one provider result and reject contradictory retries."""
        write_json = receipt.model_dump_json()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT planned_json, write_json
                FROM execution_operations
                WHERE transaction_id = ? AND operation_id = ?
                """,
                (transaction_id, operation.operation_id),
            ).fetchone()
            if row is None:
                raise JournalStateError("write references an unplanned operation")
            planned_json, existing_write = row
            if planned_json != operation.model_dump_json():
                raise JournalStateError("write operation differs from the authorized plan")
            if existing_write is not None and existing_write != write_json:
                raise JournalStateError("retry returned contradictory provider write evidence")
            connection.execute(
                """
                UPDATE execution_operations
                SET write_json = ?, status = 'write_recorded'
                WHERE transaction_id = ? AND operation_id = ?
                """,
                (write_json, transaction_id, operation.operation_id),
            )
            connection.execute(
                """
                UPDATE execution_transactions
                SET current_operation_id = ?, status = 'running', failure_reason = NULL
                WHERE transaction_id = ?
                """,
                (operation.operation_id, transaction_id),
            )

    def record_readback(
        self,
        receipt: ProviderReadbackReceipt,
        *,
        transaction_id: str,
    ) -> None:
        """Persist independent readback only after a provider write exists."""
        readback_json = receipt.model_dump_json()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT write_json, readback_json
                FROM execution_operations
                WHERE transaction_id = ? AND operation_id = ?
                """,
                (transaction_id, receipt.operation_id),
            ).fetchone()
            if row is None or row[0] is None:
                raise JournalStateError("readback has no recorded provider write")
            if row[1] is not None and row[1] != readback_json:
                raise JournalStateError("retry returned contradictory readback evidence")
            connection.execute(
                """
                UPDATE execution_operations
                SET readback_json = ?, status = 'readback_verified'
                WHERE transaction_id = ? AND operation_id = ?
                """,
                (readback_json, transaction_id, receipt.operation_id),
            )

    def fail(
        self,
        *,
        transaction_id: str,
        operation_id: str | None,
        reason: str,
    ) -> None:
        """Retain a retryable failure without deleting partial evidence."""
        with self._connect() as connection:
            updated = connection.execute(
                """
                UPDATE execution_transactions
                SET status = 'failed', current_operation_id = ?, failure_reason = ?
                WHERE transaction_id = ? AND status != 'completed'
                """,
                (operation_id, reason, transaction_id),
            ).rowcount
            if updated != 1:
                raise JournalStateError("cannot fail an unknown or completed transaction")

    def complete(self, receipt: ExecutionTransactionReceipt) -> None:
        """Complete only after every planned operation has verified readback."""
        with self._connect() as connection:
            transaction = connection.execute(
                """
                SELECT authorization_id, plan_digest, status
                FROM execution_transactions
                WHERE transaction_id = ?
                """,
                (receipt.transaction_id,),
            ).fetchone()
            if transaction is None:
                raise JournalStateError("completion references an unknown transaction")
            authorization_id, plan_digest, status = transaction
            if status == "completed":
                existing = connection.execute(
                    """
                    SELECT receipt_json FROM execution_transactions
                    WHERE transaction_id = ?
                    """,
                    (receipt.transaction_id,),
                ).fetchone()
                if existing is None or existing[0] != receipt.model_dump_json():
                    raise JournalStateError("completed transaction receipt is contradictory")
                return
            if authorization_id != receipt.authorization_id or plan_digest != receipt.plan_digest:
                raise JournalStateError("completion receipt differs from transaction identity")
            operations = connection.execute(
                """
                SELECT operation_id, readback_json
                FROM execution_operations
                WHERE transaction_id = ?
                ORDER BY sequence
                """,
                (receipt.transaction_id,),
            ).fetchall()
            expected_ids = tuple(row[0] for row in operations)
            receipt_ids = tuple(item.operation_id for item in receipt.operation_receipts)
            if expected_ids != receipt_ids or any(row[1] is None for row in operations):
                raise JournalStateError(
                    "transaction cannot complete before every planned readback is verified"
                )
            connection.execute(
                """
                UPDATE execution_transactions
                SET status = 'completed',
                    current_operation_id = NULL,
                    failure_reason = NULL,
                    completed_at = ?,
                    receipt_json = ?
                WHERE transaction_id = ?
                """,
                (
                    receipt.completed_at.isoformat(),
                    receipt.model_dump_json(),
                    receipt.transaction_id,
                ),
            )

    def status(self, transaction_id: str) -> str | None:
        """Return local retry state for observability and tests."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status FROM execution_transactions WHERE transaction_id = ?",
                (transaction_id,),
            ).fetchone()
            return None if row is None else str(row[0])

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA foreign_keys=ON")
        return connection
