from datetime import UTC, datetime

import pytest

from atlas_ros.adapters.notion import FakeNotionAdapter
from atlas_ros.adapters.todoist import FakeTodoistAdapter, TodoistComment, TodoistTask
from atlas_ros.runtime.database import RuntimeDatabase
from atlas_ros.workflows.w04_reconciliation import (
    MutationType,
    TodoistReconciliationService,
    parse_atlas_command,
)


def notion_text(value: str) -> dict[str, object]:
    return {"type": "rich_text", "rich_text": [{"plain_text": value}]}


def notion_select(value: str) -> dict[str, object]:
    return {"type": "select", "select": {"name": value}}


def action_fixture(notion: FakeNotionAdapter, task_id: str = "task-1"):
    return notion.create_page(
        "actions",
        {
            "Action": {"type": "title", "title": [{"plain_text": "Test action"}]},
            "Execution System": notion_select("Todoist"),
            "Execution Object ID": notion_text(task_id),
            "Status": notion_select("Open"),
            "Execution Priority": notion_select("P4"),
            "Execution Due Date": {"type": "date", "date": None},
        },
    )


def service(tmp_path, notion, todoist):
    database = RuntimeDatabase(tmp_path / "runtime.db")
    database.initialize()
    return TodoistReconciliationService(
        notion,
        todoist,
        database,
        action_data_source_id="actions",
        delegated_work_data_source_id="delegated",
        blocker_data_source_id="blockers",
        operations_data_source_id="operations",
    )


def test_parse_structured_commands() -> None:
    assert (
        parse_atlas_command("@atlas update Vendor confirmed Friday").body
        == "Vendor confirmed Friday"
    )
    delegate = parse_atlas_command("@atlas delegate Bill by 2026-08-15\nConfirm access")
    assert delegate and delegate.kind == "delegate" and delegate.argument.startswith("Bill")
    assert parse_atlas_command("ordinary comment") is None


def test_plan_maps_due_priority_and_completion(tmp_path) -> None:
    notion = FakeNotionAdapter()
    action_fixture(notion)
    todoist = FakeTodoistAdapter()
    todoist.tasks["task-1"] = TodoistTask(
        id="task-1",
        content="Test action",
        project_id="work",
        due_date="2026-08-01",
        priority=4,
        checked=True,
        completed_at="2026-07-21T12:00:00Z",
        updated_at="2026-07-21T12:00:00Z",
    )
    plan = service(tmp_path, notion, todoist).plan(full=True)
    update = next(
        item for item in plan.mutations if item.mutation_type == MutationType.ACTION_UPDATE
    )
    assert update.properties["Execution Due Date"]["date"]["start"] == "2026-08-01"
    assert update.properties["Execution Priority"]["select"]["name"] == "P1"
    assert update.properties["Status"]["select"]["name"] == "Completed"


def test_structured_comments_create_governed_mutations(tmp_path) -> None:
    notion = FakeNotionAdapter()
    action_fixture(notion)
    todoist = FakeTodoistAdapter()
    todoist.tasks["task-1"] = TodoistTask(
        id="task-1", content="Test", project_id="work", updated_at=datetime.now(UTC).isoformat()
    )
    todoist.add_comment("task-1", "@atlas delegate Bill by 2026-08-15\nConfirm access", "c1")
    todoist.add_comment("task-1", "@atlas blocker\nWaiting for Security approval", "c2")
    todoist.add_comment("task-1", "ordinary note", "c3")
    plan = service(tmp_path, notion, todoist).plan(full=True)
    kinds = {mutation.mutation_type for mutation in plan.mutations}
    assert MutationType.DELEGATION_UPSERT in kinds
    assert MutationType.BLOCKER_UPSERT in kinds
    assert "comment:c3" in plan.ignored


