"""Version-neutral declarative release specification contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from atlas_ros.contracts.digests import sha256_digest


class ReleaseIdentity(BaseModel):
    """Immutable identity for a release or rollback package."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    source_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    tag: str = Field(pattern=r"^v\d+\.\d+\.\d+$")

    @model_validator(mode="after")
    def validate_tag(self) -> ReleaseIdentity:
        if self.tag != f"v{self.version}":
            raise ValueError("release version and tag must agree")
        return self


class ReleaseSpecification(BaseModel):
    """One complete input to the version-neutral release compiler."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_id: Literal["atlas.release-specification"] = (
        "atlas.release-specification"
    )
    schema_version: Literal["1.0"] = "1.0"
    package_name: str = Field(min_length=1, max_length=128)
    identity: ReleaseIdentity
    authority_model_version: str = Field(pattern=r"^\d+\.\d+$")
    release_scope: tuple[str, ...] = Field(min_length=1)
    immediate_rollback: ReleaseIdentity
    historical_rollbacks: tuple[ReleaseIdentity, ...] = ()
    required_integrations: tuple[str, ...] = Field(min_length=1)
    optional_integrations: tuple[str, ...] = ()
    validation_profile: tuple[str, ...] = Field(min_length=1)
    artifact_requirements: tuple[str, ...] = Field(min_length=1)
    promotion_prerequisites: tuple[str, ...] = Field(min_length=1)
    publication_policy: tuple[str, ...] = Field(min_length=1)
    authority_activation_policy: tuple[str, ...] = Field(min_length=1)
    restoration_requirements: tuple[str, ...] = Field(min_length=1)
    migration_requirements: tuple[str, ...] = ()
    compatibility_rules: tuple[str, ...] = Field(min_length=1)
    notion_system_state_url: str = Field(pattern=r"^https://")
    integration_inventory_url: str = Field(pattern=r"^https://")
    candidate_only: Literal[True] = True
    specification_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: object) -> ReleaseSpecification:
        payload = dict(values)
        payload.pop("specification_digest", None)
        identity = ReleaseIdentity.model_validate(payload["identity"])
        immediate_rollback = ReleaseIdentity.model_validate(payload["immediate_rollback"])
        historical_rollbacks = tuple(
            ReleaseIdentity.model_validate(item)
            for item in payload.get("historical_rollbacks", ())
        )
        tuple_fields = (
            "release_scope",
            "required_integrations",
            "optional_integrations",
            "validation_profile",
            "artifact_requirements",
            "promotion_prerequisites",
            "publication_policy",
            "authority_activation_policy",
            "restoration_requirements",
            "migration_requirements",
            "compatibility_rules",
        )
        normalized = {
            **payload,
            **{
                field_name: tuple(payload.get(field_name, ()))
                for field_name in tuple_fields
            },
            "identity": identity,
            "immediate_rollback": immediate_rollback,
            "historical_rollbacks": historical_rollbacks,
        }
        provisional = cls.model_construct(
            contract_id="atlas.release-specification",
            schema_version="1.0",
            specification_digest="0" * 64,
            **normalized,
        )
        canonical = provisional.model_dump(
            mode="json",
            exclude={"specification_digest"},
            exclude_defaults=True,
        )
        normalized["specification_digest"] = sha256_digest(_spec_payload(canonical))
        return cls.model_validate(normalized)

    @model_validator(mode="after")
    def validate_specification(self) -> ReleaseSpecification:
        if self.identity.version == self.immediate_rollback.version:
            raise ValueError("candidate release cannot equal its immediate rollback")
        rollback_versions = (
            self.immediate_rollback.version,
            *(item.version for item in self.historical_rollbacks),
        )
        if len(set(rollback_versions)) != len(rollback_versions):
            raise ValueError("rollback release identities must be unique")
        for field_name in (
            "release_scope",
            "required_integrations",
            "optional_integrations",
            "validation_profile",
            "artifact_requirements",
            "promotion_prerequisites",
            "publication_policy",
            "authority_activation_policy",
            "restoration_requirements",
            "migration_requirements",
            "compatibility_rules",
        ):
            values = getattr(self, field_name)
            if len(set(values)) != len(values):
                raise ValueError(f"release specification contains duplicate {field_name}")
        if set(self.required_integrations) & set(self.optional_integrations):
            raise ValueError("required and optional integration sets must not overlap")
        if "Google Drive" in self.required_integrations:
            raise ValueError("Google Drive cannot be a required production integration")
        if set(self.required_integrations) != {"GitHub", "Notion", "Todoist"}:
            raise ValueError(
                "required production integrations must be GitHub, Notion, and Todoist"
            )
        payload = self.model_dump(
            mode="json",
            exclude={"specification_digest"},
            exclude_defaults=True,
        )
        if sha256_digest(_spec_payload(payload)) != self.specification_digest:
            raise ValueError("release specification digest does not match its fields")
        return self


class CompiledReleaseArtifact(BaseModel):
    """One deterministic compiler output."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=1, max_length=1024)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    media_type: str = Field(min_length=1, max_length=128)


class ReleaseCompilationReceipt(BaseModel):
    """Digest-bound evidence that a release specification compiled deterministically."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_id: Literal["atlas.release-compilation-receipt"] = (
        "atlas.release-compilation-receipt"
    )
    schema_version: Literal["1.0"] = "1.0"
    package_name: str
    release_version: str
    source_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    specification_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    compiler_version: str
    artifacts: tuple[CompiledReleaseArtifact, ...] = Field(min_length=1)
    output_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    production_authorized: Literal[False] = False
    published: Literal[False] = False
    authority_activated: Literal[False] = False
    provider_writes: Literal[0] = 0
    compiled_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_receipt(self) -> ReleaseCompilationReceipt:
        paths = tuple(item.path for item in self.artifacts)
        if len(set(paths)) != len(paths):
            raise ValueError("release compilation receipt contains duplicate artifact paths")
        payload = [item.model_dump(mode="json") for item in self.artifacts]
        if sha256_digest(payload) != self.output_digest:
            raise ValueError("release compilation output digest does not match artifacts")
        return self


def _spec_payload(value: object) -> object:
    if isinstance(value, dict):
        return {key: _spec_payload(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_spec_payload(item) for item in value]
    if isinstance(value, list):
        return [_spec_payload(item) for item in value]
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return value
