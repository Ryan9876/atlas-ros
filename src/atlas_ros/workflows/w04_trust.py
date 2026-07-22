from __future__ import annotations

from datetime import date
from typing import Any

from atlas_ros.adapters.notion import NotionPage
from atlas_ros.adapters.todoist import TodoistComment, TodoistTask
from atlas_ros.workflows.w04_reconciliation import (
    _extract_plain,
    AtlasCommand,
    MutationType,
    ReconciliationMutation,
    TodoistReconciliationService as BaseTodoistReconciliationService,
)


class TodoistReconciliationService(BaseTodoistReconciliationService):
    """P0 trust wrapper that hardens W04 command targeting and validation."""

    def _plan_command(
        self,
        action: NotionPage,
        parent_task: TodoistTask,
        source_task: TodoistTask,
        comment: TodoistComment,
        command: AtlasCommand,
    ) -> list[ReconciliationMutation]:
        if command.kind == "checkpoint":
            checkpoint = (command.argument or command.body).strip()
            try:
                date.fromisoformat(checkpoint)
            except ValueError:
                return [
                    ReconciliationMutation(
                        MutationType.CONFLICT,
                        action.id,
                        source_task.id,
                        "@atlas checkpoint requires an ISO date (YYYY-MM-DD)",
                        command_id=comment.id,
                    )
                ]
        if command.kind == "blocker" and not (command.body or command.argument).strip():
            return [
                ReconciliationMutation(
                    MutationType.CONFLICT,
                    action.id,
                    source_task.id,
                    "@atlas blocker requires content",
                    command_id=comment.id,
                )
            ]
        if command.kind == "unblock":
            if not self.blocker_data_source_id:
                return [
                    self._missing_configuration(action, source_task, comment, "Risks and Blockers")
                ]
            blockers = self._open_blockers(parent_task.id)
            if len(blockers) != 1:
                reason = "No open blocker found" if not blockers else "Multiple open blockers found"
                return [
                    ReconciliationMutation(
                        MutationType.CONFLICT,
                        action.id,
                        source_task.id,
                        f"{reason}; identify the blocker before unblocking",
                        command_id=comment.id,
                    )
                ]
        return super()._plan_command(action, parent_task, source_task, comment, command)

    def _open_blockers(self, parent_task_id: str) -> list[NotionPage]:
        pages = self.notion.query_pages(self.blocker_data_source_id, {})
        return [
            page
            for page in pages
            if str(_extract_plain(page.properties.get("Todoist Parent Task ID", "")))
            == parent_task_id
            and str(_extract_plain(page.properties.get("Status", ""))) == "Open"
            and str(_extract_plain(page.properties.get("Type", ""))) == "Blocker"
        ]

    def _upsert_by_key(
        self,
        data_source_id: str,
        property_name: str,
        key: str,
        properties: dict[str, Any],
    ) -> NotionPage:
        resolving_blocker = (
            data_source_id == self.blocker_data_source_id
            and property_name == "Todoist Command ID"
            and properties.get("Status", {}).get("select", {}).get("name") == "Resolved"
        )
        if resolving_blocker:
            rich_text = properties.get("Todoist Parent Task ID", {}).get("rich_text", [])
            parent_id = ""
            if rich_text and isinstance(rich_text[0], dict):
                parent_id = str(rich_text[0].get("text", {}).get("content", ""))
            blockers = self._open_blockers(parent_id)
            if len(blockers) != 1:
                raise RuntimeError("unblock target changed after planning")
            page = self.notion.update_page(blockers[0].id, properties)
            return self.notion.get_page(page.id)
        return super()._upsert_by_key(data_source_id, property_name, key, properties)
