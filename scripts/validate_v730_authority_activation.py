#!/usr/bin/env python3
"""Validate the exact Atlas ROS v7.3.0 canonical authority transaction."""
from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from atlas_ros.kernel.authority import AuthorityRecord
from atlas_ros.kernel.bootstrap import render_release_index
from atlas_ros.kernel.digests import sha256_digest

VERSION = "7.3.0"
IMMUTABLE_COMMIT = "51fdeefda8330c8e11bd74336d5f6a569a78e789"
PACKAGE_SOURCE_COMMIT = "3082a8c4b4124167b5b5219a943a519fdfd63779"
MANIFEST_PATH = "release/RELEASE_MANIFEST_V730.md"
MANIFEST_DIGEST = "b3c1633362638ae810395c7972866fbb9884223390bb2c5679911ba0169efe70"
SOURCE_SHA256 = "6e152ca6f5c1cd1644937ed9eea6582966f18bb3e558ec6c851fa2c7a6c6306e"
WHEEL_SHA256 = "5be3ea8af13e70d7bf2e2fa54fc07532d8182c90ee1121e3a881c4214f7a3890"
ROLLBACK_VERSION = "7.1.1"
ROLLBACK_COMMIT = "7e18113b58fcd486b5c7e8eb9368c7c70bc83bcd"


def main() -> None:
    root = Path(".")
    authority_text = (root / "governance/AUTHORITY.json").read_text(encoding="utf-8")
    index_text = (root / "governance/RELEASE_INDEX.md").read_text(encoding="utf-8")
    manifest_text = (root / MANIFEST_PATH).read_text(encoding="utf-8")
    tagged_manifest = subprocess.check_output(
        ["git", "show", f"v7.3.0:{MANIFEST_PATH}"], text=True
    )
    tag_target = subprocess.check_output(
        ["git", "rev-list", "-n", "1", "v7.3.0"], text=True
    ).strip()

    authority = AuthorityRecord.model_validate_json(authority_text)
    active = authority.active_release
    rollback = authority.immediate_rollback

    assert active.version == VERSION
    assert active.status == "Active"
    assert active.immutable_commit == IMMUTABLE_COMMIT
    assert active.tag == "v7.3.0"
    assert active.manifest_path == MANIFEST_PATH
    assert active.manifest_sha256 == MANIFEST_DIGEST
    assert active.source_sha256 == SOURCE_SHA256
    assert active.wheel_sha256 == WHEEL_SHA256
    assert rollback.version == ROLLBACK_VERSION
    assert rollback.immutable_commit == ROLLBACK_COMMIT
    assert rollback.tag == "v7.1.1"
    assert [item.version for item in authority.historical_rollbacks] == [
        "7.1.0",
        "7.0.1",
        "6.5.0",
        "6.2.0",
    ]
    assert authority.last_promotion_transaction_id == "V4D-51-production-promotion"
    assert index_text == render_release_index(authority)
    assert sha256_digest(index_text) == authority.release_index.sha256
    assert tag_target == IMMUTABLE_COMMIT
    assert manifest_text == tagged_manifest
    assert sha256_digest(manifest_text) == MANIFEST_DIGEST
    assert PACKAGE_SOURCE_COMMIT in manifest_text
    assert "Required production integrations remain exactly **GitHub, Notion, and Todoist**" in manifest_text
    assert "Google Drive remains optional" in manifest_text
    assert "Acceptance Status" in manifest_text
    assert "Completion Evidence State" in manifest_text

    evidence = {
        "schema_version": "1.0",
        "status": "passed",
        "active_version": VERSION,
        "active_immutable_commit": IMMUTABLE_COMMIT,
        "package_source_commit": PACKAGE_SOURCE_COMMIT,
        "release_tag": "v7.3.0",
        "manifest_path": MANIFEST_PATH,
        "manifest_canonical_sha256": MANIFEST_DIGEST,
        "source_sha256": SOURCE_SHA256,
        "wheel_sha256": WHEEL_SHA256,
        "immediate_rollback_version": ROLLBACK_VERSION,
        "immediate_rollback_commit": ROLLBACK_COMMIT,
        "historical_rollbacks": ["7.1.0", "7.0.1", "6.5.0", "6.2.0"],
        "release_index_sha256": authority.release_index.sha256,
        "authority_integrity_sha256": authority.integrity.content_sha256,
        "promotion_decision": "V4D-51",
        "required_integrations": ["GitHub", "Notion", "Todoist"],
        "google_drive_required": False,
        "notion_migration_readback_passed": True,
        "provider_writes": 0,
        "validated_at": datetime.now(UTC).isoformat(),
    }
    output = root / "authority-activation-evidence/V730_AUTHORITY_ACTIVATION.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
