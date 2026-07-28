from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from atlas_ros.contracts.authority import (
    IntegrationInventorySnapshot,
    IntegrationStatusSnapshot,
    SystemStateSnapshot,
)
from atlas_ros.kernel.bootstrap import quick_initialize
from atlas_ros.kernel.digests import sha256_digest
from atlas_ros.runtime.warm import WarmRuntimeCache, WarmRuntimeConfig
from tools.release.authority_compiler import (
    ActiveReleaseSpec,
    AuthorityCompilationSpec,
    RollbackReleaseSpec,
    compile_authority,
)


class FakeAuthorityReader:
    def __init__(self, values: dict[tuple[str, str], str]) -> None:
        self.values = values
        self.reads: list[tuple[str, str]] = []

    def read_text(self, path: PurePosixPath, *, ref: str) -> str:
        key = (path.as_posix(), ref)
        self.reads.append(key)
        return self.values[key]


class FakeDynamicReader:
    def __init__(self) -> None:
        now = datetime(2026, 7, 28, 20, 0, tzinfo=UTC)
        self.system_state = SystemStateSnapshot(
            active_version="7.1.0",
            immediate_rollback_version="7.0.1",
            authority_model_version="7.0",
            published_workspace_valid=True,
            last_verified_at=now,
        )
        self.inventory = IntegrationInventorySnapshot(
            integrations=tuple(_integration(name) for name in ("GitHub", "Notion", "Todoist")),
            last_verified_at=now,
        )
        self.inventory_references: list[str] = []

    def read_system_state(self, url: str) -> SystemStateSnapshot:
        assert url.endswith("system-state")
        return self.system_state

    def read_integration_inventory(self, reference: str) -> IntegrationInventorySnapshot:
        self.inventory_references.append(reference)
        return self.inventory


class FakeLivenessReader:
    def __init__(self, *, todoist: bool = True) -> None:
        self.todoist = todoist
        self.requests: list[frozenset[str]] = []

    def read_connector_liveness(self, names: frozenset[str]) -> dict[str, bool]:
        self.requests.append(names)
        assert names == frozenset({"Todoist"})
        return {"Todoist": self.todoist}


def _integration(name: str) -> IntegrationStatusSnapshot:
    return IntegrationStatusSnapshot(
        name=name,
        required=True,
        connection_status="connected",
        approval_status="approved",
        acceptance_status="passed",
        lifecycle_status="production",
        current=True,
        least_privilege_verified=True,
    )


def _compiled_reader(*, commit: str = "a" * 40) -> FakeAuthorityReader:
    manifest_path = "release/RELEASE_MANIFEST_V710.md"
    manifest = (
        "# Atlas ROS v7.1.0\n"
        "Integration Inventory authority: https://app.notion.com/p/inventory\n"
        "Integration Inventory data source: collection://inventory-source\n"
    )
    compiled = compile_authority(
        AuthorityCompilationSpec(
            active=ActiveReleaseSpec(
                version="7.1.0",
                immutable_commit=commit,
                tag="v7.1.0",
                manifest_path=manifest_path,
                manifest_url=(
                    f"https://github.com/Ryan9876/atlas-ros/blob/{commit}/{manifest_path}"
                ),
                manifest_sha256=sha256_digest(manifest),
                release_url="https://github.com/Ryan9876/atlas-ros/releases/tag/v7.1.0",
                source_sha256="b" * 64,
                wheel_sha256="c" * 64,
            ),
            rollback=RollbackReleaseSpec(
                version="7.0.1",
                immutable_commit="d" * 40,
                tag="v7.0.1",
                release_url="https://github.com/Ryan9876/atlas-ros/releases/tag/v7.0.1",
            ),
            notion_system_state_url="https://app.notion.com/p/system-state",
            last_promotion_transaction_id="promotion-v7.1.0",
            last_verified_at="2026-07-28T19:00:00Z",
        )
    )
    return FakeAuthorityReader(
        {
            ("governance/AUTHORITY.json", "HEAD"): compiled.authority_json,
            ("governance/RELEASE_INDEX.md", "HEAD"): compiled.release_index_markdown,
            (manifest_path, commit): manifest,
        }
    )


def _cache(tmp_path: Path) -> WarmRuntimeCache:
    return WarmRuntimeCache(
        WarmRuntimeConfig(
            root=tmp_path / "warm",
            auth_token_sha256=hashlib.sha256(b"secret").hexdigest(),
            ttl_seconds=300,
            max_entries=2,
        )
    )


def test_quick_initialization_cold_path_is_compact_and_ordered(tmp_path: Path) -> None:
    authority = _compiled_reader()
    dynamic = FakeDynamicReader()
    live = FakeLivenessReader()

    result = quick_initialize(
        authority,
        dynamic,
        live,
        warm_cache=_cache(tmp_path),
        warm_auth_token="secret",
    )

    assert result.context is not None
    assert result.receipt.status == "READY"
    assert result.receipt.execution_path == "cold"
    assert result.receipt.provider_writes == 0
    assert result.receipt.google_drive_reads == 0
    assert authority.reads == [
        ("governance/AUTHORITY.json", "HEAD"),
        ("governance/RELEASE_INDEX.md", "HEAD"),
        ("release/RELEASE_MANIFEST_V710.md", "a" * 40),
    ]
    assert dynamic.inventory_references == ["collection://inventory-source"]
    assert live.requests == [frozenset({"Todoist"})]


