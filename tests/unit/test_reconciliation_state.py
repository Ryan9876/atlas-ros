from datetime import UTC, datetime, timedelta

from atlas_ros.adapters.notion import FakeNotionAdapter
from atlas_ros.reconciliation.state import (
    NotionReconciliationStateStore,
    SQLiteReconciliationStateStore,
)
from atlas_ros.runtime.database import RuntimeDatabase


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
    assert store.event_status("comment:abc") == "Informational"
    assert store.event_processed("todoist-comment:abc")
