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
BULLET = re.compile(r"^\s*[-*]\s+\S+")
MULTI_CRITERION_PROSE = re.compile(r";|,\s+(?:and\s+)?(?:then\s+)?(?:the\s+)?[a-z]", re.I)

SECTION_PRECEDENCE = (
    "Leadership & Team",
    "Active Projects",
    "Operations",
    "Development & Learning",
    "Waiting on Others",
)
SECTION_RULES: dict[str, tuple[str, ...]] = {
    "Leadership & Team": (
        "team operating",
        "operating model",
        "performance review",
        "1:1",
        "one-on-one",
        "interview",
        "hiring",
        "roles and responsibilities",
        "responsibility standards",
        "decision rights",
        "coaching",
        "career development",
        "team standards",
        "people leadership",
    ),
    "Active Projects": (
        "migration",
        "refresh",
        "rollout",
        "implementation",
        "deployment",
        "project delivery",
        "datacenter",
        "data center",
    ),
    "Operations": (
        "incident",
        "rca",
        "maintenance",
        "monitoring",
        "remediation",
        "rule cleanup",
        "production support",
        "operational",
    ),
    "Development & Learning": (
        "certification",
        "training",
        "study",
        "read ",
        "book",
        "lab practice",
        "learning",
    ),
    "Waiting on Others": (
        "waiting for",
        "awaiting",
        "pending vendor",
        "pending approval",
        "follow up for",
    ),
}


@dataclass(frozen=True)
class SectionRoutingDecision:
    selected_section: str
    matched_rule: str
    reason: str
    rejected_higher_precedence: tuple[str, ...] = ()
    fallback_used: bool = False


@dataclass(frozen=True)
class TodoistPlan:
    action_id: str
    project: str
    subtasks: list[str]
    dry_run: bool = True
    task_id: str = ""
    routing: SectionRoutingDecision | None = None


class ActionLinkWriter(Protocol):
    def store_todoist_link(self, action_id: str, task_id: str) -> None: ...


def _validate_done_when(done_when: str) -> str:
    value = done_when.strip()
    if not value:
        raise ValueError("Done when must be non-empty")
    lines = [line.rstrip() for line in value.splitlines() if line.strip()]
    bullets = [line for line in lines if BULLET.match(line)]
    if bullets:
        if len(bullets) != len(lines):
            raise ValueError("Done when criteria must be all prose or all Markdown bullets")
        if len(bullets) < 2:
            raise ValueError("A single Done when criterion must be prose, not a bullet")
        return "\n".join(lines)
    if len(lines) > 1:
        raise ValueError("Two or more Done when criteria must be separate Markdown bullets")
    if MULTI_CRITERION_PROSE.search(lines[0]):
        raise ValueError(
            "Multiple Done when criteria cannot be comma- or semicolon-separated prose"
        )
    return lines[0]


def task_description(objective: str, done_when: str) -> str:
    objective = objective.strip()
    if not objective:
        raise ValueError("Objective must be non-empty")
    normalized_done_when = _validate_done_when(done_when)
    text = f"**Objective:**\n{objective}\n\n**Done when:**\n{normalized_done_when}"
    if NOTION_MARKERS.search(text):
        raise ValueError("Todoist content contains prohibited Notion reference")
    return text


