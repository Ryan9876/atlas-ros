"""Provider-neutral snapshots and receipts for live v7 authority initialization."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SystemStateSnapshot(BaseModel):
    """Minimal live System State projection required for initialization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    active_version: str
    immediate_rollback_version: str
    authority_model_version: Literal["7.0"]
    published_workspace_valid: bool
    last_verified_at: datetime


class IntegrationStatusSnapshot(BaseModel):
    """Governed status of one integration at initialization time."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1, max_length=128)
    required: bool
    connection_status: Literal["connected", "disconnected", "degraded", "error"]
    approval_status: Literal["approved", "pending", "not_required", "denied"]
    acceptance_status: Literal["passed", "partial", "not_run", "failed"]
    lifecycle_status: Literal[
        "production",
        "validated_not_active",
        "contract_only",
        "prohibited",
        "paused",
        "retired",
    ] = "production"
    current: bool
    least_privilege_verified: bool


class IntegrationInventorySnapshot(BaseModel):
    """Minimal live Integration Inventory projection required for initialization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    integrations: tuple[IntegrationStatusSnapshot, ...] = Field(min_length=1)
    last_verified_at: datetime

    @model_validator(mode="after")
    def validate_unique_names(self) -> IntegrationInventorySnapshot:
        names = tuple(item.name for item in self.integrations)
        if len(set(names)) != len(names):
            raise ValueError("integration inventory contains duplicate names")
        return self


class InitializationStageTiming(BaseModel):
    """Elapsed time for one deterministic initialization stage."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    stage: str = Field(min_length=1, max_length=128)
    elapsed_ms: float = Field(ge=0)


class InitializationIntegrationResult(BaseModel):
    """Compact governed and live state for one required integration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    inventory_ready: bool
    live_readable: bool


class InitializationReceipt(BaseModel):
    """Compact non-authoritative receipt for one Quick Initialization attempt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    status: Literal["READY", "READY_WITH_WARNINGS", "INITIALIZATION_BLOCKED"]
    active_version: str | None = None
    active_commit: str | None = None
    immediate_rollback_version: str | None = None
    immediate_rollback_commit: str | None = None
    authority_model_version: str | None = None
    authority_agreement: bool = False
    release_index_digest_valid: bool = False
    manifest_digest_valid: bool = False
    system_state_agreement: bool = False
    published_workspace_valid: bool = False
    required_integrations: tuple[InitializationIntegrationResult, ...] = ()
    execution_path: Literal["cold", "warm", "warm_fallback_to_cold"] = "cold"
    cache_hit: bool = False
    cache_rejection_reason: str | None = None
    stage_timings: tuple[InitializationStageTiming, ...] = ()
    total_elapsed_ms: float = Field(ge=0)
    authority_last_verified_at: datetime | None = None
    system_state_last_verified_at: datetime | None = None
    inventory_last_verified_at: datetime | None = None
    warnings: tuple[str, ...] = ()
    blocked_condition: str | None = None
    provider_writes: Literal[0] = 0
    google_drive_reads: Literal[0] = 0
