#!/usr/bin/env python3
"""Validate the only Drive dependency required for v7 promotion readiness."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


class CurrentDriveAuthorityError(ValueError):
    """Raised when current Drive authority migration evidence is unsafe."""


def canonical_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _fail(message: str) -> None:
    raise CurrentDriveAuthorityError(message)


def _sha(value: Any, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail(f"{field} must be a lowercase SHA-256")
    return value


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CurrentDriveAuthorityError(f"invalid JSON evidence: {path}") from error
    if not isinstance(value, dict):
        _fail(f"JSON evidence must be an object: {path}")
    return value


def validate_current_drive_authority(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the scoped current-authority migration evidence."""
    if payload.get("schema_version") != "1.0":
        _fail("current Drive authority schema_version must be 1.0")
    if payload.get("generated_for_release") != "7.0.0rc1":
        _fail("current Drive authority evidence must target 7.0.0rc1")

    source = payload.get("source_bootstrap")
    if not isinstance(source, dict):
        _fail("source_bootstrap must be an object")
    if source.get("drive_id") != "1F8fXT9oLtXnorbyL--5Vw0Ajo6MyW0Xk":
        _fail("unexpected Drive Release Index ID")
    if source.get("title") != "RELEASE_INDEX.md":
        _fail("unexpected Drive bootstrap title")
    if source.get("github_target") != "governance/RELEASE_INDEX.md":
        _fail("unexpected GitHub Release Index target")

    drive_sha = _sha(source.get("drive_content_sha256"), "Drive bootstrap SHA-256")
    github_sha = _sha(source.get("github_content_sha256"), "GitHub bootstrap SHA-256")
    if drive_sha != github_sha or source.get("content_equivalent") is not True:
        _fail("Drive and GitHub Release Index evidence is not equivalent")
    if source.get("migration_status") != "staged":
        _fail("current bootstrap migration must remain staged before activation")
    if source.get("disposition") != "retire_after_v7_activation":
        _fail("current bootstrap may retire only after v7 activation")

    if payload.get("current_drive_dependency_count") != 1:
        _fail("current Drive dependency count must be exactly one")
    if payload.get("promotion_scope_complete") is not True:
        _fail("current Drive authority promotion scope is incomplete")
    if payload.get("pre_v6_history_required_for_promotion") is not False:
        _fail("pre-v6 history cannot be required for v7 promotion")
    if payload.get("provider_writes") != 0:
        _fail("current authority validation cannot record provider writes")
    if payload.get("drive_retirement_authorized") is not False:
        _fail("current authority evidence cannot authorize Drive retirement")

    evidence_sha = _sha(
        payload.get("authority_migration_sha256"),
        "authority_migration_sha256",
    )
    unsigned = dict(payload)
    unsigned.pop("authority_migration_sha256", None)
    if evidence_sha != canonical_sha256(unsigned):
        _fail("current Drive authority evidence digest mismatch")

    return {
        "schema_version": "1.0",
        "status": "current_drive_authority_migration_ready",
        "authority_migration_sha256": evidence_sha,
        "current_drive_dependency_count": 1,
        "promotion_scope_complete": True,
        "pre_v6_history_required_for_promotion": False,
        "provider_writes": 0,
        "drive_retirement_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = validate_current_drive_authority(_read_json(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
