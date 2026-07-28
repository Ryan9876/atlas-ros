#!/usr/bin/env python3
"""Fail-closed validation for the committed Atlas ROS v7.1.0 production manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from atlas_ros.contracts.digests import sha256_digest

MANIFEST_PATH = Path("release/RELEASE_MANIFEST_V710.md")
CANDIDATE_PATH = Path("release/RELEASE_MANIFEST_V710_CANDIDATE.md")
SPECIFICATION_PATH = Path("release/specifications/V710.yaml")

REQUIRED_TEXT = (
    "# Atlas ROS v7.1.0 Immutable Release Manifest",
    "Package version: `7.1.0`",
    "Authority model version: `7.0`",
    "Atlas ROS v7.0.1 at `f26f5154ea6cd4b431c5a2638c439d7de9282761`",
    "Atlas ROS v6.5.0 at `bb6d6fea70d6824c9bc6a42e63ba36cc88029260`",
    "Atlas ROS v6.2.0 at `863d5ddf9ebd4723200166cf31c7acd93ebec54f`",
    "Integration Inventory authority: https://app.notion.com/p/8ba4fafb5ce244ef9add3013aff3746b",
    "Required production integrations are exactly GitHub, Notion, and Todoist.",
    "Google Drive is optional, non-authoritative historical access",
    "Publication does not activate authority.",
    "Authority activation follows independent publication readback.",
)

PROHIBITED_TEXT = (
    "Draft candidate only",
    "Status: Candidate only",
    "Production authorized: `false`",
    "Published: `false`",
    "Authority activated: `false`",
    "This document does not activate production authority",
)


def validate_manifest(root: Path, source_commit: str) -> dict[str, object]:
    """Validate the immutable production manifest and return a digest-bound receipt."""
    if re.fullmatch(r"[0-9a-f]{40}", source_commit) is None:
        raise ValueError("source commit must be an exact lowercase 40-character SHA")

    manifest_path = root / MANIFEST_PATH
    candidate_path = root / CANDIDATE_PATH
    specification_path = root / SPECIFICATION_PATH
    for path in (manifest_path, candidate_path, specification_path):
        if not path.is_file():
            raise ValueError(f"required release input is missing: {path.relative_to(root)}")

    manifest = manifest_path.read_text(encoding="utf-8")
    candidate = candidate_path.read_text(encoding="utf-8")
    specification = specification_path.read_text(encoding="utf-8")

    missing = [text for text in REQUIRED_TEXT if text not in manifest]
    if missing:
        raise ValueError("production manifest is missing required text: " + "; ".join(missing))
    present = [text for text in PROHIBITED_TEXT if text in manifest]
    if present:
        raise ValueError("production manifest contains candidate-only text: " + "; ".join(present))

    if "Draft candidate only" not in candidate or "Production authorized: `false`" not in candidate:
        raise ValueError("historical candidate manifest no longer identifies itself as candidate evidence")
    if "version: 7.1.0" not in specification:
        raise ValueError("release specification does not identify version 7.1.0")
    if "candidate_only: true" not in specification:
        raise ValueError("release compiler specification must remain candidate-only")

    raw = manifest_path.read_bytes()
    return {
        "schema_version": "1.0",
        "status": "passed",
        "release_version": "7.1.0",
        "source_commit": source_commit,
        "manifest_path": MANIFEST_PATH.as_posix(),
        "manifest_raw_sha256": hashlib.sha256(raw).hexdigest(),
        "manifest_canonical_sha256": sha256_digest(manifest),
        "candidate_manifest_path": CANDIDATE_PATH.as_posix(),
        "compiler_specification_path": SPECIFICATION_PATH.as_posix(),
        "compiler_candidate_only": True,
        "production_authorized": False,
        "published": False,
        "authority_activated": False,
        "required_integrations": ["GitHub", "Notion", "Todoist"],
        "optional_integrations": ["Google Drive"],
        "immediate_rollback": {
            "version": "7.0.1",
            "commit": "f26f5154ea6cd4b431c5a2638c439d7de9282761",
        },
        "historical_rollbacks": [
            {"version": "6.5.0", "commit": "bb6d6fea70d6824c9bc6a42e63ba36cc88029260"},
            {"version": "6.2.0", "commit": "863d5ddf9ebd4723200166cf31c7acd93ebec54f"},
        ],
        "provider_writes": 0,
        "destructive_actions": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    receipt = validate_manifest(args.root.resolve(), args.source_commit)
    payload = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")


if __name__ == "__main__":
    main()
