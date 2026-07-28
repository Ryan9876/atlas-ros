"""Build the staged GitHub authority record and generated release index for v7."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime

from atlas_ros.kernel.authority import (
    ActiveRelease,
    AuthorityRecord,
    ImmutableRelease,
    IntegrityMetadata,
    ReleaseIndexReference,
    canonical_authority_payload,
)
from atlas_ros.kernel.bootstrap import render_release_index
from atlas_ros.kernel.digests import sha256_digest


class AuthorityCompilationError(ValueError):
    """Raised when a proposed authority activation is incomplete or unsafe."""


@dataclass(frozen=True)
class ActiveReleaseSpec:
    version: str
    immutable_commit: str
    tag: str
    manifest_path: str
    manifest_url: str
    manifest_sha256: str
    release_url: str
    source_sha256: str
    wheel_sha256: str


@dataclass(frozen=True)
class RollbackReleaseSpec:
    version: str
    immutable_commit: str
    tag: str
    release_url: str


@dataclass(frozen=True)
class AuthorityCompilationSpec:
    active: ActiveReleaseSpec
    rollback: RollbackReleaseSpec
    notion_system_state_url: str
    last_promotion_transaction_id: str
    last_verified_at: str
    historical_rollbacks: tuple[RollbackReleaseSpec, ...] = ()


@dataclass(frozen=True)
class CompiledAuthority:
    record: AuthorityRecord
    authority_json: str
    release_index_markdown: str
    authority_sha256: str
    release_index_sha256: str


def compile_authority(spec: AuthorityCompilationSpec) -> CompiledAuthority:
    """Compile immutable activation inputs into mutually bound authority artifacts."""
    _validate_spec(spec)
    active = ActiveRelease.model_validate(
        {
            "version": spec.active.version,
            "status": "Active",
            "immutable_commit": spec.active.immutable_commit,
            "tag": spec.active.tag,
            "manifest_path": spec.active.manifest_path,
            "manifest_url": spec.active.manifest_url,
            "manifest_sha256": spec.active.manifest_sha256,
            "release_url": spec.active.release_url,
            "source_sha256": spec.active.source_sha256,
            "wheel_sha256": spec.active.wheel_sha256,
        }
    )
    rollback = _rollback_model(spec.rollback)
    historical = tuple(_rollback_model(item) for item in spec.historical_rollbacks)

    provisional = AuthorityRecord.model_construct(
        schema_version="1.0",
        repository="Ryan9876/atlas-ros",
        authority_model_version="7.0",
        minimum_compatible_initializer_version="7.0.1",
        active_release=active,
        immediate_rollback=rollback,
        historical_rollbacks=historical,
        notion_system_state_url=spec.notion_system_state_url,
        integration_inventory_resolution="active-release-manifest",
        release_index=ReleaseIndexReference(
            path="governance/RELEASE_INDEX.md",
            sha256="0" * 64,
        ),
        last_promotion_transaction_id=spec.last_promotion_transaction_id,
        last_verified_at=spec.last_verified_at,
        integrity=IntegrityMetadata(algorithm="sha256", content_sha256="0" * 64),
    )
    release_index = render_release_index(provisional)
    release_index_sha256 = sha256_digest(release_index)

    unsigned = AuthorityRecord.model_construct(
        schema_version="1.0",
        repository="Ryan9876/atlas-ros",
        authority_model_version="7.0",
        minimum_compatible_initializer_version="7.0.1",
        active_release=active,
        immediate_rollback=rollback,
        historical_rollbacks=historical,
        notion_system_state_url=spec.notion_system_state_url,
        integration_inventory_resolution="active-release-manifest",
        release_index=ReleaseIndexReference(
            path="governance/RELEASE_INDEX.md",
            sha256=release_index_sha256,
        ),
        last_promotion_transaction_id=spec.last_promotion_transaction_id,
        last_verified_at=spec.last_verified_at,
        integrity=IntegrityMetadata(algorithm="sha256", content_sha256="0" * 64),
    )
    payload = unsigned.model_dump(
        mode="json",
        exclude={"integrity"},
        exclude_defaults=True,
    )
    content_sha256 = sha256_digest(canonical_authority_payload(payload))
    payload["integrity"] = {"algorithm": "sha256", "content_sha256": content_sha256}
    record = AuthorityRecord.model_validate(payload)
    if render_release_index(record) != release_index:
        raise AuthorityCompilationError("generated release index changed after validation")

    authority_json = json.dumps(record.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    return CompiledAuthority(
        record=record,
        authority_json=authority_json,
        release_index_markdown=release_index,
        authority_sha256=sha256_digest(authority_json),
        release_index_sha256=release_index_sha256,
    )


def _rollback_model(spec: RollbackReleaseSpec) -> ImmutableRelease:
    return ImmutableRelease.model_validate(
        {
            "version": spec.version,
            "immutable_commit": spec.immutable_commit,
            "tag": spec.tag,
            "release_url": spec.release_url,
        }
    )


def _validate_spec(spec: AuthorityCompilationSpec) -> None:
    if re.fullmatch(r"7\.0\.\d+", spec.active.version) is None:
        raise AuthorityCompilationError("active release must be in the Atlas ROS 7.0 patch family")
    if spec.active.tag != f"v{spec.active.version}":
        raise AuthorityCompilationError("active release version and tag must agree")
    if re.fullmatch(r"release/RELEASE_MANIFEST_V\d{3,}\.md", spec.active.manifest_path) is None:
        raise AuthorityCompilationError("active manifest must use a versioned immutable path")
    if spec.rollback.version != "6.5.0" or spec.rollback.tag != "v6.5.0":
        raise AuthorityCompilationError("the v7.0 immediate rollback must be immutable v6.5.0")
    if spec.active.immutable_commit == spec.rollback.immutable_commit:
        raise AuthorityCompilationError("active and rollback commits must differ")
    expected_manifest_fragment = f"/{spec.active.immutable_commit}/{spec.active.manifest_path}"
    if expected_manifest_fragment not in spec.active.manifest_url:
        raise AuthorityCompilationError(
            "manifest URL must bind the exact active commit and manifest path"
        )
    if not spec.last_promotion_transaction_id.strip():
        raise AuthorityCompilationError("an exact promotion transaction ID is required")
    try:
        verified_at = datetime.fromisoformat(spec.last_verified_at.replace("Z", "+00:00"))
    except ValueError as error:
        raise AuthorityCompilationError("last_verified_at must be an ISO-8601 timestamp") from error
    if verified_at.tzinfo is None:
        raise AuthorityCompilationError("last_verified_at must include a timezone")
