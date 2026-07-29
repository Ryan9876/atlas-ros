"""Pure Todoist hierarchy normalization for Operational Awareness."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from atlas_ros.contracts.operational_awareness import (
    AuthoritativeSystem,
    NormalizedOperationalRecordV1,
    OperationalRecordRefV1,
    OperationalRecordType,
)


@dataclass(frozen=True, slots=True)
class TodoistOperationalStateAdapter:
    """Translate authorized task projections without interpreting commands."""

    def normalize(
        self, tasks: Iterable[dict[str, Any]]
    ) -> tuple[NormalizedOperationalRecordV1, ...]:
        rows = list(tasks)
        children: dict[str, list[str]] = {}
        for task in rows:
            parent = task.get("parent_id")
            if isinstance(parent, str) and parent:
                children.setdefault(parent, []).append(str(task["id"]))
        normalized = []
        for task in rows:
            task_id = _required(task, "id")
            revision = _required(task, "updated_at")
            reference = OperationalRecordRefV1.create(
                record_type=OperationalRecordType.TODOIST_TASK,
                canonical_record_id=f"todoist:{task_id}",
                authoritative_system=AuthoritativeSystem.TODOIST,
                canonical_url=_optional(task.get("url")),
                parent_record_id=(
                    f"todoist:{task['parent_id']}"
                    if task.get("parent_id")
                    else None
                ),
                source_revision=revision,
            )
            normalized.append(
                NormalizedOperationalRecordV1.create(
                    record_ref=reference,
                    title=_required(task, "content"),
                    observed_state="completed" if bool(task.get("completed")) else "active",
                    owner=_optional(task.get("owner")) or "Ryan",
                    accountable_party="Ryan",
                    definition_of_done=_strings(task.get("definition_of_done")),
                    completion_evidence=_strings(task.get("completion_evidence")),
                    blockers=_strings(task.get("blockers")),
                    dependencies=_strings(task.get("dependencies")),
                    due_date=_optional(task.get("due_date")),
                    priority=int(task.get("priority", 4)),
                    child_ids=tuple(
                        f"todoist:{item}"
                        for item in sorted(children.get(task_id, []))
                    ),
                    updated_at=revision,
                    completed=bool(task.get("completed", False)),
                    cancelled=bool(task.get("cancelled", False)),
                    todoist_task_id=task_id,
                    extra={"source": "todoist", "description": str(task.get("description", ""))},
                )
            )
        return tuple(sorted(normalized, key=lambda item: item.record_ref.canonical_record_id))


def _required(row: dict[str, Any], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Todoist projection requires {key}")
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
    raise ValueError("Todoist operational list field must be text or a sequence")
