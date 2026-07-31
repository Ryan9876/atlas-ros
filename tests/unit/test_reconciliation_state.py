from datetime import UTC, datetime, timedelta

import pytest

from atlas_ros import cli
from atlas_ros.adapters.notion import FakeNotionAdapter
from atlas_ros.reconciliation.state import (
    HISTORICAL_W04_DATA_SOURCE_ID,
    LedgerFailureCode,
    LedgerValidationError,
    NotionReconciliationStateStore,
    ProductionLedgerDescriptor,
    SQLiteReconciliationStateStore,
    validate_production_ledger,
)
from atlas_ros.runtime.database import RuntimeDatabase


def _production_schema():
    def select(*options):
        return {"type": "select", "options": [{"name": option} for option in options]}

    return {
        "title": "Execution Reconciliation State",
        "properties": {
            "State Key": {"type": "title"},
            "State Type": select("Checkpoint", "Processed Event"),
            "Status": select("Applied", "Failed"),
            "Cursor": {"type": "date"},
            "Event ID": {"type": "rich_text"},
            "Processed At": {"type": "date"},
            "Execution Surface": select("CLI", "ChatGPT", "Automation"),
            "Notes": {"type": "rich_text"},
        },
    }


def test_production_ledger_validation_rejects_w04_and_invalid_schema():
    notion = FakeNotionAdapter()
    notion.schemas["production"] = _production_schema()
    validate_production_ledger(
        notion, ProductionLedgerDescriptor(database_id="database", data_source_id="production")
    )
    try:
        validate_production_ledger(
            notion,
            ProductionLedgerDescriptor(
                database_id="database", data_source_id=HISTORICAL_W04_DATA_SOURCE_ID
            ),
        )
    except LedgerValidationError as exc:
        assert exc.code is LedgerFailureCode.TARGET_HISTORICAL
    else:
        raise AssertionError("W04 was accepted")
    notion.schemas["production"]["properties"].pop("Notes")
    try:
        validate_production_ledger(
            notion, ProductionLedgerDescriptor(database_id="database", data_source_id="production")
        )
    except LedgerValidationError as exc:
        assert exc.code is LedgerFailureCode.SCHEMA_INVALID
    else:
        raise AssertionError("incomplete schema was accepted")


def test_sqlite_state_store_round_trip(tmp_path):
    db = RuntimeDatabase(tmp_path / "runtime.db")
    db.initialize()
    store = SQLiteReconciliationStateStore(db)
    assert store.checkpoint() <= datetime.now(UTC)
    value = datetime(2026, 7, 21, 17, 0, tzinfo=UTC)
    store.set_checkpoint(value)
    assert store.checkpoint() == value
    assert not store.event_processed("comment:1")
    store.mark_event("comment:1", "applied")
    assert store.event_processed("comment:1")


def test_notion_state_store_round_trip_and_updates():
    notion = FakeNotionAdapter()
    store = NotionReconciliationStateStore(notion, "state")
    assert store.checkpoint() >= datetime.now(UTC) - timedelta(days=8)
    value = datetime(2026, 7, 21, 17, 30, tzinfo=UTC)
    store.set_checkpoint(value)
    assert store.checkpoint() == value
    store.set_checkpoint(value + timedelta(minutes=5))
    assert store.checkpoint() == value + timedelta(minutes=5)
    assert not store.event_processed("comment:2")
    store.mark_event("comment:2", "applied")
    assert store.event_processed("comment:2")
    store.mark_event("comment:2", "failed")
    assert not store.event_processed("comment:2")


def test_production_checkpoint_is_required_after_activation():
    notion = FakeNotionAdapter()
    store = NotionReconciliationStateStore(notion, "state")
    try:
        store.require_checkpoint()
    except LedgerValidationError as exc:
        assert exc.code is LedgerFailureCode.CHECKPOINT_MISSING
    else:
        raise AssertionError("missing checkpoint was accepted")
    notion.create_page(
        "state",
        {
            "State Key": {"title": [{"plain_text": "todoist:checkpoint"}]},
            "Notes": {"rich_text": [{"plain_text": "not a baseline receipt"}]},
        },
    )
    with pytest.raises(LedgerValidationError) as error:
        store.require_checkpoint()
    assert error.value.code is LedgerFailureCode.CHECKPOINT_MISSING


