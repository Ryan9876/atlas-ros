from __future__ import annotations

from datetime import UTC, datetime
from pathlib import PurePosixPath

import pytest

from atlas_ros.contracts.authority import (
    IntegrationInventorySnapshot,
    IntegrationStatusSnapshot,
    SystemStateSnapshot,
)
from atlas_ros.kernel.bootstrap import InitializationError, initialize_full
from atlas_ros.kernel.digests import sha256_digest
from tools.release.authority_compiler import (
    ActiveReleaseSpec,
    AuthorityCompilationSpec,
    RollbackReleaseSpec,
    compile_authority,
)


class FakeAuthorityReader:
    def __init__(self, values: dict[tuple[str, str], str]) -> None:
        self.values = values

    def read_text(self, path: PurePosixPath, *, ref: str) -> str:
        return self.values[(path.as_posix(), ref)]


class FakeDynamicReader:
    def __init__(
        self,
        system_state: SystemStateSnapshot,
        inventory: IntegrationInventorySnapshot,
    ) -> None:
        self.system_state = system_state
        self.inventory = inventory

    def read_system_state(self, url: str) -> SystemStateSnapshot:
        assert url.endswith("3a0b8344ad2c81d1b545d0266b7cd809")
        return self.system_state

    def read_integration_inventory(self, url: str) -> IntegrationInventorySnapshot:
        assert url.endswith("inventory")
        return self.inventory


def compiled_reader() -> FakeAuthorityReader:
    active_commit = "a" * 40
    manifest = (
        "# Atlas ROS v7.0.1\n"
        "Integration Inventory authority: https://app.notion.com/p/inventory"
    )
    compiled = compile_authority(
        AuthorityCompilationSpec(
            active=ActiveReleaseSpec(
                version="7.0.1",
                immutable_commit=active_commit,
                tag="v7.0.1",
                manifest_url=(
                    f"https://github.com/Ryan9876/atlas-ros/blob/{active_commit}/"
                    "release/RELEASE_MANIFEST.md"
                ),
                manifest_sha256=sha256_digest(manifest),
                release_url="https://github.com/Ryan9876/atlas-ros/releases/tag/v7.0.1",
                source_sha256="b" * 64,
                wheel_sha256="c" * 64,
            ),
            rollback=RollbackReleaseSpec(
                version="6.5.0",
                immutable_commit="d" * 40,
                tag="v6.5.0",
                release_url="https://github.com/Ryan9876/atlas-ros/releases/tag/v6.5.0",
            ),
            notion_system_state_url=(
                "https://app.notion.com/p/3a0b8344ad2c81d1b545d0266b7cd809"
            ),
            last_promotion_transaction_id="promotion-v7.0.1-001",
            last_verified_at="2026-07-28T19:00:00Z",
        )
    )
    return FakeAuthorityReader(
        {
            ("governance/AUTHORITY.json", "HEAD"): compiled.authority_json,
            ("governance/RELEASE_INDEX.md", "HEAD"): (
                compiled.release_index_markdown
            ),
            ("release/RELEASE_MANIFEST.md", active_commit): manifest,
        }
    )


def system_state() -> SystemStateSnapshot:
    return SystemStateSnapshot(
        active_version="7.0.1",
        immediate_rollback_version="6.5.0",
        authority_model_version="7.0",
        published_workspace_valid=True,
        last_verified_at=datetime.now(UTC),
    )


def integration(
    name: str,
    *,
    required: bool = True,
    connection_status: str = "connected",
) -> IntegrationStatusSnapshot:
    return IntegrationStatusSnapshot.model_validate(
        {
            "name": name,
            "required": required,
            "connection_status": connection_status,
            "approval_status": "approved",
            "acceptance_status": "passed",
            "current": True,
            "least_privilege_verified": True,
        }
    )


def inventory(*items: IntegrationStatusSnapshot) -> IntegrationInventorySnapshot:
    return IntegrationInventorySnapshot(
        integrations=items,
        last_verified_at=datetime.now(UTC),
    )


def test_full_initialization_requires_github_notion_and_todoist_to_agree() -> None:
    dynamic = FakeDynamicReader(
        system_state(),
        inventory(
            integration("GitHub"),
            integration("Notion"),
            integration("Todoist"),
            integration("Google Drive", required=False),
        ),
    )

    context = initialize_full(compiled_reader(), dynamic)

    assert context.active_version == "7.0.1"


def test_full_initialization_rejects_drive_as_required_authority() -> None:
    dynamic = FakeDynamicReader(
        system_state(),
        inventory(
            integration("Google Drive"),
            integration("Notion"),
            integration("Todoist"),
        ),
    )

    with pytest.raises(InitializationError, match="GitHub, Notion, and Todoist"):
        initialize_full(compiled_reader(), dynamic)


def test_full_initialization_rejects_degraded_required_integration() -> None:
    dynamic = FakeDynamicReader(
        system_state(),
        inventory(
            integration("GitHub", connection_status="degraded"),
            integration("Notion"),
            integration("Todoist"),
        ),
    )

    with pytest.raises(InitializationError, match="not connected: GitHub"):
        initialize_full(compiled_reader(), dynamic)
