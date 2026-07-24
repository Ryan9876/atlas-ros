from __future__ import annotations

from dataclasses import dataclass

from atlas_ros.adapters.todoist import LiveTodoistAdapter, TodoistAdapter, TodoistTask


@dataclass(frozen=True)
class TodoistExecutionTarget:
    project_id: str
    section_id: str | None


class TodoistExecutionAdapter:
    """Performs Todoist-specific reads and writes without execution-policy decisions."""

    def __init__(self, provider: TodoistAdapter) -> None:
        self._provider = provider

    def resolve_target(self, project: str, section: str, labels: tuple[str, ...]) -> TodoistExecutionTarget:
        projects = {item.name: item.id for item in self._provider.list_projects()}
        if project not in projects:
            raise ValueError("configured Todoist project is not available live")
        project_id = projects[project]
        section_id: str | None = None
        if section:
            available = self._provider.list_sections(project_id)
            if available or isinstance(self._provider, LiveTodoistAdapter):
                sections = {item["name"]: item["id"] for item in available}
                if section not in sections:
                    raise ValueError("configured Todoist section is not available live")
                section_id = sections[section]
        missing = set(labels) - set(self._provider.list_labels())
        if missing:
            raise ValueError("configured Todoist labels are not available live")
        return TodoistExecutionTarget(project_id=project_id, section_id=section_id)

    def upsert_parent(
        self,
        *,
        action_id: str,
        existing_task_id: str,
        title: str,
        description: str,
        target: TodoistExecutionTarget,
    ) -> TodoistTask:
        if existing_task_id:
            current = self._provider.get_task(existing_task_id)
            task = self._provider.update_task(
                current.id,
                content=title,
                description=description,
                project_id=target.project_id,
                section_id=target.section_id,
                parent_id=current.parent_id,
                order=current.order,
            )
        else:
            task = self._provider.create_task(
                content=title,
                project_id=target.project_id,
                section_id=target.section_id,
                parent_id=None,
                description=description,
                idempotency_key=LiveTodoistAdapter.idempotency_key(action_id),
            )
        self.verify_task(task, title, description, target.project_id, target.section_id, task.parent_id)
        return task

    def upsert_child(
        self,
        *,
        action_id: str,
        parent_id: str,
        project_id: str,
        sequence: int,
        raw_title: str,
        description: str,
        existing: TodoistTask | None,
    ) -> TodoistTask:
        title = f"{sequence:02d} — {raw_title}"
        if existing is not None:
            child = self._provider.update_task(
                existing.id,
                content=title,
                description=description,
                parent_id=parent_id,
                project_id=project_id,
                section_id=None,
                order=sequence,
            )
        else:
            child = self._provider.create_task(
                content=title,
                project_id=project_id,
                section_id=None,
                parent_id=parent_id,
                description=description,
                idempotency_key=LiveTodoistAdapter.idempotency_key(
                    f"{action_id}:{sequence}:{raw_title}"
                ),
            )
        self.verify_task(child, title, description, project_id, None, parent_id)
        return child

    def children_by_content(self, parent_id: str) -> dict[str, TodoistTask]:
        return {task.content: task for task in self._provider.list_tasks(parent_id=parent_id)}

    def verify_tree(self, parent_id: str, expected_titles: list[str]) -> None:
        children = sorted(
            self._provider.list_tasks(parent_id=parent_id),
            key=lambda child: (child.order, child.content),
        )
        if [child.content for child in children] != expected_titles:
            raise ValueError("Todoist subtask readback did not match requested tree")

    def move_group(self, task_id: str, target_section_id: str) -> None:
        parent = self._provider.get_task(task_id)
        children = sorted(
            self._provider.list_tasks(parent_id=task_id),
            key=lambda child: (child.order, child.content),
        )
        snapshot = {child.id: (child.parent_id, child.order) for child in children}
        updated_parent = self._provider.update_task(
            parent.id,
            project_id=parent.project_id,
            section_id=target_section_id,
            parent_id=parent.parent_id,
            order=parent.order,
        )
        if updated_parent.section_id != target_section_id:
            raise ValueError("Todoist parent section move readback failed")
        for child in children:
            updated = self._provider.update_task(
                child.id,
                project_id=parent.project_id,
                section_id=None,
                parent_id=task_id,
                order=child.order,
            )
            if (updated.parent_id, updated.order) != snapshot[child.id]:
                raise ValueError("Todoist hierarchy changed during section move")
        readback = self._provider.list_tasks(parent_id=task_id)
        if len(readback) != len(children) or any(child.parent_id != task_id for child in readback):
            raise ValueError("Todoist child-count or parentId validation failed")

    @staticmethod
    def verify_task(
        task: TodoistTask,
        title: str,
        description: str,
        project_id: str,
        section_id: str | None,
        parent_id: str | None,
    ) -> None:
        actual = (task.content, task.description, task.project_id, task.section_id, task.parent_id)
        expected = (title, description, project_id, section_id, parent_id)
        if actual != expected:
            raise ValueError("Todoist readback did not match requested task")
