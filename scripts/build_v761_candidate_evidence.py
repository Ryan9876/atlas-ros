from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

CANDIDATE_VERSION = "7.6.1"
EXPECTED_SOURCE = "atlas_ros-7.6.1.tar.gz"
EXPECTED_WHEEL = "atlas_ros-7.6.1-py3-none-any.whl"


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


def git_output(*arguments: str, cwd: Path) -> str:
    return subprocess.check_output(["git", *arguments], cwd=cwd, text=True).strip()


def tracked_files(root: Path) -> tuple[Path, ...]:
    output = subprocess.check_output(["git", "ls-files", "-z"], cwd=root)
    names = tuple(name for name in output.decode().split("\0") if name)
    return tuple(root / name for name in sorted(names))


def write_source_manifest(root: Path, build_directory: Path) -> Path:
    path = build_directory / "SOURCE_MANIFEST.sha256"
    path.write_text(
        "\n".join(
            f"{digest(file_path)}  {file_path.relative_to(root).as_posix()}"
            for file_path in tracked_files(root)
        )
        + "\n"
    )
    return path


def commit_timestamp(root: Path) -> str:
    raw = git_output("show", "-s", "--format=%cI", "HEAD", cwd=root)
    value = datetime.fromisoformat(raw).astimezone(UTC)
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def write_sbom(
    *, root: Path, repository: str, candidate_commit: str, source_manifest: Path,
    build_directory: Path,
) -> Path:
    files: list[dict[str, Any]] = []
    relationships: list[dict[str, str]] = []
    for index, line in enumerate(source_manifest.read_text().splitlines(), start=1):
        checksum, file_name = line.split(maxsplit=1)
        spdx_id = f"SPDXRef-File-{index}"
        files.append({
            "fileName": file_name,
            "SPDXID": spdx_id,
            "checksums": [{"algorithm": "SHA256", "checksumValue": checksum}],
            "licenseConcluded": "NOASSERTION",
            "copyrightText": "NOASSERTION",
        })
        relationships.append({
            "spdxElementId": "SPDXRef-Package-atlas-ros",
            "relationshipType": "CONTAINS",
            "relatedSpdxElement": spdx_id,
        })
    payload = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": "atlas-ros-v7.6.1-candidate",
        "documentNamespace": f"https://github.com/{repository}/spdx/{candidate_commit}",
        "creationInfo": {
            "created": commit_timestamp(root),
            "creators": ["Tool: Atlas ROS v7.6.1 candidate evidence builder"],
        },
        "documentDescribes": ["SPDXRef-Package-atlas-ros"],
        "packages": [{
            "name": "atlas-ros",
            "SPDXID": "SPDXRef-Package-atlas-ros",
            "versionInfo": CANDIDATE_VERSION,
            "downloadLocation": "NOASSERTION",
            "filesAnalyzed": True,
            "licenseConcluded": "NOASSERTION",
            "licenseDeclared": "NOASSERTION",
            "copyrightText": "NOASSERTION",
        }],
        "files": files,
        "relationships": relationships,
    }
    path = build_directory / "SBOM.spdx.json"
    write_json(path, payload)
    return path


