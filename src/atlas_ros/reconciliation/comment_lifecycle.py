"""Todoist-comment ingestion into the governed command lifecycle.

This module is provider-read-only. It converts one retrieved Todoist comment into a
canonical command source, operational snapshot, typed interpretation, and exact
unexecuted provider plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from atlas_ros.adapters.notion import NotionPage
from atlas_ros.adapters.todoist import TodoistComment, TodoistTask
from atlas_ros.adapters.todoist_command_source import TodoistCommentSourceAdapter
from atlas_ros.application.command_lifecycle import (
    CommandLifecycleCoordinator,
    CommandLifecycleResult,
)
from atlas_ros.capabilities.operational_awareness import OperationalSnapshotBuilder
from atlas_ros.contracts.operational_awareness import (
    AuthoritativeSystem,
    NormalizedOperationalRecordV1,
    OperationalRecordRefV1,
    OperationalRecordType,
)
from atlas_ros.planning.operational_awareness import OperationalLifecycleExecutionPlanner
from atlas_ros.policy.operational_awareness import load_operational_awareness_policy


class CommentInterpretationStatus(StrEnum):
    ACTIONABLE = "Awaiting Approval"
    BLOCKED = "Blocked"
    INFORMATIONAL = "Informational"
    IGNORED = "Ignored"


@dataclass(frozen=True, slots=True)
class NaturalCommentAssessment:
    event_id: str
    comment_id: str
    source_task_id: str
    parent_task_id: str
    source_digest: str
    status: CommentInterpretationStatus
    classification: str
    confidence: float | None
    blockers: tuple[str, ...]
    ambiguity: tuple[str, ...]
    field_origins: dict[str, str]
    inferred_fields: tuple[str, ...]
    command_digest: str
    plan_digest: str | None
    requires_attended_approval: bool
    result: CommandLifecycleResult


def prepare_natural_comment(
    *,
    action: NotionPage,
    parent_task: TodoistTask,
    source_task: TodoistTask,
    comment: TodoistComment,
    notion_users: list[dict[str, Any]],
    active_checkpoint_ids: tuple[str, ...] = (),
    timezone_name: str = "America/Toronto",
    retrieved_at: datetime | None = None,
) -> NaturalCommentAssessment:
    """Prepare one ordinary Todoist comment without writing either provider."""

    retrieved = retrieved_at or datetime.now(UTC)
    title = _property_text(action.properties.get("Action")) or parent_task.content
    source = TodoistCommentSourceAdapter(timezone_name=timezone_name).extract(
        comment=comment,
        source_task=source_task,
        parent_task=parent_task,
        parent_action_record_id=action.id,
        parent_action_record_url=action.url,
        parent_outcome_title=title,
        retrieved_at=retrieved,
    )
    directory = _person_directory(notion_users)
    parent_record = _record(
        page_id=action.id,
        url=action.url,
        title=title,
        record_type=OperationalRecordType.ACTION_RECORD,
        parent_id=None,
        todoist_task_id=parent_task.id,
        source_revision=_property_text(action.properties.get("Last Edited"))
        or comment.posted_at,
        owner=_owner_name(action) or "Ryan",
        definition_of_done=_definition_of_done(action),
        extra={
            "person_directory": directory,
            "active_ryan_checkpoint_ids": active_checkpoint_ids,
        },
    )
    records = [parent_record]
    if source_task.id != parent_task.id:
        records.append(
            _record(
                page_id=f"todoist-step:{source_task.id}",
                url=f"https://app.todoist.com/app/task/{source_task.id}",
                title=source_task.content,
                record_type=OperationalRecordType.EXECUTION_STEP,
                parent_id=action.id,
                todoist_task_id=source_task.id,
                source_revision=comment.posted_at,
                owner=_owner_name(action) or "Ryan",
                definition_of_done=(),
                extra={
                    "person_directory": directory,
                    "parent_record_id": action.id,
                },
            )
        )
    snapshot = OperationalSnapshotBuilder(load_operational_awareness_policy()).build(
        records,
        scope="work",
        authority_identities=("github", "notion", "todoist"),
        generated_at=retrieved,
        replay_id=source.source_event_id,
    )
    result = CommandLifecycleCoordinator(
        load_operational_awareness_policy(),
        OperationalLifecycleExecutionPlanner(),
    ).prepare(source, snapshot)
    normalization = result.normalization
    if normalization is None:
        raise ValueError("ordinary Todoist comment unexpectedly bypassed normalization")
    no_transition = normalization.blockers == ("No actionable lifecycle transition",)
    if result.canonical_plan is not None and not result.interpretation.blockers:
        status = CommentInterpretationStatus.ACTIONABLE
    elif no_transition:
        status = CommentInterpretationStatus.INFORMATIONAL
    else:
        status = CommentInterpretationStatus.BLOCKED
    inferred = tuple(
        key
        for key, origin in sorted(normalization.field_origins.items())
        if origin in {"inferred", "context-derived", "defaulted-by-policy"}
    )
    return NaturalCommentAssessment(
        event_id=source.source_event_id or f"todoist-comment:{comment.id}",
        comment_id=comment.id,
        source_task_id=source_task.id,
        parent_task_id=parent_task.id,
        source_digest=source.source_digest,
        status=status,
        classification=normalization.classification.value,
        confidence=normalization.confidence.score,
        blockers=normalization.blockers,
        ambiguity=normalization.ambiguity,
        field_origins=dict(normalization.field_origins),
        inferred_fields=inferred,
        command_digest=result.command.command_digest,
        plan_digest=(result.lifecycle_plan.plan_digest if result.lifecycle_plan else None),
        requires_attended_approval=normalization.requires_attended_approval,
        result=result,
    )


def _record(
    *,
    page_id: str,
    url: str,
    title: str,
    record_type: OperationalRecordType,
    parent_id: str | None,
    todoist_task_id: str,
    source_revision: str,
    owner: str,
    definition_of_done: tuple[str, ...],
    extra: dict[str, Any],
) -> NormalizedOperationalRecordV1:
    ref = OperationalRecordRefV1.create(
        record_type=record_type,
        canonical_record_id=page_id,
        authoritative_system=AuthoritativeSystem.NOTION,
        canonical_url=url,
        parent_record_id=parent_id,
        source_revision=source_revision,
    )
    return NormalizedOperationalRecordV1.create(
        record_ref=ref,
        title=title,
        observed_state="active",
        owner=owner,
        accountable_party=owner,
        definition_of_done=definition_of_done,
        updated_at=source_revision,
        todoist_task_id=todoist_task_id,
        extra=extra,
    )


def _person_directory(users: list[dict[str, Any]]) -> tuple[dict[str, object], ...]:
    entries: list[dict[str, object]] = []
    for user in users:
        user_id = str(user.get("id") or "").strip()
        full_name = str(user.get("name") or "").strip()
        if not user_id or not full_name:
            continue
        first_name = full_name.split()[0]
        aliases = tuple(dict.fromkeys((full_name, first_name)))
        entries.append(
            {
                "display_name": first_name,
                "canonical_identity": f"notion-user:{user_id}",
                "notion_user_id": user_id,
                "aliases": aliases,
            }
        )
    return tuple(entries)


def _owner_name(action: NotionPage) -> str:
    value = action.properties.get("Owner")
    if isinstance(value, dict):
        people = value.get("people")
        if isinstance(people, list) and people:
            name = people[0].get("name") if isinstance(people[0], dict) else None
            if isinstance(name, str) and name.strip():
                return name.split()[0]
    return "Ryan"


def _definition_of_done(action: NotionPage) -> tuple[str, ...]:
    value = _property_text(action.properties.get("Definition of Done"))
    return (value,) if value else ()


def _property_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if not isinstance(value, dict):
        return ""
    for key in ("rich_text", "title"):
        items = value.get(key)
        if isinstance(items, list):
            return "".join(
                str(item.get("plain_text", item.get("text", {}).get("content", "")))
                for item in items
                if isinstance(item, dict)
            ).strip()
    if "select" in value and isinstance(value["select"], dict):
        return str(value["select"].get("name") or "").strip()
    return ""
