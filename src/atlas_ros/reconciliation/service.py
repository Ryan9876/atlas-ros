from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from typing import Any

from atlas_ros.adapters.errors import AdapterError
from atlas_ros.adapters.notion import NotionAdapter, NotionPage
from atlas_ros.adapters.todoist import TodoistAdapter, TodoistComment, TodoistTask
from atlas_ros.reconciliation.state import (
    ReconciliationStateStore,
    SQLiteReconciliationStateStore,
)
from atlas_ros.runtime.database import RuntimeDatabase


class MutationType(StrEnum):
    ACTION_UPDATE = "action_update"
    DELEGATION_UPSERT = "delegation_upsert"
    BLOCKER_UPSERT = "blocker_upsert"
    BLOCKER_RESOLVE = "blocker_resolve"
    EXECUTION_STEP_UPDATE = "execution_step_update"
    EXECUTION_STEP_CREATE = "execution_step_create"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class ReconciliationMutation:
    mutation_type: MutationType
    notion_page_id: str
    todoist_task_id: str
    summary: str
    properties: dict[str, Any] = field(default_factory=dict)
    command_id: str = ""


@dataclass(frozen=True)
class ReconciliationPlan:
    generated_at: datetime
    mutations: tuple[ReconciliationMutation, ...]
    ignored: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()

    @property
    def has_changes(self) -> bool:
        return bool(self.mutations)


@dataclass(frozen=True)
class ReconciliationResult:
    planned: int
    applied: int
    conflicts: int
    ignored: int
    verified: int


@dataclass(frozen=True)
class AtlasCommand:
    kind: str
    body: str
    argument: str = ""


_COMMAND = re.compile(
    r"^@atlas\s+(?P<kind>update|delegate|risk|blocker|dependency|issue|"
    r"unblock|checkpoint)\s*:?[ \t]*"
    r"(?P<argument>[^\n]*)?(?:\n(?P<body>.*))?$",
    re.IGNORECASE | re.DOTALL,
)


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def parse_atlas_command(content: str) -> AtlasCommand | None:
    match = _COMMAND.match(content.strip())
    if not match:
        return None
    kind = match.group("kind").lower()
    argument = (match.group("argument") or "").strip()
    body = (match.group("body") or "").strip()
    if kind in {"update", "risk", "blocker", "dependency", "issue", "unblock"} and not body:
        body, argument = argument, ""
    return AtlasCommand(kind=kind, argument=argument, body=body)


def _date_value(value: str) -> dict[str, Any]:
    return {"date": {"start": value}}


def _rich_text(value: str) -> dict[str, Any]:
    return {"rich_text": [{"type": "text", "text": {"content": value}}]}


def _select(value: str) -> dict[str, Any]:
    return {"select": {"name": value}}


def _checkbox(value: bool) -> dict[str, Any]:
    return {"checkbox": value}


def _normalize_date(value: Any) -> Any:
    if not isinstance(value, str) or "T" not in value:
        return value
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    return parsed.replace(second=0, microsecond=0).isoformat()


def _extract_plain(property_value: Any) -> Any:
    if not isinstance(property_value, dict):
        return property_value
    property_type = property_value.get("type")
    if property_type is None:
        return _desired_plain(property_value)
    if property_type == "rich_text":
        return "".join(
            str(item.get("plain_text", ""))
            for item in property_value.get("rich_text", [])
            if isinstance(item, dict)
        )
    if property_type == "title":
        return "".join(
            str(item.get("plain_text", ""))
            for item in property_value.get("title", [])
            if isinstance(item, dict)
        )
    if property_type == "select":
        selected = property_value.get("select")
        return selected.get("name", "") if isinstance(selected, dict) else ""
    if property_type == "checkbox":
        return bool(property_value.get("checkbox"))
    if property_type == "date":
        selected = property_value.get("date")
        value = selected.get("start", "") if isinstance(selected, dict) else ""
        return _normalize_date(value)
    if property_type == "url":
        return property_value.get("url", "")
    if property_type == "number":
        return property_value.get("number")
    if property_type == "relation":
        return [
            str(item.get("id", ""))
            for item in property_value.get("relation", [])
            if isinstance(item, dict)
        ]
    return property_value


