from __future__ import annotations

import json
from datetime import date
from typing import Any
from unittest.mock import patch

import pytest

from atlas_ros.adapters.errors import AdapterConfigurationError
from atlas_ros.release.surface_sync import (
    CONTROL_CENTER_PAGE_ID,
    HOME_PAGE_ID,
    PRODUCTION_PAGE_ID,
    RELEASES_PAGE_ID,
    LiveNotionContentAdapter,
    ReleaseAuthority,
    ReleaseSurfaceSyncService,
    SurfaceSyncError,
    block_plain_text,
)


class FakeNotionContentAdapter:
    def __init__(self) -> None:
        self.blocks: dict[str, dict[str, Any]] = {}
        self.block_children: dict[str, list[str]] = {}

    def add_block(
        self,
        parent_id: str,
        block_id: str,
        block_type: str,
        block_content: dict[str, Any],
        *,
        has_children: bool = False,
    ) -> None:
        self.blocks[block_id] = {
            "object": "block",
            "id": block_id,
            "type": block_type,
            "has_children": has_children,
            block_type: dict(block_content),
        }
        self.block_children.setdefault(parent_id, []).append(block_id)

    def list_block_children(self, block_id: str) -> list[dict[str, Any]]:
        return [self.blocks[item] for item in self.block_children.get(block_id, [])]

    def get_block(self, block_id: str) -> dict[str, Any]:
        return self.blocks[block_id]

    def update_block(
        self, block_id: str, block_type: str, block_content: dict[str, Any]
    ) -> dict[str, Any]:
        current = self.blocks[block_id]
        merged = dict(current.get(block_type, {}))
        merged.update(block_content)
        updated = dict(current)
        updated[block_type] = merged
        self.blocks[block_id] = updated
        return updated


def rich_text(content: str, link: str | None = None) -> dict[str, Any]:
    text: dict[str, Any] = {"content": content}
    if link:
        text["link"] = {"url": link}
    return {"type": "text", "text": text}


def content(value: str, link: str | None = None) -> dict[str, Any]:
    return {"rich_text": [rich_text(value, link)]}


def authority() -> ReleaseAuthority:
    return ReleaseAuthority(
        active_release="v5.2.0",
        package_version="5.2.0",
        rollback_release="v5.1.1",
        active_package_url="https://drive.google.com/drive/folders/active-v520",
        review_date=date(2026, 7, 24),
    )


def seeded_adapter() -> FakeNotionContentAdapter:
    adapter = FakeNotionContentAdapter()
    adapter.add_block(
        HOME_PAGE_ID,
        "home-callout",
        "callout",
        content(
            "PRODUCTION READY\nActive release: Atlas ROS v5.0 (5.0.0rc1)  ·  "
            "Immediate rollback: Atlas ROS v4.5.3  ·  Last state review: July 23, 2026"
        ),
    )
    adapter.add_block(
        CONTROL_CENTER_PAGE_ID,
        "control-callout",
        "callout",
        content(
            "PRODUCTION READY\nActive release: Atlas ROS v5.0 (5.0.0rc1)  ·  "
            "Immediate rollback: Atlas ROS v4.5.3  ·  Operational workflows: "
            "W01, W02, W03, and attended W04 production-active"
        ),
    )
    adapter.add_block(
        PRODUCTION_PAGE_ID,
        "production-callout",
        "callout",
        content(
            "Current operational workspace for Atlas ROS v5.0. Use this page to capture, "
            "execute, decide, manage risk, and run the leadership operating system. "
            "Atlas ROS v4.5.3 is the immediate immutable rollback baseline."
        ),
    )
    adapter.add_block(
        RELEASES_PAGE_ID,
        "columns",
        "column_list",
        {},
        has_children=True,
    )
    adapter.add_block("columns", "active-column", "column", {}, has_children=True)
    adapter.add_block("columns", "rollback-column", "column", {}, has_children=True)
    adapter.add_block(
        "active-column",
        "active-callout",
        "callout",
        content(
            "Atlas ROS v5.0 — Active package",
            "https://drive.google.com/drive/folders/old-active",
        ),
    )
    adapter.add_block(
        "rollback-column",
        "rollback-callout",
        "callout",
        content("Atlas ROS v4.5.3 — Immediate immutable rollback"),
    )
    adapter.add_block(
        RELEASES_PAGE_ID,
        "active-paragraph",
        "paragraph",
        content(
            "Atlas ROS v5.0 — Active package",
            "https://drive.google.com/drive/folders/old-active",
        ),
    )
    return adapter


def test_surface_sync_plans_applies_and_becomes_idempotent() -> None:
    adapter = seeded_adapter()
    service = ReleaseSurfaceSyncService(adapter)
    plan = service.plan(authority())

    assert plan.valid
    assert len(plan.mutations) == 6
    assert plan.noops == 0
    assert plan.matched_counts["releases-active-package"] == 2

    result = service.apply(
        plan,
        confirmed=True,
        authorization_ref="decision://promote-v5.2.0",
    )
    assert result.applied == 6
    assert result.verified == 6
    assert "Atlas ROS v5.2.0" in block_plain_text(adapter.get_block("home-callout"))
    assert block_plain_text(adapter.get_block("rollback-callout")) == (
        "Atlas ROS v5.1.1 — Immediate immutable rollback"
    )

    second = service.plan(authority())
    assert second.valid
    assert second.mutations == ()
    assert second.noops == 6


