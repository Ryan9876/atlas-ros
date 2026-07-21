from uuid import uuid4

from atlas_ros.domain.models import ObservabilityEvent
from atlas_ros.runtime import Outbox, RuntimeDatabase
from atlas_ros.workflows.w01_capture import CaptureService


def test_capture_and_outbox_export(tmp_path) -> None:
    database = RuntimeDatabase(tmp_path / "runtime.db")
    database.initialize()
    item = CaptureService(database).capture("Call vendor", "raycast")
    with database.connect() as db:
        assert db.execute("SELECT count(*) FROM pending_capture").fetchone()[0] == 1
    export = Outbox(database).export(tmp_path / "exports")
    assert export and export.exists() and str(item.correlation_id) in export.read_text()


def test_event_deduplication(tmp_path) -> None:
    database = RuntimeDatabase(tmp_path / "runtime.db")
    database.initialize()
    outbox = Outbox(database)
    event = ObservabilityEvent(
        correlation_id=uuid4(), event_type="test", workflow="unit", status="ok"
    )
    assert outbox.enqueue(event)
    assert not outbox.enqueue(event)


def test_database_transaction_rolls_back(tmp_path) -> None:
    database = RuntimeDatabase(tmp_path / "runtime.db")
    database.initialize()
    try:
        with database.connect() as db:
            db.execute("INSERT INTO migration_history VALUES ('rollback-test', 'now')")
            raise RuntimeError("fixture")
    except RuntimeError:
        pass
    with database.connect() as db:
        assert db.execute("SELECT count(*) FROM migration_history").fetchone()[0] == 0
