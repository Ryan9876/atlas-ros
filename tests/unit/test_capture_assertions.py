from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

from atlas_ros import cli
from atlas_ros.runtime.database import RuntimeDatabase
from atlas_ros.workflows.w01_capture import CaptureService


def test_capture_preserves_optional_assertions(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("ATLAS_RUNTIME_DIR", str(tmp_path))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "atlas",
            "capture",
            "Prepare operating standards",
            "--source",
            "raycast",
            "--due-date",
            "next Friday",
            "--delegate-to",
            "Tina",
            "--context",
            "Focus on service ownership",
        ],
    )
    cli.main()
    output = capsys.readouterr().out
    assert '"due_date_input":"next Friday"' in output
    assert '"delegation_input":"Tina"' in output
    assert '"additional_context":"Focus on service ownership"' in output


def test_capture_assertions_are_persisted_for_inbox_processing(tmp_path: Path) -> None:
    database = RuntimeDatabase(tmp_path / "runtime.db")
    database.initialize()
    CaptureService(database).capture(
        "Prepare operating standards",
        source="raycast",
        due_date_input="next Friday",
        delegation_input="Tina",
        additional_context="Focus on service ownership",
    )
    with database.connect() as db:
        row = db.execute(
            "SELECT due_date_input, delegation_input, additional_context "
            "FROM pending_capture"
        ).fetchone()
    assert tuple(row) == (
        "next Friday",
        "Tina",
        "Focus on service ownership",
    )


def test_existing_runtime_database_is_migrated_for_capture_assertions(
    tmp_path: Path,
) -> None:
    path = tmp_path / "runtime.db"
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE pending_capture (capture_id TEXT PRIMARY KEY, "
        "correlation_id TEXT UNIQUE NOT NULL, content TEXT NOT NULL, "
        "source TEXT NOT NULL, created_at TEXT NOT NULL, "
        "status TEXT NOT NULL DEFAULT 'pending')"
    )
    connection.commit()
    connection.close()

    database = RuntimeDatabase(path)
    database.initialize()
    with database.connect() as db:
        columns = {row[1] for row in db.execute("PRAGMA table_info(pending_capture)")}
    assert {"due_date_input", "delegation_input", "additional_context"} <= columns
