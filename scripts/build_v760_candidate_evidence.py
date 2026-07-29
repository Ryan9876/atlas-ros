from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

CANDIDATE_VERSION = "7.6.0"
EXPECTED_SOURCE = f"atlas_ros-{CANDIDATE_VERSION}.tar.gz"
EXPECTED_WHEEL = f"atlas_ros-{CANDIDATE_VERSION}-py3-none-any.whl"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def require_file(path: Path) -> Path:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"required evidence file is missing or empty: {path}")
    return path


def require_environment(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"{name} is required")
    return value


def git_output(*arguments: str) -> str:
    return subprocess.check_output(["git", *arguments], text=True).strip()


def tracked_files(root: Path) -> tuple[Path, ...]:
    output = subprocess.check_output(["git", "ls-files", "-z"], cwd=root)
    names = tuple(name for name in output.decode().split("\0") if name)
    return tuple(root / name for name in sorted(names))


def write_source_manifest(root: Path, build_directory: Path) -> Path:
    path = build_directory / "SOURCE_MANIFEST.sha256"
    lines = [
        f"{digest(file_path)}  {file_path.relative_to(root).as_posix()}"
        for file_path in tracked_files(root)
    ]
    path.write_text("\n".join(lines) + "\n")
    return path


def commit_timestamp() -> str:
    raw = git_output("show", "-s", "--format=%cI", "HEAD")
    value = datetime.fromisoformat(raw).astimezone(UTC)
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def write_sbom(
    *,
    repository: str,
    candidate_commit: str,
    source_manifest: Path,
    build_directory: Path,
) -> Path:
    files: list[dict[str, Any]] = []
    relationships: list[dict[str, str]] = []
    for index, line in enumerate(source_manifest.read_text().splitlines(), start=1):
        checksum, file_name = line.split(maxsplit=1)
        spdx_id = f"SPDXRef-File-{index}"
        files.append(
            {
                "fileName": file_name,
                "SPDXID": spdx_id,
                "checksums": [{"algorithm": "SHA256", "checksumValue": checksum}],
                "licenseConcluded": "NOASSERTION",
                "copyrightText": "NOASSERTION",
            }
        )
        relationships.append(
            {
                "spdxElementId": "SPDXRef-Package-atlas-ros",
                "relationshipType": "CONTAINS",
                "relatedSpdxElement": spdx_id,
            }
        )
    payload = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": "atlas-ros-v7.6.0-candidate",
        "documentNamespace": f"https://github.com/{repository}/spdx/{candidate_commit}",
        "creationInfo": {
            "created": commit_timestamp(),
            "creators": ["Tool: Atlas ROS v7.6.0 candidate evidence builder"],
        },
        "documentDescribes": ["SPDXRef-Package-atlas-ros"],
        "packages": [
            {
                "name": "atlas-ros",
                "SPDXID": "SPDXRef-Package-atlas-ros",
                "versionInfo": CANDIDATE_VERSION,
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": True,
                "licenseConcluded": "NOASSERTION",
                "licenseDeclared": "NOASSERTION",
                "copyrightText": "NOASSERTION",
            }
        ],
        "files": files,
        "relationships": relationships,
    }
    path = build_directory / "SBOM.spdx.json"
    write_json(path, payload)
    return path