def test_apply_requires_confirmation_and_deduplicates_comments(tmp_path) -> None:
    notion = FakeNotionAdapter()
    action = action_fixture(notion)
    todoist = FakeTodoistAdapter()
    todoist.tasks["task-1"] = TodoistTask(id="task-1", content="Test", project_id="work")
    todoist.add_comment("task-1", "@atlas update Status is fresh", "c1")
    reconciler = service(tmp_path, notion, todoist)
    plan = reconciler.plan(full=True)
    with pytest.raises(PermissionError):
        reconciler.apply(plan)
    result = reconciler.apply(plan, confirmed=True)
    assert result.applied >= 1 and result.verified == result.applied
    replay = reconciler.plan(full=True)
    assert replay.mutations == ()
    assert not any(m.command_id == "c1" for m in replay.mutations)
    assert (
        notion.get_page(action.id).properties["Latest Update"]["rich_text"][0]["text"]["content"]
        == "Status is fresh"
    )


def test_apply_delegate_and_blocker_upserts(tmp_path) -> None:
    notion = FakeNotionAdapter()
    action_fixture(notion)
    todoist = FakeTodoistAdapter()
    todoist.tasks["task-1"] = TodoistTask(id="task-1", content="Test", project_id="work")
    todoist.add_comment("task-1", "@atlas delegate Bill by 2026-08-15\nConfirm access", "d1")
    todoist.add_comment("task-1", "@atlas blocker Security approval", "b1")
    reconciler = service(tmp_path, notion, todoist)
    plan = reconciler.plan(full=True)
    result = reconciler.apply(plan, confirmed=True)
    assert result.applied >= 3
    delegated = notion.query_pages("delegated", {})
    blockers = notion.query_pages("blockers", {})
    assert len(delegated) == 1 and len(blockers) == 1
    assert delegated[0].properties["Assigned Resource"]["rich_text"][0]["text"]["content"] == "Bill"
    assert blockers[0].properties["Status"]["select"]["name"] == "Open"


def test_unblock_updates_action_and_resolves_record(tmp_path) -> None:
    notion = FakeNotionAdapter()
    action_fixture(notion)
    todoist = FakeTodoistAdapter()
    todoist.tasks["task-1"] = TodoistTask(id="task-1", content="Test", project_id="work")
    todoist.add_comment("task-1", "@atlas unblock Security approved", "u1")
    reconciler = service(tmp_path, notion, todoist)
    result = reconciler.apply(reconciler.plan(full=True), confirmed=True)
    assert result.applied >= 2
    blocker = notion.query_pages("blockers", {})[0]
    assert blocker.properties["Status"]["select"]["name"] == "Resolved"


def test_missing_mapping_records_conflict(tmp_path) -> None:
    notion = FakeNotionAdapter()
    action_fixture(notion, "missing")
    todoist = FakeTodoistAdapter()
    reconciler = service(tmp_path, notion, todoist)
    plan = reconciler.plan(full=True)
    assert any(item.mutation_type == MutationType.CONFLICT for item in plan.mutations)
    result = reconciler.apply(plan, confirmed=True)
    assert result.conflicts == 1
    issues = notion.query_pages("operations", {})
    assert issues and issues[0].properties["Type"]["select"]["name"] == "Sync Conflict"


def test_execution_step_updates_existing_mapping(tmp_path) -> None:
    notion = FakeNotionAdapter()
    action = action_fixture(notion)
    notion.create_page(
        "steps",
        {
            "Step": {"type": "title", "title": [{"plain_text": "Old"}]},
            "Todoist Task ID": notion_text("sub-1"),
        },
    )
    todoist = FakeTodoistAdapter()
    todoist.tasks["task-1"] = TodoistTask(id="task-1", content="Parent", project_id="work")
    todoist.tasks["sub-1"] = TodoistTask(
        id="sub-1",
        content="01 Verify",
        project_id="work",
        parent_id="task-1",
        order=1,
        due_date="2026-08-02",
    )
    database = RuntimeDatabase(tmp_path / "runtime.db")
    database.initialize()
    reconciler = TodoistReconciliationService(
        notion,
        todoist,
        database,
        action_data_source_id="actions",
        execution_step_data_source_id="steps",
        operations_data_source_id="operations",
    )
    plan = reconciler.plan(full=True)
    assert any(item.mutation_type == MutationType.EXECUTION_STEP_UPDATE for item in plan.mutations)
    result = reconciler.apply(plan, confirmed=True)
    assert result.verified >= 2
    step = notion.query_pages("steps", {})[0]
    assert step.properties["Parent Action"]["relation"][0]["id"] == action.id


