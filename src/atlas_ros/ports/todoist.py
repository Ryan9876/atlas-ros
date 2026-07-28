"""Provider-neutral Todoist client records and boundary contracts."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol


class TodoistProjectRecord(Protocol):
    id: str
    name: str


class TodoistSectionRecord(Protocol):
    id: str
    project_id: str
    name: str


class TodoistTaskRecord(Protocol):
    id: str
    project_id: str
    section_id: str | None
    parent_id: str | None
    content: str
    description: str
    priority: int
    due_date: str | None


class TodoistClientPort(Protocol):
    """Replaceable provider client that cannot plan or authorize work."""

    def list_projects(self) -> Sequence[TodoistProjectRecord]: ...

    def list_tasks(
        self,
        *,
        project_id: str = "",
        parent_id: str = "",
    ) -> Sequence[TodoistTaskRecord]: ...

    def create_task(
        self,
        *,
        content: str,
        project_id: str,
        section_id: str | None,
        parent_id: str | None,
        description: str,
        idempotency_key: str,
    ) -> TodoistTaskRecord: ...

    def get_task(self, task_id: str) -> TodoistTaskRecord: ...


__all__ = [
    "TodoistClientPort",
    "TodoistProjectRecord",
    "TodoistSectionRecord",
    "TodoistTaskRecord",
]