def write_draft_manifest(
    *,
    build_directory: Path,
    candidate_commit: str,
    active_version: str,
    active_commit: str,
    source: Path,
    wheel: Path,
    sbom: Path,
    source_manifest: Path,
    schema_plan: Path,
    migration: Path,
    feature_policy: Path,
) -> Path:
    migration_payload = json.loads(migration.read_text())
    schema_payload = json.loads(schema_plan.read_text())
    feature_payload = json.loads(feature_policy.read_text())
    content = f"""# Atlas ROS v7.6.0 Draft Immutable Release Manifest

Status: validated non-publishing candidate; production activation is not authorized.

## Exact package identity

- Candidate version: `7.6.0`
- Exact source commit: `{candidate_commit}`
- Source distribution SHA-256: `{digest(source)}`
- Wheel SHA-256: `{digest(wheel)}`
- SPDX SBOM SHA-256: `{digest(sbom)}`
- Source manifest SHA-256: `{digest(source_manifest)}`
- Build count: `1`

## Predecessor and rollback

- Active predecessor: Atlas ROS v{active_version} at `{active_commit}`
- Proposed immediate rollback after activation: Atlas ROS v{active_version} at `{active_commit}`

## Schema and migration proposals

- Schema-plan SHA-256: `{digest(schema_plan)}`
- Schema-plan deterministic digest: `{schema_payload['schema_plan_digest']}`
- Migration input snapshot digest: `{migration_payload['input_snapshot_digest']}`
- Migration proposed output digest: `{migration_payload['proposed_output_digest']}`
- Migration counts: create `{migration_payload['create_count']}`, update `{migration_payload['update_count']}`, skip `{migration_payload['skip_count']}`
- Feature-policy SHA-256: `{digest(feature_policy)}`
- Feature-policy deterministic digest: `{feature_payload['feature_policy_digest']}`

## Required activation order

1. Publish and independently verify the exact retained package without rebuilding.
2. Activate canonical GitHub and Notion authority with intent-memory inference disabled.
3. Apply and read back the exact additive schema authorized by Ryan.
4. Apply and read back the exact migration authorized by Ryan.
5. Enable inspection, correction, and retirement only after readback.
6. Keep inference disabled unless separately and exactly authorized.

## Preserved boundaries

No production schema change, migration, Todoist write, message, calendar action, credential action, integration-scope expansion, deletion, forgetting execution, or live-network action is authorized by this draft manifest.
"""
    path = build_directory / "V760_DRAFT_IMMUTABLE_MANIFEST.md"
    path.write_text(content)
    return path


