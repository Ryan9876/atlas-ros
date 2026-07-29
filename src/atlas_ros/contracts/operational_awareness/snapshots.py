"""Immutable operational snapshot contracts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from .base import DigestBoundModel
from .evidence import EvidenceConflictV1
from .records import NormalizedOperationalRecordV1


class OperationalSnapshotV1(DigestBoundModel):
    digest_field = "snapshot_digest"

    contract_id: Literal["atlas.operational-snapshot"] = "atlas.operational-snapshot"
    schema_version: Literal["1.0"] = "1.0"
    snapshot_id: str = Field(min_length=1, max_length=512)
    scope: str = Field(min_length=1, max_length=500)
    generated_time: str
    authority_identities: tuple[str, ...]
    policy_registry_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_record_digests: tuple[str, ...]
    normalized_records: tuple[NormalizedOperationalRecordV1, ...]
    missing_sources: tuple[str, ...] = ()
    contradictions: tuple[EvidenceConflictV1, ...] = ()
    snapshot_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    replay_id: str = Field(min_length=1, max_length=512)

    @classmethod
    def create(cls, **values: Any) -> OperationalSnapshotV1:
        return cls(snapshot_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_snapshot(self) -> OperationalSnapshotV1:
        identities = tuple(
            record.record_ref.canonical_record_id for record in self.normalized_records
        )
        if identities != tuple(sorted(identities)):
            raise ValueError("snapshot records must be sorted by canonical identity")
        expected = tuple(record.record_digest for record in self.normalized_records)
        if self.source_record_digests != expected:
            raise ValueError("snapshot source digests do not match normalized records")
        if not self.verify_digest():
            raise ValueError("operational snapshot digest mismatch")
        return self
