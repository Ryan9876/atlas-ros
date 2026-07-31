from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
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

HISTORICAL_W04_DATABASE_ID = "ba2518b1-3c97-4a94-8324-414f74ed8830"
HISTORICAL_W04_DATA_SOURCE_ID = "afbb753c-3112-4784-9165-f786b503d1f7"
HISTORICAL_W04_TITLE = "HISTORICAL — W04 Reconciliation State"


class LedgerFailureCode(StrEnum):
    TARGET_DELETED = "LEDGER_TARGET_DELETED"
    TARGET_HISTORICAL = "LEDGER_TARGET_HISTORICAL"
    SCHEMA_INVALID = "LEDGER_SCHEMA_INVALID"
    NOT_UNIQUE = "LEDGER_NOT_UNIQUE"
    CHECKPOINT_MISSING = "LEDGER_CHECKPOINT_MISSING"
    READBACK_FAILED = "LEDGER_READBACK_FAILED"
    SURFACE_MISMATCH = "LEDGER_SURFACE_MISMATCH"
    PRODUCTION_FALLBACK_PROHIBITED = "LEDGER_PRODUCTION_FALLBACK_PROHIBITED"
    BASELINE_AUTHORIZATION_INVALID = "BASELINE_AUTHORIZATION_INVALID"
    BASELINE_CONFLICT = "BASELINE_CONFLICT"


