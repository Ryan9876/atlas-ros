"""Attended Todoist command-source extraction without interpretation."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from atlas_ros.adapters.todoist import TodoistComment, TodoistTask
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
            source_event_id=f"task:{task_id}:{revision}",
            source_event_type="task-update",
        )


@dataclass(frozen=True, slots=True)
class TodoistCommentSourceAdapter:
    """Create a canonical, digest-bound command source from one Todoist comment.

    Comment identity is independent from the mutable parent task revision. The adapter
    performs no interpretation and grants no execution authority.
    """

    timezone_name: str = "America/Toronto"

    def extract(
        self,
        *,
        comment: TodoistComment,
        source_task: TodoistTask,
        parent_task: TodoistTask,
        parent_action_record_id: str,
        parent_action_record_url: str,
        parent_outcome_title: str,
        retrieved_at: datetime | None = None,
    ) -> CommandSourceRefV1:
        posted_at = _required_model(comment.posted_at, "posted_at")
        text = _required_model(comment.content, "content")
        comment_id = _required_model(comment.id, "id")
        source_task_id = _required_model(source_task.id, "source task id")
        parent_task_id = _required_model(parent_task.id, "parent task id")
        event_id = f"todoist-comment:{comment_id}"
        return CommandSourceRefV1.create(
            source_provider=AuthoritativeSystem.TODOIST,
            source_task_id=source_task_id,
            source_task_revision=posted_at,
            source_command_text=text,
            parent_task_id=parent_task_id,
            source_event_id=event_id,
            source_event_type="todoist-comment",
            source_comment_id=comment_id,
            source_author_identity=comment.posted_uid,
            source_posted_at=posted_at,
            source_retrieved_at=(retrieved_at or datetime.now(UTC)).isoformat(),
            source_timezone=self.timezone_name,
            parent_action_record_id=parent_action_record_id,
            parent_action_record_url=parent_action_record_url,
            parent_outcome_title=parent_outcome_title,
        )


def _required(row: dict[str, Any], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Todoist command source requires {key}")
    return value.strip()


def _required_model(value: Any, key: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Todoist comment source requires {key}")
    return value.strip()


def _optional(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None