def test_quick_initialization_warm_path_reads_only_live_authority(tmp_path: Path) -> None:
    authority = _compiled_reader()
    dynamic = FakeDynamicReader()
    live = FakeLivenessReader()
    cache = _cache(tmp_path)

    first = quick_initialize(
        authority,
        dynamic,
        live,
        warm_cache=cache,
        warm_auth_token="secret",
    )
    assert first.receipt.execution_path == "cold"
    authority.reads.clear()

    second = quick_initialize(
        authority,
        dynamic,
        live,
        warm_cache=cache,
        warm_auth_token="secret",
    )

    assert second.receipt.status == "READY"
    assert second.receipt.execution_path == "warm"
    assert second.receipt.cache_hit is True
    assert authority.reads == [("governance/AUTHORITY.json", "HEAD")]
    assert second.context == first.context


def test_corrupt_warm_cache_falls_back_to_cold_and_reports_warning(tmp_path: Path) -> None:
    authority = _compiled_reader()
    dynamic = FakeDynamicReader()
    live = FakeLivenessReader()
    cache = _cache(tmp_path)
    quick_initialize(
        authority,
        dynamic,
        live,
        warm_cache=cache,
        warm_auth_token="secret",
    )
    for path in (tmp_path / "warm").glob("*.json"):
        path.write_text("not-json", encoding="utf-8")
    authority.reads.clear()

    result = quick_initialize(
        authority,
        dynamic,
        live,
        warm_cache=cache,
        warm_auth_token="secret",
    )

    assert result.context is not None
    assert result.receipt.status == "READY_WITH_WARNINGS"
    assert result.receipt.execution_path == "warm_fallback_to_cold"
    assert result.receipt.cache_hit is False
    assert "unreadable" in (result.receipt.cache_rejection_reason or "")
    assert authority.reads == [
        ("governance/AUTHORITY.json", "HEAD"),
        ("governance/RELEASE_INDEX.md", "HEAD"),
        ("release/RELEASE_MANIFEST_V710.md", "a" * 40),
    ]


def test_required_connector_failure_returns_blocked_receipt() -> None:
    result = quick_initialize(
        _compiled_reader(),
        FakeDynamicReader(),
        FakeLivenessReader(todoist=False),
    )

    assert result.context is None
    assert result.receipt.status == "INITIALIZATION_BLOCKED"
    assert result.receipt.provider_writes == 0
    assert result.receipt.google_drive_reads == 0
    assert "Todoist" in (result.receipt.blocked_condition or "")


class RejectingCache:
    def __init__(self, reason: str) -> None:
        self.reason = reason

    def get(self, **_: object) -> object:
        raise ValueError(self.reason)

    def put(self, **_: object) -> WrongKindSnapshot:
        return WrongKindSnapshot()


class WrongKindSnapshot:
    kind = "schema"
    payload: dict[str, object] = {}


class WrongKindCache:
    def get(self, **_: object) -> WrongKindSnapshot:
        return WrongKindSnapshot()

    def put(self, **_: object) -> WrongKindSnapshot:
        return WrongKindSnapshot()


def test_expired_cache_uses_silent_cold_fallback() -> None:
    authority = _compiled_reader()
    result = quick_initialize(
        authority,
        FakeDynamicReader(),
        FakeLivenessReader(),
        warm_cache=RejectingCache("warm-runtime snapshot has expired"),
        warm_auth_token="secret",
    )

    assert result.receipt.status == "READY"
    assert result.receipt.execution_path == "warm_fallback_to_cold"
    assert result.receipt.warnings == ()


def test_wrong_cache_kind_falls_back_and_is_reported() -> None:
    result = quick_initialize(
        _compiled_reader(),
        FakeDynamicReader(),
        FakeLivenessReader(),
        warm_cache=WrongKindCache(),
        warm_auth_token="secret",
    )

    assert result.receipt.status == "READY_WITH_WARNINGS"
    assert result.receipt.execution_path == "warm_fallback_to_cold"
    assert "snapshot kind" in (result.receipt.cache_rejection_reason or "")