def checksums(paths: tuple[Path, ...], *, relative_to: Path) -> str:
    return "\n".join(
        f"{digest(path)}  {path.relative_to(relative_to).as_posix()}" for path in sorted(paths)
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--build-directory", type=Path, default=Path("build"))
    parser.add_argument("--dist-directory", type=Path, default=Path("dist"))
    args = parser.parse_args()
    root = args.root.resolve()
    build = args.build_directory.resolve()
    dist = args.dist_directory.resolve()
    build.mkdir(parents=True, exist_ok=True)

    candidate_commit = require_environment("CANDIDATE_COMMIT")
    active_version = require_environment("ACTIVE_VERSION")
    active_commit = require_environment("ACTIVE_COMMIT")
    rollback_version = require_environment("ROLLBACK_VERSION")
    rollback_commit = require_environment("ROLLBACK_COMMIT")
    workflow_run_id = require_environment("GITHUB_RUN_ID")
    if active_version != "7.6.0":
        raise ValueError("v7.6.1 candidate requires Active v7.6.0")
    if rollback_version != "7.5.2":
        raise ValueError("v7.6.1 candidate requires v7.5.2 lineage restoration")
    if git_output("rev-parse", "HEAD", cwd=root) != candidate_commit:
        raise ValueError("candidate commit does not match checked-out source")

    source = require_file(dist / EXPECTED_SOURCE)
    wheel = require_file(dist / EXPECTED_WHEEL)
    if require_file(build / "BUILD_COUNT.txt").read_text().strip() != "1":
        raise ValueError("exact build count must equal one")
    if require_file(build / "ACTIVE_RESTORATION_COMMIT.txt").read_text().strip() != active_commit:
        raise ValueError("Active restoration identity mismatch")
    if require_file(build / "ROLLBACK_RESTORATION_COMMIT.txt").read_text().strip() != rollback_commit:
        raise ValueError("rollback restoration identity mismatch")

    require_file(build / "V761_PROPOSAL_EVIDENCE_INDEX.json")
    schemas = require_file(build / "V761_CONTRACT_SCHEMAS.json")
    policy = require_file(build / "V761_FEATURE_POLICY_TARGET.json")
    profile_schema = require_file(build / "V761_PROFILE_PROJECTION_SCHEMA_PROPOSAL.json")
    privacy = require_file(build / "V761_PRIVACY_REVIEW_RECEIPT.json")
    learning = require_file(build / "V761_LEARNING_BOUNDARY_RECEIPT.json")
    secret_scan = require_file(build / "V761_SECRET_SCAN.json")
    audit_pypi = require_file(build / "V761_PIP_AUDIT_PYPI.json")
    audit_osv = require_file(build / "V761_PIP_AUDIT_OSV.json")
    source_manifest = write_source_manifest(root, build)
    sbom = write_sbom(
        root=root,
        repository=os.environ.get("GITHUB_REPOSITORY", "Ryan9876/atlas-ros"),
        candidate_commit=candidate_commit,
        source_manifest=source_manifest,
        build_directory=build,
    )

    policy_payload = json.loads(policy.read_text())
    privacy_payload = json.loads(privacy.read_text())
    schema_payload = json.loads(profile_schema.read_text())
    if policy_payload["after_release_activation"] != "disabled":
        raise ValueError("software feature must be disabled after release activation")
    if privacy_payload["status"] != "passed":
        raise ValueError("privacy review must pass")
    if schema_payload["status"] != "no_additive_notion_schema_required":
        raise ValueError("unexpected production schema target")

    validation = {
        "schema_version": "v761-validation-receipt-v1",
        "status": "passed",
        "workflow_run_id": workflow_run_id,
        "candidate_version": CANDIDATE_VERSION,
        "candidate_commit": candidate_commit,
        "source_distribution_sha256": digest(source),
        "wheel_sha256": digest(wheel),
        "sbom_sha256": digest(sbom),
        "source_manifest_sha256": digest(source_manifest),
        "contract_schemas_sha256": digest(schemas),
        "feature_policy_sha256": digest(policy),
        "profile_projection_schema_proposal_sha256": digest(profile_schema),
        "privacy_receipt_sha256": digest(privacy),
        "learning_boundary_receipt_sha256": digest(learning),
        "secret_scan_sha256": digest(secret_scan),
        "dependency_audit_pypi_sha256": digest(audit_pypi),
        "dependency_audit_osv_sha256": digest(audit_osv),
        "active_restoration_version": active_version,
        "active_restoration_commit": active_commit,
        "rollback_restoration_version": rollback_version,
        "rollback_restoration_commit": rollback_commit,
        "build_count": 1,
        "production_profile_in_package": False,
        "profile_activation_performed": False,
        "release_publication_performed": False,
        "authority_activation_performed": False,
        "provider_writes": 0,
        "todoist_writes": 0,
    }
    validation_path = build / "V761_VALIDATION_RECEIPT.json"
    write_json(validation_path, validation)

    zero_writes = {
        "schema_version": "v761-zero-provider-write-receipt-v1",
        "candidate_commit": candidate_commit,
        "provider_writes": 0,
        "todoist_writes": 0,
        "messages_sent": 0,
        "calendar_actions": 0,
        "scheduled_actions": 0,
        "credential_actions": 0,
        "integration_scope_changes": 0,
        "deletions": 0,
        "forgetting_executions": 0,
        "profile_activations": 0,
        "release_publications": 0,
        "production_tags_created_or_moved": 0,
    }
    zero_path = build / "V761_ZERO_PROVIDER_WRITE_RECEIPT.json"
    write_json(zero_path, zero_writes)

    package = {
        "schema_version": "v761-package-index-v1",
        "candidate_version": CANDIDATE_VERSION,
        "candidate_commit": candidate_commit,
        "source_distribution": source.name,
        "source_distribution_sha256": digest(source),
        "wheel": wheel.name,
        "wheel_sha256": digest(wheel),
        "sbom_sha256": digest(sbom),
        "source_manifest_sha256": digest(source_manifest),
        "validation_receipt_sha256": digest(validation_path),
        "zero_provider_write_receipt_sha256": digest(zero_path),
        "build_count": 1,
        "profile_bundle_in_artifact": False,
        "publication_authorized": False,
    }
    package_path = build / "V761_PACKAGE_INDEX.json"
    write_json(package_path, package)

    manifest = build / "V761_DRAFT_IMMUTABLE_MANIFEST.md"
    manifest.write_text(f"""# Atlas ROS v7.6.1 Draft Immutable Release Manifest

Status: validated non-publishing candidate; publication, production activation, and profile activation are not authorized.

## Exact package identity

- Version: `7.6.1`
- Exact source commit: `{candidate_commit}`
- Source distribution SHA-256: `{digest(source)}`
- Wheel SHA-256: `{digest(wheel)}`
- SPDX SBOM SHA-256: `{digest(sbom)}`
- Source manifest SHA-256: `{digest(source_manifest)}`
- Validation receipt SHA-256: `{digest(validation_path)}`
- Build count: `1`

## Predecessor and rollback

- Active predecessor: Atlas ROS v{active_version} at `{active_commit}`
- Proposed immediate rollback after activation: Atlas ROS v{active_version} at `{active_commit}`
- Preserved predecessor lineage: Atlas ROS v{rollback_version} at `{rollback_commit}`

## Feature and profile state

- Software feature after release activation: `disabled`
- Ryan profile bundle in package artifacts: `false`
- Profile activation: separate exact governed transaction
- Dedicated Notion profile-projection schema: not required by the candidate proposal
- Safe fallback: Atlas ROS v7.6.0 baseline with v7.5 clarification behavior

## Preserved boundaries

No publication, tag, merge, canonical authority activation, production schema change, profile activation, Todoist write, message, calendar action, schedule, credential action, integration-scope expansion, deletion, forgetting execution, or live-network action is authorized by this draft manifest.
""")

    authorization = build / "V761_PACKAGE_AUTHORIZATION_CHECKPOINT.md"
    authorization.write_text(f"""# Atlas ROS v7.6.1 Package Authorization Checkpoint

This block covers the package only. The separate minimized Ryan profile bundle must be joined to this block after private profile validation and before Ryan is asked for exact authorization.

- Version: `7.6.1`
- Exact source commit: `{candidate_commit}`
- Retained artifact ID: `<assigned-by-workflow-upload>`
- Retained artifact digest: `<assigned-after-upload>`
- Source distribution SHA-256: `{digest(source)}`
- Wheel SHA-256: `{digest(wheel)}`
- SBOM SHA-256: `{digest(sbom)}`
- Source-manifest SHA-256: `{digest(source_manifest)}`
- Validation receipt SHA-256: `{digest(validation_path)}`
- Draft manifest SHA-256: `{digest(manifest)}`
- Rollback target: Atlas ROS v{active_version} at `{active_commit}`
- Publication authorized: `false`
- Production activation authorized: `false`
- Profile activation authorized: `false`
""")

    actions = build / "V761_ACTIONS_UTILIZATION.json"
    write_json(actions, {
        "schema_version": "actions-utilization-report-v1",
        "candidate_commit": candidate_commit,
        "workflow_run_id": workflow_run_id,
        "build_count": 1,
        "exact_artifacts_reused": True,
        "stale_run_cancellation_enabled": True,
        "dependency_cache_enabled": True,
        "broad_compatibility_matrix_used": False,
        "profile_bundle_readback_inside_build_workflow": False,
    })

    dist_paths = (source, wheel)
    (build / "CHECKSUMS.sha256").write_text(checksums(dist_paths, relative_to=root))
    evidence_paths = tuple(
        path for path in build.iterdir()
        if path.is_file() and path.name not in {"EVIDENCE_CHECKSUMS.sha256", "NESTED_CHECKSUMS.sha256"}
    )
    (build / "EVIDENCE_CHECKSUMS.sha256").write_text(
        checksums(evidence_paths, relative_to=root)
    )
    nested = (build / "CHECKSUMS.sha256", build / "EVIDENCE_CHECKSUMS.sha256")
    (build / "NESTED_CHECKSUMS.sha256").write_text(checksums(nested, relative_to=root))


if __name__ == "__main__":
    main()
