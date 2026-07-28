from __future__ import annotations

import json
from pathlib import PurePosixPath

import pytest

from atlas_ros.kernel.authority import canonical_authority_payload
from atlas_ros.kernel.bootstrap import InitializationError, initialize
from atlas_ros.kernel.digests import sha256_digest


class FakeAuthorityReader:
    def __init__(self, values: dict[tuple[str, str], str]) -> None:
        self.values = values

    def read_text(self, path: PurePosixPath, *, ref: str) -> str:
        return self.values[(path.as_posix(), ref)]


def manifest_text() -> str:
    return (
        "# Atlas ROS v7.0.1\n"
        "Integration Inventory authority: https://app.notion.com/p/inventory"
    )


def authority_payload() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "repository": "Ryan9876/atlas-ros",
        "authority_model_version": "7.0",
        "minimum_compatible_initializer_version": "7.0.1",
        "active_release": {
            "version": "7.0.1",
            "status": "Active",
            "immutable_commit": "a" * 40,
            "tag": "v7.0.1",
            "manifest_path": "release/RELEASE_MANIFEST.md",
            "manifest_url": (
                "https://github.com/Ryan9876/atlas-ros/blob/"
                + "a" * 40
                + "/release/RELEASE_MANIFEST.md"
            ),
            "manifest_sha256": sha256_digest(manifest_text()),
            "release_url": "https://github.com/Ryan9876/atlas-ros/releases/tag/v7.0.1",
            "source_sha256": "b" * 64,
            "wheel_sha256": "c" * 64,
        },
        "immediate_rollback": {
            "version": "6.5.0",
            "immutable_commit": "d" * 40,
            "tag": "v6.5.0",
            "release_url": "https://github.com/Ryan9876/atlas-ros/releases/tag/v6.5.0",
        },
        "notion_system_state_url": "https://app.notion.com/p/3a0b8344ad2c81d1b545d0266b7cd809",
        "integration_inventory_resolution": "active-release-manifest",
        "release_index": {"path": "governance/RELEASE_INDEX.md", "sha256": "e" * 64},
        "last_promotion_transaction_id": "promotion-7.0.1",
        "last_verified_at": "2026-07-28T00:00:00Z",
    }


def expected_index() -> str:
    return (
        "# Atlas ROS Release Index\n\n"
        "This file is generated from governance/AUTHORITY.json; do not edit it directly.\n\n"
        "## Active Release\n\n"
        "- Version: 7.0.1\n"
        "- Status: Active\n"
        + "- Immutable commit: "
        + "a" * 40
        + "\n- Tag: v7.0.1\n"
        "- Manifest: release/RELEASE_MANIFEST.md\n"
        "- Release: https://github.com/Ryan9876/atlas-ros/releases/tag/v7.0.1\n\n"
        "## Immediate Rollback\n\n"
        "- Version: 6.5.0\n"
        + "- Immutable commit: "
        + "d" * 40
        + "\n- Tag: v6.5.0\n"
        "- Release: https://github.com/Ryan9876/atlas-ros/releases/tag/v6.5.0\n"
    )


def reader_for(payload: dict[str, object]) -> FakeAuthorityReader:
    index = expected_index()
    payload["release_index"] = {
        "path": "governance/RELEASE_INDEX.md",
        "sha256": sha256_digest(index),
    }
    payload["integrity"] = {
        "algorithm": "sha256",
        "content_sha256": sha256_digest(canonical_authority_payload(payload)),
    }
    authority_text = json.dumps(payload)
    return FakeAuthorityReader(
        {
            ("governance/AUTHORITY.json", "HEAD"): authority_text,
            ("governance/RELEASE_INDEX.md", "HEAD"): index,
            ("release/RELEASE_MANIFEST.md", "a" * 40): manifest_text(),
        }
    )


def test_initialize_binds_authority_index_manifest_and_inventory() -> None:
    context = initialize(reader_for(authority_payload()))
    assert context.active_version == "7.0.1"
    assert context.integration_inventory_url.endswith("inventory")


def test_initialize_rejects_tampered_generated_index() -> None:
    reader = reader_for(authority_payload())
    reader.values[("governance/RELEASE_INDEX.md", "HEAD")] = "tampered"
    with pytest.raises(InitializationError, match="digest"):
        initialize(reader)


def test_initialize_rejects_tampered_immutable_manifest() -> None:
    reader = reader_for(authority_payload())
    reader.values[("release/RELEASE_MANIFEST.md", "a" * 40)] = "tampered"
    with pytest.raises(InitializationError, match="manifest digest"):
        initialize(reader)
