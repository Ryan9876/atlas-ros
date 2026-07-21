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
CREATE TABLE IF NOT EXISTS pending_capture (capture_id TEXT PRIMARY KEY, correlation_id TEXT UNIQUE NOT NULL, content TEXT NOT NULL, source TEXT NOT NULL, created_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending');
CREATE TABLE IF NOT EXISTS outbox_event (event_id TEXT PRIMARY KEY, correlation_id TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0, last_error TEXT, next_retry TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS runtime_lock (name TEXT PRIMARY KEY, holder TEXT NOT NULL, expires_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS outbox_pending_idx ON outbox_event(status, next_retry);
CREATE TABLE IF NOT EXISTS sync_checkpoint (integration TEXT PRIMARY KEY, cursor TEXT, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS processed_event (event_id TEXT PRIMARY KEY, processed_at TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reconciliation_outbox (mutation_id TEXT PRIMARY KEY, todoist_task_id TEXT NOT NULL, notion_page_id TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, last_error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
"""


class RuntimeDatabase:
    def __init__(self, path: Path) -> None:
        self.path = path

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path.parent.chmod(0o700)
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            connection.execute("PRAGMA user_version=40502")
        os.chmod(self.path, 0o600)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.execute("PRAGMA busy_timeout=30000")
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
