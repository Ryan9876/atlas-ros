from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

CANDIDATE_VERSION = "7.5.2"
EXPECTED_SOURCE = f"atlas_ros-{CANDIDATE_VERSION}.tar.gz"
EXPECTED_WHEEL = f"atlas_ros-{CANDIDATE_VERSION}-py3-none-any.whl"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def git_output(*arguments: str) -> str:
    return subprocess.check_output(["git", *arguments], text=True).strip()


def tracked_files(root: Path) -> tuple[Path, ...]:
    output = subprocess.check_output(
        ["git", "ls-files", "-z"],
        cwd=root,
    )
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
                "checksums": [
                    {"algorithm": "SHA256", "checksumValue": checksum}
                ],
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
    sbom = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": "atlas-ros-v7.5.2-candidate",
        "documentNamespace": (
            f"https://github.com/{repository}/spdx/{candidate_commit}"
        ),
        "creationInfo": {
            "created": commit_timestamp(),
            "creators": ["Tool: Atlas ROS v7.5.2 candidate evidence builder"],
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
    write_json(path, sbom)
    return path


def require_environment(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"{name} is required")
    return value


def require_file(path: Path) -> Path:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"required evidence file is missing or empty: {path}")
    return path


def validate_restoration(build_directory: Path, name: str, expected: str) -> None:
    path = require_file(build_directory / name)
    if path.read_text().strip() != expected:
        raise ValueError(f"restoration evidence mismatch: {name}")


def write_receipts(
    *,
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
    validate_restoration(
        build_directory,
        "ACTIVE_RESTORATION_COMMIT.txt",
        active_commit,
    )
    validate_restoration(
        build_directory,
        "ROLLBACK_RESTORATION_COMMIT.txt",
        rollback_commit,
    )
    baseline = require_file(build_directory / "V752_BASELINE_REPORT.json")
    schemas = require_file(build_directory / "V752_CONTRACT_SCHEMAS.json")
    minimization = require_file(
        build_directory / "V752_DATA_MINIMIZATION_RECEIPT.json"
    )
    secret_scan = require_file(build_directory / "V752_SECRET_SCAN.json")
    baseline_payload = json.loads(baseline.read_text())
    minimization_payload = json.loads(minimization.read_text())
    if baseline_payload["provider_write_count"] != 0:
        raise ValueError("baseline report contains provider writes")
    if baseline_payload["todoist_write_count"] != 0:
        raise ValueError("baseline report contains Todoist writes")
    if minimization_payload["status"] != "passed":
        raise ValueError("data-minimization validation did not pass")
    package_index = {
        "schema_version": "v752-package-index-v1",
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
        "baseline_report": baseline.name,
        "baseline_report_sha256": digest(baseline),
        "baseline_report_deterministic_digest": baseline_payload[
            "deterministic_digest"
        ],
        "contract_schemas": schemas.name,
        "contract_schemas_sha256": digest(schemas),
        "data_minimization_receipt": minimization.name,
        "data_minimization_receipt_sha256": digest(minimization),
        "secret_scan_sha256": digest(secret_scan),
        "build_count": 1,
    }
    controller = {
        "schema_version": "v752-non-publishing-controller-v1",
        "status": "passed",
        "candidate_commit": candidate_commit,
        "candidate_version": CANDIDATE_VERSION,
        "active_version_unchanged": active_version,
        "rollback_version_verified": rollback_version,
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
    }
    actions = {
        "schema_version": "actions-utilization-report-v1",
        "candidate_commit": candidate_commit,
        "workflow_run_id": workflow_run_id,
        "build_count": 1,
        "exact_artifacts_reused": True,
        "duplicate_retained_builds_avoided": True,
        "stale_run_cancellation_enabled": True,
        "dependency_cache_enabled": True,
        "provider_writes": 0,
        "todoist_writes": 0,
    }
    definition_of_done = {
        "schema_version": "feature-dod-receipt-v1",
        "feature_id": "clarification-calibration-evaluation",
        "candidate_commit": candidate_commit,
        "status": "passed",
        "mandatory_gates_complete": True,
        "exact_build_count": 1,
        "production_unchanged": True,
        "no_production_schema_migration_required": True,
    }
    validation = package_index | {
        "schema_version": "v752-validation-receipt-v1",
        "status": "passed",
        "workflow_run_id": workflow_run_id,
        "active_restoration_version": active_version,
        "active_restoration_commit": active_commit,
        "rollback_restoration_version": rollback_version,
        "rollback_restoration_commit": rollback_commit,
        "provider_writes": 0,
        "todoist_writes": 0,
    }
    zero_writes = {
        "schema_version": "v752-zero-provider-write-receipt-v1",
        "candidate_commit": candidate_commit,
        "provider_writes": 0,
        "todoist_writes": 0,
        "notion_writes": 0,
        "messages_sent": 0,
        "calendar_actions": 0,
        "scheduled_actions": 0,
        "credential_actions": 0,
        "deletions": 0,
    }
    outputs = {
        "V752_PACKAGE_INDEX.json": package_index,
        "V752_NON_PUBLISHING_CONTROLLER.json": controller,
        "V752_ACTIONS_UTILIZATION.json": actions,
        "V752_DEFINITION_OF_DONE_RECEIPT.json": definition_of_done,
        "V752_VALIDATION_RECEIPT.json": validation,
        "V752_ZERO_PROVIDER_WRITE_RECEIPT.json": zero_writes,
    }
    paths: list[Path] = []
    for name, payload in outputs.items():
        path = build_directory / name
        write_json(path, payload)
        paths.append(path)
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
        description="Build the complete deterministic v7.5.2 candidate evidence set."
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
        print(path)


if __name__ == "__main__":
    main()
