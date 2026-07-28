"""GitHub-only authority record validation for Atlas ROS v7."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, model_validator

from atlas_ros.kernel.digests import sha256_digest


class ImmutableRelease(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str = Field(pattern=r"^v?\d+\.\d+\.\d+$")
    immutable_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    tag: str = Field(pattern=r"^v\d+\.\d+\.\d+$")
    release_url: AnyHttpUrl


class ActiveRelease(ImmutableRelease):
    status: Literal["Active"]
    manifest_path: Literal["release/RELEASE_MANIFEST.md"]
    manifest_url: AnyHttpUrl
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    wheel_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ReleaseIndexReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Literal["governance/RELEASE_INDEX.md"]
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class IntegrityMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    algorithm: Literal["sha256"]
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class AuthorityRecord(BaseModel):
    """Canonical v7 bootstrap record, intentionally independent of Drive."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    repository: Literal["Ryan9876/atlas-ros"]
    authority_model_version: Literal["7.0"]
    minimum_compatible_initializer_version: str
    active_release: ActiveRelease
    immediate_rollback: ImmutableRelease
    historical_rollbacks: tuple[ImmutableRelease, ...] = ()
    notion_system_state_url: AnyHttpUrl
    integration_inventory_resolution: Literal["active-release-manifest"]
    release_index: ReleaseIndexReference
    last_promotion_transaction_id: str
    last_verified_at: str
    integrity: IntegrityMetadata

    @model_validator(mode="after")
    def verify_integrity(self) -> AuthorityRecord:
        payload = self.model_dump(
            mode="json",
            exclude={"integrity"},
            exclude_defaults=True,
        )
        if sha256_digest(canonical_authority_payload(payload)) != self.integrity.content_sha256:
            raise ValueError("authority integrity digest does not match")
        if self.active_release.version == self.immediate_rollback.version:
            raise ValueError("active release cannot also be immediate rollback")
        return self


def canonical_authority_payload(value: Any) -> Any:
    """Return the canonical representation used for authority integrity digests."""
    return _canonicalize_urls(value)


def _canonicalize_urls(value: Any, *, key: str = "") -> Any:
    """Normalize equivalent URL values before deterministic authority hashing."""
    if isinstance(value, dict):
        return {
            item_key: _canonicalize_urls(item, key=item_key)
            for item_key, item in value.items()
        }
    if isinstance(value, list):
        return [_canonicalize_urls(item, key=key) for item in value]
    if key.endswith("_url") and isinstance(value, str):
        return value.rstrip("/")
    return value
