from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from atlas_ros.adapters.errors import AdapterConfigurationError, AdapterError


class NotionContentAdapter(Protocol):
    def list_block_children(self, block_id: str) -> list[dict[str, Any]]: ...
    def get_block(self, block_id: str) -> dict[str, Any]: ...
    def update_block(
        self, block_id: str, block_type: str, content: dict[str, Any]
    ) -> dict[str, Any]: ...


@dataclass
class LiveNotionContentAdapter:
    """Minimal Notion block adapter for governed release-surface synchronization."""

    token: str
    base_url: str = "https://api.notion.com/v1"
    notion_version: str = "2025-09-03"
    timeout_seconds: float = 15.0

    @classmethod
    def from_environment(cls) -> LiveNotionContentAdapter:
        token = os.environ.get("ATLAS_NOTION_TOKEN", "")
        if not token:
            raise AdapterConfigurationError(
                "notion", "configure", "ATLAS_NOTION_TOKEN is not set"
            )
        base_url = os.environ.get("ATLAS_NOTION_BASE_URL", cls.base_url)
        if base_url != cls.base_url and os.environ.get("ATLAS_ALLOW_CUSTOM_BASE_URL") != "1":
            raise AdapterConfigurationError(
                "notion", "configure", "custom base URL is prohibited"
            )
        return cls(token=token, base_url=base_url)

    def _request(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        request = Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode() if payload is not None else None,
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
            retryable = exc.code == 429 or exc.code >= 500
            raise AdapterError(
                "notion", path, f"HTTP {exc.code}", retryable=retryable
            ) from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise AdapterError(
                "notion", path, "malformed JSON response", retryable=True
            ) from exc
        except TimeoutError as exc:
            raise AdapterError("notion", path, "request timed out", retryable=True) from exc
        except URLError as exc:
            raise AdapterError("notion", path, "transport failure", retryable=True) from exc
        if not isinstance(body, dict):
            raise AdapterError("notion", path, "malformed response")
        return body

    def list_block_children(self, block_id: str) -> list[dict[str, Any]]:
        blocks: list[dict[str, Any]] = []
        cursor = ""
        while True:
            query: dict[str, str | int] = {"page_size": 100}
            if cursor:
                query["start_cursor"] = cursor
            body = self._request(
                "GET", f"/blocks/{block_id}/children?{urlencode(query)}"
            )
            results = body.get("results", [])
            if not isinstance(results, list):
                raise AdapterError("notion", "blocks", "malformed block children response")
            blocks.extend(item for item in results if isinstance(item, dict))
            next_cursor = body.get("next_cursor")
            if not body.get("has_more") or not isinstance(next_cursor, str) or not next_cursor:
                break
            cursor = next_cursor
        return blocks

    def get_block(self, block_id: str) -> dict[str, Any]:
        return self._request("GET", f"/blocks/{block_id}")

    def update_block(
        self, block_id: str, block_type: str, content: dict[str, Any]
    ) -> dict[str, Any]:
        self._request("PATCH", f"/blocks/{block_id}", {block_type: content})
        return self.get_block(block_id)


class SurfaceSyncError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReleaseAuthority:
    active_release: str
    package_version: str
    rollback_release: str
    active_package_url: str
    review_date: date

    def __post_init__(self) -> None:
        for field_name, value in (
            ("active_release", self.active_release),
            ("package_version", self.package_version),
            ("rollback_release", self.rollback_release),
            ("active_package_url", self.active_package_url),
        ):
            if not value.strip():
                raise ValueError(f"{field_name} is required")
        if not self.active_release.startswith("v"):
            raise ValueError("active_release must start with v")
        if not self.rollback_release.startswith("v"):
            raise ValueError("rollback_release must start with v")
        if not self.active_package_url.startswith("https://drive.google.com/"):
            raise ValueError("active_package_url must be an authoritative Google Drive URL")

    @property
    def human_review_date(self) -> str:
        return f"{self.review_date.strftime('%B')} {self.review_date.day}, {self.review_date.year}"


@dataclass(frozen=True)
class RenderedBlockContent:
    rich_text: tuple[dict[str, Any], ...]

    @property
    def plain_text(self) -> str:
        return "".join(_rich_text_plain_text(item) for item in self.rich_text)

    @property
    def links(self) -> tuple[str, ...]:
        return tuple(link for item in self.rich_text if (link := _rich_text_link(item)))

    def notion_payload(self) -> dict[str, Any]:
        return {"rich_text": [dict(item) for item in self.rich_text]}


@dataclass(frozen=True)
class SurfaceRule:
    key: str
    page_id: str
    expected_count: int
    matches: Callable[[str], bool]
    rendered: RenderedBlockContent


@dataclass(frozen=True)
class SurfaceMutation:
    rule_key: str
    page_id: str
    block_id: str
    block_type: str
    before_content: dict[str, Any]
    before_text: str
    before_links: tuple[str, ...]
    after: RenderedBlockContent

    def as_dict(self) -> dict[str, object]:
        return {
            "surface": self.rule_key,
            "page_id": self.page_id,
            "block_id": self.block_id,
            "block_type": self.block_type,
            "before": self.before_text,
            "after": self.after.plain_text,
            "links": list(self.after.links),
        }


@dataclass(frozen=True)
class SurfaceSyncPlan:
    authority: ReleaseAuthority
    mutations: tuple[SurfaceMutation, ...]
    matched_counts: dict[str, int]
    noops: int
    conflicts: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.conflicts

    def as_dict(self) -> dict[str, object]:
        return {
            "valid": self.valid,
            "authority": {
                "active_release": self.authority.active_release,
                "package_version": self.authority.package_version,
                "rollback_release": self.authority.rollback_release,
                "active_package_url": self.authority.active_package_url,
                "review_date": self.authority.review_date.isoformat(),
            },
            "matched_counts": self.matched_counts,
            "planned_mutations": [mutation.as_dict() for mutation in self.mutations],
            "noops": self.noops,
            "conflicts": list(self.conflicts),
        }


@dataclass(frozen=True)
class SurfaceSyncResult:
    applied: int
    verified: int
    noops: int
    authorization_ref: str

    def as_dict(self) -> dict[str, object]:
        return {
            "applied": self.applied,
            "verified": self.verified,
            "noops": self.noops,
            "authorization_ref": self.authorization_ref,
        }


HOME_PAGE_ID = "39db8344-ad2c-8100-8d31-ed50e3cc970d"
CONTROL_CENTER_PAGE_ID = "3a3b8344-ad2c-810c-bf1e-cb532f9d56e2"
PRODUCTION_PAGE_ID = "3a3b8344-ad2c-81eb-a8bc-d2b786c301f2"
RELEASES_PAGE_ID = "3a3b8344-ad2c-816f-ad68-c481f1fefaa1"


def _segment(
    content: str, *, bold: bool = False, code: bool = False, link: str | None = None
) -> dict[str, Any]:
    text: dict[str, Any] = {"content": content}
    if link:
        text["link"] = {"url": link}
    return {
        "type": "text",
        "text": text,
        "annotations": {
            "bold": bold,
            "italic": False,
            "strikethrough": False,
            "underline": False,
            "code": code,
            "color": "default",
        },
    }


def _content(*segments: dict[str, Any]) -> RenderedBlockContent:
    return RenderedBlockContent(rich_text=segments)


def _default_rules(authority: ReleaseAuthority) -> tuple[SurfaceRule, ...]:
    active = f"Atlas ROS {authority.active_release}"
    rollback = f"Atlas ROS {authority.rollback_release}"
    active_package_title = f"{active} — Active package"

    home = _content(
        _segment("PRODUCTION READY", bold=True),
        _segment("\n"),
        _segment("Active release:", bold=True),
        _segment(f" {active} ("),
        _segment(authority.package_version, code=True),
        _segment(")  ·  "),
        _segment("Immediate rollback:", bold=True),
        _segment(f" {rollback}  ·  "),
        _segment("Last state review:", bold=True),
        _segment(f" {authority.human_review_date}"),
    )
    control = _content(
        _segment("PRODUCTION READY", bold=True),
        _segment("\n"),
        _segment("Active release:", bold=True),
        _segment(f" {active} ("),
        _segment(authority.package_version, code=True),
        _segment(")  ·  "),
        _segment("Immediate rollback:", bold=True),
        _segment(f" {rollback}  ·  "),
        _segment("Operational workflows:", bold=True),
        _segment(" W01, W02, W03, and attended W04 production-active"),
    )
    production = _content(
        _segment(f"Current operational workspace for {active}.", bold=True),
        _segment(
            " Use this page to capture, execute, decide, manage risk, and run the "
            f"leadership operating system. {rollback} is the immediate immutable "
            "rollback baseline."
        ),
    )
    active_package = _content(
        _segment(active_package_title, link=authority.active_package_url)
    )
    rollback_content = _content(_segment(f"{rollback} — Immediate immutable rollback"))

    return (
        SurfaceRule(
            key="leadership-home",
            page_id=HOME_PAGE_ID,
            expected_count=1,
            matches=lambda text: text.startswith("PRODUCTION READY\nActive release: Atlas ROS ")
            and "Last state review:" in text,
            rendered=home,
        ),
        SurfaceRule(
            key="control-center",
            page_id=CONTROL_CENTER_PAGE_ID,
            expected_count=1,
            matches=lambda text: text.startswith("PRODUCTION READY\nActive release: Atlas ROS ")
            and "Operational workflows:" in text,
            rendered=control,
        ),
        SurfaceRule(
            key="production-workspace",
            page_id=PRODUCTION_PAGE_ID,
            expected_count=1,
            matches=lambda text: text.startswith(
                "Current operational workspace for Atlas ROS v"
            ),
            rendered=production,
        ),
        SurfaceRule(
            key="releases-active-package",
            page_id=RELEASES_PAGE_ID,
            expected_count=2,
            matches=lambda text: text.startswith("Atlas ROS v")
            and text.endswith("— Active package"),
            rendered=active_package,
        ),
        SurfaceRule(
            key="releases-immediate-rollback",
            page_id=RELEASES_PAGE_ID,
            expected_count=1,
            matches=lambda text: text.startswith("Atlas ROS v")
            and text.endswith("— Immediate immutable rollback"),
            rendered=rollback_content,
        ),
    )


def _rich_text_plain_text(item: dict[str, Any]) -> str:
    plain_text = item.get("plain_text")
    if isinstance(plain_text, str):
        return plain_text
    text = item.get("text")
    if isinstance(text, dict):
        content = text.get("content")
        return content if isinstance(content, str) else ""
    return ""


def _rich_text_link(item: dict[str, Any]) -> str | None:
    href = item.get("href")
    if isinstance(href, str) and href:
        return href
    text = item.get("text")
    if not isinstance(text, dict):
        return None
    link = text.get("link")
    if not isinstance(link, dict):
        return None
    url = link.get("url")
    return url if isinstance(url, str) and url else None


def _block_identity(block: dict[str, Any]) -> tuple[str, str]:
    block_id = block.get("id")
    block_type = block.get("type")
    if not isinstance(block_id, str) or not isinstance(block_type, str):
        raise SurfaceSyncError("Notion returned a block without a stable identity")
    return block_id, block_type


def _block_content(block: dict[str, Any]) -> dict[str, Any]:
    _, block_type = _block_identity(block)
    content = block.get(block_type)
    if not isinstance(content, dict):
        raise SurfaceSyncError(f"Notion block {block_type} omitted its content")
    return content


def _block_rich_text(block: dict[str, Any]) -> list[dict[str, Any]]:
    rich_text = _block_content(block).get("rich_text", [])
    if not isinstance(rich_text, list):
        return []
    return [item for item in rich_text if isinstance(item, dict)]


def block_plain_text(block: dict[str, Any]) -> str:
    return "".join(_rich_text_plain_text(item) for item in _block_rich_text(block))


def block_links(block: dict[str, Any]) -> tuple[str, ...]:
    return tuple(link for item in _block_rich_text(block) if (link := _rich_text_link(item)))


def _matches_rendered(block: dict[str, Any], rendered: RenderedBlockContent) -> bool:
    return block_plain_text(block) == rendered.plain_text and block_links(block) == rendered.links


class ReleaseSurfaceSyncService:
    def __init__(self, notion: NotionContentAdapter) -> None:
        self.notion = notion

    def _walk(self, parent_id: str) -> list[dict[str, Any]]:
        discovered: list[dict[str, Any]] = []
        pending = [parent_id]
        visited: set[str] = set()
        while pending:
            current = pending.pop()
            if current in visited:
                raise SurfaceSyncError(f"Notion block hierarchy contains a cycle at {current}")
            visited.add(current)
            children = self.notion.list_block_children(current)
            discovered.extend(children)
            for child in reversed(children):
                child_id, _ = _block_identity(child)
                if child.get("has_children") is True:
                    pending.append(child_id)
        return discovered

    def plan(self, authority: ReleaseAuthority) -> SurfaceSyncPlan:
        rules = _default_rules(authority)
        page_blocks: dict[str, list[dict[str, Any]]] = {}
        matched_counts: dict[str, int] = {}
        mutations: list[SurfaceMutation] = []
        conflicts: list[str] = []
        noops = 0
        matched_block_ids: set[str] = set()

        for rule in rules:
            blocks = page_blocks.get(rule.page_id)
            if blocks is None:
                blocks = self._walk(rule.page_id)
                page_blocks[rule.page_id] = blocks
            matches = [block for block in blocks if rule.matches(block_plain_text(block))]
            matched_counts[rule.key] = len(matches)
            if len(matches) != rule.expected_count:
                conflicts.append(
                    f"{rule.key}: expected {rule.expected_count} matching block(s), "
                    f"found {len(matches)}"
                )
                continue
            for block in matches:
                block_id, block_type = _block_identity(block)
                if block_id in matched_block_ids:
                    conflicts.append(f"{rule.key}: block {block_id} matched more than one rule")
                    continue
                matched_block_ids.add(block_id)
                if _matches_rendered(block, rule.rendered):
                    noops += 1
                    continue
                if block_type not in {"callout", "paragraph"}:
                    conflicts.append(
                        f"{rule.key}: block {block_id} has unsupported type {block_type}"
                    )
                    continue
                before_content = dict(_block_content(block))
                mutations.append(
                    SurfaceMutation(
                        rule_key=rule.key,
                        page_id=rule.page_id,
                        block_id=block_id,
                        block_type=block_type,
                        before_content=before_content,
                        before_text=block_plain_text(block),
                        before_links=block_links(block),
                        after=rule.rendered,
                    )
                )

        return SurfaceSyncPlan(
            authority=authority,
            mutations=tuple(mutations),
            matched_counts=matched_counts,
            noops=noops,
            conflicts=tuple(conflicts),
        )

    def apply(
        self,
        plan: SurfaceSyncPlan,
        *,
        confirmed: bool,
        authorization_ref: str,
    ) -> SurfaceSyncResult:
        if not confirmed:
            raise PermissionError("release surface synchronization requires explicit confirmation")
        if not authorization_ref.strip():
            raise PermissionError("authorization_ref is required for an authoritative Notion write")
        if not plan.valid:
            raise SurfaceSyncError("cannot apply a release surface plan with conflicts")

        applied: list[SurfaceMutation] = []
        verified = 0
        try:
            for mutation in plan.mutations:
                self.notion.update_block(
                    mutation.block_id,
                    mutation.block_type,
                    mutation.after.notion_payload(),
                )
                applied.append(mutation)
                readback = self.notion.get_block(mutation.block_id)
                if not _matches_rendered(readback, mutation.after):
                    raise SurfaceSyncError(
                        f"readback verification failed for {mutation.rule_key} "
                        f"block {mutation.block_id}"
                    )
                verified += 1
        except Exception as exc:
            rollback_failures: list[str] = []
            for mutation in reversed(applied):
                try:
                    self.notion.update_block(
                        mutation.block_id,
                        mutation.block_type,
                        mutation.before_content,
                    )
                    restored = self.notion.get_block(mutation.block_id)
                    if (
                        block_plain_text(restored) != mutation.before_text
                        or block_links(restored) != mutation.before_links
                    ):
                        rollback_failures.append(mutation.block_id)
                except Exception:
                    rollback_failures.append(mutation.block_id)
            suffix = (
                f"; rollback failed for {', '.join(rollback_failures)}"
                if rollback_failures
                else "; prior writes were rolled back"
            )
            raise SurfaceSyncError(f"release surface synchronization failed{suffix}") from exc

        return SurfaceSyncResult(
            applied=len(applied),
            verified=verified,
            noops=plan.noops,
            authorization_ref=authorization_ref,
        )
