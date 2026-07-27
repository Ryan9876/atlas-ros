"""Provider-neutral snapshots used to verify live v7 dynamic authorities."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SystemStateSnapshot(BaseModel):
    """Minimal live System State projection required for initialization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

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
    current: bool
    least_privilege_verified: bool


class IntegrationInventorySnapshot(BaseModel):
    """Minimal live Integration Inventory projection required for initialization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    integrations: tuple[IntegrationStatusSnapshot, ...] = Field(min_length=1)
    last_verified_at: datetime

    @model_validator(mode="after")
    def validate_unique_names(self) -> IntegrationInventorySnapshot:
        names = tuple(item.name for item in self.integrations)
        if len(set(names)) != len(names):
            raise ValueError("integration inventory contains duplicate names")
        return self
