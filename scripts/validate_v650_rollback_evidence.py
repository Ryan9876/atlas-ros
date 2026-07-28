#!/usr/bin/env python3
"""Generate reconciled Atlas ROS v6.5 rollback evidence from immutable assets."""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import tomllib
from pathlib import Path

from tools.release.rollback_evidence import (
    RollbackEvidenceReceipt,
    RollbackPackageEvidence,
    load_receipt,
    reconcile_v650_rollback,
    write_receipt,
)

_MANIFEST_VERSION = re.compile(r"Atlas ROS v(\d+\.\d+\.\d+)")


class RollbackEvidenceValidationError(ValueError):
    """Raised when immutable rollback assets cannot be reconciled."""


def validate_v650_rollback_evidence(
    *,
    repository_root: Path,
    source_commit: str,
    release_assets_dir: Path,
    clean_install_version: str,
    restoration_passed: bool,
    metadata_exception_record_url: str,
    output_path: Path,
) -> RollbackEvidenceReceipt:
    """Verify immutable v6.5 evidence and write a deterministic receipt."""
    package_text = _git_show(repository_root, source_commit, "pyproject.toml")
    manifest_text = _git_show(
        repository_root,
        source_commit,
        "release/RELEASE_MANIFEST.md",
    )
    package_version = str(tomllib.loads(package_text)["project"]["version"])
    manifest_match = _MANIFEST_VERSION.search(manifest_text)
    if manifest_match is None:
        raise RollbackEvidenceValidationError(
            "immutable rollback manifest does not declare an Atlas ROS version"
        )
    manifest_version = manifest_match.group(1)
    commit_message = _git(
        repository_root,
        "show",
        "-s",
        "--format=%s",
        source_commit,
    ).strip()
    tag_commit = _git(repository_root, "rev-list", "-n", "1", "v6.5.0").strip()
    release_tag_points_to_source = tag_commit == source_commit

    checksum_path = release_assets_dir / "CHECKSUMS.sha256"
    checksums_passed = _verify_checksums(release_assets_dir, checksum_path)
    wheel = _single_asset(release_assets_dir, "atlas_ros-6.5.0*.whl", "wheel")
    source = _source_asset(release_assets_dir)
    release_asset_version = _asset_version(wheel.name)
    source_sha256 = _sha256(source)
    wheel_sha256 = _sha256(wheel)
    manifest_sha256 = hashlib.sha256(manifest_text.encode("utf-8")).hexdigest()

    evidence = RollbackPackageEvidence(
        target_version="6.5.0",
        target_tag="v6.5.0",
        source_commit=source_commit,
        source_commit_message=commit_message,
        package_version=package_version,
        manifest_declared_version=manifest_version,
        manifest_sha256=manifest_sha256,
        release_asset_version=release_asset_version,
        release_tag_points_to_source=release_tag_points_to_source,
        published_release_readable=True,
        publication_checksums_passed=checksums_passed,
        source_archive_sha256=source_sha256,
        wheel_sha256=wheel_sha256,
        clean_install_version=clean_install_version,
        clean_install_passed=clean_install_version == "6.5.0",
        restoration_tests_passed=restoration_passed,
        metadata_exception_record_url=metadata_exception_record_url,
        metadata_exception_acknowledges_manifest_mismatch=(
            manifest_version != package_version
        ),
        provider_writes_during_validation=0,
    )
    receipt = reconcile_v650_rollback(evidence)
    write_receipt(evidence, receipt, output_path)
    readback = load_receipt(output_path)
    if readback != receipt:
        raise RollbackEvidenceValidationError(
            "rollback evidence failed deterministic readback"
        )
    return receipt


def _verify_checksums(root: Path, checksum_path: Path) -> bool:
    if not checksum_path.is_file():
        raise RollbackEvidenceValidationError("v6.5 release CHECKSUMS.sha256 is missing")
    entries = 0
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            expected, relative = line.split("  ", 1)
        except ValueError as error:
            raise RollbackEvidenceValidationError(
                "v6.5 release checksum line is malformed"
            ) from error
        path = root / relative
        if not path.is_file() or _sha256(path) != expected:
            raise RollbackEvidenceValidationError(
                f"v6.5 release checksum failed: {relative}"
            )
        entries += 1
    if entries < 2:
        raise RollbackEvidenceValidationError(
            "v6.5 release checksum inventory is incomplete"
        )
    return True


def _source_asset(root: Path) -> Path:
    candidates = sorted(
        path
        for pattern in ("atlas_ros-6.5.0*.tar.gz", "Atlas_ROS_v6.5.0*.zip")
        for path in root.glob(pattern)
    )
    if len(candidates) != 1:
        raise RollbackEvidenceValidationError(
            "expected exactly one v6.5 source or restoration archive"
        )
    return candidates[0]


def _single_asset(root: Path, pattern: str, label: str) -> Path:
    candidates = sorted(root.glob(pattern))
    if len(candidates) != 1:
        raise RollbackEvidenceValidationError(
            f"expected exactly one v6.5 {label} asset"
        )
    return candidates[0]


def _asset_version(name: str) -> str:
    match = re.search(r"6\.5\.0", name)
    if match is None:
        raise RollbackEvidenceValidationError(
            "v6.5 release asset filename does not identify version 6.5.0"
        )
    return match.group(0)


def _git_show(root: Path, commit: str, path: str) -> str:
    return _git(root, "show", f"{commit}:{path}")


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RollbackEvidenceValidationError(
            f"git evidence read failed: {' '.join(args)}: {completed.stderr.strip()}"
        )
    return completed.stdout


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--release-assets-dir", type=Path, required=True)
    parser.add_argument("--clean-install-version", required=True)
    parser.add_argument("--restoration-passed", action="store_true")
    parser.add_argument("--metadata-exception-record-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = validate_v650_rollback_evidence(
        repository_root=args.repository_root,
        source_commit=args.source_commit,
        release_assets_dir=args.release_assets_dir,
        clean_install_version=args.clean_install_version,
        restoration_passed=args.restoration_passed,
        metadata_exception_record_url=args.metadata_exception_record_url,
        output_path=args.output,
    )
    if receipt.status != "ready":
        raise SystemExit("; ".join(receipt.blockers))


if __name__ == "__main__":
    main()