def test_event_identity_alias_and_metadata_round_trip(tmp_path):
    db = RuntimeDatabase(tmp_path / "runtime.db")
    db.initialize()
    store = SQLiteReconciliationStateStore(db)
    store.mark_event(
        "todoist-comment:abc",
        "Informational",
        {
            "event_type": "Todoist Comment",
            "source_provider": "Todoist",
            "source_task_id": "task-1",
            "source_comment_id": "abc",
            "source_posted_at": "2026-07-30T23:20:17Z",
            "source_digest": "a" * 64,
            "interpretation_classification": "update",
            "interpretation_status": "Informational",
            "confidence": 0.0,
            "blockers": (),
            "command_digest": "b" * 64,
            "plan_digest": "",
            "processing_outcome": "Informational",
            "execution_surface": "test",
        },
    )
    assert store.event_processed("todoist-comment:abc")
    assert store.event_processed("comment:abc")
    with db.connect() as connection:
        row = connection.execute(
            "SELECT source_task_id, source_comment_id, interpretation_status "
            "FROM processed_event WHERE event_id = ?",
            ("todoist-comment:abc",),
        ).fetchone()
    assert tuple(row) == ("task-1", "abc", "Informational")


def test_notion_event_uses_existing_shared_schema_and_notes_envelope():
    notion = FakeNotionAdapter()
    store = NotionReconciliationStateStore(notion, "state")
    store.mark_event(
        "todoist-comment:abc",
        "Informational",
        {
            "event_type": "Todoist Comment",
            "source_provider": "Todoist",
            "source_task_id": "task-1",
            "source_comment_id": "abc",
            "source_posted_at": "2026-07-30T23:20:17Z",
            "source_digest": "a" * 64,
            "interpretation_classification": "General update",
            "interpretation_status": "Informational",
            "confidence": 0.0,
            "blockers": (),
            "command_digest": "b" * 64,
            "plan_digest": "",
            "processing_outcome": "Informational",
            "execution_surface": "connector-test",
        },
    )
    page = next(iter(notion.pages.values()))
    assert set(page.properties) == {
        "State Key",
        "State Type",
        "Status",
        "Event ID",
        "Processed At",
        "Execution Surface",
        "Notes",
    }
    assert page.properties["Status"]["select"]["name"] == "Applied"
    assert page.properties["Execution Surface"]["select"]["name"] == "ChatGPT"
    notes = page.properties["Notes"]["rich_text"][0]["text"]["content"]
    import json

    envelope = json.loads(notes)
    assert envelope["logical_status"] == "Informational"
    assert envelope["source_comment_id"] == "abc"
    assert envelope["execution_surface"] == "connector-test"
    assert envelope["release_identity"] == "8.2.1"
    assert envelope["source_object_type"] == ""
    assert store.event_status("comment:abc") == "Informational"
    assert store.event_processed("todoist-comment:abc")


def test_shared_production_configuration_rejects_multiple_and_mismatched_surfaces(monkeypatch):
    monkeypatch.setenv("ATLAS_RECONCILIATION_STATE_DATABASE_ID", "database")
    monkeypatch.setenv("ATLAS_RECONCILIATION_STATE_DATA_SOURCE_ID", "source")
    assert cli.production_ledger_configuration() == ("database", "source")
    monkeypatch.setenv("ATLAS_CHATGPT_RECONCILIATION_STATE_DATA_SOURCE_ID", "other")
    try:
        cli.production_ledger_configuration()
    except RuntimeError as exc:
        assert "LEDGER_SURFACE_MISMATCH" in str(exc)
    else:
        raise AssertionError("cross-surface mismatch was accepted")
    monkeypatch.delenv("ATLAS_CHATGPT_RECONCILIATION_STATE_DATA_SOURCE_ID")
    monkeypatch.setenv("ATLAS_RECONCILIATION_STATE_DATA_SOURCE_ID", "source,other")
    try:
        cli.production_ledger_configuration()
    except RuntimeError as exc:
        assert "LEDGER_NOT_UNIQUE" in str(exc)
    else:
        raise AssertionError("multiple ledgers were accepted")
