#!/usr/bin/env python3
"""Build and validate the exact Atlas ROS v7.0.0 final package without publishing."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from atlas_ros.capabilities.compiler import compile_capability_registry
from atlas_ros.contracts.compiler import compile_contract_registry
from atlas_ros.contracts.schemas import require_valid_contract_schemas

FINAL_VERSION = "7.0.0"
CANDIDATE_VERSION = "7.0.0rc1"
V650_SOURCE_COMMIT = "bb6d6fea70d6824c9bc6a42e63ba36cc88029260"
V620_SOURCE_COMMIT = "863d5ddf9ebd4723200166cf31c7acd93ebec54f"


class FinalPackageBuildError(ValueError):
    """Raised when the exact final package cannot be built or validated."""


def build_final_package(
    *,
    repository_root: Path,
    final_source_commit: str,
    workflow_run_id: str,
    candidate_exact_validation_path: Path,
    candidate_exact_artifact_id: str,
    candidate_exact_artifact_digest: str,
    decision_record_url: str,
    review_record_url: str,
    output_dir: Path,
) -> dict[str, Any]:
    """Build one non-publishing final package and emit checksum-bound evidence."""
    root = repository_root.resolve()
    exact = _read_json(candidate_exact_validation_path)
    _validate_candidate_lineage(
        exact,
        artifact_id=candidate_exact_artifact_id,
        artifact_digest=candidate_exact_artifact_digest,
    )
    _require_sha("final source commit", final_source_commit, 40)
    if _run(root, "git", "rev-parse", "HEAD").stdout.strip() != final_source_commit:
        raise FinalPackageBuildError("working tree is not the exact final source commit")

    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    if project["version"] != FINAL_VERSION:
        raise FinalPackageBuildError("pyproject version is not 7.0.0")
    runtime_version = _run(
        root,
        sys.executable,
        "-c",
        "import atlas_ros; print(atlas_ros.__version__)",
    ).stdout.strip()
    if runtime_version != FINAL_VERSION:
        raise FinalPackageBuildError("runtime version is not 7.0.0")

    work = root / ".v700-final-work"
    evidence = work / "evidence"
    publication = output_dir.resolve()
    for path in (work, publication, root / "dist", root / "build"):
        if path.exists():
            shutil.rmtree(path)
    evidence.mkdir(parents=True)
    publication.mkdir(parents=True)
    (evidence / "benchmarks").mkdir()
    (evidence / "test-results").mkdir()

    _write_source_manifest(root, evidence / "SOURCE_MANIFEST.sha256")
    _run(root, sys.executable, "-m", "build")
    sdist = root / "dist" / f"atlas_ros-{FINAL_VERSION}.tar.gz"
    wheel = root / "dist" / f"atlas_ros-{FINAL_VERSION}-py3-none-any.whl"
    _require_file(sdist)
    _require_file(wheel)

    final_env = work / "clean-final"
    _create_venv(root, final_env)
    _run(root, str(final_env / "bin/python"), "-m", "pip", "install", str(wheel))
    installed_version = _run(
        root,
        str(final_env / "bin/python"),
        "-c",
        "import atlas_ros; print(atlas_ros.__version__)",
    ).stdout.strip()
    if installed_version != FINAL_VERSION:
        raise FinalPackageBuildError("clean final wheel installation reported wrong version")
    _run(
        root,
        str(final_env / "bin/atlas"),
        "verify",
        "--json",
        stdout_path=evidence / "FINAL_RUNTIME_VERIFY.json",
    )

    v650_assets = work / "v650-assets"
    v620_assets = work / "v620-assets"
    v650_assets.mkdir()
    v620_assets.mkdir()
    _run(
        root,
        "gh",
        "release",
        "download",
        "v6.5.0",
        "--repo",
        _repository(),
        "--dir",
        str(v650_assets),
    )
    _run(
        root,
        "gh",
        "release",
        "download",
        "v6.2.0",
        "--repo",
        _repository(),
        "--dir",
        str(v620_assets),
    )
    _verify_release_checksums(v650_assets)
    _verify_release_checksums(v620_assets)

    v650_env = work / "restore-v650"
    v620_env = work / "restore-v620"
    _install_release_wheel(root, v650_assets, "6.5.0", v650_env)
    _install_release_wheel(root, v620_assets, "6.2.0", v620_env)

    _run(
        root,
        sys.executable,
        "-m",
        "scripts.validate_v650_rollback_evidence",
        "--repository-root",
        str(root),
        "--source-commit",
        V650_SOURCE_COMMIT,
        "--release-assets-dir",
        str(v650_assets),
        "--clean-install-version",
        "6.5.0",
        "--restoration-passed",
        "--metadata-exception-record-url",
        "https://app.notion.com/p/3aab8344ad2c81efad29c12b9b132374",
        "--output",
        str(evidence / "V650_ROLLBACK_EVIDENCE.json"),
    )
    _run(
        root,
        sys.executable,
        "scripts/compare_v700_performance.py",
        "--candidate-python",
        str(final_env / "bin/python"),
        "--baseline-python",
        str(v650_env / "bin/python"),
        "--dataset",
        "benchmarks/execution-planning-v1.json",
        "--iterations",
        "7",
        "--max-regression",
        "0.10",
        "--output",
        str(evidence / "benchmarks/V700_V650_PERFORMANCE.json"),
    )

    governance = _governance_evidence(root)
    _write_json(evidence / "GOVERNANCE_DIGESTS.json", governance)
    drive = _drive_evidence(root, evidence)
    integration = _integration_evidence(root)
    _write_json(evidence / "INTEGRATION_READINESS.json", integration)

    source_sha = _sha256(sdist)
    wheel_sha = _sha256(wheel)
    package_digest = hashlib.sha256(
        f"{final_source_commit}:{source_sha}:{wheel_sha}".encode("utf-8")
    ).hexdigest()
    candidate_sha = _required_string(exact, "candidate_sha")
    candidate_artifact_id = str(exact.get("candidate_artifact_id", ""))
    candidate_artifact_digest = _required_string(exact, "candidate_artifact_digest")
    rollback = _read_json(evidence / "V650_ROLLBACK_EVIDENCE.json")["receipt"]
    performance = _read_json(evidence / "benchmarks/V700_V650_PERFORMANCE.json")

    identity = {
        "schema_version": "1.0",
        "final_version": FINAL_VERSION,
        "final_tag": "v7.0.0",
        "final_source_commit": final_source_commit,
        "workflow_run_id": workflow_run_id,
        "source": {"name": sdist.name, "sha256": source_sha},
        "wheel": {"name": wheel.name, "sha256": wheel_sha},
        "final_package_digest": package_digest,
        "candidate_lineage": {
            "version": CANDIDATE_VERSION,
            "commit": candidate_sha,
            "artifact_id": candidate_artifact_id,
            "artifact_digest": candidate_artifact_digest,
            "exact_artifact_id": candidate_exact_artifact_id,
            "exact_artifact_digest": candidate_exact_artifact_digest,
        },
        "governance": governance,
        "drive_migration_ledger_sha256": drive["ledger_sha256"],
        "v650_rollback_evidence_sha256": rollback["evidence_digest"],
        "production_baseline": {"version": "6.5.0", "commit": V650_SOURCE_COMMIT},
        "immediate_rollback": {"version": "6.5.0", "commit": V650_SOURCE_COMMIT},
        "historical_rollback": {"version": "6.2.0", "commit": V620_SOURCE_COMMIT},
        "decision_record_url": decision_record_url,
        "review_record_url": review_record_url,
        "provider_writes": 0,
        "publication_authorized": False,
        "publication_performed": False,
        "tag_created": False,
        "authority_activated": False,
        "drive_retired": False,
    }
    _write_json(evidence / "FINAL_IDENTITY.json", identity)

    validation = {
        "schema_version": "1.0",
        "status": "passed_with_findings",
        "final_version": FINAL_VERSION,
        "final_source_commit": final_source_commit,
        "workflow_run_id": workflow_run_id,
        "final_package_digest": package_digest,
        "source_sha256": source_sha,
        "wheel_sha256": wheel_sha,
        "candidate_exact_validation_passed": True,
        "candidate_sha": candidate_sha,
        "candidate_exact_artifact_id": candidate_exact_artifact_id,
        "candidate_exact_artifact_digest": candidate_exact_artifact_digest,
        "clean_install_passed": True,
        "v650_restoration_passed": True,
        "v620_restoration_passed": True,
        "v650_rollback_evidence_reconciled": rollback["status"] == "ready",
        "v650_rollback_evidence_sha256": rollback["evidence_digest"],
        "performance_gate": performance,
        "integration_snapshot_ready": integration["ready"],
        "drive_migration_ledger_complete": drive["complete_for_promotion_readiness"],
        "drive_migration_ledger_sha256": drive["ledger_sha256"],
        "publication_checksums_passed": True,
        "nested_evidence_checksums_passed": True,
        "findings": [
            "final live-authority snapshot is required before production authorization",
            "exact-package Ryan production authorization is required before publication",
        ],
        "provider_writes": 0,
        "publication_performed": False,
        "tag_created": False,
        "authority_activated": False,
        "drive_retired": False,
    }
    _write_json(evidence / "FINAL_PACKAGE_VALIDATION.json", validation)
    _write_manifest(evidence / "RELEASE_MANIFEST.md", identity, validation)
    _write_sbom(evidence / "SBOM.cdx.json", project, identity)
    shutil.copy2(root / "release/RELEASE_NOTES_V700.md", evidence / "RELEASE_NOTES.md")
    shutil.copy2(root / "release/RELEASE_SCOPE_V700.md", evidence / "RELEASE_SCOPE.md")

    _write_checksums(evidence, "EVIDENCE_CHECKSUMS.sha256")
    shutil.copy2(sdist, publication / sdist.name)
    shutil.copy2(wheel, publication / wheel.name)
    shutil.copytree(evidence, publication / "evidence")
    evidence_archive = publication / "Atlas_ROS_v7.0.0_final_evidence.tar.gz"
    _run(
        publication,
        "tar",
        "-czf",
        str(evidence_archive),
        "-C",
        str(publication),
        "evidence",
    )
    _write_checksums(publication, "PUBLICATION_CHECKSUMS.sha256", max_depth=1)
    _verify_checksums(publication, publication / "PUBLICATION_CHECKSUMS.sha256")
    return validation


def _validate_candidate_lineage(
    exact: dict[str, Any], *, artifact_id: str, artifact_digest: str
) -> None:
    if exact.get("status") not in {"passed", "passed_with_findings"}:
        raise FinalPackageBuildError("candidate exact-artifact validation did not pass")
    if exact.get("provider_writes") != 0:
        raise FinalPackageBuildError("candidate exact-artifact validation wrote providers")
    if str(exact.get("candidate_artifact_id", "")) == "":
        raise FinalPackageBuildError("candidate artifact ID is missing")
    _require_sha("candidate exact artifact digest", artifact_digest, 64)
    if not artifact_id.strip():
        raise FinalPackageBuildError("candidate exact artifact ID is required")


def _governance_evidence(root: Path) -> dict[str, Any]:
    require_valid_contract_schemas()
    contracts = compile_contract_registry(root / "governance/contract-catalog.yaml")
    capabilities = compile_capability_registry(root / "governance/capability-catalog.yaml")
    return {
        "contract_catalog_sha256": contracts.digest,
        "contract_count": len(contracts.contracts),
        "capability_catalog_sha256": capabilities.digest,
        "capability_count": len(capabilities.capabilities),
        "sole_planning_authority": capabilities.planning_authority_id,
        "contract_schema_equivalence": "passed",
    }


def _drive_evidence(root: Path, evidence: Path) -> dict[str, Any]:
    _run(
        root,
        sys.executable,
        "-m",
        "scripts.validate_v700_current_drive_authority",
        "--input",
        "release/v700-current-drive-authority-migration.json",
        "--output",
        str(evidence / "V700_CURRENT_DRIVE_AUTHORITY.json"),
    )
    _run(
        root,
        sys.executable,
        "-m",
        "tools.release.drive_migration_cli",
        "compile",
        "release/v700-drive-migration-inventory.json",
        str(evidence / "V700_DRIVE_MIGRATION_LEDGER.json"),
        stdout_path=evidence / "V700_DRIVE_MIGRATION_SUMMARY.json",
    )
    _run(
        root,
        sys.executable,
        "-m",
        "scripts.validate_v700_pre_v6_deletion_plan",
        "--plan",
        "release/v700-pre-v6-deletion-plan.json",
        "--folder-tree",
        "release/v700-drive-folder-traversal.json",
        "--output",
        str(evidence / "V700_PRE_V6_DELETION_PLAN.json"),
    )
    _run(
        root,
        sys.executable,
        "-m",
        "scripts.validate_v700_pre_v6_exclusion_review",
        "--review",
        "release/v700-pre-v6-exclusion-review.json",
        "--plan",
        "release/v700-pre-v6-deletion-plan.json",
        "--folder-tree",
        "release/v700-drive-folder-traversal.json",
        "--output",
        str(evidence / "V700_PRE_V6_EXCLUSION_REVIEW.json"),
    )
    summary = _read_json(evidence / "V700_DRIVE_MIGRATION_SUMMARY.json")
    if summary.get("complete_for_promotion_readiness") is not True:
        raise FinalPackageBuildError("Drive migration ledger is not promotion-ready")
    if summary.get("provider_actions_performed") != 0:
        raise FinalPackageBuildError("Drive validation performed provider actions")
    return summary


def _integration_evidence(root: Path) -> dict[str, Any]:
    snapshot = _read_json(root / "release/v700-integration-readiness.json")
    required = snapshot.get("required_v7_integrations")
    if not isinstance(required, list) or {item.get("name") for item in required} != {
        "GitHub",
        "Notion",
        "Todoist",
    }:
        raise FinalPackageBuildError("required integration set is not exact")
    ready = all(
        item.get("connection_status") == "connected"
        and item.get("approval_status") == "approved"
        and item.get("acceptance_status") == "passed"
        and item.get("current") is True
        and item.get("least_privilege_verified") is True
        for item in required
    )
    if not ready:
        raise FinalPackageBuildError("required integration snapshot is not ready")
    return {"ready": True, "required_integrations": required, "provider_writes": 0}


def _write_manifest(path: Path, identity: dict[str, Any], validation: dict[str, Any]) -> None:
    path.write_text(
        "# Atlas ROS v7.0.0 Final Release Manifest\n\n"
        "Status: exact final package validated; publication not authorized.\n\n"
        f"- Final source commit: `{identity['final_source_commit']}`\n"
        f"- Source SHA-256: `{identity['source']['sha256']}`\n"
        f"- Wheel SHA-256: `{identity['wheel']['sha256']}`\n"
        f"- Final package digest: `{identity['final_package_digest']}`\n"
        f"- Candidate lineage commit: `{identity['candidate_lineage']['commit']}`\n"
        f"- Candidate exact artifact digest: "
        f"`{identity['candidate_lineage']['exact_artifact_digest']}`\n"
        f"- Drive migration ledger SHA-256: `{identity['drive_migration_ledger_sha256']}`\n"
        f"- v6.5 rollback evidence SHA-256: "
        f"`{identity['v650_rollback_evidence_sha256']}`\n"
        f"- Performance gate: `{validation['performance_gate']['status']}`\n"
        "- Required integrations: `ready`\n"
        "- Provider writes during validation: `0`\n"
        "- Publication performed: `false`\n"
        "- Final tag created: `false`\n"
        "- Authority activated: `false`\n"
        "- Google Drive retired: `false`\n"
        "- Immediate rollback after promotion: `v6.5.0`\n\n"
        "Publication requires a separate exact-package Ryan authorization, followed by "
        "independent publication and live-authority readback.\n",
        encoding="utf-8",
    )


def _write_sbom(path: Path, project: dict[str, Any], identity: dict[str, Any]) -> None:
    components = [
        {
            "type": "library",
            "name": dependency.split("<", 1)[0].split(">", 1)[0].split("=", 1)[0],
            "version": dependency,
        }
        for dependency in project["dependencies"]
    ]
    payload = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:atlas-ros-{identity['final_source_commit']}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(UTC).isoformat(),
            "component": {
                "type": "application",
                "name": "atlas-ros",
                "version": FINAL_VERSION,
                "hashes": [{"alg": "SHA-256", "content": identity["wheel"]["sha256"]}],
            },
        },
        "components": components,
    }
    _write_json(path, payload)


def _write_source_manifest(root: Path, output: Path) -> None:
    paths = _run(root, "git", "ls-files", "-z", text=False).stdout.split(b"\0")
    lines = []
    for raw in paths:
        if not raw:
            continue
        relative = Path(raw.decode("utf-8"))
        lines.append(f"{_sha256(root / relative)}  {relative.as_posix()}")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _install_release_wheel(root: Path, assets: Path, version: str, env: Path) -> None:
    wheels = sorted(assets.glob(f"atlas_ros-{version}*.whl"))
    if len(wheels) != 1:
        raise FinalPackageBuildError(f"expected one Atlas ROS {version} wheel")
    _create_venv(root, env)
    _run(root, str(env / "bin/python"), "-m", "pip", "install", str(wheels[0]))
    actual = _run(
        root,
        str(env / "bin/python"),
        "-c",
        "import atlas_ros; print(atlas_ros.__version__)",
    ).stdout.strip()
    if actual != version:
        raise FinalPackageBuildError(f"restored Atlas ROS {version} reported {actual}")


def _create_venv(root: Path, path: Path) -> None:
    _run(root, sys.executable, "-m", "venv", str(path))


def _verify_release_checksums(root: Path) -> None:
    checksum = root / "CHECKSUMS.sha256"
    _require_file(checksum)
    _verify_checksums(root, checksum)


def _write_checksums(root: Path, filename: str, *, max_depth: int | None = None) -> None:
    output = root / filename
    files = sorted(path for path in root.rglob("*") if path.is_file() and path != output)
    if max_depth is not None:
        files = [path for path in files if len(path.relative_to(root).parts) <= max_depth]
    output.write_text(
        "".join(f"{_sha256(path)}  {path.relative_to(root).as_posix()}\n" for path in files),
        encoding="utf-8",
    )
    _verify_checksums(root, output)


def _verify_checksums(root: Path, checksum: Path) -> None:
    count = 0
    for line in checksum.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, relative = line.split("  ", 1)
        path = root / relative
        if not path.is_file() or _sha256(path) != expected:
            raise FinalPackageBuildError(f"checksum failed: {relative}")
        count += 1
    if count == 0:
        raise FinalPackageBuildError("checksum inventory is empty")


def _run(
    cwd: Path,
    *command: str,
    stdout_path: Path | None = None,
    text: bool = True,
) -> subprocess.CompletedProcess[Any]:
    completed = subprocess.run(
        list(command),
        cwd=cwd,
        capture_output=True,
        text=text,
        check=False,
        env=os.environ.copy(),
    )
    if completed.returncode != 0:
        stderr = completed.stderr if text else completed.stderr.decode("utf-8", errors="replace")
        raise FinalPackageBuildError(f"command failed: {' '.join(command)}: {stderr.strip()}")
    if stdout_path is not None:
        data = completed.stdout if text else completed.stdout.decode("utf-8")
        stdout_path.write_text(data, encoding="utf-8")
    return completed


def _repository() -> str:
    value = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if not value:
        raise FinalPackageBuildError("GITHUB_REPOSITORY is required")
    return value


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise FinalPackageBuildError(f"invalid JSON evidence: {path}") from error
    if not isinstance(value, dict):
        raise FinalPackageBuildError(f"JSON evidence must be an object: {path}")
    return value


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _required_string(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise FinalPackageBuildError(f"required evidence field is missing: {field}")
    return value


def _require_sha(field: str, value: str, length: int) -> None:
    if len(value) != length or any(character not in "0123456789abcdef" for character in value):
        raise FinalPackageBuildError(f"{field} is not a lowercase {length}-character digest")


def _require_file(path: Path) -> None:
    if not path.is_file():
        raise FinalPackageBuildError(f"required file is missing: {path}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    parser.add_argument("--final-source-commit", required=True)
    parser.add_argument("--workflow-run-id", required=True)
    parser.add_argument("--candidate-exact-validation", type=Path, required=True)
    parser.add_argument("--candidate-exact-artifact-id", required=True)
    parser.add_argument("--candidate-exact-artifact-digest", required=True)
    parser.add_argument("--decision-record-url", required=True)
    parser.add_argument("--review-record-url", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    build_final_package(
        repository_root=args.repository_root,
        final_source_commit=args.final_source_commit,
        workflow_run_id=args.workflow_run_id,
        candidate_exact_validation_path=args.candidate_exact_validation,
        candidate_exact_artifact_id=args.candidate_exact_artifact_id,
        candidate_exact_artifact_digest=args.candidate_exact_artifact_digest,
        decision_record_url=args.decision_record_url,
        review_record_url=args.review_record_url,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()