def _desired_plain(property_value: Any) -> Any:
    if not isinstance(property_value, dict):
        return property_value
    if "rich_text" in property_value:
        return "".join(
            str(item.get("text", {}).get("content", ""))
            for item in property_value.get("rich_text", [])
            if isinstance(item, dict)
        )
    if "title" in property_value:
        return "".join(
            str(item.get("text", {}).get("content", ""))
            for item in property_value.get("title", [])
            if isinstance(item, dict)
        )
    if "select" in property_value:
        selected = property_value.get("select")
        return selected.get("name", "") if isinstance(selected, dict) else ""
    if "checkbox" in property_value:
        return bool(property_value.get("checkbox"))
    if "date" in property_value:
        selected = property_value.get("date")
        value = selected.get("start", "") if isinstance(selected, dict) else ""
        return _normalize_date(value)
    if "url" in property_value:
        return property_value.get("url", "")
    if "number" in property_value:
        return property_value.get("number")
    if "relation" in property_value:
        return [
            str(item.get("id", ""))
            for item in property_value.get("relation", [])
            if isinstance(item, dict)
        ]
    return property_value


def _changed_properties(current: dict[str, Any], desired: dict[str, Any]) -> dict[str, Any]:
    return {
        name: value
        for name, value in desired.items()
        if _extract_plain(current.get(name)) != _desired_plain(value)
    }


