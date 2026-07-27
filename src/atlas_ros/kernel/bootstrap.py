"""GitHub-first, provider-neutral authority bootstrap verification."""

from __future__ import annotations

import json
from pathlib import PurePosixPath
from typing import Any

from atlas_ros.kernel.authority import AuthorityRecord
from atlas_ros.kernel.context import InitializationContext
from atlas_ros.kernel.digests import sha256_digest
from atlas_ros.ports.authority import AuthorityReader

_AUTHORITY_PATH = PurePosixPath("governance/AUTHORITY.json")
_RELEASE_INDEX_PATH = PurePosixPath("governance/RELEASE_INDEX.md")


class InitializationError(ValueError):
    """Raised when authoritative initialization evidence is incomplete or contradictory."""


def render_release_index(authority: AuthorityRecord) -> str:
    """Render the only supported human-readable projection of the authority record."""
    active = authority.active_release
    rollback = authority.immediate_rollback
    return (
        "# Atlas ROS Release Index\n\n"
        "This file is generated from `governance/AUTHORITY.json`; do not edit it directly.\n\n"
        "## Active Release\n\n"
        f"- Version: `{active.version}`\n"
        f"- Status: `{active.status}`\n"
        f"- Immutable commit: `{active.immutable_commit}`\n"
        f"- Tag: `{active.tag}`\n"
        f"- Manifest: `{active.manifest_path}`\n"
        f"- Release: {active.release_url}\n\n"
        "## Immediate Rollback\n\n"
        f"- Version: `{rollback.version}`\n"
        f"- Immutable commit: `{rollback.immutable_commit}`\n"
        f"- Tag: `{rollback.tag}`\n"
        f"- Release: {rollback.release_url}\n"
    )


def _parse_authority(text: str) -> AuthorityRecord:
    try:
        raw: Any = json.loads(text)
    except json.JSONDecodeError as error:
        raise InitializationError("AUTHORITY.json is not valid JSON") from error
    try:
        return AuthorityRecord.model_validate(raw)
    except ValueError as error:
        raise InitializationError(f"AUTHORITY.json is invalid: {error}") from error


def initialize(reader: AuthorityReader) -> InitializationContext:
    """Verify the GitHub authority record and all deterministic repository evidence.

    Dynamic Notion reads are deliberately left to the Notion adapter/application layer: this
    kernel function guarantees that all GitHub-controlled evidence agrees before that read.
    """
    authority = _parse_authority(reader.read_text(_AUTHORITY_PATH, ref="HEAD"))
    active = authority.active_release
    if active.tag != f"v{active.version.removeprefix('v')}":
        raise InitializationError("active release version and tag disagree")
    if not str(active.manifest_url).endswith(\n        active.manifest_path\n    ):
        raise InitializationError("active manifest URL does not resolve to the declared manifest path")

    release_index = reader.read_text(_RELEASE_INDEX_PATH, ref=active.immutable_commit)
    if sha256_digest(release_index) != authority.release_index.sha256:
        raise InitializationError(\n            "generated RELEASE_INDEX.md digest does not match AUTHORITY.json"\n        )
    expected_index = render_release_index(authority)
    if release_index != expected_index:
        raise InitializationError("RELEASE_INDEX.md is not the generated authority projection")

    manifest = reader.read_text(PurePosixPath(active.manifest_path), ref=active.immutable_commit)
    if active.version not in manifest or active.immutable_commit not in manifest:
        raise InitializationError("active manifest does not identify the authoritative release and commit")
    inventory_url = _integration_inventory_url(manifest)
    return InitializationContext(
        authority=authority,
        release_index_markdown=release_index,
        release_manifest_markdown=manifest,
        system_state_url=str(authority.notion_system_state_url),
        integration_inventory_url=inventory_url,
    )


def _integration_inventory_url(manifest: str) -> str:
    marker = "Integration Inventory authority:"
    for line in manifest.splitlines():
        if line.strip().startswith(marker):
            url = line.split(marker, 1)[1].strip()
            if url.startswith("https://"):
                return url
    raise InitializationError("active manifest does not provide the Integration Inventory URL")
