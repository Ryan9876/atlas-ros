from __future__ import annotations

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


class ReconciliationStateStore(ABC):
    @abstractmethod
    def checkpoint(self) -> datetime: ...

    @abstractmethod
    def set_checkpoint(self, value: datetime) -> None: ...

    @abstractmethod
    def event_processed(self, event_id: str) -> bool: ...

    @abstractmethod
    def mark_event(self, event_id: str, status: str) -> None: ...


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

    def event_processed(self, event_id: str) -> bool:
        with self.database.connect() as db:
            row = db.execute(
                "SELECT 1 FROM processed_event WHERE event_id = ? AND status = 'applied'",
                (event_id,),
            ).fetchone()
        return row is not None

    def mark_event(self, event_id: str, status: str) -> None:
        with self.database.connect() as db:
            db.execute(
                "INSERT INTO processed_event(event_id, processed_at, status) VALUES(?, ?, ?) "
                "ON CONFLICT(event_id) DO UPDATE SET processed_at=excluded.processed_at, "
                "status=excluded.status",
                (event_id, datetime.now(UTC).isoformat(), status),
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

    def event_processed(self, event_id: str) -> bool:
        page = self._find(event_id)
        if page is None:
            return False
        value = page.properties.get("Status", {})
        if isinstance(value, dict):
            selected = value.get("select")
            return isinstance(selected, dict) and selected.get("name") == "Applied"
        return False

    def mark_event(self, event_id: str, status: str) -> None:
        now = datetime.now(UTC).isoformat()
        normalized = "Applied" if status.lower() == "applied" else status.title()
        properties = {
            "State Key": {"title": [{"text": {"content": event_id}}]},
            "State Type": _select("Processed Event"),
            "Status": _select(normalized),
            "Event ID": _rich(event_id),
            "Processed At": _date(now),
        }
        existing = self._find(event_id)
        if existing:
            self.notion.update_page(existing.id, properties)
        else:
            self.notion.create_page(self.data_source_id, properties)
