"""Attended Todoist command-source extraction without interpretation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from atlas_ros.contracts.operational_awareness import (
    AuthoritativeSystem,
    CommandSourceRefV1,
)


@dataclass(frozen=True, slots=True)
class TodoistCommandSourceAdapter:
    """Extract exact task text and identity; parsing belongs to the capability layer."""

    def extract(self, task: dict[str, Any]) -> CommandSourceRefV1:
        task_id = _required(task, "id")
        revision = _required(task, "updated_at")
        text = _required(task, "content")
        description = task.get("description")
        if isinstance(description, str) and description.strip():
            text = f"{text}\n{description.strip()}"
        return CommandSourceRefV1.create(
            source_provider=AuthoritativeSystem.TODOIST,
            source_task_id=task_id,
            source_task_revision=revision,
            source_command_text=text,
            parent_task_id=_optional(task.get("parent_id")),
        )


def _required(row: dict[str, Any], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Todoist command source requires {key}")
    return value.strip()


def _optional(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None
