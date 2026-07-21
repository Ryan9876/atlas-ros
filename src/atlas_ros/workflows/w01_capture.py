# ruff: noqa: E501
from __future__ import annotations

from atlas_ros.domain.models import Capture, ObservabilityEvent
from atlas_ros.runtime.database import RuntimeDatabase


class CaptureService:
    def __init__(self, database: RuntimeDatabase) -> None:
        self.database = database

    def capture(self, content: str, source: str = "cli") -> Capture:
        capture = Capture(content=content, source=source)
        event = ObservabilityEvent(
            correlation_id=capture.correlation_id,
            event_type="capture.persisted",
            workflow="w01",
            status="pending",
        )
        now = capture.created_at.isoformat()
        with self.database.connect() as db:
            db.execute(
                "INSERT INTO pending_capture(capture_id,correlation_id,content,source,created_at) VALUES(?,?,?,?,?)",
                (
                    str(capture.capture_id),
                    str(capture.correlation_id),
                    capture.content,
                    capture.source,
                    now,
                ),
            )
            db.execute(
                "INSERT INTO outbox_event(event_id,correlation_id,payload,created_at,updated_at) VALUES(?,?,?,?,?)",
                (str(event.event_id), str(event.correlation_id), event.model_dump_json(), now, now),
            )
        return capture
