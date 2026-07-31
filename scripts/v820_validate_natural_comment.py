#!/usr/bin/env python3
"""Generate deterministic v8.2 natural-comment connector evidence with fake providers."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from atlas_ros.adapters.notion import FakeNotionAdapter
from atlas_ros.adapters.todoist import FakeTodoistAdapter, TodoistComment, TodoistTask
from atlas_ros.reconciliation.service import (
    ReconciliationApplyAuthorization,
    TodoistReconciliationService,
)
from atlas_ros.runtime.database import RuntimeDatabase

FIXTURE = (
    "I spoke to Kweku, he is going to document what happend. "
    "I need to follow up with him on Monday."
)


def _text(value: str) -> dict[str, object]:
    return {"type": "rich_text", "rich_text": [{"plain_text": value}]}


def _title(value: str) -> dict[str, object]:
    return {"type": "title", "title": [{"plain_text": value}]}


def _select(value: str) -> dict[str, object]:
    return {"type": "select", "select": {"name": value}}


def generate() -> dict[str, object]:
    notion = FakeNotionAdapter()
    notion.users.append({"object": "user", "id": "kweku-user", "name": "Kweku Folson"})
    action = notion.create_page(
        "actions",
        {
            "Action": _title("Address Kweku’s delayed response to Rivian"),
            "Definition of Done": _text(
                "The discussion is complete and the Rivian response owner is confirmed."
            ),
            "Execution System": _select("Todoist"),
            "Execution Object ID": _text("parent-1"),
            "Status": _select("Open"),
            "Execution Priority": _select("P3"),
            "Execution Due Date": {"type": "date", "date": None},
        },
    )
    todoist = FakeTodoistAdapter()
    todoist.tasks["parent-1"] = TodoistTask(
        id="parent-1",
        content="Address delayed Rivian response with Kweku",
        project_id="work",
        section_id="leadership",
        priority=2,
        updated_at="2026-07-30T22:34:00Z",
    )
    todoist.comments["parent-1"] = [
        TodoistComment(
            id="c1",
            task_id="parent-1",
            content=FIXTURE,
            posted_at="2026-07-30T23:20:17Z",
            posted_uid="651726",
        )
    ]
    with tempfile.TemporaryDirectory() as directory:
        database = RuntimeDatabase(Path(directory) / "runtime.db")
        database.initialize()
        service = TodoistReconciliationService(
            notion,
            todoist,
            database,
            action_data_source_id="actions",
            execution_step_data_source_id="steps",
            delegated_work_data_source_id="delegated",
            blocker_data_source_id="blockers",
            operations_data_source_id="operations",
        )
        plan = service.plan(task_id="parent-1")
        event = next(item for item in plan.events if item.source_comment_id == "c1")
        notion_operation = next(
            operation for operation in plan.provider_operations if operation.provider == "notion"
        )
        checkpoint_operation = next(
            operation
            for operation in plan.provider_operations
            if operation.action == "upsert_current_checkpoint"
        )
        assert event.interpretation_status == "Awaiting Approval"
        assert notion_operation.payload["expected_outcome"] == (
            "Kweku documents what happened regarding the delayed Rivian response."
        )
        assert notion_operation.payload["completion_criteria"] == (
            "The documentation is completed and available for Ryan’s review.",
        )
        assert notion_operation.payload["delegate_due"] is None
        assert notion_operation.payload["follow_up_checkpoint"] == "2026-08-03"
        assert checkpoint_operation.payload["content"] == (
            "Follow up with Kweku on Rivian response documentation"
        )
        dry_run_digest = plan.plan_digest
        result = service.apply(
            plan,
            confirmed=True,
            authorization=ReconciliationApplyAuthorization(
                authorization_id="v820-evidence-authorization",
                actor="Ryan",
                plan_digest=dry_run_digest,
                authorized_event_ids=(event.event_id,),
            ),
        )
        replay = service.plan(task_id="parent-1")
        delegated = notion.query_pages("delegated", {})
        checkpoints = todoist.list_tasks(parent_id="parent-1")
        assert result.applied == result.verified
        assert len(delegated) == 1
        assert len(checkpoints) == 1
        assert replay.events == ()
        assert replay.mutations == ()
        assert replay.provider_operations == ()
        assert todoist.get_task("parent-1").checked is False
        assert notion.get_page(action.id).properties["Status"]["select"]["name"] == "Waiting"
        return {
            "schema_version": "v820-natural-comment-evidence-v1",
            "fixture": FIXTURE,
            "event_id": event.event_id,
            "source_digest": event.source_digest,
            "classification": event.interpretation_classification,
            "interpretation_status": event.interpretation_status,
            "responsible_party": notion_operation.payload["responsible_party"],
            "expected_outcome": notion_operation.payload["expected_outcome"],
            "completion_criteria": list(notion_operation.payload["completion_criteria"]),
            "delegate_due": notion_operation.payload["delegate_due"],
            "follow_up_checkpoint": notion_operation.payload["follow_up_checkpoint"],
            "checkpoint_content": checkpoint_operation.payload["content"],
            "inferred_fields": list(event.inferred_fields),
            "field_origins": dict(event.field_origins),
            "plan_digest": dry_run_digest,
            "fake_provider_apply_count": result.applied,
            "fake_provider_verified_count": result.verified,
            "replay_event_count": len(replay.events),
            "replay_mutation_count": len(replay.mutations),
            "replay_provider_operation_count": len(replay.provider_operations),
            "production_provider_writes": 0,
            "production_notion_writes": 0,
            "production_todoist_writes": 0,
            "attended_authorization_required": True,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evidence = generate()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
