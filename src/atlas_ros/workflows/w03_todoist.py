from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from atlas_ros.adapters.todoist import LiveTodoistAdapter, TodoistAdapter, TodoistTask
from atlas_ros.config.loader import load_config
from atlas_ros.domain.models import Action
from atlas_ros.workflows.w03a_decomposition import DecompositionService

NOTION_MARKERS = re.compile(
    r"(?:notion\.(?:so|site)|app\.notion\.com|Notion (?:Action|Capture):|References:|collection://|[0-9a-f]{32})",
    re.I,
)


@dataclass(frozen=True)
class TodoistPlan:
    action_id: str
    project: str
    subtasks: list[str]
    dry_run: bool = True
    task_id: str = ""


class ActionLinkWriter(Protocol):
    def store_todoist_link(self, action_id: str, task_id: str) -> None: ...


def task_description(objective: str, done_when: str) -> str:
    objective, done_when = objective.strip(), done_when.strip()
    if not objective or not done_when:
        raise ValueError("Objective and Done when must be non-empty")
    text = f"**Objective:**\n{objective}\n\n**Done when:**\n{done_when}"
    if NOTION_MARKERS.search(text):
        raise ValueError("Todoist content contains prohibited Notion reference")
    return text


class TodoistService:
    def __init__(
        self, adapter: TodoistAdapter | None = None, link_writer: ActionLinkWriter | None = None
    ) -> None:
        self.adapter, self.link_writer = adapter, link_writer

    def plan(self, action: Action) -> TodoistPlan:
        report = DecompositionService().readiness(action)
        if report.status.value != "ready":
            raise ValueError(f"W03A gate failed: {', '.join(report.failed_rules)}")
        config = load_config("todoist")
        if action.todoist_project not in config["projects"]:
            raise ValueError("invalid Todoist project")
        approved = set(config.get("approved_labels", ()))
        if any(
            label in set(config["prohibited_labels"]) or (approved and label not in approved)
            for label in action.labels
        ):
            raise ValueError("prohibited or unapproved Todoist label")
        task_description(action.title, action.definition_of_done)
        return TodoistPlan(action.id, action.todoist_project, report.proposed_subtasks)

    def apply(self, action: Action, confirmed: bool = False) -> TodoistPlan:
        if not confirmed:
            raise PermissionError("explicit confirmation is required")
        if self.adapter is None:
            raise PermissionError("no production Todoist adapter is configured")
        plan = self.plan(action)
        projects = {p.name: p.id for p in self.adapter.list_projects()}
        if plan.project not in projects:
            raise ValueError("configured Todoist project is not available live")
        section_id = None
        if action.todoist_section:
            sections = {
                s["name"]: s["id"] for s in self.adapter.list_sections(projects[plan.project])
            }
            if action.todoist_section not in sections:
                raise ValueError("configured Todoist section is not available live")
            section_id = sections[action.todoist_section]
        missing = set(action.labels) - set(self.adapter.list_labels())
        if missing:
            raise ValueError("configured Todoist labels are not available live")
        description = task_description(action.title, action.definition_of_done)
        if action.todoist_task_id:
            task = self.adapter.update_task(
                action.todoist_task_id,
                content=action.title,
                description=description,
                project_id=projects[plan.project],
                section_id=section_id,
            )
        else:
            task = self.adapter.create_task(
                content=action.title,
                project_id=projects[plan.project],
                section_id=section_id,
                parent_id=None,
                description=description,
                idempotency_key=LiveTodoistAdapter.idempotency_key(action.id),
            )
        self._validate_readback(
            task, action.title, description, projects[plan.project], section_id, None
        )
        existing = {t.content: t for t in self.adapter.list_tasks(parent_id=task.id)}
        for index, raw in enumerate(plan.subtasks, 1):
            title = f"{index:02d} — {raw}"
            subdesc = task_description(raw, f"{raw} is completed and verified.")
            child = existing.get(title)
            if child:
                child = self.adapter.update_task(
                    child.id,
                    content=title,
                    description=subdesc,
                    parent_id=task.id,
                    project_id=projects[plan.project],
                    order=index,
                )
            else:
                child = self.adapter.create_task(
                    content=title,
                    project_id=projects[plan.project],
                    section_id=None,
                    parent_id=task.id,
                    description=subdesc,
                    idempotency_key=LiveTodoistAdapter.idempotency_key(
                        f"{action.id}:{index}:{raw}"
                    ),
                )
            self._validate_readback(child, title, subdesc, projects[plan.project], None, task.id)
        children = sorted(
            self.adapter.list_tasks(parent_id=task.id), key=lambda t: (t.order, t.content)
        )
        expected = [f"{i:02d} — {raw}" for i, raw in enumerate(plan.subtasks, 1)]
        if [c.content for c in children] != expected:
            raise ValueError("Todoist subtask readback did not match requested tree")
        if self.link_writer:
            self.link_writer.store_todoist_link(action.id, task.id)
        return TodoistPlan(action.id, plan.project, plan.subtasks, False, task.id)

    @staticmethod
    def _validate_readback(
        task: TodoistTask,
        title: str,
        description: str,
        project_id: str,
        section_id: str | None,
        parent_id: str | None,
    ) -> None:
        if (task.content, task.description, task.project_id, task.section_id, task.parent_id) != (
            title,
            description,
            project_id,
            section_id,
            parent_id,
        ):
            raise ValueError("Todoist readback did not match requested task")
        if NOTION_MARKERS.search(task.content + "\n" + task.description):
            raise ValueError("Todoist readback contains prohibited Notion content")
