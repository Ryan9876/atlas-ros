from atlas_ros.adapters.notion import FakeNotionAdapter
from atlas_ros.adapters.todoist import FakeTodoistAdapter, TodoistTask
from atlas_ros.runtime.database import RuntimeDatabase
from atlas_ros.workflows import TodoistReconciliationService as Exported
from atlas_ros.workflows.w04_reconciliation import MutationType
from atlas_ros.workflows.w04_trust import TodoistReconciliationService


def text(value: str) -> dict[str, object]:
    return {"type": "rich_text", "rich_text": [{"plain_text": value}]}


def select(value: str) -> dict[str, object]:
    return {"type": "select", "select": {"name": value}}


def service(tmp_path, notion, todoist):
    database = RuntimeDatabase(tmp_path / "runtime.db")
    database.initialize()
    return TodoistReconciliationService(
        notion,
        todoist,
        database,
        action_data_source_id="actions",
        blocker_data_source_id="blockers",
        operations_data_source_id="operations",
    )


def action(notion):
    return notion.create_page(
        "actions",
        {
            "Action": {"type": "title", "title": [{"plain_text": "Test"}]},
            "Execution System": select("Todoist"),
            "Execution Object ID": text("task-1"),
            "Status": select("Open"),
        },
    )


def test_trust_wrapper_is_exported() -> None:
    assert Exported is TodoistReconciliationService


def test_invalid_checkpoint_and_empty_blocker_conflict(tmp_path) -> None:
    notion = FakeNotionAdapter()
    action(notion)
    todoist = FakeTodoistAdapter()
    todoist.tasks["task-1"] = TodoistTask(id="task-1", content="Test", project_id="work")
    todoist.add_comment("task-1", "@atlas checkpoint next Friday", "p1")
    todoist.add_comment("task-1", "@atlas blocker", "b1")
    plan = service(tmp_path, notion, todoist).plan(full=True)
    assert len([m for m in plan.mutations if m.mutation_type == MutationType.CONFLICT]) == 2


def test_unblock_requires_unique_existing_blocker(tmp_path) -> None:
    notion = FakeNotionAdapter()
    action(notion)
    todoist = FakeTodoistAdapter()
    todoist.tasks["task-1"] = TodoistTask(id="task-1", content="Test", project_id="work")
    todoist.add_comment("task-1", "@atlas unblock resolved", "u1")
    plan = service(tmp_path, notion, todoist).plan(full=True)
    assert any(m.mutation_type == MutationType.CONFLICT for m in plan.mutations)


def test_unblock_resolves_existing_blocker(tmp_path) -> None:
    notion = FakeNotionAdapter()
    action(notion)
    blocker = notion.create_page(
        "blockers",
        {
            "Risk or Blocker": {"type": "title", "title": [{"plain_text": "Approval"}]},
            "Type": select("Blocker"),
            "Status": select("Open"),
            "Todoist Parent Task ID": text("task-1"),
            "Todoist Command ID": text("b0"),
        },
    )
    todoist = FakeTodoistAdapter()
    todoist.tasks["task-1"] = TodoistTask(id="task-1", content="Test", project_id="work")
    todoist.add_comment("task-1", "@atlas unblock approved", "u1")
    reconciler = service(tmp_path, notion, todoist)
    result = reconciler.apply(reconciler.plan(full=True), confirmed=True)
    assert result.conflicts == 0
    assert notion.get_page(blocker.id).properties["Status"]["select"]["name"] == "Resolved"


def test_valid_checkpoint_uses_base_behavior(tmp_path) -> None:
    notion = FakeNotionAdapter()
    action(notion)
    todoist = FakeTodoistAdapter()
    todoist.tasks["task-1"] = TodoistTask(id="task-1", content="Test", project_id="work")
    todoist.add_comment("task-1", "@atlas checkpoint 2026-08-20", "p1")
    plan = service(tmp_path, notion, todoist).plan(full=True)
    assert any("checkpoint" in m.summary.lower() for m in plan.mutations)
