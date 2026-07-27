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
    """Minimal provider client surface used by exact attended execution."""

    def list_projects(self) -> Sequence[TodoistProjectRecord]: ...

    def list_tasks(self, *, project_id: str | None = None) -> Sequence[TodoistTaskRecord]: ...

    def create_task(
        self,
        *,
        content: str,
        description: str,
        project_id: str,
        section_id: str | None = None,
        parent_id: str | None = None,
        priority: int = 1,
        due_date: str | None = None,
    ) -> TodoistTaskRecord: ...

    def get_task(self, task_id: str) -> TodoistTaskRecord: ...


__all__ = [
    "TodoistClientPort",
    "TodoistProjectRecord",
    "TodoistSectionRecord",
    "TodoistTaskRecord",
]