def test_active_release_change_invalidates_cached_immutable_material(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    quick_initialize(
        _compiled_reader(commit="a" * 40),
        FakeDynamicReader(),
        FakeLivenessReader(),
        warm_cache=cache,
        warm_auth_token="secret",
    )
    changed = _compiled_reader(commit="e" * 40)

    result = quick_initialize(
        changed,
        FakeDynamicReader(),
        FakeLivenessReader(),
        warm_cache=cache,
        warm_auth_token="secret",
    )

    assert result.receipt.execution_path == "warm_fallback_to_cold"
    assert "source digest" in (result.receipt.cache_rejection_reason or "")
    assert changed.reads == [
        ("governance/AUTHORITY.json", "HEAD"),
        ("governance/RELEASE_INDEX.md", "HEAD"),
        ("release/RELEASE_MANIFEST_V710.md", "e" * 40),
    ]


def test_manifest_page_url_remains_compatible_when_no_data_source_marker() -> None:
    authority = _compiled_reader()
    manifest_key = ("release/RELEASE_MANIFEST_V710.md", "a" * 40)
    manifest = (
        "# Atlas ROS v7.1.0\n"
        "Integration Inventory authority: https://app.notion.com/p/inventory\n"
    )
    compiled = compile_authority(
        AuthorityCompilationSpec(
            active=ActiveReleaseSpec(
                version="7.1.0",
                immutable_commit="a" * 40,
                tag="v7.1.0",
                manifest_path=manifest_key[0],
                manifest_url=(
                    "https://github.com/Ryan9876/atlas-ros/blob/"
                    + "a" * 40
                    + "/"
                    + manifest_key[0]
                ),
                manifest_sha256=sha256_digest(manifest),
                release_url="https://github.com/Ryan9876/atlas-ros/releases/tag/v7.1.0",
                source_sha256="b" * 64,
                wheel_sha256="c" * 64,
            ),
            rollback=RollbackReleaseSpec(
                version="7.0.1",
                immutable_commit="d" * 40,
                tag="v7.0.1",
                release_url="https://github.com/Ryan9876/atlas-ros/releases/tag/v7.0.1",
            ),
            notion_system_state_url="https://app.notion.com/p/system-state",
            last_promotion_transaction_id="promotion-v7.1.0",
            last_verified_at="2026-07-28T19:00:00Z",
        )
    )
    authority.values[("governance/AUTHORITY.json", "HEAD")] = compiled.authority_json
    authority.values[("governance/RELEASE_INDEX.md", "HEAD")] = (
        compiled.release_index_markdown
    )
    authority.values[manifest_key] = manifest
    dynamic = FakeDynamicReader()

    result = quick_initialize(authority, dynamic, FakeLivenessReader())

    assert result.receipt.status == "READY"
    assert dynamic.inventory_references == ["https://app.notion.com/p/inventory"]


def test_system_state_disagreement_blocks() -> None:
    dynamic = FakeDynamicReader()
    dynamic.system_state = dynamic.system_state.model_copy(
        update={"active_version": "7.0.1"}
    )

    result = quick_initialize(_compiled_reader(), dynamic, FakeLivenessReader())

    assert result.receipt.status == "INITIALIZATION_BLOCKED"
    assert "System State active release" in (result.receipt.blocked_condition or "")


def test_inventory_requires_exact_production_ready_set() -> None:
    dynamic = FakeDynamicReader()
    github, notion, todoist = dynamic.inventory.integrations
    dynamic.inventory = dynamic.inventory.model_copy(
        update={
            "integrations": (
                github,
                notion,
                todoist.model_copy(update={"lifecycle_status": "contract_only"}),
            )
        }
    )

    result = quick_initialize(_compiled_reader(), dynamic, FakeLivenessReader())

    assert result.receipt.status == "INITIALIZATION_BLOCKED"
    assert "not production: Todoist" in (result.receipt.blocked_condition or "")


def test_receipt_is_compact_and_contains_stage_telemetry() -> None:
    result = quick_initialize(
        _compiled_reader(),
        FakeDynamicReader(),
        FakeLivenessReader(),
    )

    payload = result.receipt.model_dump(mode="json")
    assert payload["provider_writes"] == 0
    assert payload["google_drive_reads"] == 0
    assert payload["required_integrations"] == [
        {"name": "GitHub", "inventory_ready": True, "live_readable": True},
        {"name": "Notion", "inventory_ready": True, "live_readable": True},
        {"name": "Todoist", "inventory_ready": True, "live_readable": True},
    ]
    stages = {item["stage"] for item in payload["stage_timings"]}
    assert {
        "live_authority_read",
        "release_index_read_validation",
        "manifest_read_validation",
        "system_state_read",
        "integration_inventory_read",
        "todoist_liveness_read",
    } <= stages
    assert "release_index_markdown" not in payload
    assert "release_manifest_markdown" not in payload


class ExtraLivenessReader:
    def read_connector_liveness(self, names: frozenset[str]) -> dict[str, bool]:
        assert names == frozenset({"Todoist"})
        return {"Todoist": True, "GitHub": True}


def test_todoist_probe_rejects_extra_connector_results() -> None:
    result = quick_initialize(
        _compiled_reader(),
        FakeDynamicReader(),
        ExtraLivenessReader(),
    )

    assert result.receipt.status == "INITIALIZATION_BLOCKED"
    assert "exactly the Todoist result" in (result.receipt.blocked_condition or "")
