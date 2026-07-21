# ruff: noqa: E501
from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from atlas_ros.domain.models import ObservabilityEvent
from atlas_ros.runtime.database import RuntimeDatabase


class Outbox:
    def __init__(self, database: RuntimeDatabase) -> None:
        self.database = database

    def enqueue(self, event: ObservabilityEvent) -> bool:
        now = datetime.now(UTC).isoformat()
        with self.database.connect() as db:
            cursor = db.execute(
                "INSERT OR IGNORE INTO outbox_event(event_id,correlation_id,payload,created_at,updated_at) VALUES(?,?,?,?,?)",
                (str(event.event_id), str(event.correlation_id), event.model_dump_json(), now, now),
            )
            return cursor.rowcount == 1

    def export(self, directory: Path, limit: int = 100) -> Path | None:
        with self.database.connect() as db:
            rows = db.execute(
                "SELECT event_id,payload FROM outbox_event WHERE status='pending' ORDER BY created_at LIMIT ?",
                (limit,),
            ).fetchall()
            if not rows:
                return None
            payload = "".join(
                json.dumps(json.loads(row["payload"]), sort_keys=True) + "\n" for row in rows
            )
            import hashlib

            digest = hashlib.sha256(payload.encode()).hexdigest()
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            target = directory / f"events-{digest}.jsonl"
            fd, temporary = tempfile.mkstemp(dir=directory, prefix=".events-", suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, target)
                os.chmod(target, 0o600)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
            db.executemany(
                "UPDATE outbox_event SET status='exported',updated_at=? WHERE event_id=?",
                [(datetime.now(UTC).isoformat(), row["event_id"]) for row in rows],
            )
            return target
