# ruff: noqa: E501
from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys=ON;
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS migration_history (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS pending_capture (capture_id TEXT PRIMARY KEY, correlation_id TEXT UNIQUE NOT NULL, content TEXT NOT NULL, source TEXT NOT NULL, due_date_input TEXT NOT NULL DEFAULT '', delegation_input TEXT NOT NULL DEFAULT '', additional_context TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending');
CREATE TABLE IF NOT EXISTS outbox_event (event_id TEXT PRIMARY KEY, correlation_id TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0, last_error TEXT, next_retry TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS runtime_lock (name TEXT PRIMARY KEY, holder TEXT NOT NULL, expires_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS outbox_pending_idx ON outbox_event(status, next_retry);
CREATE TABLE IF NOT EXISTS sync_checkpoint (integration TEXT PRIMARY KEY, cursor TEXT, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS processed_event (event_id TEXT PRIMARY KEY, processed_at TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reconciliation_outbox (mutation_id TEXT PRIMARY KEY, todoist_task_id TEXT NOT NULL, notion_page_id TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, last_error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
"""


class RuntimeDatabase:
    """Local runtime database with POSIX-only explicit file permission hardening.

    On non-POSIX platforms SQLite behavior is preserved, but POSIX mode bits are not
    asserted because the platform does not provide equivalent chmod semantics.
    """

    def __init__(self, path: Path) -> None:
        self.path = path

    def initialize(self) -> None:
        self._secure_database_files()
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            self._ensure_capture_assertion_columns(connection)
            connection.execute("PRAGMA user_version=50001")
        self._secure_database_files()

    def _secure_database_files(self) -> None:
        """Restore private modes for the runtime directory, database, WAL, and SHM."""
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
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

    @staticmethod
    def _ensure_capture_assertion_columns(connection: sqlite3.Connection) -> None:
        existing = {
            row[1] for row in connection.execute("PRAGMA table_info(pending_capture)")
        }
        for column, definition in (
            ("due_date_input", "TEXT NOT NULL DEFAULT ''"),
            ("delegation_input", "TEXT NOT NULL DEFAULT ''"),
            ("additional_context", "TEXT NOT NULL DEFAULT ''"),
        ):
            if column not in existing:
                connection.execute(
                    f"ALTER TABLE pending_capture ADD COLUMN {column} {definition}"
                )

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self._secure_database_files()
        connection = sqlite3.connect(self.path, timeout=30)
        connection.execute("PRAGMA busy_timeout=30000")
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
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