def test_missing_execution_step_mapping_is_created(tmp_path) -> None:
    notion = FakeNotionAdapter()
    action_fixture(notion)
    todoist = FakeTodoistAdapter()
    todoist.tasks["task-1"] = TodoistTask(id="task-1", content="Parent", project_id="work")
    todoist.tasks["sub-1"] = TodoistTask(
        id="sub-1", content="01 Verify", project_id="work", parent_id="task-1"
    )
    database = RuntimeDatabase(tmp_path / "runtime.db")
    database.initialize()
    reconciler = TodoistReconciliationService(
        notion,
        todoist,
        database,
        action_data_source_id="actions",
        execution_step_data_source_id="steps",
        operations_data_source_id="operations",
    )
    plan = reconciler.plan(full=True)
    assert any(item.mutation_type == MutationType.EXECUTION_STEP_CREATE for item in plan.mutations)
    result = reconciler.apply(plan, confirmed=True)
    assert result.conflicts == 0
    steps = notion.query_pages("steps", {})
    assert len(steps) == 1
    assert steps[0].properties["Todoist Task ID"]["rich_text"][0]["text"]["content"] == "sub-1"


def test_checkpoint_command_and_missing_delegate_configuration(tmp_path) -> None:
    notion = FakeNotionAdapter()
    action_fixture(notion)
    todoist = FakeTodoistAdapter()
    todoist.tasks["task-1"] = TodoistTask(id="task-1", content="Parent", project_id="work")
    todoist.add_comment("task-1", "@atlas checkpoint 2026-08-20", "p1")
    todoist.add_comment("task-1", "@atlas delegate Bill\nDo work", "p2")
    database = RuntimeDatabase(tmp_path / "runtime.db")
    database.initialize()
    reconciler = TodoistReconciliationService(
        notion,
        todoist,
        database,
        action_data_source_id="actions",
        operations_data_source_id="operations",
    )
    plan = reconciler.plan(full=True)
    assert any("checkpoint" in item.summary.lower() for item in plan.mutations)
    assert any(item.mutation_type == MutationType.CONFLICT for item in plan.mutations)


def test_plan_has_changes_property(tmp_path) -> None:
    notion = FakeNotionAdapter()
    action_fixture(notion)
    todoist = FakeTodoistAdapter()
    todoist.tasks["task-1"] = TodoistTask(id="task-1", content="Parent", project_id="work")
    assert service(tmp_path, notion, todoist).plan(full=True).has_changes


def test_replay_is_idempotent_after_apply(tmp_path) -> None:
    notion = FakeNotionAdapter()
    action_fixture(notion)
    todoist = FakeTodoistAdapter()
    todoist.tasks["task-1"] = TodoistTask(
        id="task-1",
        content="Parent",
        project_id="work",
        priority=1,
        updated_at="2026-07-21T14:53:10.578801Z",
    )
    reconciler = service(tmp_path, notion, todoist)
    first = reconciler.plan(full=True)
    assert first.mutations
    reconciler.apply(first, confirmed=True)
    assert reconciler.plan(full=True).mutations == ()


