from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field

from atlas_ros.adapters.errors import AdapterConfigurationError, AdapterError
from atlas_ros.adapters.keychain import MacOSKeychain


class NotionPage(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    url: str
    properties: dict[str, Any] = Field(default_factory=dict)


class NotionAdapter(Protocol):
    def get_current_user(self) -> dict[str, Any]: ...
    def list_users(self) -> list[dict[str, Any]]: ...
    def fetch_data_source(self, data_source_id: str) -> dict[str, Any]: ...
    def create_page(self, data_source_id: str, properties: dict[str, Any]) -> NotionPage: ...
    def get_page(self, page_id: str) -> NotionPage: ...
    def update_page(self, page_id: str, properties: dict[str, Any]) -> NotionPage: ...
    def query_pages(self, data_source_id: str, query: dict[str, Any]) -> list[NotionPage]: ...


@dataclass
class LiveNotionAdapter:
    """Thin Notion REST adapter. Tokens are read only from process configuration."""

    token: str
    base_url: str = "https://api.notion.com/v1"
    notion_version: str = "2025-09-03"
    timeout_seconds: float = 15.0

    @classmethod
    def from_environment(cls) -> LiveNotionAdapter:
        token = os.environ.get("ATLAS_NOTION_TOKEN", "")
        if not token:
            raise AdapterConfigurationError("notion", "configure", "ATLAS_NOTION_TOKEN is not set")
        base_url = os.environ.get("ATLAS_NOTION_BASE_URL", cls.base_url)
        if base_url != cls.base_url and os.environ.get("ATLAS_ALLOW_CUSTOM_BASE_URL") != "1":
            raise AdapterConfigurationError("notion", "configure", "custom base URL is prohibited")
        return cls(token=token, base_url=base_url)

    @classmethod
    def from_keychain(cls, account: str) -> LiveNotionAdapter:
        return cls(token=MacOSKeychain(account).read("atlas-ros-notion-token"))

    def _request(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        request = Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode() if payload else None,
            method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Notion-Version": self.notion_version,
                "Content-Type": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode())
        except HTTPError as exc:
            raise AdapterError(
                "notion", path, f"HTTP {exc.code}", retryable=exc.code == 429 or exc.code >= 500
            ) from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise AdapterError("notion", path, "malformed JSON response", retryable=True) from exc
        except TimeoutError as exc:
            raise AdapterError("notion", path, "request timed out", retryable=True) from exc
        except URLError as exc:
            raise AdapterError("notion", path, "transport failure", retryable=True) from exc
        if not isinstance(body, dict):
            raise AdapterError("notion", path, "malformed response")
        return body

    @staticmethod
    def _page(body: dict[str, Any]) -> NotionPage:
        page_id, url = body.get("id"), body.get("url")
        if not isinstance(page_id, str) or not isinstance(url, str):
            raise AdapterError("notion", "readback", "response omitted page identity")
        properties = body.get("properties", {})
        return NotionPage(
            id=page_id, url=url, properties=properties if isinstance(properties, dict) else {}
        )

    def fetch_data_source(self, data_source_id: str) -> dict[str, Any]:
        return self._request("GET", f"/data_sources/{data_source_id}")

    def get_current_user(self) -> dict[str, Any]:
        return self._request("GET", "/users/me")

    def list_users(self) -> list[dict[str, Any]]:
        users: list[dict[str, Any]] = []
        path = "/users?page_size=100"
        while path:
            body = self._request("GET", path)
            results = body.get("results", [])
            if not isinstance(results, list):
                raise AdapterError("notion", "users", "malformed users response")
            users.extend(item for item in results if isinstance(item, dict))
            cursor = body.get("next_cursor")
            if body.get("has_more") and isinstance(cursor, str) and cursor:
                path = f"/users?page_size=100&start_cursor={cursor}"
            else:
                path = ""
        return users

    def create_page(self, data_source_id: str, properties: dict[str, Any]) -> NotionPage:
        page = self._page(
            self._request(
                "POST",
                "/pages",
                {"parent": {"data_source_id": data_source_id}, "properties": properties},
            )
        )
        return self.get_page(page.id)

    def get_page(self, page_id: str) -> NotionPage:
        return self._page(self._request("GET", f"/pages/{page_id}"))

    def update_page(self, page_id: str, properties: dict[str, Any]) -> NotionPage:
        page = self._page(self._request("PATCH", f"/pages/{page_id}", {"properties": properties}))
        return self.get_page(page.id)

    def query_pages(self, data_source_id: str, query: dict[str, Any]) -> list[NotionPage]:
        pages: list[NotionPage] = []
        payload = dict(query)
        while True:
            body = self._request("POST", f"/data_sources/{data_source_id}/query", payload)
            results = body.get("results", [])
            if not isinstance(results, list):
                raise AdapterError("notion", "query", "malformed query response")
            pages.extend(self._page(item) for item in results if isinstance(item, dict))
            cursor = body.get("next_cursor")
            if not body.get("has_more") or not isinstance(cursor, str) or not cursor:
                break
            payload["start_cursor"] = cursor
        return pages


class FakeNotionAdapter:
    def __init__(self) -> None:
        self.pages: dict[str, NotionPage] = {}
        self.schemas: dict[str, dict[str, Any]] = {}
        self.page_sources: dict[str, str] = {}

    def fetch_data_source(self, data_source_id: str) -> dict[str, Any]:
        return self.schemas[data_source_id]

    def get_current_user(self) -> dict[str, Any]:
        return {"object": "user", "id": "notion-test-user", "name": "Ryan Smith"}

    def list_users(self) -> list[dict[str, Any]]:
        return [
            {"object": "user", "id": "notion-test-user", "name": "Ryan Smith"},
            {"object": "user", "id": "bill-user", "name": "Bill"},
        ]

    def create_page(self, data_source_id: str, properties: dict[str, Any]) -> NotionPage:
        page = NotionPage(
            id=f"page-{len(self.pages) + 1}",
            url=f"https://notion.test/{len(self.pages) + 1}",
            properties=properties,
        )
        self.pages[page.id] = page
        self.page_sources[page.id] = data_source_id
        return page

    def get_page(self, page_id: str) -> NotionPage:
        return self.pages[page_id]

    def update_page(self, page_id: str, properties: dict[str, Any]) -> NotionPage:
        current = self.pages[page_id]
        merged = dict(current.properties)
        merged.update(properties)
        page = current.model_copy(update={"properties": merged})
        self.pages[page_id] = page
        return page

    def query_pages(self, data_source_id: str, query: dict[str, Any]) -> list[NotionPage]:
        pages = [
            page
            for page_id, page in self.pages.items()
            if self.page_sources.get(page_id) == data_source_id
        ]
        filter_spec = query.get("filter")
        if not isinstance(filter_spec, dict):
            return pages

        def plain(value: Any) -> Any:
            if isinstance(value, dict):
                for key in ("rich_text", "title"):
                    if key in value and isinstance(value[key], list):
                        return "".join(
                            str(item.get("plain_text", item.get("text", {}).get("content", "")))
                            for item in value[key]
                            if isinstance(item, dict)
                        )
                if "select" in value:
                    selected = value["select"]
                    return selected.get("name", "") if isinstance(selected, dict) else ""
            return value

        def matches(page: NotionPage, node: dict[str, Any]) -> bool:
            if "and" in node:
                return all(matches(page, child) for child in node["and"])
            prop = node.get("property")
            if not isinstance(prop, str):
                return True
            actual = plain(page.properties.get(prop, ""))
            condition: Any = next((value for key, value in node.items() if key != "property"), {})
            if not isinstance(condition, dict):
                return True
            if "equals" in condition:
                return bool(actual == condition["equals"])
            if condition.get("is_not_empty") is True:
                return bool(actual)
            return True

        return [page for page in pages if matches(page, filter_spec)]