class LedgerValidationError(ValueError):
    def __init__(self, code: LedgerFailureCode, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class ProductionLedgerDescriptor:
    """The only configuration accepted for production reconciliation state."""

    database_id: str
    data_source_id: str
    title: str = "Execution Reconciliation State"


_REQUIRED_PROPERTIES: dict[str, tuple[str, ...]] = {
    "State Key": ("title",),
    "State Type": ("select",),
    "Status": ("select",),
    "Cursor": ("date",),
    "Event ID": ("rich_text", "text"),
    "Processed At": ("date",),
    "Execution Surface": ("select",),
    "Notes": ("rich_text", "text"),
}

_REQUIRED_ENVELOPE_KEYS = frozenset(
    {
        "schema_version", "state_key", "event_id", "event_aliases", "logical_status",
        "processed_at", "execution_surface", "event_type", "source_provider",
        "source_object_type", "source_task_id", "parent_task_id", "source_comment_id",
        "source_posted_at", "source_updated_at", "source_digest",
        "interpretation_classification", "interpretation_status", "confidence", "blockers",
        "ambiguity", "inferred_fields", "field_origins", "command_digest", "plan_digest",
        "authorization_identity", "correlation_id", "causation_id", "processing_outcome",
        "readback_status", "release_identity",
    }
)


def validate_production_ledger(
    notion: NotionAdapter,
    descriptor: ProductionLedgerDescriptor,
) -> None:
    """Fail closed before any plan or apply reads production ledger state."""
    if not descriptor.database_id or not descriptor.data_source_id:
        raise LedgerValidationError(
            LedgerFailureCode.NOT_UNIQUE, "database and data source are required"
        )
    if (
        descriptor.database_id == HISTORICAL_W04_DATABASE_ID
        or descriptor.data_source_id == HISTORICAL_W04_DATA_SOURCE_ID
    ):
        raise LedgerValidationError(
            LedgerFailureCode.TARGET_HISTORICAL, "W04 identity is prohibited"
        )
    try:
        source = notion.fetch_data_source(descriptor.data_source_id)
    except Exception as exc:
        raise LedgerValidationError(
            LedgerFailureCode.READBACK_FAILED, "data source is inaccessible"
        ) from exc
    if bool(source.get("archived") or source.get("in_trash") or source.get("deleted")):
        raise LedgerValidationError(
            LedgerFailureCode.TARGET_DELETED, "data source is deleted or trashed"
        )
    parent = source.get("parent")
    if isinstance(parent, Mapping):
        parent_id = str(parent.get("database_id") or parent.get("id") or "")
        if parent_id and parent_id != descriptor.database_id:
            raise LedgerValidationError(
                LedgerFailureCode.SURFACE_MISMATCH,
                "configured database does not own the data source",
            )
    title = str(source.get("title") or source.get("name") or "")
    if (
        not title
        or title != descriptor.title
        or "historical" in title.casefold()
        or "w04" in title.casefold()
    ):
        raise LedgerValidationError(
            LedgerFailureCode.TARGET_HISTORICAL, "data source title is not production"
        )
    properties = source.get("properties") or source.get("schema")
    if not isinstance(properties, dict):
        raise LedgerValidationError(LedgerFailureCode.SCHEMA_INVALID, "properties are absent")
    for name, types in _REQUIRED_PROPERTIES.items():
        property_spec = properties.get(name)
        actual_type = property_spec.get("type") if isinstance(property_spec, dict) else None
        if actual_type not in types:
            raise LedgerValidationError(
                LedgerFailureCode.SCHEMA_INVALID, f"{name} has invalid type"
            )
    for name, expected in {
        "State Type": {"Checkpoint", "Processed Event"},
        "Status": {"Applied", "Failed"},
        "Execution Surface": {"CLI", "ChatGPT", "Automation"},
    }.items():
        options = properties[name].get("select", {}).get(
            "options", properties[name].get("options", [])
        )
        values = {str(item.get("name")) for item in options if isinstance(item, dict)}
        if not expected.issubset(values):
            raise LedgerValidationError(
                LedgerFailureCode.SCHEMA_INVALID, f"{name} options are incomplete"
            )


def _event_identity_aliases(event_id: str) -> tuple[str, ...]:
    if event_id.startswith("comment:"):
        return (event_id, "todoist-comment:" + event_id.removeprefix("comment:"))
    if event_id.startswith("todoist-comment:"):
        return (event_id, "comment:" + event_id.removeprefix("todoist-comment:"))
    return (event_id,)


def event_identity_aliases(event_id: str) -> tuple[str, ...]:
    """Return canonical and compatibility identities without exposing implementation detail."""
    return _event_identity_aliases(event_id)


def event_envelope(
    event_id: str,
    status: str,
    processed_at: str,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Produce a complete, version-neutral evidence envelope for every ledger event."""
    values = dict(metadata or {})
    envelope: dict[str, Any] = {
        "schema_version": "8.2",
        "state_key": event_id,
        "event_id": event_id,
        "event_aliases": list(_event_identity_aliases(event_id)[1:]),
        "logical_status": status,
        "processed_at": processed_at,
        "execution_surface": "ChatGPT",
        "event_type": "",
        "source_provider": "",
        "source_object_type": "",
        "source_task_id": "",
        "parent_task_id": "",
        "source_comment_id": "",
        "source_posted_at": "",
        "source_updated_at": "",
        "source_digest": "",
        "interpretation_classification": "",
        "interpretation_status": status,
        "confidence": None,
        "blockers": [],
        "ambiguity": [],
        "inferred_fields": {},
        "field_origins": {},
        "command_digest": "",
        "plan_digest": "",
        "authorization_identity": "",
        "correlation_id": "",
        "causation_id": "",
        "processing_outcome": status,
        "readback_status": "pending",
        "release_identity": "8.2.1",
    }
    envelope.update(values)
    envelope["state_key"] = event_id
    envelope["event_id"] = event_id
    envelope["event_aliases"] = list(_event_identity_aliases(event_id)[1:])
    return envelope


def has_complete_envelope(envelope: Mapping[str, Any]) -> bool:
    return _REQUIRED_ENVELOPE_KEYS.issubset(envelope)


def decode_event_envelope(value: str) -> dict[str, Any] | None:
    """Decode direct JSON or the single extra string layer used by connector writes."""
    decoded: Any = value
    for _ in range(2):
        if not isinstance(decoded, str):
            break
        try:
            decoded = json.loads(decoded)
        except json.JSONDecodeError:
            return None
    return decoded if isinstance(decoded, dict) else None


class ReconciliationStateStore(ABC):
    @abstractmethod
    def checkpoint(self) -> datetime: ...

    @abstractmethod
    def set_checkpoint(self, value: datetime, metadata: dict[str, Any] | None = None) -> None: ...

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

    def set_checkpoint(self, value: datetime, metadata: dict[str, Any] | None = None) -> None:
        del metadata
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

    def require_checkpoint(self) -> None:
        checkpoint = self._find(self.CHECKPOINT_KEY)
        if checkpoint is None:
            raise LedgerValidationError(
                LedgerFailureCode.CHECKPOINT_MISSING,
                "production reconciliation is not activated until baseline checkpoint readback",
            )
        notes = self._rich_text_value(checkpoint.properties.get("Notes", {}))
        envelope = decode_event_envelope(notes)
        if envelope is None:
            raise LedgerValidationError(
                LedgerFailureCode.CHECKPOINT_MISSING,
                "production reconciliation checkpoint evidence is invalid",
            )
        if not (
            isinstance(envelope, dict)
            and has_complete_envelope(envelope)
            and envelope.get("event_id") == self.CHECKPOINT_KEY
            and envelope.get("logical_status") == "applied"
            and envelope.get("processing_outcome") == "baseline_checkpoint_created"
            and envelope.get("readback_status") == "verified"
        ):
            raise LedgerValidationError(
                LedgerFailureCode.CHECKPOINT_MISSING,
                "production reconciliation checkpoint evidence is incomplete",
            )

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
        notes = self._rich_text_value(page.properties.get("Notes", {}))
        envelope = decode_event_envelope(notes)
        if envelope is not None:
            exact_cutover = envelope.get("baseline_cutover_at")
            if isinstance(exact_cutover, str) and exact_cutover:
                return datetime.fromisoformat(exact_cutover.replace("Z", "+00:00"))
        value = page.properties.get("Cursor", {})
        if isinstance(value, dict):
            selected = value.get("date")
            if isinstance(selected, dict) and selected.get("start"):
                return datetime.fromisoformat(str(selected["start"]).replace("Z", "+00:00"))
        return datetime.now(UTC) - timedelta(days=7)

    def set_checkpoint(self, value: datetime, metadata: dict[str, Any] | None = None) -> None:
        now = datetime.now(UTC).isoformat()
        properties = {
            "State Key": {"title": [{"text": {"content": self.CHECKPOINT_KEY}}]},
            "State Type": _select("Checkpoint"),
            "Status": _select("Applied"),
            "Cursor": _date(value.isoformat()),
            "Processed At": _date(now),
            "Event ID": _rich(""),
            "Execution Surface": _select("CLI"),
            "Notes": _rich(json.dumps(event_envelope(
                self.CHECKPOINT_KEY,
                "applied",
                now,
                {
                    "execution_surface": "CLI",
                    "processing_outcome": "checkpoint_created",
                    **(metadata or {}),
                },
            ), sort_keys=True, default=str)),
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
            envelope = decode_event_envelope(notes)
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
        envelope = event_envelope(
            event_id,
            logical_status,
            now,
            {"execution_surface": requested_surface, **values},
        )
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
