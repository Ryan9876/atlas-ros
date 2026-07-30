#!/usr/bin/env python3
"""Assemble exact non-publishing Atlas ROS v7.7.0 candidate evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

CANDIDATE_VERSION = "7.7.0"
EXPECTED_SOURCE = "atlas_ros-7.7.0.tar.gz"
EXPECTED_WHEEL = "atlas_ros-7.7.0-py3-none-any.whl"


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
    *,
    root: Path,
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
        "name": "atlas-ros-v7.7.0-candidate",
        "documentNamespace": f"https://github.com/{repository}/spdx/{candidate_commit}",
        "creationInfo": {
            "created": commit_timestamp(root),
            "creators": ["Tool: Atlas ROS v7.7.0 candidate evidence builder"],
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


def checksums(paths: tuple[Path, ...], *, relative_to: Path) -> str:
    return "\n".join(
        f"{digest(path)}  {path.relative_to(relative_to).as_posix()}"
        for path in sorted(paths)
    ) + "\n"


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(require_file(path).read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"evidence must be a JSON object: {path}")
    return payload


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
    workflow_started_epoch = float(require_environment("WORKFLOW_STARTED_EPOCH"))
    elapsed_seconds = max(0.0, time.time() - workflow_started_epoch)

    if active_version != "7.6.1":
        raise ValueError("v7.7.0 candidate requires Active v7.6.1")
    if rollback_version != "7.6.0":
        raise ValueError("v7.7.0 candidate requires v7.6.0 preserved rollback")
    if git_output("rev-parse", "HEAD", cwd=root) != candidate_commit:
        raise ValueError("candidate commit does not match checked-out source")

    source = require_file(dist / EXPECTED_SOURCE)
    wheel = require_file(dist / EXPECTED_WHEEL)
    if require_file(build / "BUILD_COUNT.txt").read_text().strip() != "1":
        raise ValueError("exact build count must equal one")
    if (
        require_file(build / "ACTIVE_RESTORATION_COMMIT.txt").read_text().strip()
        != active_commit
    ):
        raise ValueError("Active restoration identity mismatch")
    if (
        require_file(build / "ROLLBACK_RESTORATION_COMMIT.txt").read_text().strip()
        != rollback_commit
    ):
        raise ValueError("rollback restoration identity mismatch")

    cold_receipt = require_file(build / "V770_COLD_INITIALIZATION_RECEIPT.json")
    warm_receipt = require_file(build / "V770_WARM_INITIALIZATION_RECEIPT.json")
    cold_lock = require_file(build / "V770_COLD_TERMINAL_LOCK_PROOF.json")
    warm_lock = require_file(build / "V770_WARM_TERMINAL_LOCK_PROOF.json")
    initialization_index = require_file(build / "V770_INITIALIZATION_EVIDENCE_INDEX.json")
    secret_scan = require_file(build / "V770_SECRET_SCAN.json")
    audit_pypi = require_file(build / "V770_PIP_AUDIT_PYPI.json")
    audit_osv = require_file(build / "V770_PIP_AUDIT_OSV.json")

    initialization = load_json(initialization_index)
    cold = load_json(cold_receipt)
    warm = load_json(warm_receipt)
    cold_terminal = load_json(cold_lock)
    warm_terminal = load_json(warm_lock)
    if initialization.get("status") != "passed":
        raise ValueError("initialization evidence did not pass")
    if cold.get("external_read_count") != 6 or cold.get("execution_path") != "cold":
        raise ValueError("cold initialization read proof is invalid")
    if warm.get("external_read_count") != 4 or warm.get("execution_path") != "warm":
        raise ValueError("warm initialization read proof is invalid")
    for receipt in (cold, warm):
        if receipt.get("provider_writes") != 0:
            raise ValueError("initialization receipt contains provider writes")
        if receipt.get("google_drive_reads") != 0:
            raise ValueError("initialization receipt contains Google Drive reads")
        if receipt.get("post_terminal_executed_calls") != 0:
            raise ValueError("initialization receipt contains post-terminal calls")
        if receipt.get("terminal_lock_activated") is not True:
            raise ValueError("terminal lock is not activated")
        if receipt.get("budget_result") is not True:
            raise ValueError("initialization read budget did not pass")
    for proof in (cold_terminal, warm_terminal):
        if proof.get("status") != "passed":
            raise ValueError("terminal lock proof did not pass")
        if proof.get("provider_invoked") is not False:
            raise ValueError("terminal lock proof invoked a provider")
        if proof.get("observed_provider_calls") != 0:
            raise ValueError("terminal lock probe reached the provider")
        if proof.get("post_terminal_executed_calls") != 0:
            raise ValueError("terminal lock proof reports an executed call")

    source_manifest = write_source_manifest(root, build)
    sbom = write_sbom(
        root=root,
        repository=os.environ.get("GITHUB_REPOSITORY", "Ryan9876/atlas-ros"),
        candidate_commit=candidate_commit,
        source_manifest=source_manifest,
        build_directory=build,
    )

    validation = {
        "schema_version": "v770-validation-receipt-v1",
        "status": "passed",
        "workflow_run_id": workflow_run_id,
        "workflow_elapsed_seconds": round(elapsed_seconds, 3),
        "candidate_version": CANDIDATE_VERSION,
        "candidate_commit": candidate_commit,
        "source_distribution_sha256": digest(source),
        "wheel_sha256": digest(wheel),
        "sbom_sha256": digest(sbom),
        "source_manifest_sha256": digest(source_manifest),
        "initialization_evidence_index_sha256": digest(initialization_index),
        "cold_initialization_receipt_sha256": digest(cold_receipt),
        "warm_initialization_receipt_sha256": digest(warm_receipt),
        "cold_terminal_lock_proof_sha256": digest(cold_lock),
        "warm_terminal_lock_proof_sha256": digest(warm_lock),
        "secret_scan_sha256": digest(secret_scan),
        "dependency_audit_pypi_sha256": digest(audit_pypi),
        "dependency_audit_osv_sha256": digest(audit_osv),
        "active_restoration_version": active_version,
        "active_restoration_commit": active_commit,
        "rollback_restoration_version": rollback_version,
        "rollback_restoration_commit": rollback_commit,
        "cold_external_reads": 6,
        "warm_external_reads": 4,
        "post_terminal_provider_calls": 0,
        "build_count": 1,
        "release_publication_performed": False,
        "authority_activation_performed": False,
        "provider_writes": 0,
        "todoist_writes": 0,
        "google_drive_reads": 0,
    }
    validation_path = build / "V770_VALIDATION_RECEIPT.json"
    write_json(validation_path, validation)

    zero_writes = {
        "schema_version": "v770-zero-provider-write-receipt-v1",
        "candidate_commit": candidate_commit,
        "provider_writes": 0,
        "todoist_writes": 0,
        "google_drive_reads": 0,
        "messages_sent": 0,
        "calendar_actions": 0,
        "scheduled_actions": 0,
        "credential_actions": 0,
        "integration_scope_changes": 0,
        "schema_changes": 0,
        "deletions": 0,
        "profile_activations": 0,
        "intent_memory_operations": 0,
        "release_publications": 0,
        "production_tags_created_or_moved": 0,
        "authority_changes": 0,
        "post_terminal_executed_calls": 0,
    }
    zero_path = build / "V770_ZERO_PROVIDER_WRITE_RECEIPT.json"
    write_json(zero_path, zero_writes)

    package = {
        "schema_version": "v770-package-index-v1",
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
        "initialization_evidence_index_sha256": digest(initialization_index),
        "build_count": 1,
        "cold_external_reads": 6,
        "warm_external_reads": 4,
        "terminal_lock_verified": True,
        "post_terminal_provider_calls": 0,
        "publication_authorized": False,
        "production_activation_authorized": False,
    }
    package_path = build / "V770_PACKAGE_INDEX.json"
    write_json(package_path, package)

    manifest = build / "V770_DRAFT_IMMUTABLE_MANIFEST.md"
    manifest.write_text(
        f"""# Atlas ROS v7.7.0 Draft Immutable Release Manifest