class TodoistReconciliationService:
    """Attended Todoist-to-Notion reconciliation.

    Todoist is authoritative only for execution dates, execution priority,
    completion, subtask completion, and explicitly prefixed ``@atlas`` comments.
    Management context remains Notion-authoritative.
    """

    def __init__(
        self,
        notion: NotionAdapter,
        todoist: TodoistAdapter,
        database: RuntimeDatabase,
        *,
        action_data_source_id: str,
        execution_step_data_source_id: str = "",
        delegated_work_data_source_id: str = "",
        blocker_data_source_id: str = "",
        operations_data_source_id: str = "",
        state_store: ReconciliationStateStore | None = None,
    ) -> None:
        self.notion = notion
        self.todoist = todoist
        self.database = database
        self.action_data_source_id = action_data_source_id
        self.execution_step_data_source_id = execution_step_data_source_id
        self.delegated_work_data_source_id = delegated_work_data_source_id
        self.blocker_data_source_id = blocker_data_source_id
        self.operations_data_source_id = operations_data_source_id
        self.state_store = state_store or SQLiteReconciliationStateStore(database)

    def plan(self, *, full: bool = False, task_id: str = "") -> ReconciliationPlan:
        snapshot_at = datetime.now(UTC)
        actions = self.notion.query_pages(
            self.action_data_source_id,
            {
                "filter": {
                    "and": [
                        {"property": "Execution System", "select": {"equals": "Todoist"}},
                        {"property": "Execution Object ID", "rich_text": {"is_not_empty": True}},
                    ]
                }
            },
        )
        mutations: list[ReconciliationMutation] = []
        ignored: list[str] = []
        conflicts: list[str] = []
        since = self.state_store.checkpoint() if not full else snapshot_at - timedelta(days=42)
        completed = {task.id: task for task in self.todoist.list_completed_tasks(since)}

        for action in actions:
            mapped_task_id = str(_extract_plain(action.properties.get("Execution Object ID", "")))
            if not mapped_task_id or (task_id and mapped_task_id != task_id):
                continue
            task = completed.get(mapped_task_id)
            if task is None:
                try:
                    task = self.todoist.get_task(mapped_task_id)
                except (KeyError, AdapterError):
                    conflicts.append(f"{mapped_task_id}: mapped Todoist task was not found")
                    mutations.append(
                        ReconciliationMutation(
                            MutationType.CONFLICT,
                            action.id,
                            mapped_task_id,
                            "Mapped Todoist task was not found",
                        )
                    )
                    continue
            mutations.extend(self._plan_action(action, task))
            child_tasks = self._child_tasks(task, completed)
            comment_tasks = [task, *child_tasks]
            for comment_task in comment_tasks:
                for comment in self.todoist.list_comments(comment_task.id):
                    event_id = f"comment:{comment.id}"
                    if self.state_store.event_processed(event_id):
                        continue
                    posted_at = _parse_timestamp(comment.posted_at)
                    if posted_at is not None and posted_at <= since:
                        # The shared checkpoint is the authoritative boundary between
                        # previously reconciled history and new Todoist events. This
                        # prevents a second execution surface from replaying older
                        # commands that were already included in an earlier apply.
                        continue
                    command = parse_atlas_command(comment.content)
                    if command is None:
                        ignored.append(f"comment:{comment.id}")
                        continue
                    mutations.extend(
                        self._plan_command(action, task, comment_task, comment, command)
                    )
            if self.execution_step_data_source_id:
                mutations.extend(self._plan_steps(action, task, completed, child_tasks))

        conflict_summaries = [
            f"{mutation.todoist_task_id}: {mutation.summary}"
            for mutation in mutations
            if mutation.mutation_type == MutationType.CONFLICT
        ]
        return ReconciliationPlan(
            generated_at=snapshot_at,
            mutations=tuple(mutations),
            ignored=tuple(ignored),
            conflicts=tuple(dict.fromkeys([*conflicts, *conflict_summaries])),
        )

    def apply(self, plan: ReconciliationPlan, *, confirmed: bool = False) -> ReconciliationResult:
        if not confirmed:
            raise PermissionError("reconciliation apply requires explicit attended confirmation")
        applied = verified = conflicts = 0
        groups: dict[str, list[ReconciliationMutation]] = {}
        for index, mutation in enumerate(plan.mutations):
            key = f"comment:{mutation.command_id}" if mutation.command_id else f"mutation:{index}"
            groups.setdefault(key, []).append(mutation)
        for key, mutations in groups.items():
            if key.startswith("comment:") and self.state_store.event_processed(key):
                continue
            try:
                for mutation in mutations:
                    if mutation.mutation_type == MutationType.CONFLICT:
                        conflicts += 1
                        self._record_conflict(mutation)
                        continue
                    if mutation.mutation_type in {
                        MutationType.ACTION_UPDATE,
                        MutationType.EXECUTION_STEP_UPDATE,
                    }:
                        page = self.notion.update_page(mutation.notion_page_id, mutation.properties)
                        self._verify_properties(self.notion.get_page(page.id), mutation.properties)
                    elif mutation.mutation_type == MutationType.EXECUTION_STEP_CREATE:
                        page = self.notion.create_page(
                            self.execution_step_data_source_id, mutation.properties
                        )
                        self._verify_properties(self.notion.get_page(page.id), mutation.properties)
                    elif mutation.mutation_type == MutationType.DELEGATION_UPSERT:
                        page = self._upsert_by_key(
                            self.delegated_work_data_source_id,
                            "Todoist Command ID",
                            mutation.command_id,
                            mutation.properties,
                        )
                        self._verify_properties(page, mutation.properties)
                    elif mutation.mutation_type in {
                        MutationType.BLOCKER_UPSERT,
                        MutationType.BLOCKER_RESOLVE,
                    }:
                        page = self._upsert_by_key(
                            self.blocker_data_source_id,
                            "Todoist Command ID",
                            mutation.command_id,
                            mutation.properties,
                        )
                        self._verify_properties(page, mutation.properties)
                    applied += 1
                    verified += 1
            except Exception:
                if key.startswith("comment:"):
                    self.state_store.mark_event(key, "failed")
                raise
            if key.startswith("comment:"):
                self.state_store.mark_event(key, "applied")
        self.state_store.set_checkpoint(plan.generated_at)
        return ReconciliationResult(
            len(plan.mutations), applied, conflicts, len(plan.ignored), verified
        )

    @staticmethod
    def _verify_properties(page: NotionPage, desired: dict[str, Any]) -> None:
        remaining = _changed_properties(page.properties, desired)
        if remaining:
            raise RuntimeError(f"Notion readback mismatch: {', '.join(sorted(remaining))}")

    def _plan_action(self, action: NotionPage, task: TodoistTask) -> list[ReconciliationMutation]:
        properties: dict[str, Any] = {}
        current_status = str(_extract_plain(action.properties.get("Status", "")))
        current_due = str(_extract_plain(action.properties.get("Execution Due Date", "")))
        current_priority = str(_extract_plain(action.properties.get("Execution Priority", "")))
        desired_status = (
            "Completed"
            if task.checked
            else ("In Progress" if current_status == "Completed" else current_status)
        )
        if task.due_date != current_due:
            properties["Execution Due Date"] = (
                _date_value(task.due_date) if task.due_date else {"date": None}
            )
        desired_priority = f"P{5 - task.priority}" if task.priority in {1, 2, 3, 4} else ""
        if desired_priority and desired_priority != current_priority:
            properties["Execution Priority"] = _select(desired_priority)
        if desired_status and desired_status != current_status:
            properties["Status"] = _select(desired_status)
        if task.checked:
            properties["Completed At"] = _date_value(
                task.completed_at or datetime.now(UTC).isoformat()
            )
        properties["Todoist Updated At"] = _date_value(
            task.updated_at or datetime.now(UTC).isoformat()
        )
        properties["Last Sync Source"] = _select("Todoist")
        properties["Last Verified"] = _date_value(date.today().isoformat())
        properties["Sync State"] = _select("Synced")
        properties["Sync Error"] = _rich_text("")
        properties = _changed_properties(action.properties, properties)
        if not properties:
            return []
        return [
            ReconciliationMutation(
                MutationType.ACTION_UPDATE,
                action.id,
                task.id,
                "Synchronize Todoist execution fields to Action Record",
                properties,
            )
        ]

    def _plan_command(
        self,
        action: NotionPage,
        parent_task: TodoistTask,
        source_task: TodoistTask,
        comment: TodoistComment,
        command: AtlasCommand,
    ) -> list[ReconciliationMutation]:
        now = comment.posted_at or datetime.now(UTC).isoformat()
        if command.kind == "update":
            if source_task.parent_id:
                step = self._execution_step_for_task(source_task.id)
                if step is None:
                    return [
                        ReconciliationMutation(
                            MutationType.CONFLICT,
                            action.id,
                            source_task.id,
                            "Execution Step mapping is required for a subtask update command",
                            command_id=comment.id,
                        )
                    ]
                properties = _changed_properties(
                    step.properties,
                    {
                        "Latest Update": _rich_text(command.body),
                        "Last Verified": _date_value(date.today().isoformat()),
                        "Sync State": _select("Synced"),
                        "Sync Error": _rich_text(""),
                    },
                )
                if not properties:
                    return []
                return [
                    ReconciliationMutation(
                        MutationType.EXECUTION_STEP_UPDATE,
                        step.id,
                        source_task.id,
                        "Apply Todoist subtask update",
                        properties,
                        comment.id,
                    )
                ]
            properties = _changed_properties(
                action.properties,
                {
                    "Latest Update": _rich_text(command.body),
                    "Latest Update At": _date_value(now),
                    "Last Sync Source": _select("Todoist"),
                },
            )
            if not properties:
                return []
            return [
                ReconciliationMutation(
                    MutationType.ACTION_UPDATE,
                    action.id,
                    parent_task.id,
                    "Apply Todoist status update",
                    properties,
                    comment.id,
                )
            ]
        if command.kind == "checkpoint":
            checkpoint = command.argument or command.body
            return [
                ReconciliationMutation(
                    MutationType.ACTION_UPDATE,
                    action.id,
                    parent_task.id,
                    "Apply Todoist checkpoint",
                    {"Follow-up Date": _date_value(checkpoint)},
                    comment.id,
                )
            ]
        if command.kind == "delegate":
            if not self.delegated_work_data_source_id:
                return [self._missing_configuration(action, source_task, comment, "Delegated Work")]
            delegate, due = self._parse_delegate(command.argument)
            outcome = command.body or f"Complete delegated work for {source_task.content}"
            properties = {
                "Delegated Outcome": {"title": [{"text": {"content": outcome}}]},
                "Assigned Resource": _rich_text(delegate),
                "Status": _select("Assigned"),
                "Assigned Date": _date_value(now),
                "Latest Update": _rich_text(f"Delegated from Todoist: {outcome}"),
                "Todoist Command ID": _rich_text(comment.id),
                "Todoist Parent Task ID": _rich_text(parent_task.id),
                "Parent Action": {"relation": [{"id": action.id}]},
                "Resource Type": _select("Team Member"),
            }
            person_ids = self._resolve_notion_people(delegate)
            if len(person_ids) > 1:
                return [
                    ReconciliationMutation(
                        MutationType.CONFLICT,
                        action.id,
                        source_task.id,
                        f"Ambiguous delegate: {delegate}",
                        command_id=comment.id,
                    )
                ]
            if person_ids:
                properties["Assigned Person"] = {"people": [{"id": person_ids[0]}]}
            if due:
                properties["Delivery Due Date"] = _date_value(due)
            return [
                ReconciliationMutation(
                    MutationType.DELEGATION_UPSERT,
                    action.id,
                    source_task.id,
                    f"Delegate to {delegate}",
                    properties,
                    comment.id,
                )
            ]
        if command.kind in {"risk", "dependency", "issue"}:
            if not self.blocker_data_source_id:
                return [
                    self._missing_configuration(action, source_task, comment, "Risks and Blockers")
                ]
            text = (command.body or command.argument).strip()
            if not text:
                return [
                    ReconciliationMutation(
                        MutationType.CONFLICT,
                        action.id,
                        source_task.id,
                        f"@atlas {command.kind} requires content",
                        command_id=comment.id,
                    )
                ]
            return [
                ReconciliationMutation(
                    MutationType.BLOCKER_UPSERT,
                    action.id,
                    source_task.id,
                    f"Create linked {command.kind}",
                    {
                        "Risk or Blocker": {"title": [{"text": {"content": text}}]},
                        "Type": _select(command.kind.title()),
                        "Status": _select("Open"),
                        "Related Action URL": {"url": action.url},
                        "Todoist Command ID": _rich_text(comment.id),
                        "Todoist Parent Task ID": _rich_text(parent_task.id),
                        **(
                            {"Related Execution Step": {"relation": [{"id": step.id}]}}
                            if (step := self._execution_step_for_task(source_task.id))
                            else {}
                        ),
                    },
                    comment.id,
                )
            ]
        if command.kind == "blocker":
            if not self.blocker_data_source_id:
                return [
                    self._missing_configuration(action, source_task, comment, "Risks and Blockers")
                ]
            text = command.body or command.argument
            return [
                ReconciliationMutation(
                    MutationType.ACTION_UPDATE,
                    action.id,
                    parent_task.id,
                    "Set Action Record to Waiting",
                    {"Status": _select("Waiting"), "Waiting On": _rich_text(text)},
                    comment.id,
                ),
                ReconciliationMutation(
                    MutationType.BLOCKER_UPSERT,
                    action.id,
                    source_task.id,
                    "Create linked blocker",
                    {
                        "Risk or Blocker": {"title": [{"text": {"content": text}}]},
                        "Type": _select("Blocker"),
                        "Status": _select("Open"),
                        "Related Action URL": {"url": action.url},
                        "Todoist Command ID": _rich_text(comment.id),
                        "Todoist Parent Task ID": _rich_text(parent_task.id),
                    },
                    comment.id,
                ),
            ]
        if command.kind == "unblock":
            if not self.blocker_data_source_id:
                return [
                    self._missing_configuration(action, source_task, comment, "Risks and Blockers")
                ]
            text = command.body or command.argument or "Blocker resolved"
            return [
                ReconciliationMutation(
                    MutationType.ACTION_UPDATE,
                    action.id,
                    parent_task.id,
                    "Clear Action waiting state",
                    {
                        "Status": _select("In Progress"),
                        "Waiting On": _rich_text(""),
                        "Latest Update": _rich_text(text),
                        "Latest Update At": _date_value(now),
                    },
                    comment.id,
                ),
                ReconciliationMutation(
                    MutationType.BLOCKER_RESOLVE,
                    action.id,
                    source_task.id,
                    "Resolve linked blocker",
                    {
                        "Status": _select("Resolved"),
                        "Mitigation": _rich_text(text),
                        "Todoist Command ID": _rich_text(comment.id),
                        "Todoist Parent Task ID": _rich_text(parent_task.id),
                    },
                    comment.id,
                ),
            ]
        return []

    def _child_tasks(
        self, parent: TodoistTask, completed: dict[str, TodoistTask]
    ) -> list[TodoistTask]:
        tasks = self.todoist.list_tasks(parent_id=parent.id)
        for task in completed.values():
            if task.parent_id == parent.id and all(existing.id != task.id for existing in tasks):
                tasks.append(task)
        return sorted(tasks, key=lambda item: (item.order, item.id))

    def _plan_steps(
        self,
        action: NotionPage,
        parent: TodoistTask,
        completed: dict[str, TodoistTask],
        tasks: list[TodoistTask] | None = None,
    ) -> list[ReconciliationMutation]:
        tasks = tasks if tasks is not None else self._child_tasks(parent, completed)
        mutations: list[ReconciliationMutation] = []
        for task in tasks:
            existing = self.notion.query_pages(
                self.execution_step_data_source_id,
                {"filter": {"property": "Todoist Task ID", "rich_text": {"equals": task.id}}},
            )
            properties = {
                "Step": {"title": [{"text": {"content": task.content}}]},
                "Parent Action": {"relation": [{"id": action.id}]},
                "Todoist Task ID": _rich_text(task.id),
                "Todoist Task URL": {"url": f"https://app.todoist.com/app/task/{task.id}"},
                "Sequence": {"number": task.order},
                "Status": _select("Completed" if task.checked else "Open"),
                "Completed": _checkbox(task.checked),
                "Execution Priority": _select(
                    f"P{5 - task.priority}" if task.priority in {1, 2, 3, 4} else "P4"
                ),
                "Execution State": _select("Complete" if task.checked else "Ready"),
                "Last Verified": _date_value(date.today().isoformat()),
                "Sync State": _select("Synced"),
            }
            if task.due_date:
                properties["Due Date"] = _date_value(task.due_date)
            if task.checked:
                properties["Completed At"] = _date_value(
                    task.completed_at or datetime.now(UTC).isoformat()
                )
            if existing:
                changed = _changed_properties(existing[0].properties, properties)
                if changed:
                    mutations.append(
                        ReconciliationMutation(
                            MutationType.EXECUTION_STEP_UPDATE,
                            existing[0].id,
                            task.id,
                            "Synchronize Todoist subtask",
                            changed,
                        )
                    )
            else:
                mutations.append(
                    ReconciliationMutation(
                        MutationType.EXECUTION_STEP_CREATE,
                        action.id,
                        task.id,
                        "Create missing Execution Step mapping",
                        properties,
                    )
                )
        return mutations

    @staticmethod
    def _parse_delegate(argument: str) -> tuple[str, str]:
        normalized = re.sub(r"^to\s+", "", argument.strip(), flags=re.IGNORECASE)
        match = re.match(r"(?P<name>.+?)(?:\s+by\s+(?P<due>\d{4}-\d{2}-\d{2}))?$", normalized)
        if not match or not match.group("name"):
            raise ValueError("@atlas delegate requires a delegate name")
        return match.group("name").strip(), (match.group("due") or "")

    def _execution_step_for_task(self, task_id: str) -> NotionPage | None:
        if not self.execution_step_data_source_id:
            return None
        pages = self.notion.query_pages(
            self.execution_step_data_source_id,
            {"filter": {"property": "Todoist Task ID", "rich_text": {"equals": task_id}}},
        )
        return pages[0] if pages else None

    def _resolve_notion_people(self, name: str) -> list[str]:
        normalized = name.casefold().strip()
        if not normalized:
            return []
        matches: list[str] = []
        for user in self.notion.list_users():
            user_name = str(user.get("name", "")).casefold().strip()
            user_id = user.get("id")
            if isinstance(user_id, str) and (
                user_name == normalized or user_name.startswith(normalized + " ")
            ):
                matches.append(user_id)
        return matches

    @staticmethod
    def _missing_configuration(
        action: NotionPage, task: TodoistTask, comment: TodoistComment, target: str
    ) -> ReconciliationMutation:
        return ReconciliationMutation(
            MutationType.CONFLICT,
            action.id,
            task.id,
            f"{target} data source is not configured",
            command_id=comment.id,
        )

    def _upsert_by_key(
        self, data_source_id: str, property_name: str, key: str, properties: dict[str, Any]
    ) -> NotionPage:
        if not data_source_id:
            raise RuntimeError(f"data source missing for {property_name}")
        existing = self.notion.query_pages(
            data_source_id,
            {"filter": {"property": property_name, "rich_text": {"equals": key}}},
        )
        page = (
            self.notion.update_page(existing[0].id, properties)
            if existing
            else self.notion.create_page(data_source_id, properties)
        )
        return self.notion.get_page(page.id)

    def _record_conflict(self, mutation: ReconciliationMutation) -> None:
        if not self.operations_data_source_id:
            return
        self.notion.create_page(
            self.operations_data_source_id,
            {
                "Issue": {"title": [{"text": {"content": mutation.summary}}]},
                "Type": _select("Sync Conflict"),
                "Severity": _select("High"),
                "Status": _select("Open"),
                "Workflow": _rich_text("Execution Reconciliation"),
                "Affected Object URL": {
                    "url": f"https://app.todoist.com/app/task/{mutation.todoist_task_id}"
                },
                "Error Signature": _rich_text(mutation.summary),
                "Next Action": _rich_text("Review the conflict and rerun reconciliation."),
                "Occurrence Count": {"number": 1},
                "Retry Count": {"number": 0},
                "Last Occurrence": _date_value(datetime.now(UTC).isoformat()),
            },
        )
