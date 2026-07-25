from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from atlas_ros.adapters.errors import AdapterError
from atlas_ros.adapters.todoist import LiveTodoistAdapter, TodoistAdapter, TodoistTask
from atlas_ros.contracts import (
    ErrorClassification,
    ProviderName,
    ProviderOperation,
    ProviderOperationResult,
    ProviderOperationType,
)
from atlas_ros.orchestration.ports import ProviderExecutionError


@dataclass(frozen=True)
class TodoistExecutionTarget:
    project_id: str
    section_id: str | None


class TodoistExecutionAdapter:
    """Performs Todoist-specific reads and writes without execution-policy decisions."""

    def __init__(self, provider: TodoistAdapter) -> None:
        self._provider = provider

    def resolve_target(
        self,
        project: str,
        section: str,
        labels: tuple[str, ...],
    ) -> TodoistExecutionTarget:
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
        self.verify_task(
            task,
            title,
            description,
            target.project_id,
            target.section_id,
            task.parent_id,
        )
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


class TodoistExecutionAdapterV2(TodoistExecutionAdapter):
    """Todoist provider port; it owns rendering and readback, never planning policy."""

    provider_name = ProviderName.TODOIST

    @staticmethod
    def render_description(objective: object, done_when: object) -> str:
        objective_text = str(objective).strip()
        done_when_text = str(done_when).strip()
        if not objective_text:
            raise ValueError("Objective must be non-empty")
        if not done_when_text:
            raise ValueError("Done when must be non-empty")
        return f"**Objective:**\n{objective_text}\n\n**Done when:**\n{done_when_text}"

    @classmethod
    def _payload_description(cls, payload: dict[str, Any]) -> str:
        if "description" in payload:
            description = str(payload["description"]).strip()
            if not description:
                raise ValueError("Todoist description must be non-empty")
            return description
        return cls.render_description(payload.get("objective", ""), payload.get("done_when", ""))

    def execute_operation(
        self,
        operation: ProviderOperation,
        context: dict[str, Any],
        *,
        attempt: int,
        simulation: bool = False,
    ) -> ProviderOperationResult:
        if operation.provider != self.provider_name:
            raise ProviderExecutionError(
                ErrorClassification.VALIDATION_FAILURE,
                "Todoist adapter received an operation for another provider",
            )
        if simulation:
            return ProviderOperationResult(
                operation_id=operation.operation_id,
                provider=self.provider_name,
                operation_type=operation.operation_type,
                attempt=attempt,
                evidence={"simulation": "true"},
            )
        payload = operation.payload
        try:
            result = self._execute(operation.operation_type, payload, context)
        except ProviderExecutionError:
            raise
        except AdapterError as exc:
            classification = (
                ErrorClassification.RETRYABLE_PROVIDER_5XX
                if exc.retryable
                else ErrorClassification.PERMISSION_FAILURE
            )
            raise ProviderExecutionError(classification, str(exc)) from exc
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderExecutionError(
                ErrorClassification.VALIDATION_FAILURE,
                str(exc),
            ) from exc
        return ProviderOperationResult(
            operation_id=operation.operation_id,
            provider=self.provider_name,
            operation_type=operation.operation_type,
            attempt=attempt,
            applied=operation.operation_type
            in {
                ProviderOperationType.UPSERT_PARENT,
                ProviderOperationType.UPSERT_CHILD,
                ProviderOperationType.MOVE_GROUP,
            },
            readback_verified=True,
            provider_object_references=result,
        )

    def _execute(
        self,
        operation_type: ProviderOperationType,
        payload: dict[str, Any],
        context: dict[str, Any],
    ) -> tuple[str, ...]:
        if operation_type == ProviderOperationType.RESOLVE_TARGET:
            resolved_target = self.resolve_target(
                str(payload["project"]),
                str(payload.get("section", "")),
                tuple(str(label) for label in payload.get("labels", ())),
            )
            context["todoist_target"] = resolved_target
            return (resolved_target.project_id,)
        if operation_type == ProviderOperationType.READ_PARENT:
            task_id = str(payload.get("existing_task_id", ""))
            if task_id:
                context["todoist_parent"] = self._provider.get_task(task_id)
                return (task_id,)
            return ()
        if operation_type == ProviderOperationType.UPSERT_PARENT:
            parent_target = context.get("todoist_target")
            if not isinstance(parent_target, TodoistExecutionTarget):
                raise ValueError("Todoist target was not resolved")
            parent = self.upsert_parent(
                action_id=str(payload["action_id"]),
                existing_task_id=str(payload.get("existing_task_id", "")),
                title=str(payload["title"]),
                description=self._payload_description(payload),
                target=parent_target,
            )
            context["todoist_parent"] = parent
            return (parent.id,)
        if operation_type == ProviderOperationType.VERIFY_PARENT:
            parent_for_verify = context.get("todoist_parent")
            target_for_verify = context.get("todoist_target")
            if not isinstance(parent_for_verify, TodoistTask) or not isinstance(
                target_for_verify, TodoistExecutionTarget
            ):
                raise ValueError("Todoist parent verification context is incomplete")
            readback = self._provider.get_task(parent_for_verify.id)
            self.verify_task(
                readback,
                str(payload["title"]),
                self._payload_description(payload),
                target_for_verify.project_id,
                target_for_verify.section_id,
                readback.parent_id,
            )
            return (readback.id,)
        if operation_type == ProviderOperationType.READ_CHILDREN:
            parent_for_children = context.get("todoist_parent")
            if not isinstance(parent_for_children, TodoistTask):
                raise ValueError("Todoist parent is unavailable")
            context["todoist_children"] = self.children_by_content(parent_for_children.id)
            return tuple(
                child.id
                for child in context["todoist_children"].values()
                if isinstance(child, TodoistTask)
            )
        if operation_type == ProviderOperationType.UPSERT_CHILD:
            child_parent = context.get("todoist_parent")
            child_target = context.get("todoist_target")
            existing = context.get("todoist_children", {})
            if not isinstance(child_parent, TodoistTask) or not isinstance(
                child_target, TodoistExecutionTarget
            ):
                raise ValueError("Todoist child context is incomplete")
            sequence = int(payload["sequence"])
            raw_title = str(payload["raw_title"])
            title = f"{sequence:02d} — {raw_title}"
            child = self.upsert_child(
                action_id=str(payload["action_id"]),
                parent_id=child_parent.id,
                project_id=child_target.project_id,
                sequence=sequence,
                raw_title=raw_title,
                description=self._payload_description(payload),
                existing=existing.get(title) if isinstance(existing, dict) else None,
            )
            context[f"todoist_child_{sequence}"] = child
            return (child.id,)
        if operation_type == ProviderOperationType.VERIFY_CHILD:
            child_for_verify = context.get(f"todoist_child_{int(payload['sequence'])}")
            if not isinstance(child_for_verify, TodoistTask):
                raise ValueError("Todoist child is unavailable")
            readback = self._provider.get_task(child_for_verify.id)
            if readback != child_for_verify:
                raise ProviderExecutionError(
                    ErrorClassification.READBACK_MISMATCH,
                    "Todoist child readback mismatch",
                )
            return (child_for_verify.id,)
        if operation_type == ProviderOperationType.VERIFY_HIERARCHY:
            hierarchy_parent = context.get("todoist_parent")
            if not isinstance(hierarchy_parent, TodoistTask):
                raise ValueError("Todoist parent is unavailable")
            self.verify_tree(
                hierarchy_parent.id,
                [str(title) for title in payload.get("expected_titles", ())],
            )
            return (hierarchy_parent.id,)
        if operation_type == ProviderOperationType.MOVE_GROUP:
            task_id = str(payload["task_id"])
            self.move_group(task_id, str(payload["target_section_id"]))
            return (task_id,)
        raise ValueError(f"unsupported Todoist execution operation: {operation_type}")

    def readback_before_retry(
        self,
        operation: ProviderOperation,
        context: dict[str, Any],
    ) -> ProviderOperationResult | None:
        if operation.operation_type == ProviderOperationType.UPSERT_PARENT:
            task_id = str(operation.payload.get("existing_task_id", ""))
            parent = context.get("todoist_parent")
            if isinstance(parent, TodoistTask):
                task_id = parent.id
            if task_id:
                task = self._provider.get_task(task_id)
                context["todoist_parent"] = task
                return ProviderOperationResult(
                    operation_id=operation.operation_id,
                    provider=self.provider_name,
                    operation_type=operation.operation_type,
                    attempt=1,
                    applied=True,
                    readback_verified=True,
                    provider_object_references=(task.id,),
                    evidence={"recovered_by_readback": "true"},
                )
        if operation.operation_type == ProviderOperationType.UPSERT_CHILD:
            parent = context.get("todoist_parent")
            if isinstance(parent, TodoistTask):
                expected = (
                    f"{int(operation.payload['sequence']):02d} — {operation.payload['raw_title']}"
                )
                child = self.children_by_content(parent.id).get(expected)
                if child is not None:
                    context[f"todoist_child_{int(operation.payload['sequence'])}"] = child
                    return ProviderOperationResult(
                        operation_id=operation.operation_id,
                        provider=self.provider_name,
                        operation_type=operation.operation_type,
                        attempt=1,
                        applied=True,
                        readback_verified=True,
                        provider_object_references=(child.id,),
                        evidence={"recovered_by_readback": "true"},
                    )
        return None

    def compensate_operation(
        self,
        operation: ProviderOperation,
        context: dict[str, Any],
        *,
        attempt: int,
    ) -> ProviderOperationResult:
        del context
        if not operation.compensation_allowed:
            raise ProviderExecutionError(
                ErrorClassification.UNKNOWN_REVIEW,
                "Todoist compensation was not authorized",
            )
        raise ProviderExecutionError(
            ErrorClassification.UNKNOWN_REVIEW,
            "Todoist destructive compensation requires manual recovery",
        )