def test_execution_step_replay_is_idempotent(tmp_path) -> None:
    notion = FakeNotionAdapter()
    action = action_fixture(notion)
    notion.create_page(
        "steps",
        {
            "Step": {"type": "title", "title": [{"plain_text": "01 Verify"}]},
            "Parent Action": {"type": "relation", "relation": [{"id": action.id}]},
            "Todoist Task ID": notion_text("sub-1"),
            "Todoist Task URL": {"type": "url", "url": "https://app.todoist.com/app/task/sub-1"},
            "Sequence": {"type": "number", "number": 1},
            "Status": notion_select("Open"),
            "Last Verified": {"type": "date", "date": {"start": "2026-07-21"}},
            "Sync State": notion_select("Synced"),
        },
    )
    todoist = FakeTodoistAdapter()
    todoist.tasks["task-1"] = TodoistTask(id="task-1", content="Parent", project_id="work")
    todoist.tasks["sub-1"] = TodoistTask(
        id="sub-1", content="01 Verify", project_id="work", parent_id="task-1", order=1
    )
    database = RuntimeDatabase(tmp_path / "runtime.db")
    database.initialize()
    reconciler = TodoistReconciliationService(
        notion,
        todoist,
        database,
        action_data_source_id="actions",
        execution_step_data_source_id="steps",
        operations_data_source_id="operations",
    )
    first = reconciler.plan(full=True)
    assert any(item.mutation_type == MutationType.EXECUTION_STEP_UPDATE for item in first.mutations)
    reconciler.apply(first, confirmed=True)
    assert not any(
        item.mutation_type == MutationType.EXECUTION_STEP_UPDATE
        for item in reconciler.plan(full=True).mutations
    )


def test_status_comment_replay_is_idempotent_with_fresh_runtime(tmp_path) -> None:
    notion = FakeNotionAdapter()
    action_fixture(notion)
    todoist = FakeTodoistAdapter()
    todoist.tasks["task-1"] = TodoistTask(id="task-1", content="Parent", project_id="work")
    todoist.add_comment(
        "task-1",
        "@atlas update W04 controlled acceptance: reverse synchronization validation in progress.",
        "status-1",
    )
    first = service(tmp_path / "first", notion, todoist)
    first.apply(first.plan(full=True), confirmed=True)

    fresh = service(tmp_path / "fresh", notion, todoist)
    assert fresh.plan(full=True).mutations == ()


def test_conflict_mutations_are_aggregated_in_plan(tmp_path) -> None:
    notion = FakeNotionAdapter()
    action_fixture(notion, "missing")
    todoist = FakeTodoistAdapter()
    plan = service(tmp_path, notion, todoist).plan(full=True)
    assert any(item.mutation_type == MutationType.CONFLICT for item in plan.mutations)
    assert plan.conflicts
    assert "mapped Todoist task was not found" in plan.conflicts[0]


def test_shared_checkpoint_suppresses_unledgered_older_comment(tmp_path) -> None:
    notion = FakeNotionAdapter()
    action_fixture(notion)
    todoist = FakeTodoistAdapter()
    reconciler = service(tmp_path, notion, todoist)
    todoist.tasks["task-1"] = TodoistTask(
        id="task-1",
        content="Task",
        project_id="work",
        priority=3,
        checked=False,
    )
    todoist.comments["task-1"] = [
        TodoistComment(
            id="old-comment",
            task_id="task-1",
            content="@atlas update In Progress",
            posted_at="2026-07-21T17:31:50Z",
        )
    ]
    reconciler.state_store.set_checkpoint(datetime(2026, 7, 21, 17, 55, tzinfo=UTC))

    plan = reconciler.plan(task_id="task-1")

    assert not any(m.command_id == "old-comment" for m in plan.mutations)


def test_shared_checkpoint_keeps_newer_unprocessed_comment(tmp_path) -> None:
    notion = FakeNotionAdapter()
    action_fixture(notion)
    todoist = FakeTodoistAdapter()
    reconciler = service(tmp_path, notion, todoist)
    todoist.tasks["task-1"] = TodoistTask(
        id="task-1",
        content="Task",
        project_id="work",
        priority=3,
        checked=False,
    )
    todoist.comments["task-1"] = [
        TodoistComment(
            id="new-comment",
            task_id="task-1",
            content="@atlas update New status",
            posted_at="2026-07-21T17:56:00Z",
        )
    ]
    reconciler.state_store.set_checkpoint(datetime(2026, 7, 21, 17, 55, tzinfo=UTC))

    plan = reconciler.plan(task_id="task-1")

    assert any(m.command_id == "new-comment" for m in plan.mutations)


