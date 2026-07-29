"""Provider-neutral immutable operational snapshot construction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Iterable

from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.contracts.operational_awareness import (
    EvidenceConflictV1,
    NormalizedOperationalRecordV1,
    OperationalSnapshotV1,
)
from atlas_ros.policy.operational_awareness import OperationalAwarenessPolicy


@dataclass(frozen=True, slots=True)
class OperationalSnapshotBuilder:
    policy: OperationalAwarenessPolicy

    def build(
        self,
        records: Iterable[NormalizedOperationalRecordV1],
        *,
        scope: str,
        authority_identities: tuple[str, ...],
        missing_sources: tuple[str, ...] = (),
        contradictions: tuple[EvidenceConflictV1, ...] = (),
        generated_at: datetime | None = None,
        replay_id: str | None = None,
    ) -> OperationalSnapshotV1:
        now = generated_at or datetime.now(UTC)
        ordered = tuple(
            sorted(records, key=lambda item: item.record_ref.canonical_record_id)
        )
        source_digests = tuple(item.record_digest for item in ordered)
        seed = {
            "scope": scope,
            "generated_time": now.isoformat(),
            "authority_identities": authority_identities,
            "policy_registry_digest": self.policy.policy_digest,
            "source_record_digests": source_digests,
            "missing_sources": missing_sources,
            "contradictions": [item.conflict_digest for item in contradictions],
        }
        snapshot_id = f"operational-snapshot:{sha256_digest(seed)}"
        return OperationalSnapshotV1.create(
            snapshot_id=snapshot_id,
            scope=scope,
            generated_time=now.isoformat(),
            authority_identities=authority_identities,
            policy_registry_digest=self.policy.policy_digest,
            source_record_digests=source_digests,
            normalized_records=ordered,
            missing_sources=missing_sources,
            contradictions=contradictions,
            replay_id=replay_id or snapshot_id,
        )
