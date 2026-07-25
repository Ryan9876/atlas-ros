from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

from atlas_ros.adapters.todoist import TodoistAdapter, TodoistTask
from atlas_ros.adapters.todoist_execution import TodoistExecutionAdapterV2
from atlas_ros.config.loader import load_config
from atlas_ros.contracts import (
    ExecutionReceiptV2,
    ProviderName,
    ProviderOperation,
    ProviderOperationType,
    deterministic_digest,
)
from atlas_ros.domain.models import Action
from atlas_ros.orchestration import (
    ExecutionOrchestratorV2,
)
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
    """Legacy W03 compatibility service over planning, orchestration, and provider adapter."""

    def __init__(
        self, adapter: TodoistAdapter | None = None, link_writer: ActionLinkWriter | None = None
    ) -> None:
        self.adapter = adapter
        self.link_writer = link_writer
        self.last_receipt: ExecutionReceiptV2 | None = None
        self._execution_adapter_v2 = (
            TodoistExecutionAdapterV2(adapter) if adapter is not None else None
        )
        self._orchestrator_v2 = (
            ExecutionOrchestratorV2((self._execution_adapter_v2,))
            if self._execution_adapter_v2 is not None
            else None
        )

    def plan(self, action: Action) -> TodoistPlan:
        report = DecompositionService().readiness(action)
        if report.status.value != "ready":
            raise ValueError(f"W03A gate failed: {', '.join(report.failed_rules)}")
        config = load_config("todoist")
        if action.todoist_project not in config["projects"]:
            raise ValueError("invalid Todoist project")
        approved = set(config.get("approved_labels", ()))
        prohibited = set(config["prohibited_labels"])
        invalid_label = any(
            label in prohibited or (approved and label not in approved) for label in action.labels
        )
        if invalid_label:
            raise ValueError("prohibited or unapproved Todoist label")
        task_description(action.title, action.definition_of_done)
        routing = route_todoist_section(action) if action.todoist_project == "Work" else None
        return TodoistPlan(
            action.id,
            action.todoist_project,
            report.proposed_subtasks,
            routing=routing,
        )

    def apply(self, action: Action, confirmed: bool = False) -> TodoistPlan:
        if self._orchestrator_v2 is None:
            if not confirmed:
                raise PermissionError("explicit confirmation is required")
            raise PermissionError("no production Todoist adapter is configured")
        if not confirmed:
            raise PermissionError("explicit confirmation is required")
        plan = self.plan(action)
        selected = plan.routing.selected_section if plan.routing else action.todoist_section
        descriptions = tuple(
            task_description(raw, f"{raw} is completed and verified.") for raw in plan.subtasks
        )
        correlation_id = str(uuid4())
        description = task_description(action.title, action.definition_of_done)
        plan_payload = {
            "action_id": action.id,
            "title": action.title,
            "description": description,
            "project": plan.project,
            "section": selected,
            "labels": tuple(action.labels),
            "subtasks": tuple(plan.subtasks),
            "subtask_descriptions": descriptions,
        }
        plan_digest = deterministic_digest(plan_payload)
        operations = self._compatibility_operations(
            action=action,
            project=plan.project,
            section=selected,
            description=description,
            subtasks=tuple(plan.subtasks),
            subtask_descriptions=descriptions,
            plan_digest=plan_digest,
        )
        authorization = ExecutionOrchestratorV2.issue_authorization(
            plan_id=f"legacy-w03:{action.id}",
            plan_digest=plan_digest,
            action_id=action.id,
            correlation_id=correlation_id,
            operations=operations,
            reason="Preserve attended W03 compatibility behavior",
            attended_confirmation_evidence=(
                "Legacy confirmed=True translated at the attended W03 boundary "
                "for this exact plan and provider scope."
            ),
        )
        command = ExecutionOrchestratorV2.build_command(
            plan_id=f"legacy-w03:{action.id}",
            plan_digest=plan_digest,
            action_id=action.id,
            correlation_id=correlation_id,
            authorization=authorization,
            operations=operations,
        )
        _, receipt = self._orchestrator_v2.execute(command, authorization)
        self.last_receipt = receipt
        parent_id = next(
            (
                reference
                for reference in receipt.provider_object_references
                if reference.startswith("task-")
            ),
            receipt.provider_object_references[0],
        )
        if self.link_writer:
            self.link_writer.store_todoist_link(action.id, parent_id)
        return TodoistPlan(
            action.id,
            plan.project,
            plan.subtasks,
            False,
            parent_id,
            plan.routing,
        )

    def move_task_group(
        self, task_id: str, target_section_id: str, confirmed: bool = False
    ) -> None:
        if self._orchestrator_v2 is None:
            if not confirmed:
                raise PermissionError("explicit confirmation is required")
            raise PermissionError("no production Todoist adapter is configured")
        if not confirmed:
            raise PermissionError("explicit confirmation is required")
        correlation_id = str(uuid4())
        plan_digest = deterministic_digest(
            {"task_id": task_id, "target_section_id": target_section_id}
        )
        operation = ProviderOperation(
            operation_id=f"move:{task_id}",
            provider=ProviderName.TODOIST,
            operation_type=ProviderOperationType.MOVE_GROUP,
            sequence=1,
            payload={"task_id": task_id, "target_section_id": target_section_id},
            idempotency_key=deterministic_digest(
                {"task_id": task_id, "target_section_id": target_section_id}
            ),
        )
        authorization = ExecutionOrchestratorV2.issue_authorization(
            plan_id=f"legacy-w03-move:{task_id}",
            plan_digest=plan_digest,
            action_id=task_id,
            correlation_id=correlation_id,
            operations=(operation,),
            reason="Preserve attended W03 parent-group move",
            attended_confirmation_evidence=(
                "Legacy confirmed=True translated for this exact hierarchy-preserving move."
            ),
        )
        command = ExecutionOrchestratorV2.build_command(
            plan_id=f"legacy-w03-move:{task_id}",
            plan_digest=plan_digest,
            action_id=task_id,
            correlation_id=correlation_id,
            authorization=authorization,
            operations=(operation,),
        )
        self._orchestrator_v2.execute(command, authorization)

    @staticmethod
    def _compatibility_operations(
        *,
        action: Action,
        project: str,
        section: str,
        description: str,
        subtasks: tuple[str, ...],
        subtask_descriptions: tuple[str, ...],
        plan_digest: str,
    ) -> tuple[ProviderOperation, ...]:
        specs: list[tuple[ProviderOperationType, dict[str, object]]] = [
            (
                ProviderOperationType.RESOLVE_TARGET,
                {"project": project, "section": section, "labels": tuple(action.labels)},
            ),
            (
                ProviderOperationType.READ_PARENT,
                {"existing_task_id": action.todoist_task_id},
            ),
            (
                ProviderOperationType.UPSERT_PARENT,
                {
                    "action_id": action.id,
                    "existing_task_id": action.todoist_task_id,
                    "title": action.title,
                    "description": description,
                },
            ),
            (
                ProviderOperationType.VERIFY_PARENT,
                {"title": action.title, "description": description},
            ),
            (ProviderOperationType.READ_CHILDREN, {}),
        ]
        for sequence, (title, child_description) in enumerate(
            zip(subtasks, subtask_descriptions, strict=True), 1
        ):
            payload = {
                "action_id": action.id,
                "sequence": sequence,
                "raw_title": title,
                "description": child_description,
            }
            specs.append((ProviderOperationType.UPSERT_CHILD, payload))
            specs.append((ProviderOperationType.VERIFY_CHILD, {"sequence": sequence}))
        specs.append(
            (
                ProviderOperationType.VERIFY_HIERARCHY,
                {
                    "expected_titles": tuple(
                        f"{sequence:02d} — {title}" for sequence, title in enumerate(subtasks, 1)
                    )
                },
            )
        )
        return tuple(
            ProviderOperation(
                operation_id=f"w03:{action.id}:{index}:{operation_type.value}",
                provider=ProviderName.TODOIST,
                operation_type=operation_type,
                sequence=index,
                payload=payload,
                idempotency_key=deterministic_digest(
                    {
                        "plan_digest": plan_digest,
                        "action_id": action.id,
                        "sequence": index,
                        "operation_type": operation_type,
                        "payload": payload,
                    }
                ),
            )
            for index, (operation_type, payload) in enumerate(specs, 1)
        )

    @staticmethod
    def _validate_readback(
        task: TodoistTask,
        title: str,
        description: str,
        project_id: str,
        section_id: str | None,
        parent_id: str | None,
    ) -> None:
        TodoistExecutionAdapterV2.verify_task(
            task,
            title,
            description,
            project_id,
            section_id,
            parent_id,
        )
        if NOTION_MARKERS.search(task.content + "\n" + task.description):
            raise ValueError("Todoist readback contains prohibited Notion content")