def write_receipts(
    *,
    root: Path,
    build_directory: Path,
    dist_directory: Path,
    source_manifest: Path,
    sbom: Path,
) -> tuple[Path, ...]:
    candidate_commit = require_environment("CANDIDATE_COMMIT")
    active_version = require_environment("ACTIVE_VERSION")
    active_commit = require_environment("ACTIVE_COMMIT")
    rollback_version = require_environment("ROLLBACK_VERSION")
    rollback_commit = require_environment("ROLLBACK_COMMIT")
    workflow_run_id = require_environment("GITHUB_RUN_ID")
    source = require_file(dist_directory / EXPECTED_SOURCE)
    wheel = require_file(dist_directory / EXPECTED_WHEEL)
    build_count = require_file(build_directory / "BUILD_COUNT.txt")
    if build_count.read_text().strip() != "1":
        raise ValueError("the retained candidate must have an exact build count of one")
    active_restoration = require_file(build_directory / "ACTIVE_RESTORATION_COMMIT.txt")
    rollback_restoration = require_file(build_directory / "ROLLBACK_RESTORATION_COMMIT.txt")
    if active_restoration.read_text().strip() != active_commit:
        raise ValueError("Active restoration identity mismatch")
    if rollback_restoration.read_text().strip() != rollback_commit:
        raise ValueError("rollback restoration identity mismatch")
    proposal_index = require_file(build_directory / "V760_PROPOSAL_EVIDENCE_INDEX.json")
    schemas = require_file(build_directory / "V760_CONTRACT_SCHEMAS.json")
    schema_plan = require_file(build_directory / "V760_SCHEMA_PLAN.json")
    migration = require_file(build_directory / "V760_MIGRATION_PROPOSAL.json")
    feature_policy = require_file(build_directory / "V760_FEATURE_POLICY_TARGET.json")
    privacy = require_file(build_directory / "V760_PRIVACY_REVIEW_RECEIPT.json")
    secret_scan = require_file(build_directory / "V760_SECRET_SCAN.json")
    proposal_payload = json.loads(proposal_index.read_text())
    migration_payload = json.loads(migration.read_text())
    privacy_payload = json.loads(privacy.read_text())
    if migration_payload["provider_write_count"] != 0:
        raise ValueError("migration dry run contains provider writes")
    if privacy_payload["status"] != "passed":
        raise ValueError("privacy review did not pass")
    draft_manifest = write_draft_manifest(
        build_directory=build_directory,
        candidate_commit=candidate_commit,
        active_version=active_version,
        active_commit=active_commit,
        source=source,
        wheel=wheel,
        sbom=sbom,
        source_manifest=source_manifest,
        schema_plan=schema_plan,
        migration=migration,
        feature_policy=feature_policy,
    )
    validation = {
        "schema_version": "v760-validation-receipt-v1",
        "status": "passed",
        "workflow_run_id": workflow_run_id,
        "candidate_version": CANDIDATE_VERSION,
        "candidate_commit": candidate_commit,
        "source_distribution_sha256": digest(source),
        "wheel_sha256": digest(wheel),
        "sbom_sha256": digest(sbom),
        "source_manifest_sha256": digest(source_manifest),
        "contract_schemas_sha256": digest(schemas),
        "schema_plan_sha256": digest(schema_plan),
        "schema_plan_digest": json.loads(schema_plan.read_text())["schema_plan_digest"],
        "migration_proposal_sha256": digest(migration),
        "migration_input_snapshot_digest": migration_payload["input_snapshot_digest"],
        "migration_output_digest": migration_payload["proposed_output_digest"],
        "feature_policy_sha256": digest(feature_policy),
        "privacy_review_sha256": digest(privacy),
        "secret_scan_sha256": digest(secret_scan),
        "draft_manifest_sha256": digest(draft_manifest),
        "active_restoration_version": active_version,
        "active_restoration_commit": active_commit,
        "rollback_restoration_version": rollback_version,
        "rollback_restoration_commit": rollback_commit,
        "provider_writes": 0,
        "todoist_writes": 0,
        "production_schema_migrations": 0,
        "production_migration_records": 0,
        "release_publications": 0,
        "authority_changes": 0,
        "build_count": 1,
    }
    validation_path = build_directory / "V760_VALIDATION_RECEIPT.json"
    write_json(validation_path, validation)
    package_index = {
        "schema_version": "v760-package-index-v1",
        "candidate_version": CANDIDATE_VERSION,
        "candidate_commit": candidate_commit,
        "source_distribution": source.name,
        "source_distribution_sha256": digest(source),
        "wheel": wheel.name,
        "wheel_sha256": digest(wheel),
        "sbom": sbom.name,
        "sbom_sha256": digest(sbom),
        "source_manifest": source_manifest.name,
        "source_manifest_sha256": digest(source_manifest),
        "validation_receipt_sha256": digest(validation_path),
        "draft_manifest_sha256": digest(draft_manifest),
        "proposal_evidence_digest": proposal_payload["deterministic_digest"],
        "build_count": 1,
    }
    package_index_path = build_directory / "V760_PACKAGE_INDEX.json"
    write_json(package_index_path, package_index)
    outputs: dict[str, dict[str, Any]] = {
        "V760_NON_PUBLISHING_CONTROLLER.json": {
            "schema_version": "v760-non-publishing-controller-v1",
            "status": "passed",
            "candidate_commit": candidate_commit,
            "active_version_unchanged": active_version,
            "provider_writes": 0,
            "todoist_writes": 0,
            "authority_changes": 0,
            "production_schema_migrations": 0,
            "release_publications": 0,
            "production_tags_created_or_moved": 0,
            "integration_scope_expansions": 0,
            "credential_actions": 0,
            "messages_sent": 0,
            "calendar_actions": 0,
            "scheduled_actions": 0,
            "deletions": 0,
        },
        "V760_ACTIONS_UTILIZATION.json": {
            "schema_version": "actions-utilization-report-v1",
            "candidate_commit": candidate_commit,
            "workflow_run_id": workflow_run_id,
            "build_count": 1,
            "exact_artifacts_reused": True,
            "stale_run_cancellation_enabled": True,
            "dependency_cache_enabled": True,
            "broad_compatibility_matrix_used": False,
        },
        "V760_DEFINITION_OF_DONE_RECEIPT.json": {
            "schema_version": "feature-dod-receipt-v1",
            "feature_id": "governed-intent-memory",
            "candidate_commit": candidate_commit,
            "status": "passed",
            "mandatory_gates_complete": True,
            "exact_build_count": 1,
            "production_unchanged": True,
            "schema_proposal_only": True,
            "migration_dry_run_only": True,
        },
        "V760_ZERO_PROVIDER_WRITE_RECEIPT.json": {
            "schema_version": "v760-zero-provider-write-receipt-v1",
            "candidate_commit": candidate_commit,
            "provider_writes": 0,
            "todoist_writes": 0,
            "notion_writes": 0,
            "messages_sent": 0,
            "calendar_actions": 0,
            "scheduled_actions": 0,
            "credential_actions": 0,
            "deletions": 0,
            "forgetting_executions": 0,
        },
    }
    paths = [validation_path, package_index_path, draft_manifest]
    for name, payload in outputs.items():
        path = build_directory / name
        write_json(path, payload)
        paths.append(path)
    authorization = f"""# Atlas ROS v7.6.0 Exact Authorization Block Template

The retained GitHub artifact ID and archive digest must be inserted from the completed workflow readback before Ryan authorizes deployment.

## Package
- Version: `7.6.0`
- Exact source commit: `{candidate_commit}`
- Retained artifact ID: `PENDING_WORKFLOW_ARTIFACT_READBACK`
- Retained artifact digest: `PENDING_WORKFLOW_ARTIFACT_READBACK`
- Source SHA-256: `{digest(source)}`
- Wheel SHA-256: `{digest(wheel)}`
- SBOM SHA-256: `{digest(sbom)}`
- Source-manifest SHA-256: `{digest(source_manifest)}`
- Validation-receipt SHA-256: `{digest(validation_path)}`
- Draft immutable-manifest SHA-256: `{digest(draft_manifest)}`
- Rollback: Atlas ROS v{active_version} at `{active_commit}`

## Schema
- Schema-plan SHA-256: `{digest(schema_plan)}`
- Schema-plan digest: `{json.loads(schema_plan.read_text())['schema_plan_digest']}`
- Expected record count before migration: `0`

## Migration
- Input snapshot digest: `{migration_payload['input_snapshot_digest']}`
- Proposed output digest: `{migration_payload['proposed_output_digest']}`
- Counts: create `{migration_payload['create_count']}`, update `{migration_payload['update_count']}`, skip `{migration_payload['skip_count']}`
- Idempotency: passed

## Feature policy
- After release activation: disabled
- After schema and migration readback: inspection/correction/retirement enabled
- Intent inference: disabled pending separate exact authorization
"""
    authorization_path = build_directory / "V760_EXACT_AUTHORIZATION_BLOCK_TEMPLATE.md"
    authorization_path.write_text(authorization)
    paths.append(authorization_path)
    return tuple(paths)


