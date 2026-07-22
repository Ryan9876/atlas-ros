from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from uuid import UUID

from atlas_ros.intelligence.records import CanonicalRecordType, RecordRef, parse_record


class RecordNotFoundError(KeyError):
    pass


class IntegrityError(ValueError):
    pass


class ReferenceResolutionError(ValueError):
    pass


class SQLiteIntelligenceRecordStore:
    """Append-only persistence for canonical intelligence records."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS intelligence_records (
                    record_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    integrity_hash TEXT NOT NULL UNIQUE,
                    payload TEXT NOT NULL
                )
                """
            )

    def append(self, record: CanonicalRecordType) -> None:
        if not record.verify_integrity():
            raise IntegrityError(f"record {record.record_id} failed integrity verification")
        payload = record.model_dump_json()
        with sqlite3.connect(self.path) as connection:
            existing = connection.execute(
                "SELECT payload FROM intelligence_records WHERE record_id = ?",
                (str(record.record_id),),
            ).fetchone()
            if existing:
                if existing[0] == payload:
                    return
                raise IntegrityError(f"record {record.record_id} is immutable")
            connection.execute(
                """
                INSERT INTO intelligence_records
                    (record_id, kind, schema_version, created_at, integrity_hash, payload)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(record.record_id),
                    record.kind.value,
                    record.schema_version,
                    record.created_at.isoformat(),
                    record.integrity_hash,
                    payload,
                ),
            )

    def append_many(self, records: Iterable[CanonicalRecordType]) -> None:
        materialized = tuple(records)
        self.validate_references(materialized)
        for record in materialized:
            self.append(record)

    def get(self, record_id: UUID) -> CanonicalRecordType:
        with sqlite3.connect(self.path) as connection:
            row = connection.execute(
                "SELECT payload FROM intelligence_records WHERE record_id = ?",
                (str(record_id),),
            ).fetchone()
        if not row:
            raise RecordNotFoundError(str(record_id))
        payload = json.loads(row[0])
        record = parse_record(payload)
        if not record.verify_integrity():
            raise IntegrityError(f"stored record {record_id} failed integrity verification")
        return record

    def resolve(self, ref: RecordRef) -> CanonicalRecordType:
        record = self.get(ref.record_id)
        if record.kind is not ref.kind or record.integrity_hash != ref.integrity_hash:
            raise ReferenceResolutionError(f"reference mismatch for {ref.record_id}")
        return record

    def validate_references(self, records: Iterable[CanonicalRecordType]) -> None:
        materialized = tuple(records)
        staged = {record.record_id: record for record in materialized}
        for record in materialized:
            direct_refs = list(record.links)
            for field_name in (
                "evidence_refs",
                "context_ref",
                "recommendation_ref",
                "prediction_ref",
                "decision_ref",
                "supersedes",
            ):
                value = getattr(record, field_name, None)
                if value is None:
                    continue
                direct_refs.extend(value if isinstance(value, tuple) else (value,))
            for ref in direct_refs:
                target = staged.get(ref.record_id)
                if target is None:
                    try:
                        target = self.get(ref.record_id)
                    except RecordNotFoundError as error:
                        raise ReferenceResolutionError(
                            f"unresolved reference {ref.record_id} from {record.record_id}"
                        ) from error
                if target.kind is not ref.kind or target.integrity_hash != ref.integrity_hash:
                    raise ReferenceResolutionError(
                        f"reference mismatch {ref.record_id} from {record.record_id}"
                    )

    def count(self) -> int:
        with sqlite3.connect(self.path) as connection:
            row = connection.execute("SELECT COUNT(*) FROM intelligence_records").fetchone()
        return int(row[0]) if row else 0