def route_todoist_section(action: Action) -> SectionRoutingDecision:
    if action.todoist_section:
        if action.todoist_section not in SECTION_PRECEDENCE:
            raise ValueError("invalid governed Todoist section")
        return SectionRoutingDecision(
            action.todoist_section,
            "explicit_section",
            "The action supplied an explicit governed section.",
        )

    text = f"{action.title}\n{action.definition_of_done}".casefold()
    rejected: list[str] = []
    for section in SECTION_PRECEDENCE:
        matched = next((word for word in SECTION_RULES[section] if word in text), "")
        if matched:
            return SectionRoutingDecision(
                section,
                matched,
                f"Matched the governed {section} domain rule: {matched}.",
                tuple(rejected),
            )
        rejected.append(section)

    return SectionRoutingDecision(
        "Active Projects",
        "governed_fallback",
        "No specific domain matched; Active Projects is the governed fallback.",
        ("Leadership & Team",),
        True,
    )


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
        prohibited = set(config["prohibited_labels"])
        if any(label in prohibited or (approved and label not in approved) for label in action.labels):
            raise ValueError("prohibited or unapproved Todoist label")
        task_description(action.title, action.definition_of_done)
        routing = (
            route_todoist_section(action) if action.todoist_project == "Work" else None
        )
        return TodoistPlan(
            action.id,
            action.todoist_project,
            report.proposed_subtasks,
            routing=routing,
        )

    def _resolve_section(self, project_id: str, selected: str) -> str | None:
        if not selected or self.adapter is None:
            return None
        available = self.adapter.list_sections(project_id)
        if not available and not isinstance(self.adapter, LiveTodoistAdapter):
            return None
        sections = {item["name"]: item["id"] for item in available}
        if selected not in sections:
            raise ValueError("configured Todoist section is not available live")
        return sections[selected]

    def apply(self, action: Action, confirmed: bool = False) -> TodoistPlan:
        if not confirmed:
            raise PermissionError("explicit confirmation is required")
        if self.adapter is None:
            raise PermissionError("no production Todoist adapter is configured")
        plan = self.plan(action)
        projects = {project.name: project.id for project in self.adapter.list_projects()}
        if plan.project not in projects:
            raise ValueError("configured Todoist project is not available live")
        selected = plan.routing.selected_section if plan.routing else action.todoist_section
        section_id = self._resolve_section(projects[plan.project], selected)
        missing = set(action.labels) - set(self.adapter.list_labels())
        if missing:
            raise ValueError("configured Todoist labels are not available live")
        description = task_description(action.title, action.definition_of_done)

        if action.todoist_task_id:
            current = self.adapter.get_task(action.todoist_task_id)
            task = self.adapter.update_task(
                current.id,
                content=action.title,
                description=description,
                project_id=projects[plan.project],
                section_id=section_id,
                parent_id=current.parent_id,
                order=current.order,
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
            task,
            action.title,
            description,
            projects[plan.project],
            section_id,
            task.parent_id,
        )

        existing = {child.content: child for child in self.adapter.list_tasks(parent_id=task.id)}
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
                    section_id=None,
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
            self._validate_readback(
                child,
                title,
                subdesc,
                projects[plan.project],
                None,
                task.id,
            )

        children = sorted(
            self.adapter.list_tasks(parent_id=task.id),
            key=lambda child: (child.order, child.content),
        )
        expected = [f"{index:02d} — {raw}" for index, raw in enumerate(plan.subtasks, 1)]
        if [child.content for child in children] != expected:
            raise ValueError("Todoist subtask readback did not match requested tree")
        if self.link_writer:
            self.link_writer.store_todoist_link(action.id, task.id)
        return TodoistPlan(
            action.id,
            plan.project,
            plan.subtasks,
            False,
            task.id,
            plan.routing,
        )

    def move_task_group(
        self, task_id: str, target_section_id: str, confirmed: bool = False
    ) -> None:
        if not confirmed:
            raise PermissionError("explicit confirmation is required")
        if self.adapter is None:
            raise PermissionError("no production Todoist adapter is configured")
        parent = self.adapter.get_task(task_id)
        children = sorted(
            self.adapter.list_tasks(parent_id=task_id),
            key=lambda child: (child.order, child.content),
        )
        snapshot = {child.id: (child.parent_id, child.order) for child in children}
        updated_parent = self.adapter.update_task(
            parent.id,
            project_id=parent.project_id,
            section_id=target_section_id,
            parent_id=parent.parent_id,
            order=parent.order,
        )
        if updated_parent.section_id != target_section_id:
            raise ValueError("Todoist parent section move readback failed")
        for child in children:
            updated = self.adapter.update_task(
                child.id,
                project_id=parent.project_id,
                section_id=None,
                parent_id=task_id,
                order=child.order,
            )
            if (updated.parent_id, updated.order) != snapshot[child.id]:
                raise ValueError("Todoist hierarchy changed during section move")
        readback = self.adapter.list_tasks(parent_id=task_id)
        if len(readback) != len(children) or any(
            child.parent_id != task_id for child in readback
        ):
            raise ValueError("Todoist child-count or parentId validation failed")

    @staticmethod
    def _validate_readback(
        task: TodoistTask,
        title: str,
        description: str,
        project_id: str,
        section_id: str | None,
        parent_id: str | None,
    ) -> None:
        actual = (
            task.content,
            task.description,
            task.project_id,
            task.section_id,
            task.parent_id,
        )
        expected = (title, description, project_id, section_id, parent_id)
        if actual != expected:
            raise ValueError("Todoist readback did not match requested task")
        if NOTION_MARKERS.search(task.content + "\n" + task.description):
            raise ValueError("Todoist readback contains prohibited Notion content")
