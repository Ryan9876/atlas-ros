"""Canonical operational-record identity and normalized read models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from .base import (
    AcceptanceState,
    AuthoritativeSystem,
    DigestBoundModel,
    OperationalRecordType,
)


class OperationalRecordRefV1(DigestBoundModel):
    digest_field = "source_digest"

    contract_id: Literal["atlas.operational-record-ref"] = "atlas.operational-record-ref"
    schema_version: Literal["1.0"] = "1.0"
    record_type: OperationalRecordType
    canonical_record_id: str = Field(min_length=1, max_length=512)
    authoritative_system: AuthoritativeSystem
    canonical_url: str | None = Field(default=None, max_length=2_000)
    parent_record_id: str | None = Field(default=None, max_length=512)
    source_revision: str = Field(min_length=1, max_length=512)
    source_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(
        cls,
        *,
        record_type: OperationalRecordType,
        canonical_record_id: str,
        authoritative_system: AuthoritativeSystem,
        source_revision: str,
        canonical_url: str | None = None,
        parent_record_id: str | None = None,
    ) -> OperationalRecordRefV1:
        values: dict[str, Any] = {
            "record_type": record_type,
            "canonical_record_id": canonical_record_id,
            "authoritative_system": authoritative_system,
            "canonical_url": canonical_url,
            "parent_record_id": parent_record_id,
            "source_revision": source_revision,
        }
        return cls(source_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_digest(self) -> OperationalRecordRefV1:
        if not self.verify_digest():
            raise ValueError("operational record source digest mismatch")
        return self


class NormalizedOperationalRecordV1(DigestBoundModel):
    """Provider-neutral operational record used by all awareness capabilities."""

    digest_field = "record_digest"

    contract_id: Literal["atlas.normalized-operational-record"] = (
        "atlas.normalized-operational-record"
    )
    schema_version: Literal["1.0"] = "1.0"
    record_ref: OperationalRecordRefV1
    title: str = Field(min_length=1, max_length=1_000)
    observed_state: str = Field(default="", max_length=200)
    owner: str | None = Field(default=None, max_length=300)
    responsible_party: str | None = Field(default=None, max_length=300)
    accountable_party: str | None = Field(default=None, max_length=300)
    definition_of_done: tuple[str, ...] = ()
    completion_evidence: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    due_date: str | None = None
    checkpoint: str | None = None
    priority: int = Field(default=4, ge=1, le=4)
    child_ids: tuple[str, ...] = ()
    delegated: bool = False
    acceptance_status: AcceptanceState = AcceptanceState.NOT_REQUIRED
    updated_at: str | None = None
    completed: bool = False
    technically_complete: bool = False
    approval_required: bool = False
    approval_received: bool = False
    cancelled: bool = False
    protected_history: bool = False
    todoist_task_id: str | None = None
    expected_outcome: str | None = None
    delegate_due: str | None = None
    follow_up_checkpoint: str | None = None
    todoist_checkpoint_id: str | None = None
    todoist_checkpoint_url: str | None = None
    source_update: str | None = None
    command_digest: str | None = None
    idempotency_identity: str | None = None
    latest_reconciliation_state: str | None = None
    received_evidence: tuple[str, ...] = ()
    extra: dict[str, Any] = Field(default_factory=dict)
    record_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> NormalizedOperationalRecordV1:
        return cls(record_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_record(self) -> NormalizedOperationalRecordV1:
        if not self.record_ref.verify_digest():
            raise ValueError("normalized record contains invalid record reference")
        if len(set(self.child_ids)) != len(self.child_ids):
            raise ValueError("normalized record contains duplicate child IDs")
        if not self.verify_digest():
            raise ValueError("normalized record digest mismatch")
        return self
