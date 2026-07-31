"""Attended, replay-safe initialization of the production reconciliation ledger."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from atlas_ros.adapters.notion import NotionAdapter, NotionPage
from atlas_ros.adapters.todoist import TodoistAdapter, TodoistComment, TodoistTask
from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.reconciliation.state import (
    LedgerFailureCode,
    LedgerValidationError,
    NotionReconciliationStateStore,
    event_identity_aliases,
    has_complete_envelope,
)


def _plain(value: Any) -> str:
    if not isinstance(value, dict):
        return str(value or "")
    for property_type in ("rich_text", "title"):
        items = value.get(property_type)
        if isinstance(items, list):
            return "".join(
                str(item.get("plain_text", item.get("text", {}).get("content", "")))
                for item in items
                if isinstance(item, dict)
            )
    selected = value.get("select")
    return str(selected.get("name", "")) if isinstance(selected, dict) else ""


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ValueError("cutover timestamp must be UTC")
    return parsed


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _is_historical_w04_action(properties: Mapping[str, Any]) -> bool:
    """Exclude retired W04-labelled Action Records from the production inventory."""
    title = _plain(properties.get("Action", "")).casefold()
    return "historical" in title or "w04" in title


@dataclass(frozen=True)
class BaselineEvent:
    event_id: str
    aliases: tuple[str, ...]
    source_task_id: str
    parent_task_id: str
    source_comment_id: str
    source_posted_at: str
    source_digest: str

    def evidence(self, *, cutover_at: str, run_id: str, plan_digest: str) -> dict[str, Any]:
        return {
            "execution_surface": "CLI",
            "event_type": "Todoist Comment",
            "source_provider": "Todoist",
            "source_object_type": "comment",
            "source_task_id": self.source_task_id,
            "parent_task_id": self.parent_task_id,
            "source_comment_id": self.source_comment_id,
            "source_posted_at": self.source_posted_at,
            "source_updated_at": "",
            "source_digest": self.source_digest,
            "interpretation_classification": "not_interpreted",
            "interpretation_status": "ignored",
            "confidence": None,
            "blockers": [],
            "ambiguity": [],
            "inferred_fields": {},
            "field_origins": {},
            "command_digest": "",
            "plan_digest": plan_digest,
            "authorization_identity": "",
            "correlation_id": run_id,
            "causation_id": self.source_comment_id,
            "processing_outcome": "baseline_existing_before_cutover",
            "readback_status": "verified",
            "release_identity": "8.2.1",
            "baseline_cutover_at": cutover_at,
            "baseline_run_id": run_id,
        }


@dataclass(frozen=True)
class BaselinePlan:
    run_id: str
    cutover_at: str
    source_inventory_digest: str
    plan_digest: str
    events: tuple[BaselineEvent, ...]
    mapped_parent_count: int
    subtask_count: int


@dataclass(frozen=True)
class BaselineAuthorization:
    run_id: str
    cutover_at: str
    source_inventory_digest: str
    plan_digest: str
    authorization_identity: str
    attended: bool = True


@dataclass(frozen=True)
class BaselineReceipt:
    run_id: str
    planned_events: int
    written_events: int
    replayed_events: int
    checkpoint_created: bool
    complete: bool
    failures: tuple[str, ...] = ()


class ProductionBaselineService:
    """Build and apply an inert baseline without interpreting source comments."""

    def __init__(
        self,
        notion: NotionAdapter,
        todoist: TodoistAdapter,
        state: NotionReconciliationStateStore,
        *,
        action_data_source_id: str,
    ) -> None:
        self.notion = notion
        self.todoist = todoist
        self.state = state
        self.action_data_source_id = action_data_source_id

    def plan(self, *, run_id: str, cutover_at: str) -> BaselinePlan:
        if not run_id.strip():
            raise ValueError("baseline run identity is required")
        cutover = _utc(cutover_at)
        if cutover_at != cutover.isoformat():
            raise ValueError("cutover timestamp must be exact UTC ISO-8601")
        actions = self.notion.query_pages(
            self.action_data_source_id,
            {"filter": {"and": [
                {"property": "Execution System", "select": {"equals": "Todoist"}},
                {"property": "Execution Object ID", "rich_text": {"is_not_empty": True}},
            ]}},
        )
        events: list[BaselineEvent] = []
        parent_count = subtask_count = 0
        seen_comments: set[str] = set()
        for action in actions:
            if _is_historical_w04_action(action.properties):
                continue
            parent_id = _plain(action.properties.get("Execution Object ID", ""))
            if not parent_id:
                continue
            parent_count += 1
            self.todoist.get_task(parent_id)
            child_index = {task.id: task for task in self.todoist.list_tasks(parent_id=parent_id)}
            child_index.update(
                {
                    task.id: task
                    for task in self.todoist.list_completed_tasks(datetime(1970, 1, 1, tzinfo=UTC))
                    if task.parent_id == parent_id
                }
            )
            children = tuple(child_index.values())
            subtask_count += len(children)
            for task in (self.todoist.get_task(parent_id), *children):
                for comment in self.todoist.list_comments(task.id):
                    if comment.id in seen_comments:
                        raise LedgerValidationError(
                            LedgerFailureCode.BASELINE_CONFLICT,
                            f"comment {comment.id} is mapped more than once",
                        )
                    seen_comments.add(comment.id)
                    if not comment.posted_at:
                        raise LedgerValidationError(
                            LedgerFailureCode.BASELINE_CONFLICT,
                            f"comment {comment.id} has no posted timestamp",
                        )
                    if _utc(comment.posted_at) > cutover:
                        continue
                    events.append(self._event(task, parent_id, comment))
        events.sort(key=lambda item: (item.source_posted_at, item.event_id))
        inventory = [
            {
                "event_id": item.event_id,
                "aliases": item.aliases,
                "source_task_id": item.source_task_id,
                "parent_task_id": item.parent_task_id,
                "source_comment_id": item.source_comment_id,
                "source_posted_at": item.source_posted_at,
                "source_digest": item.source_digest,
            }
            for item in events
        ]
        inventory_digest = sha256_digest(_canonical_json(inventory))
        digest = sha256_digest(_canonical_json({
            "run_id": run_id,
            "cutover_at": cutover_at,
            "source_inventory_digest": inventory_digest,
            "event_ids": [item.event_id for item in events],
        }))
        return BaselinePlan(
            run_id, cutover_at, inventory_digest, digest, tuple(events), parent_count, subtask_count
        )

    @staticmethod
    def _event(task: TodoistTask, parent_id: str, comment: TodoistComment) -> BaselineEvent:
        event_id = f"todoist-comment:{comment.id}"
        digest = sha256_digest(_canonical_json({
            "comment_id": comment.id,
            "task_id": task.id,
            "parent_task_id": parent_id,
            "content": comment.content,
            "posted_at": comment.posted_at,
            "posted_uid": comment.posted_uid or "",
        }))
        return BaselineEvent(
            event_id, event_identity_aliases(event_id)[1:], task.id, parent_id,
            comment.id, comment.posted_at, digest,
        )

    def apply(self, plan: BaselinePlan, authorization: BaselineAuthorization) -> BaselineReceipt:
        if (
            not authorization.attended
            or authorization.run_id != plan.run_id
            or authorization.cutover_at != plan.cutover_at
            or authorization.source_inventory_digest != plan.source_inventory_digest
            or authorization.plan_digest != plan.plan_digest
            or not authorization.authorization_identity.strip()
        ):
            raise LedgerValidationError(
                LedgerFailureCode.BASELINE_AUTHORIZATION_INVALID,
                "authorization is not bound to this exact baseline plan",
            )
        written = replayed = 0
        failures: list[str] = []
        for event in plan.events:
            expected = event.evidence(
                cutover_at=plan.cutover_at, run_id=plan.run_id, plan_digest=plan.plan_digest
            )
            expected["authorization_identity"] = authorization.authorization_identity
            existing = self._existing(event)
            if existing is not None:
                if self._matches(existing, event, expected):
                    replayed += 1
                    continue
                failures.append(f"{event.event_id}: existing evidence conflicts")
                continue
            try:
                self.state.mark_event(event.event_id, "ignored", expected)
                page = self._existing(event)
                if page is None or not self._matches(page, event, expected):
                    failures.append(f"{event.event_id}: readback failed")
                else:
                    written += 1
            except Exception as exc:
                # Preserve prior successful evidence; never checkpoint partial work.
                failures.append(f"{event.event_id}: write failed ({type(exc).__name__})")
        if failures:
            return BaselineReceipt(
                plan.run_id, len(plan.events), written, replayed, False, False, tuple(failures)
            )
        checkpoint = self.state._find(self.state.CHECKPOINT_KEY)
        if checkpoint is not None:
            if self._checkpoint_matches(checkpoint, plan, authorization):
                return BaselineReceipt(
                    plan.run_id, len(plan.events), written, replayed, False, True
                )
            return BaselineReceipt(
                plan.run_id, len(plan.events), written, replayed, False, False,
                ("existing checkpoint conflicts with baseline plan",),
            )
        self.state.set_checkpoint(
            _utc(plan.cutover_at),
            {
                "baseline_cutover_at": plan.cutover_at,
                "baseline_run_id": plan.run_id,
                "source_inventory_digest": plan.source_inventory_digest,
                "plan_digest": plan.plan_digest,
                "authorization_identity": authorization.authorization_identity,
                "processing_outcome": "baseline_checkpoint_created",
                "readback_status": "verified",
                "release_identity": "8.2.1",
            },
        )
        checkpoint = self.state._find(self.state.CHECKPOINT_KEY)
        if checkpoint is None or not self._checkpoint_matches(checkpoint, plan, authorization):
            return BaselineReceipt(
                plan.run_id, len(plan.events), written, replayed, False, False,
                ("checkpoint readback failed",),
            )
        return BaselineReceipt(plan.run_id, len(plan.events), written, replayed, True, True)

    def _existing(self, event: BaselineEvent) -> NotionPage | None:
        found = [self.state._find(key) for key in (event.event_id, *event.aliases)]
        pages = [page for page in found if page is not None]
        if len({page.id for page in pages}) > 1:
            raise LedgerValidationError(
                LedgerFailureCode.BASELINE_CONFLICT,
                f"duplicate canonical or alias records for {event.event_id}",
            )
        return pages[0] if pages else None

    def _matches(self, page: NotionPage, event: BaselineEvent, expected: dict[str, Any]) -> bool:
        notes = self.state._rich_text_value(page.properties.get("Notes", {}))
        try:
            envelope = json.loads(notes)
        except json.JSONDecodeError:
            return False
        return bool(
            isinstance(envelope, dict)
            and has_complete_envelope(envelope)
            and envelope.get("event_id") == event.event_id
            and envelope.get("source_digest") == event.source_digest
            and envelope.get("processing_outcome") == "baseline_existing_before_cutover"
            and envelope.get("logical_status") == "ignored"
            and envelope.get("baseline_cutover_at") == expected["baseline_cutover_at"]
            and envelope.get("plan_digest") == expected["plan_digest"]
        )

    def _checkpoint_matches(
        self, page: NotionPage, plan: BaselinePlan, authorization: BaselineAuthorization
    ) -> bool:
        notes = self.state._rich_text_value(page.properties.get("Notes", {}))
        try:
            envelope = json.loads(notes)
        except json.JSONDecodeError:
            return False
        return bool(
            isinstance(envelope, dict)
            and has_complete_envelope(envelope)
            and envelope.get("baseline_run_id") == plan.run_id
            and envelope.get("baseline_cutover_at") == plan.cutover_at
            and envelope.get("source_inventory_digest") == plan.source_inventory_digest
            and envelope.get("plan_digest") == plan.plan_digest
            and envelope.get("authorization_identity") == authorization.authorization_identity
        )
