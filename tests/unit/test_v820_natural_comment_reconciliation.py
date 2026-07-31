from __future__ import annotations

from datetime import UTC, datetime

import pytest

from atlas_ros.adapters.notion import FakeNotionAdapter
from atlas_ros.adapters.todoist import FakeTodoistAdapter, TodoistComment, TodoistTask
from atlas_ros.reconciliation.service import (
    MutationType,
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


def _service(tmp_path, *, with_subtask: bool = False):
    notion = FakeNotionAdapter()
    notion.users.extend(
        [
            {"object": "user", "id": "kweku-user", "name": "Kweku Folson"},
            {"object": "user", "id": "tina-user", "name": "Tina Berinyuy"},
            {"object": "user", "id": "josh-user", "name": "Josh Gunning"},
        ]
    )
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
    if with_subtask:
        todoist.tasks["sub-1"] = TodoistTask(
            id="sub-1",
            content="Capture the incident details",
            project_id="work",
            parent_id="parent-1",
            updated_at="2026-07-30T22:34:00Z",
        )
    database = RuntimeDatabase(tmp_path / "runtime.db")
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
    return notion, todoist, service, action


def _comment(todoist, content: str, *, task_id: str = "parent-1", comment_id: str = "c1"):
    comment = TodoistComment(
        id=comment_id,
        task_id=task_id,
        content=content,
        posted_at="2026-07-30T23:20:17Z",
        posted_uid="651726",
    )
    todoist.comments.setdefault(task_id, []).append(comment)
    return comment


def _event(plan):
    return next(item for item in plan.events if item.source_comment_id == "c1")


def test_exact_kweku_rivian_comment_produces_reviewable_plan(tmp_path) -> None:
    notion, todoist, service, _ = _service(tmp_path)
    _comment(todoist, FIXTURE)

    plan = service.plan(task_id="parent-1")
    event = _event(plan)
    notion_op = next(op for op in plan.provider_operations if op.provider == "notion")
    todoist_op = next(
        op for op in plan.provider_operations if op.action == "upsert_current_checkpoint"
    )

    assert event.event_id == "todoist-comment:c1"
    assert event.interpretation_classification == "delegate"
    assert event.interpretation_status == "Awaiting Approval"
    assert event.requires_attended_approval
    assert notion_op.payload["responsible_party"] == "Kweku"
    assert notion_op.payload["expected_outcome"] == (
        "Kweku documents what happened regarding the delayed Rivian response."
    )
    assert notion_op.payload["completion_criteria"] == (
        "The documentation is completed and available for Ryan’s review.",
    )
    assert notion_op.payload["delegate_due"] is None
    assert notion_op.payload["follow_up_checkpoint"] == "2026-08-03"
    assert todoist_op.payload["content"] == (
        "Follow up with Kweku on Rivian response documentation"
    )
    assert todoist_op.payload["due"] == "2026-08-03"
    assert {"outcome", "done-when", "follow-up"} <= set(event.inferred_fields)
    assert any(
        mutation.mutation_type == MutationType.ACTION_UPDATE
        and mutation.properties.get("Status", {}).get("select", {}).get("name") == "Waiting"
        for mutation in plan.mutations
    )
    assert plan.scope_report.comments_inspected == 1
    assert plan.scope_report.natural_actionable_found == 1
    assert not notion.query_pages("delegated", {})


def test_natural_provider_writes_require_exact_attended_authorization(tmp_path) -> None:
    _, todoist, service, _ = _service(tmp_path)
    _comment(todoist, FIXTURE)
    plan = service.plan(task_id="parent-1")

    with pytest.raises(PermissionError):
        service.apply(plan, confirmed=True)
    with pytest.raises(PermissionError):
        service.apply(
            plan,
            confirmed=True,
            authorization=ReconciliationApplyAuthorization(
                authorization_id="auth-1",
                actor="Ryan",
                plan_digest="0" * 64,
                authorized_event_ids=("todoist-comment:c1",),
            ),
        )


def test_exact_authorization_applies_reads_back_and_replays_zero(tmp_path) -> None:
    notion, todoist, service, action = _service(tmp_path)
    _comment(todoist, FIXTURE)
    plan = service.plan(task_id="parent-1")
    before_digest = service.plan(task_id="parent-1").plan_digest
    assert before_digest == plan.plan_digest

    result = service.apply(
        plan,
        confirmed=True,
        authorization=ReconciliationApplyAuthorization(
            authorization_id="attended-v820-test",
            actor="Ryan",
            plan_digest=plan.plan_digest,
            authorized_event_ids=("todoist-comment:c1",),
        ),
    )

    assert result.applied == result.verified
    delegated = notion.query_pages("delegated", {})
    assert len(delegated) == 1
    children = todoist.list_tasks(parent_id="parent-1")
    assert len(children) == 1
    assert children[0].content == "Follow up with Kweku on Rivian response documentation"
    assert children[0].due_date == "2026-08-03"
    assert notion.get_page(action.id).properties["Status"]["select"]["name"] == "Waiting"
    replay = service.plan(task_id="parent-1")
    assert replay.events == ()
    assert replay.provider_operations == ()
    assert replay.mutations == ()


def test_subtask_comment_is_ingested_without_parent_task_revision_change(tmp_path) -> None:
    _, todoist, service, _ = _service(tmp_path, with_subtask=True)
    unchanged = todoist.get_task("parent-1").updated_at
    _comment(todoist, FIXTURE, task_id="sub-1")

    plan = service.plan(task_id="parent-1")

    assert _event(plan).source_task_id == "sub-1"
    assert plan.scope_report.subtasks_inspected == 1
    assert todoist.get_task("parent-1").updated_at == unchanged


@pytest.mark.parametrize(
    "content",
    [
        "Kweku is going to document what happened. Follow up with Kweku Monday.",
        "Kweku will document what happened. Follow up with Kweku Monday.",
        "Kweku agreed to document what happened. Follow up with Kweku Monday.",
        "Kweku committed to documenting what happened. Follow up with Kweku Monday.",
        "Kweku plans to document what happened. Follow up with Kweku Monday.",
        "Kweku said they would document what happened. Follow up with Kweku Monday.",
    ],
)
def test_commitment_patterns_are_deterministically_recognized(tmp_path, content) -> None:
    _, todoist, service, _ = _service(tmp_path)
    _comment(todoist, content)
    plan = service.plan(task_id="parent-1")
    assert _event(plan).interpretation_classification == "delegate"
    assert plan.provider_operations


def test_ambiguous_pronoun_fails_closed_and_is_reported(tmp_path) -> None:
    _, todoist, service, _ = _service(tmp_path)
    _comment(todoist, "I talked to Tina and Josh. He will document what happened Monday.")
    plan = service.plan(task_id="parent-1")
    event = _event(plan)
    assert event.interpretation_status == "Blocked"
    assert event.blockers
    assert plan.provider_operations == ()
    assert plan.scope_report.blocked_found == 1
    assert any("blocked" in item for item in plan.ignored)


@pytest.mark.parametrize(
    "content",
    [
        "Kweku will take care of it. I need to follow up with him on Monday.",
        "Bill may handle this. Follow up with Bill Monday.",
        "Follow up Friday.",
    ],
)
def test_vague_tentative_or_unresolved_updates_fail_closed(tmp_path, content) -> None:
    _, todoist, service, _ = _service(tmp_path)
    _comment(todoist, content)
    plan = service.plan(task_id="parent-1")
    assert _event(plan).interpretation_status in {"Blocked", "Informational"}
    assert plan.provider_operations == ()


def test_informational_comment_is_visible_and_ledger_recorded_without_mutation(tmp_path) -> None:
    _, todoist, service, _ = _service(tmp_path)
    _comment(todoist, "I spoke with Kweku about Rivian.")
    plan = service.plan(task_id="parent-1")
    event = _event(plan)
    assert event.interpretation_status == "Informational"
    assert plan.provider_operations == ()
    assert plan.scope_report.informational_found == 1
    service.apply(plan, confirmed=True)
    assert service.state_store.event_status(event.event_id) == "Informational"
    assert service.plan(task_id="parent-1").events == ()


def test_unseen_comment_before_global_checkpoint_is_still_processed(tmp_path) -> None:
    _, todoist, service, _ = _service(tmp_path)
    todoist.comments["parent-1"] = [
        TodoistComment(
            id="c1",
            task_id="parent-1",
            content=FIXTURE,
            posted_at="2026-07-20T12:00:00Z",
        )
    ]
    service.state_store.set_checkpoint(datetime(2026, 7, 30, 12, 0, tzinfo=UTC))
    assert _event(service.plan(task_id="parent-1")).event_id == "todoist-comment:c1"


def test_existing_checkpoint_is_completed_before_successor_is_created(tmp_path) -> None:
    notion, todoist, service, action = _service(tmp_path)
    todoist.tasks["old-checkpoint"] = TodoistTask(
        id="old-checkpoint",
        content="Old follow-up",
        project_id="work",
        parent_id="parent-1",
    )
    notion.create_page(
        "delegated",
        {
            "Delegated Outcome": _title("Old outcome"),
            "Parent Action": {"type": "relation", "relation": [{"id": action.id}]},
            "Todoist Checkpoint ID": _text("old-checkpoint"),
            "Latest Reconciliation State": _text("applied"),
        },
    )
    _comment(todoist, FIXTURE)
    plan = service.plan(task_id="parent-1")
    assert [op.action for op in plan.provider_operations if op.provider == "todoist"] == [
        "complete_obsolete_checkpoint",
        "upsert_current_checkpoint",
    ]
    service.apply(
        plan,
        confirmed=True,
        authorization=ReconciliationApplyAuthorization(
            authorization_id="auth-replace",
            actor="Ryan",
            plan_digest=plan.plan_digest,
            authorized_event_ids=("todoist-comment:c1",),
        ),
    )
    assert todoist.get_task("old-checkpoint").checked
    assert not todoist.get_task("parent-1").checked
