from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from atlas_ros.intelligence.memory import (
    ConflictState,
    GovernedMemoryStore,
    MemoryPolicy,
    MemoryTier,
    PrivacyClass,
    RetrievalQuery,
)
from atlas_ros.intelligence.record_store import (
    RecordNotFoundError,
    SQLiteIntelligenceRecordStore,
)
from atlas_ros.intelligence.records import (
    AuthorityLevel,
    ContextSnapshot,
    EvidenceEnvelope,
    ValidationStatus,
)

NOW = datetime(2026, 7, 22, 5, 0, tzinfo=UTC)
HASH = "sha256:" + "a" * 64


def evidence(
    record_id: int, authority: AuthorityLevel, confidence: float = 0.9
) -> EvidenceEnvelope:
    return EvidenceEnvelope(
        record_id=UUID(f"00000000-0000-4000-8000-{record_id:012d}"),
        created_at=NOW,
        statement=f"Evidence {record_id}",
        source_authority=authority,
        confidence=confidence,
        observed_at=NOW,
        validation_status=ValidationStatus.VERIFIED,
        source_content_hash=HASH,
    )


def stores(tmp_path: Path) -> tuple[SQLiteIntelligenceRecordStore, GovernedMemoryStore]:
    records = SQLiteIntelligenceRecordStore(tmp_path / "records.db")
    records.initialize()
    memory = GovernedMemoryStore(tmp_path / "memory.db", records)
    memory.initialize()
    return records, memory


def test_policy_weights_must_sum_to_one() -> None:
    with pytest.raises(ValidationError, match="sum to 1.0"):
        MemoryPolicy(authority_weight=1.0)


def test_verified_primary_evidence_enters_governed_memory(tmp_path: Path) -> None:
    records, memory = stores(tmp_path)
    item = evidence(1, AuthorityLevel.PRIMARY)
    records.append(item)
    entry = memory.retain(
        item,
        subject="active release authority",
        privacy=PrivacyClass.INTERNAL,
        tags=("release", "authority"),
        retained_at=NOW,
    )
    assert entry.tier is MemoryTier.GOVERNED
    assert entry.expires_at is None


def test_context_is_working_memory_and_expires(tmp_path: Path) -> None:
    records, memory = stores(tmp_path)
    item = ContextSnapshot(
        record_id=UUID("00000000-0000-4000-8000-000000000002"),
        created_at=NOW,
        active_objective="Implement Milestone 4",
        decision_horizon="current session",
    )
    records.append(item)
    entry = memory.retain(
        item, subject="current objective", privacy=PrivacyClass.PERSONAL, retained_at=NOW
    )
    assert entry.tier is MemoryTier.WORKING
    assert entry.expires_at == NOW + timedelta(hours=24)
    assert memory.purge_expired(NOW + timedelta(days=2)) == 1


def test_low_confidence_evidence_is_rejected(tmp_path: Path) -> None:
    records, memory = stores(tmp_path)
    item = evidence(3, AuthorityLevel.UNVERIFIED, confidence=0.2)
    records.append(item)
    with pytest.raises(ValueError, match="below memory threshold"):
        memory.retain(item, subject="weak claim", privacy=PrivacyClass.INTERNAL, retained_at=NOW)


def test_retrieval_honors_privacy_and_authority_ranking(tmp_path: Path) -> None:
    records, memory = stores(tmp_path)
    primary = evidence(4, AuthorityLevel.PRIMARY, confidence=0.95)
    inferred = evidence(5, AuthorityLevel.INFERRED, confidence=0.95)
    records.append_many((primary, inferred))
    memory.retain(
        primary,
        subject="release status",
        privacy=PrivacyClass.INTERNAL,
        tags=("release",),
        retained_at=NOW,
    )
    memory.retain(
        inferred,
        subject="release guess",
        privacy=PrivacyClass.PERSONAL,
        tags=("release",),
        retained_at=NOW,
    )
    internal = memory.retrieve(RetrievalQuery(text="release", as_of=NOW))
    assert [item.entry.memory_id for item in internal] == [primary.record_id]
    all_results = memory.retrieve(
        RetrievalQuery(
            text="release",
            allowed_privacy=(PrivacyClass.INTERNAL, PrivacyClass.PERSONAL),
            as_of=NOW,
        )
    )
    assert all_results[0].entry.memory_id == primary.record_id
    assert all_results[0].score > all_results[1].score


def test_conflicts_are_hidden_until_resolved(tmp_path: Path) -> None:
    records, memory = stores(tmp_path)
    first = evidence(6, AuthorityLevel.USER_PROVIDED)
    second = evidence(7, AuthorityLevel.PRIMARY)
    records.append_many((first, second))
    memory.retain(
        first,
        subject="project status",
        privacy=PrivacyClass.INTERNAL,
        tags=("status",),
        retained_at=NOW,
    )
    memory.retain(
        second,
        subject="project status",
        privacy=PrivacyClass.INTERNAL,
        tags=("status",),
        retained_at=NOW,
    )
    memory.mark_conflict(first.record_id, second.record_id, confirmed=True)
    assert memory.retrieve(RetrievalQuery(text="status", as_of=NOW)) == ()
    memory.resolve_conflict(first.record_id, second.record_id)
    old = memory.get(first.record_id)
    assert old.conflict_state is ConflictState.RESOLVED
    results = memory.retrieve(RetrievalQuery(text="status", as_of=NOW))
    assert [result.entry.memory_id for result in results] == [second.record_id, first.record_id]


def test_memory_evaluation_detects_privacy_boundary(tmp_path: Path) -> None:
    records, memory = stores(tmp_path)
    item = evidence(8, AuthorityLevel.PRIMARY)
    records.append(item)
    memory.retain(item, subject="restricted fact", privacy=PrivacyClass.RESTRICTED, retained_at=NOW)
    report = memory.evaluate(allowed_privacy=(PrivacyClass.INTERNAL,), as_of=NOW)
    assert not report.valid
    assert report.privacy_violations == 1
    report = memory.evaluate(allowed_privacy=(PrivacyClass.RESTRICTED,), as_of=NOW)
    assert report.valid


def test_retention_is_idempotent_and_record_backed(tmp_path: Path) -> None:
    records, memory = stores(tmp_path)
    item = evidence(9, AuthorityLevel.PRIMARY)
    with pytest.raises(RecordNotFoundError):
        memory.retain(item, subject="not persisted", privacy=PrivacyClass.INTERNAL, retained_at=NOW)
    records.append(item)
    first = memory.retain(item, subject="persisted", privacy=PrivacyClass.INTERNAL, retained_at=NOW)
    second = memory.retain(
        item, subject="ignored duplicate", privacy=PrivacyClass.INTERNAL, retained_at=NOW
    )
    assert first == second
