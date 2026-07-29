#!/usr/bin/env python3
"""Assemble one exact, non-publishing Atlas ROS v7.3.0 promotion-review package."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

VERSION = "7.3.0"
ACTIVE_VERSION = "7.1.1"
ACTIVE_COMMIT = "7e18113b58fcd486b5c7e8eb9368c7c70bc83bcd"
ROLLBACK_VERSION = "7.1.0"
ROLLBACK_COMMIT = "0711b045f34f5ab7b03f7a61bc80653e0d815463"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def assemble(
    *,
    repository_root: Path,
    package_root: Path,
    source_commit: str,
    source_timestamp: str,
    installed_packages_path: Path,
    performance_path: Path,
    migration_receipt_path: Path,
    validation_summary_path: Path,
) -> dict[str, Any]:
    if len(source_commit) != 40:
        raise ValueError("source commit must be an exact 40-character commit SHA")
    datetime.fromisoformat(source_timestamp.replace("Z", "+00:00"))
    source = package_root / f"atlas_ros-{VERSION}.tar.gz"
    wheel = package_root / f"atlas_ros-{VERSION}-py3-none-any.whl"
    required = (
        source,
        wheel,
        installed_packages_path,
        performance_path,
        migration_receipt_path,
        validation_summary_path,
        repository_root / "release/RELEASE_MANIFEST_V730_CANDIDATE.md",
        repository_root / "release/v730-notion-schema-migration.yaml",
    )
    for path in required:
        if not path.is_file():
            raise ValueError(f"required package input is missing: {path}")
    installed = json.loads(installed_packages_path.read_text(encoding="utf-8"))
    performance = json.loads(performance_path.read_text(encoding="utf-8"))
    migration = json.loads(migration_receipt_path.read_text(encoding="utf-8"))
    validation = json.loads(validation_summary_path.read_text(encoding="utf-8"))
    if performance.get("status") != "passed" or performance.get("provider_writes") != 0:
        raise ValueError("performance evidence is not passing and zero-write")
    if migration.get("status") != "validated_unapplied" or migration.get("live_writes") != 0:
        raise ValueError("Notion migration evidence is not validated and unapplied")
    if validation.get("status") != "passed" or validation.get("provider_writes") != 0:
        raise ValueError("validation summary is not passing and zero-write")

    source_sha = _sha256(source)
    wheel_sha = _sha256(wheel)
    source_manifest = {
        "schema_version": "1.0",
        "package_name": "atlas-ros",
        "release_version": VERSION,
        "source_commit": source_commit,
        "source_timestamp": source_timestamp,
        "sdist_file": source.name,
        "sdist_sha256": source_sha,
        "wheel_file": wheel.name,
        "wheel_sha256": wheel_sha,
        "active_production_version": ACTIVE_VERSION,
        "active_production_commit": ACTIVE_COMMIT,
        "immediate_rollback_version": ROLLBACK_VERSION,
        "immediate_rollback_commit": ROLLBACK_COMMIT,
        "required_integrations": ["GitHub", "Notion", "Todoist"],
        "provider_writes": 0,
        "build_count": 1,
        "production_authorized": False,
        "published": False,
        "authority_activated": False,
    }
    _write_json(package_root / "SOURCE_MANIFEST_FINAL.json", source_manifest)

    packages = []
    for index, package in enumerate(sorted(installed, key=lambda item: item["name"].lower()), 1):
        packages.append(
            {
                "SPDXID": f"SPDXRef-Package-{index}",
                "name": package["name"],
                "versionInfo": package["version"],
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
                "licenseConcluded": "NOASSERTION",
                "licenseDeclared": "NOASSERTION",
                "copyrightText": "NOASSERTION",
            }
        )
    sbom = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"atlas-ros-{VERSION}",
        "documentNamespace": f"https://github.com/Ryan9876/atlas-ros/candidate/{source_commit}",
        "creationInfo": {
            "created": source_timestamp,
            "creators": ["Tool: Atlas ROS v7.3.0 non-publishing package assembler"],
        },
        "packages": packages,
    }
    _write_json(package_root / "SBOM.spdx.json", sbom)

    manifest_payload = {
        "schema_version": "1.0",
        "status": "candidate_validated_not_authorized",
        "release_version": VERSION,
        "source_commit": source_commit,
        "source_sha256": source_sha,
        "wheel_sha256": wheel_sha,
        "active_production": {"version": ACTIVE_VERSION, "commit": ACTIVE_COMMIT},
        "immediate_rollback": {"version": ROLLBACK_VERSION, "commit": ROLLBACK_COMMIT},
        "required_integrations": ["GitHub", "Notion", "Todoist"],
        "google_drive_required": False,
        "notion_migration_applied": False,
        "provider_writes": 0,
        "build_count": 1,
        "promotion_authorized": False,
        "published": False,
        "authority_activated": False,
    }
    manifest_payload["manifest_digest"] = _canonical_digest(manifest_payload)
    _write_json(package_root / "RELEASE_MANIFEST_V730_CANDIDATE.json", manifest_payload)

    identity = {
        "schema_version": "1.0",
        "status": "implementation_ready_for_ryan_promotion_review",
        "release_version": VERSION,
        "candidate_commit": source_commit,
        "source_sha256": source_sha,
        "wheel_sha256": wheel_sha,
        "manifest_digest": manifest_payload["manifest_digest"],
        "source_manifest_sha256": _sha256(package_root / "SOURCE_MANIFEST_FINAL.json"),
        "sbom_sha256": _sha256(package_root / "SBOM.spdx.json"),
        "performance_evidence_sha256": _sha256(performance_path),
        "migration_evidence_sha256": _sha256(migration_receipt_path),
        "validation_summary_sha256": _sha256(validation_summary_path),
        "provider_writes": 0,
        "build_count": 1,
        "production_promotion_authorized": False,
        "final_tag_created": False,
        "final_release_published": False,
        "authority_activated": False,
        "production_notion_schema_changed": False,
        "todoist_tasks_created": 0,
        "messages_sent": 0,
        "scheduled_operations": 0,
        "records_deleted": 0,
        "credentials_changed": False,
        "integration_scope_expanded": False,
    }
    identity["identity_digest"] = _canonical_digest(identity)
    _write_json(package_root / "FINAL_PACKAGE_IDENTITY.json", identity)
    _write_json(
        package_root / "PROMOTION_INPUTS.json",
        {
            "schema_version": "1.0",
            "candidate_commit": source_commit,
            "release_version": VERSION,
            "source_sha256": source_sha,
            "wheel_sha256": wheel_sha,
            "manifest_digest": manifest_payload["manifest_digest"],
            "requires_new_exact_package_authorization": True,
            "promotion_authorized": False,
        },
    )
    return identity


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    parser.add_argument("--package-root", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--source-timestamp", required=True)
    parser.add_argument("--installed-packages", type=Path, required=True)
    parser.add_argument("--performance", type=Path, required=True)
    parser.add_argument("--migration-receipt", type=Path, required=True)
    parser.add_argument("--validation-summary", type=Path, required=True)
    args = parser.parse_args()
    identity = assemble(
        repository_root=args.repository_root.resolve(),
        package_root=args.package_root.resolve(),
        source_commit=args.source_commit,
        source_timestamp=args.source_timestamp,
        installed_packages_path=args.installed_packages.resolve(),
        performance_path=args.performance.resolve(),
        migration_receipt_path=args.migration_receipt.resolve(),
        validation_summary_path=args.validation_summary.resolve(),
    )
    print(json.dumps(identity, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
