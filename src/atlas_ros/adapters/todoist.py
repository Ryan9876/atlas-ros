from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict

from atlas_ros.adapters.errors import AdapterConfigurationError, AdapterError
from atlas_ros.adapters.keychain import MacOSKeychain


class TodoistTask(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    content: str
    project_id: str
    section_id: str | None = None
    parent_id: str | None = None
    description: str = ""
    due_date: str = ""
    priority: int = 1
    checked: bool = False
    completed_at: str = ""
    updated_at: str = ""
    responsible_uid: str | None = None
    order: int = 0


class TodoistComment(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    task_id: str
    content: str
    posted_at: str = ""


class TodoistProject(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    name: str


class TodoistAdapter(Protocol):
    def list_projects(self) -> list[TodoistProject]: ...
    def list_sections(self, project_id: str) -> list[dict[str, str]]: ...
    def list_labels(self) -> list[str]: ...
    def create_task(
        self,
        *,
        content: str,
        project_id: str,
        section_id: str | None,
        parent_id: str | None,
        description: str,
        idempotency_key: str,
    ) -> TodoistTask: ...
    def get_task(self, task_id: str) -> TodoistTask: ...
    def update_task(self, task_id: str, **changes: Any) -> TodoistTask: ...
    def list_tasks(self, *, project_id: str = "", parent_id: str = "") -> list[TodoistTask]: ...
    def list_comments(self, task_id: str) -> list[TodoistComment]: ...
    def list_completed_tasks(self, since: datetime) -> list[TodoistTask]: ...


@dataclass
class LiveTodoistAdapter:
    token: str
    base_url: str = "https://api.todoist.com/api/v1"
    timeout_seconds: float = 15.0

    @classmethod
    def from_environment(cls) -> LiveTodoistAdapter:
        token = os.environ.get("ATLAS_TODOIST_TOKEN", "")
        if not token:
            raise AdapterConfigurationError(
                "todoist", "configure", "ATLAS_TODOIST_TOKEN is not set"
            )
        base_url = os.environ.get("ATLAS_TODOIST_BASE_URL", cls.base_url)
        if base_url != cls.base_url and os.environ.get("ATLAS_ALLOW_CUSTOM_BASE_URL") != "1":
            raise AdapterConfigurationError("todoist", "configure", "custom base URL is prohibited")
        return cls(token=token, base_url=base_url)

    @classmethod
    def from_keychain(cls, account: str) -> LiveTodoistAdapter:
        return cls(token=MacOSKeychain(account).read("atlas-ros-todoist-token"))

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> Any:
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        if request_id:
            headers["X-Request-Id"] = request_id
        request = Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode() if payload else None,
            method=method,
            headers=headers,
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode())
        except HTTPError as exc:
            raise AdapterError(
                "todoist", path, f"HTTP {exc.code}", retryable=exc.code == 429 or exc.code >= 500
            ) from exc
        except TimeoutError as exc:
            raise AdapterError("todoist", path, "request timed out", retryable=True) from exc
        except URLError as exc:
            raise AdapterError("todoist", path, "transport failure", retryable=True) from exc

    def _list(self, path: str) -> list[dict[str, Any]]:
        """Read every page from a Todoist API v1 collection endpoint."""
        items: list[dict[str, Any]] = []
        next_path: str | None = path
        while next_path:
            body = self._request("GET", next_path)
            # Todoist API v1 collection endpoints return a cursor envelope.
            # Retaining list support keeps the adapter compatible with the
            # legacy API response shape used by existing test doubles.
            if isinstance(body, list):
                page, cursor = body, None
            elif isinstance(body, dict) and isinstance(body.get("results"), list):
                page, cursor = body["results"], body.get("next_cursor")
            elif isinstance(body, dict) and isinstance(body.get("items"), list):
                # Completed-task endpoints use an ``items`` envelope rather
                # than the ``results`` envelope used by standard collections.
                page, cursor = body["items"], body.get("next_cursor")
            else:
                raise AdapterError("todoist", path, "malformed response")
            items.extend(item for item in page if isinstance(item, dict))
            if isinstance(cursor, str) and cursor:
                next_path = self._with_cursor(path, cursor)
            else:
                next_path = None
        return items

    @staticmethod
    def _with_cursor(path: str, cursor: str) -> str:
        parts = urlsplit(path)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query["cursor"] = cursor
        return urlunsplit(
            (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
        )

    @staticmethod
    def _task(body: Any) -> TodoistTask:
        if not isinstance(body, dict) or not isinstance(body.get("id"), str):
            raise AdapterError("todoist", "readback", "malformed task response")
        return TodoistTask(
            id=body["id"],
            content=str(body.get("content", "")),
            project_id=str(body.get("project_id", "")),
            section_id=body.get("section_id"),
            parent_id=body.get("parent_id"),
            description=str(body.get("description", "")),
            due_date=str((body.get("due") or {}).get("date", ""))
            if isinstance(body.get("due"), dict)
            else "",
            priority=int(body.get("priority", 1) or 1),
            checked=bool(body.get("checked", False)),
            completed_at=str(body.get("completed_at", "") or ""),
            updated_at=str(body.get("updated_at", "") or ""),
            responsible_uid=str(body.get("responsible_uid"))
            if body.get("responsible_uid") is not None
            else None,
            order=int(body.get("child_order", body.get("order", 0)) or 0),
        )

    def list_projects(self) -> list[TodoistProject]:
        return [
            TodoistProject(id=str(item["id"]), name=str(item["name"]))
            for item in self._list("/projects")
            if "id" in item and "name" in item
        ]

    def list_sections(self, project_id: str) -> list[dict[str, str]]:
        return [
            {"id": str(item["id"]), "name": str(item["name"])}
            for item in self._list(f"/sections?project_id={project_id}")
            if "id" in item and "name" in item
        ]

    def list_labels(self) -> list[str]:
        return [str(item["name"]) for item in self._list("/labels") if "name" in item]

    def create_task(
        self,
        *,
        content: str,
        project_id: str,
        section_id: str | None,
        parent_id: str | None,
        description: str,
        idempotency_key: str,
    ) -> TodoistTask:
        payload: dict[str, Any] = {
            "content": content,
            "project_id": project_id,
            "description": description,
        }
        if section_id:
            payload["section_id"] = section_id
        if parent_id:
            payload["parent_id"] = parent_id
        task = self._task(self._request("POST", "/tasks", payload, idempotency_key))
        return self.get_task(task.id)

    def get_task(self, task_id: str) -> TodoistTask:
        return self._task(self._request("GET", f"/tasks/{task_id}"))

    def update_task(self, task_id: str, **changes: Any) -> TodoistTask:
        allowed = {
            "content",
            "description",
            "project_id",
            "section_id",
            "parent_id",
            "priority",
            "due_date",
            "labels",
            "order",
        }
        unknown = set(changes) - allowed
        if unknown:
            raise ValueError(f"unsupported Todoist update fields: {sorted(unknown)}")
        payload = {k: v for k, v in changes.items() if k != "due_date"}
        if "due_date" in changes:
            payload["due_date"] = changes["due_date"] or None
        self._request("POST", f"/tasks/{task_id}", payload)
        return self.get_task(task_id)

    def list_tasks(self, *, project_id: str = "", parent_id: str = "") -> list[TodoistTask]:
        query: list[str] = []
        if project_id:
            query.append(f"project_id={project_id}")
        if parent_id:
            query.append(f"parent_id={parent_id}")
        path = "/tasks" + ("?" + "&".join(query) if query else "")
        return [self._task(item) for item in self._list(path)]

    def list_comments(self, task_id: str) -> list[TodoistComment]:
        return [
            TodoistComment(
                id=str(item["id"]),
                task_id=str(item.get("task_id", item.get("item_id", task_id))),
                content=str(item.get("content", "")),
                posted_at=str(item.get("posted_at", "") or ""),
            )
            for item in self._list(f"/comments?task_id={task_id}")
            if "id" in item
        ]

    def list_completed_tasks(self, since: datetime) -> list[TodoistTask]:
        until = datetime.now(UTC)
        path = (
            "/tasks/completed/by_completion_date?"
            f"since={since.astimezone(UTC).isoformat().replace('+00:00', 'Z')}&"
            f"until={until.isoformat().replace('+00:00', 'Z')}&limit=200"
        )
        return [self._task(item) for item in self._list(path)]

    @staticmethod
    def idempotency_key(action_id: str) -> str:
        return hashlib.sha256(f"atlas-w03:{action_id}".encode()).hexdigest()


class FakeTodoistAdapter:
    def __init__(
        self, projects: list[TodoistProject] | None = None, labels: list[str] | None = None
    ) -> None:
        self.projects = projects or [
            TodoistProject(id="work", name="Work"),
            TodoistProject(id="personal", name="Personal"),
        ]
        self.labels = labels or []
        self.tasks: dict[str, TodoistTask] = {}
        self.keys: dict[str, str] = {}
        self.comments: dict[str, list[TodoistComment]] = {}

    def list_projects(self) -> list[TodoistProject]:
        return self.projects

    def list_sections(self, project_id: str) -> list[dict[str, str]]:
        return []

    def list_labels(self) -> list[str]:
        return self.labels

    def create_task(
        self,
        *,
        content: str,
        project_id: str,
        section_id: str | None,
        parent_id: str | None,
        description: str,
        idempotency_key: str,
    ) -> TodoistTask:
        if idempotency_key in self.keys:
            return self.tasks[self.keys[idempotency_key]]
        task = TodoistTask(
            id=f"task-{len(self.tasks) + 1}",
            content=content,
            project_id=project_id,
            section_id=section_id,
            parent_id=parent_id,
            description=description,
        )
        self.tasks[task.id] = task
        self.keys[idempotency_key] = task.id
        return task

    def get_task(self, task_id: str) -> TodoistTask:
        if task_id not in self.tasks:
            raise KeyError(task_id)
        return self.tasks[task_id]

    def update_task(self, task_id: str, **changes: Any) -> TodoistTask:
        if task_id not in self.tasks:
            raise KeyError(task_id)
        task = self.tasks[task_id].model_copy(update=changes)
        self.tasks[task_id] = task
        return task

    def list_tasks(self, *, project_id: str = "", parent_id: str = "") -> list[TodoistTask]:
        return [
            task
            for task in self.tasks.values()
            if (not project_id or task.project_id == project_id)
            and (not parent_id or task.parent_id == parent_id)
            and not task.checked
        ]

    def list_comments(self, task_id: str) -> list[TodoistComment]:
        return list(self.comments.get(task_id, []))

    def list_completed_tasks(self, since: datetime) -> list[TodoistTask]:
        del since
        return [task for task in self.tasks.values() if task.checked]

    def add_comment(self, task_id: str, content: str, comment_id: str = "") -> TodoistComment:
        comment = TodoistComment(
            id=comment_id or f"comment-{sum(len(v) for v in self.comments.values()) + 1}",
            task_id=task_id,
            content=content,
            posted_at=datetime.now(UTC).isoformat(),
        )
        self.comments.setdefault(task_id, []).append(comment)
        return comment