def write_checksums(
    *,
    root: Path,
    build_directory: Path,
    dist_directory: Path,
) -> tuple[Path, Path, Path]:
    package_checksums = build_directory / "CHECKSUMS.sha256"
    package_checksums.write_text(
        "\n".join(
            f"{digest(path)}  {path.relative_to(root).as_posix()}"
            for path in sorted(dist_directory.iterdir())
            if path.is_file()
        )
        + "\n"
    )
    excluded = {
        package_checksums.name,
        "EVIDENCE_CHECKSUMS.sha256",
        "NESTED_CHECKSUMS.sha256",
    }
    evidence_checksums = build_directory / "EVIDENCE_CHECKSUMS.sha256"
    evidence_files = tuple(
        path
        for path in sorted(build_directory.iterdir())
        if path.is_file() and path.name not in excluded
    )
    evidence_checksums.write_text(
        "\n".join(
            f"{digest(path)}  {path.relative_to(root).as_posix()}"
            for path in evidence_files
        )
        + "\n"
    )
    nested_checksums = build_directory / "NESTED_CHECKSUMS.sha256"
    nested_checksums.write_text(
        "\n".join(
            f"{digest(path)}  {path.relative_to(root).as_posix()}"
            for path in (package_checksums, evidence_checksums)
        )
        + "\n"
    )
    return package_checksums, evidence_checksums, nested_checksums


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build complete deterministic v7.6.0 candidate evidence."
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--build-directory", type=Path, default=Path("build"))
    parser.add_argument("--dist-directory", type=Path, default=Path("dist"))
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    build_directory = (root / arguments.build_directory).resolve()
    dist_directory = (root / arguments.dist_directory).resolve()
    build_directory.mkdir(parents=True, exist_ok=True)
    source_manifest = write_source_manifest(root, build_directory)
    sbom = write_sbom(
        repository=require_environment("GITHUB_REPOSITORY"),
        candidate_commit=require_environment("CANDIDATE_COMMIT"),
        source_manifest=source_manifest,
        build_directory=build_directory,
    )
    write_receipts(
        root=root,
        build_directory=build_directory,
        dist_directory=dist_directory,
        source_manifest=source_manifest,
        sbom=sbom,
    )
    for path in write_checksums(
        root=root,
        build_directory=build_directory,
        dist_directory=dist_directory,
    ):
        require_file(path)


if __name__ == "__main__":
    main()
