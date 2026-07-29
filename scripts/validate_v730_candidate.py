#!/usr/bin/env python3
"""Validate one exact v7.3.0 package tree without rebuilding or publishing."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


class CandidateValidationError(ValueError):
    """Raised when exact candidate evidence is incomplete or unsafe."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CandidateValidationError(f"expected JSON object: {path}")
    return value


def validate(package_root: Path, source_commit: str) -> dict[str, Any]:
    checksums = package_root / "SHA256SUMS"
    if not checksums.is_file():
        raise CandidateValidationError("nested SHA256SUMS is missing")
    for line in checksums.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, relative = line.split("  ", 1)
        path = package_root / relative
        if not path.is_file() or _sha256(path) != digest:
            raise CandidateValidationError(f"checksum failed: {relative}")
    identity = _read(package_root / "FINAL_PACKAGE_IDENTITY.json")
    source_manifest = _read(package_root / "SOURCE_MANIFEST_FINAL.json")
    manifest = _read(package_root / "RELEASE_MANIFEST_V730_CANDIDATE.json")
    performance = _read(package_root / "performance.json")
    migration = _read(package_root / "migration-validation.json")
    validation = _read(package_root / "validation-summary.json")
    if identity.get("candidate_commit") != source_commit:
        raise CandidateValidationError("candidate identity does not match exact source commit")
    if source_manifest.get("source_commit") != source_commit:
        raise CandidateValidationError("source manifest does not match exact source commit")
    if identity.get("release_version") != "7.3.0" or manifest.get("release_version") != "7.3.0":
        raise CandidateValidationError("candidate version is not v7.3.0")
    if identity.get("source_sha256") != source_manifest.get("sdist_sha256"):
        raise CandidateValidationError("source checksum identity mismatch")
    if identity.get("wheel_sha256") != source_manifest.get("wheel_sha256"):
        raise CandidateValidationError("wheel checksum identity mismatch")
    if identity.get("manifest_digest") != manifest.get("manifest_digest"):
        raise CandidateValidationError("manifest digest identity mismatch")
    if performance.get("status") != "passed" or migration.get("status") != "validated_unapplied":
        raise CandidateValidationError("performance or migration evidence is not passing")
    if validation.get("status") != "passed":
        raise CandidateValidationError("mandatory validation summary is not passing")
    prohibited_truthy = (
        "production_promotion_authorized",
        "final_tag_created",
        "final_release_published",
        "authority_activated",
        "production_notion_schema_changed",
        "credentials_changed",
        "integration_scope_expanded",
    )
    if any(identity.get(field) for field in prohibited_truthy):
        raise CandidateValidationError("candidate claims a prohibited live action")
    zero_fields = (
        "provider_writes",
        "todoist_tasks_created",
        "messages_sent",
        "scheduled_operations",
        "records_deleted",
    )
    if any(identity.get(field) != 0 for field in zero_fields):
        raise CandidateValidationError("candidate validation was not zero-write")
    if identity.get("build_count") != 1 or source_manifest.get("build_count") != 1:
        raise CandidateValidationError("candidate was not built exactly once")
    result = {
        "schema_version": "1.0",
        "status": "passed",
        "completion_state": "IMPLEMENTATION READY FOR RYAN PROMOTION REVIEW",
        "candidate_commit": source_commit,
        "source_sha256": identity["source_sha256"],
        "wheel_sha256": identity["wheel_sha256"],
        "manifest_digest": identity["manifest_digest"],
        "provider_writes": 0,
        "build_count": 1,
        "promotion_authorized": False,
        "published": False,
        "authority_activated": False,
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.package_root, args.source_commit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
