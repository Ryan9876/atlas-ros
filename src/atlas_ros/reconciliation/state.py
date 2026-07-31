from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Any

from atlas_ros.adapters.notion import NotionAdapter, NotionPage
from atlas_ros.runtime.database import RuntimeDatabase


def _date(value: str) -> dict[str, Any]:
    return {"date": {"start": value}}


def _rich(value: str) -> dict[str, Any]:
    return {"rich_text": [{"type": "text", "text": {"content": value}}]}


def _select(value: str) -> dict[str, Any]:
    return {"select": {"name": value}}


_TERMINAL_EVENT_STATUSES = {"applied", "blocked", "informational", "ignored"}


def _event_identity_aliases(event_id: str) -> tuple[str, ...]:
    if event_id.startswith("comment:"):
        return (event_id, "todoist-comment:" + event_id.removeprefix("comment:"))
    if event_id.startswith("todoist-comment:"):
        return (event_id, "comment:" + event_id.removeprefix("todoist-comment:"))
    return (event_id,)


class ReconciliationStateStore(ABC):
    @abstractmethod
    def checkpoint(self) -> datetime: ...

    @abstractmethod
    def set_checkpoint(self, value: datetime) -> None: ...

    @abstractmethod
    def event_processed(self, event_id: str) -> bool: ...

    @abstractmethod
    def event_status(self, event_id: str) -> str | None: ...

    @abstractmethod
    def mark_event(
        self,
        event_id: str,
        status: str,
        metadata: dict[str, Any] | None = None,
    ) -> None: ...


