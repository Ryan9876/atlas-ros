from __future__ import annotations

from dataclasses import dataclass

import pytest

from atlas_ros.application.canonical_processing import CanonicalProcessingCoordinator
from atlas_ros.contracts.execution.pipeline import CaptureEnvelope
from atlas_ros.kernel.authority import AuthorityRecord
from atlas_ros.kernel.digests import sha256_digest


@dataclass(frozen=True)
class UppercaseStage:
    name: str = "normalization"

    def process(self, value: CaptureEnvelope) -> str:
        return value.content.upper()


def test_canonical_coordinator_records_stage_lineage() -> None:
    coordinator = CanonicalProcessingCoordinator(
        release_version="7.0.0",
        source_commit="a" * 40,
        initializer_version="7.0",
        contract_catalog_digest="b" * 64,
        policy_registry_digest="c" * 64,
        capability_catalog_digest="d" * 64,
        stages=(UppercaseStage(),),
    )
    result, lineage = coordinator.process(CaptureEnvelope(source="test", content="hello"))

    assert result == "HELLO"
    assert lineage.stage_digests["normalization"] == sha256_digest("HELLO")
    assert lineage.execution_transaction_id is None


def test_authority_record_rejects_tampered_integrity() -> None:
    payload = {
        "schema_version": "1.0",
        "repository": "Ryan9876/atlas-ros",
        "authority_model_version": "7.0",
        "minimum_compatible_initializer_version": "7.0",
        "active_release": {
            "version": "7.0.0",
            "status": "Active",
            "immutable_commit": "a" * 40,
            "tag": "v7.0.0",
            "manifest_path": "release/RELEASE_MANIFEST.md",
            "manifest_url": "https://github.com/Ryan9876/atlas-ros/blob/v7.0.0/release/RELEASE_MANIFEST.md",
            "release_url": "https://github.com/Ryan9876/atlas-ros/releases/tag/v7.0.0",
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
        "last_promotion_transaction_id": "candidate",
        "last_verified_at": "2026-07-27T00:00:00Z",
    }
    payload["integrity"] = {"algorithm": "sha256", "content_sha256": sha256_digest(payload)}

    assert AuthorityRecord.model_validate(payload).active_release.version == "7.0.0"
    payload["active_release"]["tag"] = "v7.0.1"
    with pytest.raises(ValueError, match="integrity"):
        AuthorityRecord.model_validate(payload)