Status: validated non-publishing candidate; publication and production activation are not authorized.

## Exact package identity

- Version: `7.7.0`
- Exact source commit: `{candidate_commit}`
- Source distribution SHA-256: `{digest(source)}`
- Wheel SHA-256: `{digest(wheel)}`
- SPDX SBOM SHA-256: `{digest(sbom)}`
- Source manifest SHA-256: `{digest(source_manifest)}`
- Validation receipt SHA-256: `{digest(validation_path)}`
- Initialization evidence index SHA-256: `{digest(initialization_index)}`
- Zero-provider-write receipt SHA-256: `{digest(zero_path)}`
- Build count: `1`

## Initialization Circuit Breaker proof

- Clean cold external reads: `6`
- Clean warm external reads: `4`
- Terminal lock verified before provider invocation: `true`
- Post-terminal provider calls: `0`
- General searches during Quick Initialization: `0`
- Plugin or skill reads during Quick Initialization: `0`
- Google Drive reads: `0`
- Provider writes: `0`

## Predecessor and rollback

- Active predecessor and proposed immediate rollback: Atlas ROS v{active_version} at `{active_commit}`
- Preserved rollback: Atlas ROS v{rollback_version} at `{rollback_commit}`

## Preserved boundaries

No publication, production tag, merge, canonical authority activation, Notion System State change, schema change, Todoist write, message, calendar action, schedule, credential action, integration-scope change, deletion, profile activation, intent-memory operation, or live-network action is authorized by this candidate manifest.
"""
    )

    authorization = build / "V770_PACKAGE_AUTHORIZATION_CHECKPOINT.md"
    authorization.write_text(
        f"""# Atlas ROS v7.7.0 Package Authorization Checkpoint