def test_surface_sync_fails_closed_when_surface_is_missing() -> None:
    adapter = seeded_adapter()
    adapter.block_children[RELEASES_PAGE_ID].remove("active-paragraph")

    plan = ReleaseSurfaceSyncService(adapter).plan(authority())

    assert not plan.valid
    assert "expected 2 matching block(s), found 1" in plan.conflicts[0]
    with pytest.raises(SurfaceSyncError, match="conflicts"):
        ReleaseSurfaceSyncService(adapter).apply(
            plan,
            confirmed=True,
            authorization_ref="decision://promotion",
        )


def test_surface_sync_requires_confirmation_and_authorization() -> None:
    service = ReleaseSurfaceSyncService(seeded_adapter())
    plan = service.plan(authority())

    with pytest.raises(PermissionError, match="confirmation"):
        service.apply(plan, confirmed=False, authorization_ref="decision://promotion")
    with pytest.raises(PermissionError, match="authorization_ref"):
        service.apply(plan, confirmed=True, authorization_ref="")


def test_surface_sync_rolls_back_verified_prior_writes() -> None:
    class FailingAdapter(FakeNotionContentAdapter):
        def __init__(self, source: FakeNotionContentAdapter) -> None:
            super().__init__()
            self.blocks = {key: dict(value) for key, value in source.blocks.items()}
            self.block_children = {
                key: list(value) for key, value in source.block_children.items()
            }
            self.update_calls = 0
            self.failed = False

        def update_block(
            self, block_id: str, block_type: str, block_content: dict[str, Any]
        ) -> dict[str, Any]:
            self.update_calls += 1
            if self.update_calls == 2 and not self.failed:
                self.failed = True
                raise RuntimeError("simulated write failure")
            return super().update_block(block_id, block_type, block_content)

    adapter = FailingAdapter(seeded_adapter())
    original = block_plain_text(adapter.get_block("home-callout"))
    service = ReleaseSurfaceSyncService(adapter)

    with pytest.raises(SurfaceSyncError, match="rolled back"):
        service.apply(
            service.plan(authority()),
            confirmed=True,
            authorization_ref="decision://promotion",
        )

    assert block_plain_text(adapter.get_block("home-callout")) == original


def test_release_authority_validation() -> None:
    with pytest.raises(ValueError, match="active_release"):
        ReleaseAuthority(
            active_release="",
            package_version="5.2.0",
            rollback_release="v5.1.1",
            active_package_url="https://drive.google.com/drive/folders/active",
            review_date=date(2026, 7, 24),
        )
    with pytest.raises(ValueError, match="start with v"):
        ReleaseAuthority(
            active_release="5.2.0",
            package_version="5.2.0",
            rollback_release="v5.1.1",
            active_package_url="https://drive.google.com/drive/folders/active",
            review_date=date(2026, 7, 24),
        )
    with pytest.raises(ValueError, match="Google Drive"):
        ReleaseAuthority(
            active_release="v5.2.0",
            package_version="5.2.0",
            rollback_release="v5.1.1",
            active_package_url="https://example.com/active",
            review_date=date(2026, 7, 24),
        )


class Response:
    def __init__(self, body: object) -> None:
        self.body = body

    def __enter__(self) -> "Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.body).encode()


def test_live_content_adapter_paginates_and_verifies_update(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ATLAS_NOTION_TOKEN", raising=False)
    with pytest.raises(AdapterConfigurationError, match="ATLAS_NOTION_TOKEN"):
        LiveNotionContentAdapter.from_environment()

    replies = iter(
        [
            {
                "results": [
                    {
                        "id": "block-1",
                        "type": "paragraph",
                        "has_children": False,
                        "paragraph": {"rich_text": []},
                    }
                ],
                "has_more": True,
                "next_cursor": "page two",
            },
            {
                "results": [],
                "has_more": False,
                "next_cursor": None,
            },
            {
                "id": "block-1",
                "type": "paragraph",
                "has_children": False,
                "paragraph": {"rich_text": []},
            },
            {
                "id": "block-1",
                "type": "paragraph",
                "has_children": False,
                "paragraph": {"rich_text": []},
            },
        ]
    )
    requested: list[tuple[str, str]] = []

    def reply(request: object, **_kwargs: object) -> Response:
        requested.append(
            (
                request.get_method(),  # type: ignore[union-attr]
                request.full_url,  # type: ignore[union-attr]
            )
        )
        return Response(next(replies))

    with patch("atlas_ros.release.surface_sync.urlopen", side_effect=reply):
        adapter = LiveNotionContentAdapter("token", base_url="https://notion.test")
        blocks = adapter.list_block_children("page")
        updated = adapter.update_block("block-1", "paragraph", {"rich_text": []})

    assert [block["id"] for block in blocks] == ["block-1"]
    assert requested[1] == (
        "GET",
        "https://notion.test/blocks/page/children?page_size=100&start_cursor=page+two",
    )
    assert requested[2][0] == "PATCH"
    assert updated["id"] == "block-1"