def test_subtask_comment_updates_linked_execution_step(tmp_path) -> None:
    notion = FakeNotionAdapter()
    action = action_fixture(notion)
    step = notion.create_page(
        "steps",
        {
            "Step": {"type": "title", "title": [{"plain_text": "03 Reconcile"}]},
            "Parent Action": {"type": "relation", "relation": [{"id": action.id}]},
            "Todoist Task ID": notion_text("sub-1"),
            "Status": notion_select("Open"),
        },
    )
    todoist = FakeTodoistAdapter()
    todoist.tasks["task-1"] = TodoistTask(id="task-1", content="Parent", project_id="work")
    todoist.tasks["sub-1"] = TodoistTask(
        id="sub-1", content="03 Reconcile", project_id="work", parent_id="task-1", order=3
    )
    todoist.add_comment("sub-1", "@atlas update: I hope everything works!", "sub-update")
    database = RuntimeDatabase(tmp_path / "runtime.db")
    database.initialize()
    reconciler = TodoistReconciliationService(
        notion,
        todoist,
        database,
        action_data_source_id="actions",
        execution_step_data_source_id="steps",
        delegated_work_data_source_id="delegated",
        operations_data_source_id="operations",
    )
    result = reconciler.apply(reconciler.plan(full=True), confirmed=True)
    assert result.applied >= 1
    assert (
        notion.get_page(step.id).properties["Latest Update"]["rich_text"][0]["text"]["content"]
        == "I hope everything works!"
    )


def test_delegate_to_syntax_resolves_notion_person(tmp_path) -> None:
    notion = FakeNotionAdapter()
    action_fixture(notion)
    todoist = FakeTodoistAdapter()
    todoist.tasks["task-1"] = TodoistTask(id="task-1", content="Parent", project_id="work")
    todoist.add_comment("task-1", "@atlas delegate to Ryan", "delegate-ryan")
    reconciler = service(tmp_path, notion, todoist)
    reconciler.apply(reconciler.plan(full=True), confirmed=True)
    delegated = notion.query_pages("delegated", {})[0]
    assert delegated.properties["Assigned Resource"]["rich_text"][0]["text"]["content"] == "Ryan"
    assert delegated.properties["Assigned Person"]["people"][0]["id"] == "notion-test-user"
    assert delegated.properties["Resource Type"]["select"]["name"] == "Team Member"


def test_subtask_delegate_uses_parent_task_linkage(tmp_path) -> None:
    notion = FakeNotionAdapter()
    action_fixture(notion)
    todoist = FakeTodoistAdapter()
    todoist.tasks["task-1"] = TodoistTask(id="task-1", content="Parent", project_id="work")
    todoist.tasks["sub-1"] = TodoistTask(
        id="sub-1", content="Investigate issue", project_id="work", parent_id="task-1"
    )
    todoist.add_comment("sub-1", "@atlas delegate Bill", "delegate-sub")
    reconciler = service(tmp_path, notion, todoist)
    reconciler.apply(reconciler.plan(full=True), confirmed=True)
    delegated = notion.query_pages("delegated", {})[0]
    assert (
        delegated.properties["Todoist Parent Task ID"]["rich_text"][0]["text"]["content"]
        == "task-1"
    )
    assert (
        "Investigate issue"
        in delegated.properties["Delegated Outcome"]["title"][0]["text"]["content"]
    )


def test_parse_extended_risk_commands() -> None:
    for kind in ("risk", "dependency", "issue"):
        command = parse_atlas_command(f"@atlas {kind}: test condition")
        assert command is not None
        assert command.kind == kind
        assert command.body == "test condition"
