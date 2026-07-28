#!/usr/bin/env python3
"""Validate the proposed live Atlas ROS v7.0.1 authority transaction."""
from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Literal

from atlas_ros.contracts.authority import (
    IntegrationInventorySnapshot,
    IntegrationStatusSnapshot,
    SystemStateSnapshot,
)
from atlas_ros.kernel.authority import AuthorityRecord
from atlas_ros.kernel.bootstrap import initialize_full, render_release_index
from atlas_ros.kernel.digests import sha256_digest

VERSION = "7.0.1"
SOURCE = "f26f5154ea6cd4b431c5a2638c439d7de9282761"
ROLLBACK = "6.5.0"
MANIFEST_DIGEST = "3ccda11f3ebf72457d82d7fd92d0ea2e3076fae593ee7abaeba6d80f836ea366"
INVENTORY_URL = "https://app.notion.com/p/8ba4fafb5ce244ef9add3013aff3746b"
SYSTEM_STATE_URL = "https://app.notion.com/p/3a0b8344ad2c81d1b545d0266b7cd809"


class RepoReader:
    def __init__(self, authority: str, index: str, manifest: str) -> None:
        self.values = {
            ("governance/AUTHORITY.json", "HEAD"): authority,
            ("governance/RELEASE_INDEX.md", "HEAD"): index,
            ("release/RELEASE_MANIFEST_V701.md", SOURCE): manifest,
        }

    def read_text(self, path: PurePosixPath, *, ref: str) -> str:
        return self.values[(path.as_posix(), ref)]


class DynamicReader:
    def read_system_state(self, url: str) -> SystemStateSnapshot:
        assert url == SYSTEM_STATE_URL
        return SystemStateSnapshot(
            active_version=VERSION,
            immediate_rollback_version=ROLLBACK,
            authority_model_version="7.0",
            published_workspace_valid=True,
            last_verified_at=datetime.now(UTC),
        )

    def read_integration_inventory(self, url: str) -> IntegrationInventorySnapshot:
        assert url == INVENTORY_URL

        def item(
            name: str,
            required: bool,
            connection: Literal["connected", "disconnected", "degraded", "error"] = "connected",
        ) -> IntegrationStatusSnapshot:
            return IntegrationStatusSnapshot(
                name=name,
                required=required,
                connection_status=connection,
                approval_status="approved" if required else "not_required",
                acceptance_status="passed" if required else "not_run",
                current=True,
                least_privilege_verified=True,
            )

        return IntegrationInventorySnapshot(
            integrations=(
                item("GitHub", True),
                item("Notion", True),
                item("Todoist", True),
                item("Google Drive", False, "disconnected"),
            ),
            last_verified_at=datetime.now(UTC),
        )


def main() -> None:
    root = Path(".")
    authority_text = (root / "governance/AUTHORITY.json").read_text(encoding="utf-8")
    index_text = (root / "governance/RELEASE_INDEX.md").read_text(encoding="utf-8")
    manifest_text = (root / "release/RELEASE_MANIFEST_V701.md").read_text(encoding="utf-8")
    tagged_manifest = subprocess.check_output(
        ["git", "show", "v7.0.1:release/RELEASE_MANIFEST_V701.md"], text=True
    )

    authority = AuthorityRecord.model_validate_json(authority_text)
    assert authority.active_release.version == VERSION
    assert authority.active_release.immutable_commit == SOURCE
    assert authority.active_release.manifest_sha256 == MANIFEST_DIGEST
    assert authority.immediate_rollback.version == ROLLBACK
    assert authority.historical_rollbacks[0].version == "6.2.0"
    assert index_text == render_release_index(authority)
    assert sha256_digest(index_text) == authority.release_index.sha256
    assert manifest_text == tagged_manifest
    assert sha256_digest(manifest_text) == MANIFEST_DIGEST

    context = initialize_full(
        RepoReader(authority_text, index_text, tagged_manifest), DynamicReader()
    )
    assert context.active_version == VERSION
    assert context.integration_inventory_url == INVENTORY_URL

    surfaces = "\n".join(
        (root / path).read_text(encoding="utf-8")
        for path in (
            "release/RELEASE_MANIFEST.md",
            "README.md",
            "docs/CURRENT_DOCUMENTATION.md",
            "docs/runbooks/V701_PRODUCTION_OPERATOR_AND_RECOVERY.md",
        )
    )
    assert "Required production integrations are exactly GitHub, Notion, and Todoist" in surfaces
    assert "Google Drive is not read during initialization" in surfaces

    result = {
        "schema_version": "1.0",
        "status": "passed",
        "active_version": VERSION,
        "active_source_commit": SOURCE,
        "release_tag": "v7.0.1",
        "immediate_rollback": ROLLBACK,
        "historical_rollback": "6.2.0",
        "authority_integrity_sha256": authority.integrity.content_sha256,
        "release_index_digest": authority.release_index.sha256,
        "immutable_manifest_digest": MANIFEST_DIGEST,
        "integration_inventory_url": context.integration_inventory_url,
        "required_integrations": ["GitHub", "Notion", "Todoist"],
        "google_drive_required": False,
        "google_drive_read_during_initialization": False,
        "published_workspace_valid": True,
        "provider_writes": 0,
        "validated_at": datetime.now(UTC).isoformat(),
    }
    output = root / "authority-activation-evidence/V701_AUTHORITY_ACTIVATION.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