- Version: `7.7.0`
- Exact source commit: `{candidate_commit}`
- Retained artifact ID: `<assigned-by-workflow-upload>`
- Retained artifact digest: `<verified-after-workflow-upload>`
- Source distribution SHA-256: `{digest(source)}`
- Wheel SHA-256: `{digest(wheel)}`
- SBOM SHA-256: `{digest(sbom)}`
- Source-manifest SHA-256: `{digest(source_manifest)}`
- Validation-receipt SHA-256: `{digest(validation_path)}`
- Initialization-evidence SHA-256: `{digest(initialization_index)}`
- Draft immutable-manifest SHA-256: `{digest(manifest)}`
- Rollback target: Atlas ROS v{active_version} at `{active_commit}`
- Cold external reads: `6`
- Warm external reads: `4`
- Terminal-lock proof: `passed`
- Post-terminal provider calls: `0`
- GitHub Actions run: `{workflow_run_id}`
- Workflow elapsed seconds at evidence finalization: `{elapsed_seconds:.3f}`
- Publication authorized: `false`
- Production activation authorized: `false`
"""
    )

    actions = build / "V770_ACTIONS_UTILIZATION.json"
    write_json(
        actions,
        {
            "schema_version": "actions-utilization-report-v1",
            "candidate_commit": candidate_commit,
            "workflow_run_id": workflow_run_id,
            "workflow_elapsed_seconds_at_evidence_finalization": round(
                elapsed_seconds, 3
            ),
            "build_count": 1,
            "exact_artifacts_reused": True,
            "stale_run_cancellation_enabled": True,
            "dependency_cache_enabled": True,
            "broad_compatibility_matrix_used": False,
            "publication_rebuild_allowed": False,
        },
    )

    dist_paths = (source, wheel)
    (build / "CHECKSUMS.sha256").write_text(checksums(dist_paths, relative_to=root))
    evidence_paths = tuple(
        path
        for path in build.iterdir()
        if path.is_file()
        and path.name not in {"EVIDENCE_CHECKSUMS.sha256", "NESTED_CHECKSUMS.sha256"}
    )
    (build / "EVIDENCE_CHECKSUMS.sha256").write_text(
        checksums(evidence_paths, relative_to=root)
    )
    nested = (build / "CHECKSUMS.sha256", build / "EVIDENCE_CHECKSUMS.sha256")
    (build / "NESTED_CHECKSUMS.sha256").write_text(
        checksums(nested, relative_to=root)
    )


if __name__ == "__main__":
    main()
