from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Iterable, Sequence
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from atlas_ros.intelligence.record_store import SQLiteIntelligenceRecordStore
from atlas_ros.intelligence.records import (
    AuthorityLevel,
    CanonicalRecordType,
    EvidenceEnvelope,
    LifecycleState,
    RecordKind,
    RecordRef,
    ValidationStatus,
)


class MemoryTier(StrEnum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    GOVERNED = "governed"


class PrivacyClass(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    PERSONAL = "personal"
    RESTRICTED = "restricted"


class ConflictState(StrEnum):
    NONE = "none"
    POTENTIAL = "potential"
    CONFIRMED = "confirmed"
    RESOLVED = "resolved"


class MemoryPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    working_ttl_hours: int = Field(default=24, ge=1)
    episodic_ttl_days: int = Field(default=180, ge=1)
    semantic_ttl_days: int = Field(default=730, ge=1)
    governed_requires_verified: bool = True
    minimum_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    authority_weight: float = Field(default=0.35, ge=0.0)
    confidence_weight: float = Field(default=0.25, ge=0.0)
    salience_weight: float = Field(default=0.20, ge=0.0)
    recency_weight: float = Field(default=0.20, ge=0.0)

    @model_validator(mode="after")
    def validate_weights(self) -> MemoryPolicy:
        total = (
            self.authority_weight
            + self.confidence_weight
            + self.salience_weight
            + self.recency_weight
        )
        if not math.isclose(total, 1.0, abs_tol=1e-9):
            raise ValueError("memory ranking weights must sum to 1.0")
        return self


class MemoryEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    memory_id: UUID
    record_ref: RecordRef
    tier: MemoryTier
    privacy: PrivacyClass
    subject: str = Field(min_length=1)
    tags: tuple[str, ...] = ()
    salience: float = Field(default=0.5, ge=0.0, le=1.0)
    retained_at: datetime
    expires_at: datetime | None = None
    conflict_state: ConflictState = ConflictState.NONE
    superseded_by: UUID | None = None

    @model_validator(mode="after")
    def validate_lifecycle(self) -> MemoryEntry:
        if self.expires_at is not None and self.expires_at <= self.retained_at:
            raise ValueError("memory expiration must be after retention")
        if self.conflict_state is ConflictState.RESOLVED and self.superseded_by is None:
            raise ValueError("resolved conflicts require a superseding memory")
        return self


class RetrievalQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str = ""
    tags: tuple[str, ...] = ()
    allowed_privacy: tuple[PrivacyClass, ...] = (
        PrivacyClass.PUBLIC,
        PrivacyClass.INTERNAL,
    )
    tiers: tuple[MemoryTier, ...] = tuple(MemoryTier)
    limit: int = Field(default=10, ge=1, le=100)
    include_conflicted: bool = False
    as_of: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RetrievalResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    entry: MemoryEntry
    score: float = Field(ge=0.0, le=1.0)
    authority_score: float
    confidence_score: float
    salience_score: float
    recency_score: float
    matched_terms: tuple[str, ...] = ()


class MemoryEvaluation(BaseModel):
    model_config = ConfigDict(frozen=True)

    total_memories: int
    active_memories: int
    expired_memories: int
    conflicted_memories: int
    unresolved_references: int
    integrity_failures: int
    privacy_violations: int
    valid: bool


@dataclass(frozen=True)
class RetentionDecision:
    tier: MemoryTier
    expires_at: datetime | None


_AUTHORITY_SCORES = {
    AuthorityLevel.PRIMARY: 1.0,
    AuthorityLevel.AUTHORITATIVE_APPLICATION: 0.95,
    AuthorityLevel.GOVERNED_INTERNAL: 0.85,
    AuthorityLevel.USER_PROVIDED: 0.75,
    AuthorityLevel.INFERRED: 0.45,
    AuthorityLevel.UNVERIFIED: 0.20,
}


class GovernedMemoryStore:
    """Policy-governed memory metadata over immutable canonical records."""

    def __init__(
        self,
        path: Path,
        record_store: SQLiteIntelligenceRecordStore,
        policy: MemoryPolicy | None = None,
    ) -> None:
        self.path = path
        self.record_store = record_store
        self.policy = policy or MemoryPolicy()

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_entries (
                    memory_id TEXT PRIMARY KEY,
                    record_id TEXT NOT NULL UNIQUE,
                    record_kind TEXT NOT NULL,
                    record_hash TEXT NOT NULL,
                    tier TEXT NOT NULL,
                    privacy TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    salience REAL NOT NULL,
                    retained_at TEXT NOT NULL,
                    expires_at TEXT,
                    conflict_state TEXT NOT NULL,
                    superseded_by TEXT
                )
                """
            )

    def decide_retention(self, record: CanonicalRecordType, now: datetime) -> RetentionDecision:
        if record.lifecycle_state is not LifecycleState.ACTIVE:
            raise ValueError("only active records may enter memory")
        if isinstance(record, EvidenceEnvelope):
            if record.confidence < self.policy.minimum_confidence:
                raise ValueError("record confidence is below memory threshold")
            if (
                self.policy.governed_requires_verified
                and record.source_authority in {
                    AuthorityLevel.PRIMARY,
                    AuthorityLevel.AUTHORITATIVE_APPLICATION,
                    AuthorityLevel.GOVERNED_INTERNAL,
                }
                and record.validation_status is ValidationStatus.VERIFIED
            ):
                return RetentionDecision(MemoryTier.GOVERNED, None)
        if record.kind is RecordKind.CONTEXT:
            return RetentionDecision(
                MemoryTier.WORKING, now + timedelta(hours=self.policy.working_ttl_hours)
            )
        if record.kind in {RecordKind.DECISION, RecordKind.LEARNING}:
            return RetentionDecision(
                MemoryTier.SEMANTIC, now + timedelta(days=self.policy.semantic_ttl_days)
            )
        return RetentionDecision(
            MemoryTier.EPISODIC, now + timedelta(days=self.policy.episodic_ttl_days)
        )

    def retain(
        self,
        record: CanonicalRecordType,
        *,
        subject: str,
        privacy: PrivacyClass,
        tags: Sequence[str] = (),
        salience: float = 0.5,
        retained_at: datetime | None = None,
    ) -> MemoryEntry:
        if not record.verify_integrity():
            raise ValueError("record failed integrity verification")
        self.record_store.resolve(record.ref())
        now = retained_at or datetime.now(UTC)
        decision = self.decide_retention(record, now)
        entry = MemoryEntry(
            memory_id=record.record_id,
            record_ref=record.ref(),
            tier=decision.tier,
            privacy=privacy,
            subject=subject,
            tags=tuple(sorted(set(tags))),
            salience=salience,
            retained_at=now,
            expires_at=decision.expires_at,
        )
        with sqlite3.connect(self.path) as connection:
            existing = connection.execute(
                "SELECT record_hash FROM memory_entries WHERE record_id = ?",
                (str(record.record_id),),
            ).fetchone()
            if existing:
                if existing[0] == record.integrity_hash:
                    return self.get(entry.memory_id)
                raise ValueError("memory record identity is immutable")
            connection.execute(
                """
                INSERT INTO memory_entries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(entry.memory_id),
                    str(entry.record_ref.record_id),
                    entry.record_ref.kind.value,
                    entry.record_ref.integrity_hash,
                    entry.tier.value,
                    entry.privacy.value,
                    entry.subject,
                    "\u001f".join(entry.tags),
                    entry.salience,
                    entry.retained_at.isoformat(),
                    entry.expires_at.isoformat() if entry.expires_at else None,
                    entry.conflict_state.value,
                    None,
                ),
            )
        return entry

    def get(self, memory_id: UUID) -> MemoryEntry:
        with sqlite3.connect(self.path) as connection:
            row = connection.execute(
                "SELECT * FROM memory_entries WHERE memory_id = ?", (str(memory_id),)
            ).fetchone()
        if not row:
            raise KeyError(str(memory_id))
        return self._entry(row)

    def _entry(self, row: tuple[object, ...]) -> MemoryEntry:
        return MemoryEntry(
            memory_id=UUID(str(row[0])),
            record_ref=RecordRef(
                record_id=UUID(str(row[1])),
                kind=RecordKind(str(row[2])),
                integrity_hash=str(row[3]),
            ),
            tier=MemoryTier(str(row[4])),
            privacy=PrivacyClass(str(row[5])),
            subject=str(row[6]),
            tags=tuple(filter(None, str(row[7]).split("\u001f"))),
            salience=float(row[8]),
            retained_at=datetime.fromisoformat(str(row[9])),
            expires_at=datetime.fromisoformat(str(row[10])) if row[10] else None,
            conflict_state=ConflictState(str(row[11])),
            superseded_by=UUID(str(row[12])) if row[12] else None,
        )

    def retrieve(self, query: RetrievalQuery) -> tuple[RetrievalResult, ...]:
        with sqlite3.connect(self.path) as connection:
            rows = connection.execute("SELECT * FROM memory_entries").fetchall()
        terms = tuple(term.lower() for term in query.text.split() if term)
        results: list[RetrievalResult] = []
        for row in rows:
            entry = self._entry(row)
            if entry.tier not in query.tiers or entry.privacy not in query.allowed_privacy:
                continue
            if entry.expires_at is not None and entry.expires_at <= query.as_of:
                continue
            if not query.include_conflicted and entry.conflict_state in {
                ConflictState.POTENTIAL,
                ConflictState.CONFIRMED,
            }:
                continue
            haystack = f"{entry.subject} {' '.join(entry.tags)}".lower()
            matched = tuple(term for term in terms if term in haystack)
            if terms and not matched:
                continue
            record = self.record_store.resolve(entry.record_ref)
            authority = self._authority(record)
            confidence = self._confidence(record)
            age_days = max((query.as_of - entry.retained_at).total_seconds() / 86400, 0.0)
            recency = math.exp(-age_days / 180.0)
            score = (
                authority * self.policy.authority_weight
                + confidence * self.policy.confidence_weight
                + entry.salience * self.policy.salience_weight
                + recency * self.policy.recency_weight
            )
            results.append(
                RetrievalResult(
                    entry=entry,
                    score=min(max(score, 0.0), 1.0),
                    authority_score=authority,
                    confidence_score=confidence,
                    salience_score=entry.salience,
                    recency_score=recency,
                    matched_terms=matched,
                )
            )
        results.sort(key=lambda item: (-item.score, item.entry.retained_at, str(item.entry.memory_id)))
        return tuple(results[: query.limit])

    def mark_conflict(self, first: UUID, second: UUID, confirmed: bool = False) -> None:
        if first == second:
            raise ValueError("a memory cannot conflict with itself")
        self.get(first)
        self.get(second)
        state = ConflictState.CONFIRMED if confirmed else ConflictState.POTENTIAL
        with sqlite3.connect(self.path) as connection:
            connection.executemany(
                "UPDATE memory_entries SET conflict_state = ? WHERE memory_id = ?",
                ((state.value, str(first)), (state.value, str(second))),
            )

    def resolve_conflict(self, superseded: UUID, winner: UUID) -> None:
        if superseded == winner:
            raise ValueError("winner must differ from superseded memory")
        old = self.get(superseded)
        self.get(winner)
        if old.conflict_state not in {ConflictState.POTENTIAL, ConflictState.CONFIRMED}:
            raise ValueError("memory is not in conflict")
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "UPDATE memory_entries SET conflict_state = ?, superseded_by = ? WHERE memory_id = ?",
                (ConflictState.RESOLVED.value, str(winner), str(superseded)),
            )
            connection.execute(
                "UPDATE memory_entries SET conflict_state = ? WHERE memory_id = ?",
                (ConflictState.NONE.value, str(winner)),
            )

    def purge_expired(self, as_of: datetime) -> int:
        with sqlite3.connect(self.path) as connection:
            cursor = connection.execute(
                "DELETE FROM memory_entries WHERE expires_at IS NOT NULL AND expires_at <= ?",
                (as_of.isoformat(),),
            )
            return int(cursor.rowcount)

    def evaluate(self, *, allowed_privacy: Iterable[PrivacyClass], as_of: datetime) -> MemoryEvaluation:
        allowed = set(allowed_privacy)
        with sqlite3.connect(self.path) as connection:
            rows = connection.execute("SELECT * FROM memory_entries").fetchall()
        expired = conflicted = unresolved = integrity = privacy = active = 0
        for row in rows:
            entry = self._entry(row)
            if entry.expires_at is not None and entry.expires_at <= as_of:
                expired += 1
            else:
                active += 1
            if entry.conflict_state in {ConflictState.POTENTIAL, ConflictState.CONFIRMED}:
                conflicted += 1
            if entry.privacy not in allowed:
                privacy += 1
            try:
                record = self.record_store.resolve(entry.record_ref)
                if not record.verify_integrity():
                    integrity += 1
            except Exception:
                unresolved += 1
        return MemoryEvaluation(
            total_memories=len(rows),
            active_memories=active,
            expired_memories=expired,
            conflicted_memories=conflicted,
            unresolved_references=unresolved,
            integrity_failures=integrity,
            privacy_violations=privacy,
            valid=(unresolved == 0 and integrity == 0 and privacy == 0),
        )

    @staticmethod
    def _authority(record: CanonicalRecordType) -> float:
        if isinstance(record, EvidenceEnvelope):
            return _AUTHORITY_SCORES[record.source_authority]
        if record.provenance:
            return max(_AUTHORITY_SCORES[hop.authority] for hop in record.provenance)
        return _AUTHORITY_SCORES[AuthorityLevel.INFERRED]

    @staticmethod
    def _confidence(record: CanonicalRecordType) -> float:
        for field in ("confidence", "probability", "confidence_after"):
            value = getattr(record, field, None)
            if isinstance(value, (float, int)):
                return float(value)
        if isinstance(record, EvidenceEnvelope):
            return record.confidence
        return 0.5