class SQLiteReconciliationStateStore(ReconciliationStateStore):
    def __init__(self, database: RuntimeDatabase) -> None:
        self.database = database

    def checkpoint(self) -> datetime:
        with self.database.connect() as db:
            row = db.execute(
                "SELECT cursor FROM sync_checkpoint WHERE integration = 'todoist'"
            ).fetchone()
        if row is None or not row[0]:
            return datetime.now(UTC) - timedelta(days=7)
        return datetime.fromisoformat(str(row[0]))

    def set_checkpoint(self, value: datetime) -> None:
        with self.database.connect() as db:
            db.execute(
                "INSERT INTO sync_checkpoint(integration, cursor, updated_at) "
                "VALUES('todoist', ?, ?) ON CONFLICT(integration) DO UPDATE SET "
                "cursor=excluded.cursor, updated_at=excluded.updated_at",
                (value.isoformat(), datetime.now(UTC).isoformat()),
            )

    def event_status(self, event_id: str) -> str | None:
        candidates = _event_identity_aliases(event_id)
        with self.database.connect() as db:
            row = None
            for candidate in candidates:
                row = db.execute(
                    "SELECT status FROM processed_event WHERE event_id = ?",
                    (candidate,),
                ).fetchone()
                if row is not None:
                    break
        return str(row[0]) if row is not None and row[0] else None

    def event_processed(self, event_id: str) -> bool:
        status = self.event_status(event_id)
        return bool(status and status.casefold() in _TERMINAL_EVENT_STATUSES)

    def mark_event(
        self,
        event_id: str,
        status: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        values = dict(metadata or {})
        now = datetime.now(UTC).isoformat()
        with self.database.connect() as db:
            db.execute(
                """
                INSERT INTO processed_event(
                    event_id, processed_at, status, event_type, source_provider,
                    source_task_id, source_comment_id, source_posted_at, source_digest,
                    interpretation_classification, interpretation_status, confidence,
                    blockers, command_digest, plan_digest, authorization_identity,
                    processing_outcome, execution_surface, metadata_json
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(event_id) DO UPDATE SET
                    processed_at=excluded.processed_at,
                    status=excluded.status,
                    event_type=excluded.event_type,
                    source_provider=excluded.source_provider,
                    source_task_id=excluded.source_task_id,
                    source_comment_id=excluded.source_comment_id,
                    source_posted_at=excluded.source_posted_at,
                    source_digest=excluded.source_digest,
                    interpretation_classification=excluded.interpretation_classification,
                    interpretation_status=excluded.interpretation_status,
                    confidence=excluded.confidence,
                    blockers=excluded.blockers,
                    command_digest=excluded.command_digest,
                    plan_digest=excluded.plan_digest,
                    authorization_identity=excluded.authorization_identity,
                    processing_outcome=excluded.processing_outcome,
                    execution_surface=excluded.execution_surface,
                    metadata_json=excluded.metadata_json
                """,
                (
                    event_id,
                    now,
                    status,
                    values.get("event_type", ""),
                    values.get("source_provider", ""),
                    values.get("source_task_id", ""),
                    values.get("source_comment_id", ""),
                    values.get("source_posted_at", ""),
                    values.get("source_digest", ""),
                    values.get("interpretation_classification", ""),
                    values.get("interpretation_status", status),
                    values.get("confidence"),
                    json.dumps(values.get("blockers", ()), sort_keys=True),
                    values.get("command_digest", ""),
                    values.get("plan_digest", ""),
                    values.get("authorization_identity", ""),
                    values.get("processing_outcome", status),
                    values.get("execution_surface", ""),
                    json.dumps(values, sort_keys=True, default=str),
                ),
            )


class NotionReconciliationStateStore(ReconciliationStateStore):
    """Shared canonical reconciliation state for CLI and connector sessions."""

    CHECKPOINT_KEY = "todoist:checkpoint"

    def __init__(self, notion: NotionAdapter, data_source_id: str) -> None:
        self.notion = notion
        self.data_source_id = data_source_id

    def _find(self, key: str) -> NotionPage | None:
        pages = self.notion.query_pages(
            self.data_source_id,
            {"filter": {"property": "State Key", "title": {"equals": key}}},
        )
        return pages[0] if pages else None

    def checkpoint(self) -> datetime:
        page = self._find(self.CHECKPOINT_KEY)
        if page is None:
            return datetime.now(UTC) - timedelta(days=7)
        value = page.properties.get("Cursor", {})
        if isinstance(value, dict):
            selected = value.get("date")
            if isinstance(selected, dict) and selected.get("start"):
                return datetime.fromisoformat(str(selected["start"]).replace("Z", "+00:00"))
        return datetime.now(UTC) - timedelta(days=7)

    def set_checkpoint(self, value: datetime) -> None:
        now = datetime.now(UTC).isoformat()
        properties = {
            "State Key": {"title": [{"text": {"content": self.CHECKPOINT_KEY}}]},
            "State Type": _select("Checkpoint"),
            "Status": _select("Applied"),
            "Cursor": _date(value.isoformat()),
            "Processed At": _date(now),
            "Event ID": _rich(""),
        }
        existing = self._find(self.CHECKPOINT_KEY)
        if existing:
            self.notion.update_page(existing.id, properties)
        else:
            self.notion.create_page(self.data_source_id, properties)

    @staticmethod
    def _rich_text_value(value: Any) -> str:
        if not isinstance(value, dict):
            return ""
        items = value.get("rich_text")
        if not isinstance(items, list):
            return ""
        return "".join(
            str(item.get("plain_text", item.get("text", {}).get("content", "")))
            for item in items
            if isinstance(item, dict)
        )

    def event_status(self, event_id: str) -> str | None:
        page = next(
            (found for key in _event_identity_aliases(event_id) if (found := self._find(key))),
            None,
        )
        if page is None:
            return None

        notes = self._rich_text_value(page.properties.get("Notes", {}))
        if notes:
            try:
                envelope = json.loads(notes)
            except json.JSONDecodeError:
                envelope = None
            if isinstance(envelope, dict):
                logical = envelope.get("logical_status") or envelope.get(
                    "interpretation_status"
                )
                if isinstance(logical, str) and logical.strip():
                    return logical.strip()

        value = page.properties.get("Status", {})
        if isinstance(value, dict):
            selected = value.get("select")
            if isinstance(selected, dict) and selected.get("name"):
                return str(selected["name"])
        return None

    def event_processed(self, event_id: str) -> bool:
        status = self.event_status(event_id)
        return bool(status and status.casefold() in _TERMINAL_EVENT_STATUSES)

    def mark_event(
        self,
        event_id: str,
        status: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        values = dict(metadata or {})
        logical_status = status.strip() or "Failed"
        physical_status = "Failed" if logical_status.casefold() == "failed" else "Applied"
        requested_surface = str(values.get("execution_surface") or "ChatGPT")
        execution_surface = (
            requested_surface if requested_surface in {"CLI", "ChatGPT"} else "ChatGPT"
        )
        envelope = {
            "schema_version": "1.0",
            "event_id": event_id,
            "logical_status": logical_status,
            "processed_at": now,
            "execution_surface": requested_surface,
            **values,
        }
        properties: dict[str, Any] = {
            "State Key": {"title": [{"text": {"content": event_id}}]},
            "State Type": _select("Processed Event"),
            "Status": _select(physical_status),
            "Event ID": _rich(event_id),
            "Processed At": _date(now),
            "Execution Surface": _select(execution_surface),
            "Notes": _rich(json.dumps(envelope, sort_keys=True, default=str)),
        }
        existing = next(
            (found for key in _event_identity_aliases(event_id) if (found := self._find(key))),
            None,
        )
        if existing:
            self.notion.update_page(existing.id, properties)
        else:
            self.notion.create_page(self.data_source_id, properties)
