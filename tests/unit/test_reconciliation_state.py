from datetime import UTC, datetime, timedelta

from atlas_ros.adapters.notion import FakeNotionAdapter
from atlas_ros.runtime.database import RuntimeDatabase
from atlas_ros.workflows.reconciliation_state import (
    NotionReconciliationStateStore,
    SQLiteReconciliationStateStore,
)


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
