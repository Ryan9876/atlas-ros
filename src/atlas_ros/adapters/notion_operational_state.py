"""Pure Notion-to-operational-record translation; no planning or writes."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from atlas_ros.contracts.operational_awareness import (
    AcceptanceState,
    AuthoritativeSystem,
    NormalizedOperationalRecordV1,
    OperationalRecordRefV1,
    OperationalRecordType,
)


@dataclass(frozen=True, slots=True)
class NotionOperationalStateAdapter:
    """Normalize already-authorized Notion projections into canonical records."""

    def normalize(
        self, rows: Iterable[dict[str, Any]]
    ) -> tuple[NormalizedOperationalRecordV1, ...]:
        return tuple(
            sorted(
                (self._normalize(row) for row in rows),
                key=lambda item: item.record_ref.canonical_record_id,
            )
        )

    @staticmethod
    def _normalize(row: dict[str, Any]) -> NormalizedOperationalRecordV1:
        record_id = _required(row, "id")
        revision = _required(row, "last_edited_time")
        raw_type = str(row.get("record_type", "action_record"))
        reference = OperationalRecordRefV1.create(
            record_type=OperationalRecordType(raw_type),
            canonical_record_id=record_id,
            authoritative_system=AuthoritativeSystem.NOTION,
            canonical_url=_optional(row.get("url")),
            parent_record_id=_optional(row.get("parent_record_id")),
            source_revision=revision,
        )
        acceptance = str(row.get("acceptance_status", "not_required"))
        return NormalizedOperationalRecordV1.create(
            record_ref=reference,
            title=_required(row, "title"),
            observed_state=str(row.get("state", "")),
            owner=_optional(row.get("owner")),
            responsible_party=_optional(row.get("responsible_party")),
            accountable_party=_optional(row.get("accountable_party")),
            definition_of_done=_strings(row.get("definition_of_done")),
            completion_evidence=_strings(row.get("completion_evidence")),
            blockers=_strings(row.get("blockers")),
            dependencies=_strings(row.get("dependencies")),
            due_date=_optional(row.get("due_date")),
            checkpoint=_optional(row.get("checkpoint")),
            priority=int(row.get("priority", 4)),
            child_ids=_strings(row.get("child_ids")),
            delegated=bool(row.get("delegated", False)),
            acceptance_status=AcceptanceState(acceptance),
            updated_at=_optional(row.get("updated_at")) or revision,
            completed=bool(row.get("completed", False)),
            technically_complete=bool(row.get("technically_complete", False)),
            approval_required=bool(row.get("approval_required", False)),
            approval_received=bool(row.get("approval_received", False)),
            cancelled=bool(row.get("cancelled", False)),
            protected_history=bool(row.get("protected_history", False)),
            todoist_task_id=_optional(row.get("todoist_task_id")),
            expected_outcome=_optional(row.get("expected_outcome")),
            delegate_due=_optional(row.get("delegate_due")),
            follow_up_checkpoint=_optional(row.get("follow_up_checkpoint")),
            todoist_checkpoint_id=_optional(row.get("todoist_checkpoint_id")),
            todoist_checkpoint_url=_optional(row.get("todoist_checkpoint_url")),
            source_update=_optional(row.get("source_update")),
            command_digest=_optional(row.get("command_digest")),
            idempotency_identity=_optional(row.get("idempotency_identity")),
            latest_reconciliation_state=_optional(row.get("latest_reconciliation_state")),
            received_evidence=_strings(row.get("received_evidence")),
            extra=dict(row.get("extra") or {}),
        )


def _required(row: dict[str, Any], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Notion operational projection requires {key}")
    return value.strip()


def _optional(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _strings(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,) if value else ()
    if isinstance(value, list | tuple):
        return tuple(str(item) for item in value if str(item).strip())
    raise ValueError("operational list field must be text or a sequence")
