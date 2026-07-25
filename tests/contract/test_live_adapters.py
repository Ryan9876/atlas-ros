import io
import json
from datetime import UTC, datetime
from unittest.mock import patch
from urllib.error import HTTPError

import pytest

from atlas_ros.adapters.errors import AdapterConfigurationError, AdapterError
from atlas_ros.adapters.notion import FakeNotionAdapter, LiveNotionAdapter
from atlas_ros.adapters.todoist import FakeTodoistAdapter, LiveTodoistAdapter
from atlas_ros.domain.models import Action
from atlas_ros.services.todoist_execution import TodoistService


class LinkWriter:
    def __init__(self) -> None:
        self.links: list[tuple[str, str]] = []

    def store_todoist_link(self, action_id: str, task_id: str) -> None:
        self.links.append((action_id, task_id))


def test_notion_fake_create_then_readback() -> None:
    adapter = FakeNotionAdapter()
    page = adapter.create_page("actions", {"Name": "Acceptance"})
    assert adapter.get_page(page.id) == page


def test_w03_live_adapter_contract_is_idempotent_and_links_last() -> None:
    writer = LinkWriter()
    adapter = FakeTodoistAdapter()
    service = TodoistService(adapter, writer)
    action = Action(
        id="acceptance-action",
        title="Atlas adapter acceptance",
        owner="Ryan",
        definition_of_done="Task exists and is readable",
        execution_ready=True,
        delegated_work_present=True,
    )
    first = service.apply(action, confirmed=True)
    second = service.apply(action, confirmed=True)
    assert first.task_id == second.task_id
    assert len(adapter.tasks) == 6
    assert writer.links == [(action.id, first.task_id), (action.id, second.task_id)]


class Response:
    def __init__(self, body: object) -> None:
        self.body = body

    def __enter__(self) -> "Response":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.body).encode()


def test_live_notion_adapter_contract_and_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ATLAS_NOTION_TOKEN", raising=False)
    with pytest.raises(AdapterConfigurationError):
        LiveNotionAdapter.from_environment()
    replies = iter(
        [
            {"id": "data-source", "properties": {}},
            {"id": "page-1", "url": "https://notion.test/page-1", "properties": {"Name": "A"}},
            {"id": "page-1", "url": "https://notion.test/page-1", "properties": {"Name": "A"}},
            {"id": "page-1", "url": "https://notion.test/page-1", "properties": {"Name": "B"}},
            {"id": "page-1", "url": "https://notion.test/page-1", "properties": {"Name": "B"}},
        ]
    )
    with patch(
        "atlas_ros.adapters.notion.urlopen",
        side_effect=lambda *_args, **_kwargs: Response(next(replies)),
    ):
        adapter = LiveNotionAdapter("token", base_url="https://notion.test")
        assert adapter.fetch_data_source("data-source")["id"] == "data-source"
        assert adapter.create_page("data-source", {"Name": "A"}).id == "page-1"
        assert adapter.update_page("page-1", {"Name": "B"}).properties["Name"] == "B"


def test_live_todoist_adapter_contract_and_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ATLAS_TODOIST_TOKEN", raising=False)
    with pytest.raises(AdapterConfigurationError):
        LiveTodoistAdapter.from_environment()
    task = {"id": "task-1", "content": "A", "project_id": "work", "description": "Done"}
    replies = iter(
        [
            {"results": [{"id": "work", "name": "Work"}], "next_cursor": None},
            {"results": [{"id": "sec", "name": "Now"}], "next_cursor": None},
            {"results": [{"name": "ROS"}], "next_cursor": None},
            task,
            task,
            task,
        ]
    )
    with patch(
        "atlas_ros.adapters.todoist.urlopen",
        side_effect=lambda *_args, **_kwargs: Response(next(replies)),
    ):
        adapter = LiveTodoistAdapter("token", base_url="https://todoist.test")
        assert adapter.list_projects()[0].name == "Work"
        assert adapter.list_sections("work")[0]["name"] == "Now"
        assert adapter.list_labels() == ["ROS"]
        assert (
            adapter.create_task(
                content="A",
                project_id="work",
                section_id=None,
                parent_id=None,
                description="Done",
                idempotency_key="key",
            ).id
            == "task-1"
        )
        assert adapter.get_task("task-1").id == "task-1"


def test_live_todoist_adapter_follows_cursor_pagination() -> None:
    replies = iter(
        [
            {"results": [{"id": "one", "name": "One"}], "next_cursor": "page two"},
            {"results": [{"id": "two", "name": "Two"}], "next_cursor": None},
        ]
    )
    requested_urls: list[str] = []

    def reply(request: object, **_kwargs: object) -> Response:
        requested_urls.append(request.full_url)  # type: ignore[union-attr]
        return Response(next(replies))

    with patch("atlas_ros.adapters.todoist.urlopen", side_effect=reply):
        projects = LiveTodoistAdapter("token", base_url="https://todoist.test").list_projects()

    assert [project.name for project in projects] == ["One", "Two"]
    assert requested_urls[-1] == "https://todoist.test/projects?cursor=page+two"


def test_live_notion_adapter_uses_data_source_version_and_reports_error_body() -> None:
    captured_headers: dict[str, str] = {}

    def fail(request: object, **_kwargs: object) -> Response:
        captured_headers.update(dict(request.header_items()))  # type: ignore[union-attr]
        raise HTTPError(
            request.full_url,  # type: ignore[union-attr]
            400,
            "Bad Request",
            {},
            io.BytesIO(b'{"code":"validation_error","message":"invalid query"}'),
        )

    with patch("atlas_ros.adapters.notion.urlopen", side_effect=fail):
        adapter = LiveNotionAdapter("token", base_url="https://notion.test")
        with pytest.raises(AdapterError, match="HTTP 400"):
            adapter.query_pages("data-source", {})

    assert captured_headers["Notion-version"] == "2025-09-03"


def test_todoist_completed_tasks_accept_items_envelope(monkeypatch) -> None:
    responses = iter(
        [
            {
                "items": [
                    {
                        "id": "done-1",
                        "content": "Completed item",
                        "project_id": "work",
                        "completed_at": "2026-07-21T15:00:00Z",
                    }
                ],
                "next_cursor": None,
            }
        ]
    )
    monkeypatch.setattr(
        LiveTodoistAdapter,
        "_request",
        lambda self, method, path, payload=None, request_id=None: next(responses),
    )
    adapter = LiveTodoistAdapter(token="token")
    tasks = adapter.list_completed_tasks(datetime(2026, 7, 20, tzinfo=UTC))
    assert [task.id for task in tasks] == ["done-1"]
    assert tasks[0].completed_at == "2026-07-21T15:00:00Z"
