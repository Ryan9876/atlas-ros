from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from atlas_ros.adapters.errors import AdapterConfigurationError
from atlas_ros.adapters.notion import FakeNotionAdapter, LiveNotionAdapter, NotionPage
from atlas_ros.adapters.todoist import FakeTodoistAdapter, LiveTodoistAdapter, TodoistTask
from atlas_ros.config.loader import load_config
from atlas_ros.domain.models import Action
from atlas_ros.release.tooling import verify
from atlas_ros.runtime.database import RuntimeDatabase
from atlas_ros.workflows.reconciliation_state import SQLiteReconciliationStateStore
from atlas_ros.workflows.w03_todoist import TodoistService, task_description
from atlas_ros.workflows.w04_reconciliation import TodoistReconciliationService


def _text(value: str) -> dict:
    return {"type": "rich_text", "rich_text": [{"plain_text": value}]}


def _select(value: str) -> dict:
    return {"type": "select", "select": {"name": value}}


def _action(notion: FakeNotionAdapter) -> NotionPage:
    page = NotionPage(
        id="action-1",
        url="https://notion.test/action-1",
        properties={
            "Execution System": _select("Todoist"),
            "Execution Object ID": _text("task-1"),
            "Status": _select("Open"),
            "Execution Priority": _select("P4"),
        },
    )
    notion.pages[page.id] = page
    notion.page_sources[page.id] = "actions"
    return page


def test_packaged_config_is_isolated_and_validated() -> None:
    first = load_config("todoist")
    first["projects"].append("Mutated")
    assert "Mutated" not in load_config("todoist")["projects"]
    with pytest.raises(ValueError, match="invalid configuration name"):
        load_config("../secret")


def test_w03_creates_complete_compliant_tree() -> None:
    adapter = FakeTodoistAdapter()
    action = Action(
        id="a1",
        title="Investigate circuit",
        owner="Ryan",
        definition_of_done="Root cause documented",
        execution_ready=True,
        delegated_work_present=True,
    )
    result = TodoistService(adapter).apply(action, confirmed=True)
    parent = adapter.get_task(result.task_id)
    assert "**Objective:**" in parent.description
    assert "**Done when:**" in parent.description
    children = adapter.list_tasks(parent_id=parent.id)
    assert len(children) == 5
    assert all(child.content.startswith(("01", "02", "03", "04", "05")) for child in children)
    assert all("**Done when:**" in child.description for child in children)


def test_todoist_description_rejects_notion_content() -> None:
    with pytest.raises(ValueError, match="prohibited"):
        task_description("Review", "See https://app.notion.com/p/abc")


def test_custom_provider_urls_are_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATLAS_NOTION_TOKEN", "x")
    monkeypatch.setenv("ATLAS_NOTION_BASE_URL", "https://evil.test")
    with pytest.raises(AdapterConfigurationError):
        LiveNotionAdapter.from_environment()
    monkeypatch.setenv("ATLAS_TODOIST_TOKEN", "x")
    monkeypatch.setenv("ATLAS_TODOIST_BASE_URL", "https://evil.test")
    with pytest.raises(AdapterConfigurationError):
        LiveTodoistAdapter.from_environment()


def test_release_verifier_rejects_traversal(tmp_path: Path) -> None:
    root = tmp_path / "release"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret")
    checksum = root / "CHECKSUMS.sha256"
    checksum.write_text("0" * 64 + "  ../outside.txt\n")
    assert verify(root, checksum) == ["line 1"]


def test_w04_risk_command_creates_record_and_advances_snapshot(tmp_path: Path) -> None:
    notion = FakeNotionAdapter()
    _action(notion)
    todoist = FakeTodoistAdapter()
    todoist.tasks["task-1"] = TodoistTask(id="task-1", content="Parent", project_id="work")
    todoist.add_comment("task-1", "@atlas risk: Vendor outage", "risk-1")
    db = RuntimeDatabase(tmp_path / "runtime.db")
    db.initialize()
    state = SQLiteReconciliationStateStore(db)
    service = TodoistReconciliationService(
        notion,
        todoist,
        db,
        action_data_source_id="actions",
        blocker_data_source_id="risks",
        state_store=state,
    )
    before = datetime.now(UTC)
    plan = service.plan(full=True)
    service.apply(plan, confirmed=True)
    risks = notion.query_pages("risks", {})
    assert risks and risks[0].properties["Type"]["select"]["name"] == "Risk"
    assert state.event_processed("comment:risk-1")
    assert state.checkpoint() >= before


def test_w04_failed_group_is_retryable(tmp_path: Path) -> None:
    class FailingNotion(FakeNotionAdapter):
        failed = False

        def create_page(self, data_source_id: str, properties: dict):
            if data_source_id == "risks" and not self.failed:
                self.failed = True
                raise RuntimeError("injected")
            return super().create_page(data_source_id, properties)

    notion = FailingNotion()
    _action(notion)
    todoist = FakeTodoistAdapter()
    todoist.tasks["task-1"] = TodoistTask(id="task-1", content="Parent", project_id="work")
    todoist.add_comment("task-1", "@atlas blocker: Carrier", "block-1")
    db = RuntimeDatabase(tmp_path / "runtime.db")
    db.initialize()
    state = SQLiteReconciliationStateStore(db)
    service = TodoistReconciliationService(
        notion,
        todoist,
        db,
        action_data_source_id="actions",
        blocker_data_source_id="risks",
        state_store=state,
    )
    plan = service.plan(full=True)
    with pytest.raises(RuntimeError, match="injected"):
        service.apply(plan, confirmed=True)
    assert not state.event_processed("comment:block-1")
    service.apply(service.plan(full=True), confirmed=True)
    assert state.event_processed("comment:block-1")
    assert len(notion.query_pages("risks", {})) == 1
