"""Canonical v7 lineage contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from atlas_ros.contracts.digests import sha256_digest


class CaptureEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_id: Literal["atlas.capture-envelope"] = "atlas.capture-envelope"
    schema_version: Literal["1.0"] = "1.0"
    correlation_id: UUID = Field(default_factory=uuid4)
    source: str = Field(min_length=1, max_length=128)
    content: str = Field(min_length=1, max_length=50_000)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def input_digest(self) -> str:
        return sha256_digest(self.model_dump(mode="json", exclude={"created_at"}))


class PipelineRunEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_id: Literal["atlas.pipeline-run-envelope"] = "atlas.pipeline-run-envelope"
    schema_version: Literal["1.0"] = "1.0"
    run_id: UUID = Field(default_factory=uuid4)
    correlation_id: UUID
    release_version: str
    source_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    authority_model_version: Literal["7.0"] = "7.0"
    initializer_version: str
    contract_catalog_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy_registry_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    capability_catalog_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    input_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    stage_digests: dict[str, str] = Field(default_factory=dict)
    authorization_id: str | None = None
    execution_transaction_id: str | None = None
    provider_operation_receipts: tuple[str, ...] = ()
    readback_results: tuple[str, ...] = ()
    reconciliation_receipt: str | None = None
    warnings: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    completion_state: Literal["completed", "blocked", "failed"] = "completed"
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_state(self) -> PipelineRunEnvelope:
        if self.completion_state == "completed" and self.blockers:
            raise ValueError("completed pipeline cannot retain blockers")
        if self.execution_transaction_id and not self.authorization_id:
            raise ValueError("execution transaction requires authorization")
        return self
