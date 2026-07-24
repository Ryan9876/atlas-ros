from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from atlas_ros.intelligence.migrations import RecordMigrator, UnsupportedSchemaVersionError
from atlas_ros.intelligence.record_io import load_record, write_record
from atlas_ros.intelligence.record_store import (
    IntegrityError,
    ReferenceResolutionError,
    SQLiteIntelligenceRecordStore,
)
from atlas_ros.intelligence.records import (
    AuthorityLevel,
    ContextSnapshot,
    DecisionRecord,
    EvidenceEnvelope,
    LearningEvent,
    PredictionRecord,
    ProvenanceHop,
    RecommendationOption,
    RecommendationRecord,
    RecordKind,
    ValidationStatus,
    parse_record,
)

NOW = datetime(2026, 7, 22, 4, 0, tzinfo=UTC)
CONTENT_HASH = "sha256:" + "a" * 64
RECORD_ID = UUID("00000000-0000-4000-8000-000000000001")


def evidence() -> EvidenceEnvelope:
    return EvidenceEnvelope(
        record_id=RECORD_ID,
        created_at=NOW,
        statement="The live release index identifies v4.5.3 as Active.",
        source_authority=AuthorityLevel.PRIMARY,
        confidence=1.0,
        observed_at=NOW,
        validation_status=ValidationStatus.VERIFIED,
        source_locator="drive://release-index",
        source_content_hash=CONTENT_HASH,
        citation="RELEASE_INDEX.md lines 8-11",
        provenance=(
            ProvenanceHop(
                source="Google Drive",
                authority=AuthorityLevel.PRIMARY,
                observed_at=NOW,
                locator="drive://release-index",
                content_hash=CONTENT_HASH,
                validation_status=ValidationStatus.VERIFIED,
            ),
        ),
    )


def context(item: EvidenceEnvelope) -> ContextSnapshot:
    return ContextSnapshot(
        created_at=NOW,
        active_objective="Implement canonical intelligence records",
        constraints=("Do not change production authority",),
        available_authorities=("Google Drive", "Notion"),
        decision_horizon="Milestone 3",
        evidence_refs=(item.ref(),),
    )


def prediction(item: EvidenceEnvelope) -> PredictionRecord:
    return PredictionRecord(
        created_at=NOW,
        prediction="Milestone 3 tests will pass",
        probability=0.8,
        confidence_low=0.6,
        confidence_high=0.9,
        expires_at=NOW + timedelta(days=1),
        evidence_refs=(item.ref(),),
    )


def test_record_is_deterministic_immutable_and_lossless(tmp_path: Path) -> None:
    item = evidence()
    assert item.verify_integrity()
    assert item.integrity_hash == evidence().integrity_hash
    with pytest.raises(ValidationError):
        item.statement = "mutated"  # type: ignore[misc]

    path = tmp_path / "record.json"
    write_record(path, item)
    loaded = load_record(path)
    assert loaded == item
    assert loaded.canonical_json() == item.canonical_json()


def test_tampering_is_detected() -> None:
    payload = evidence().model_dump(mode="json")
    payload["statement"] = "tampered"
    with pytest.raises(ValidationError, match="integrity hash mismatch"):
        parse_record(payload)


def test_prediction_contract_enforces_interval_and_outcome_pair() -> None:
    item = evidence()
    with pytest.raises(ValidationError, match="confidence interval"):
        PredictionRecord(
            created_at=NOW,
            prediction="bad interval",
            probability=0.9,
            confidence_low=0.1,
            confidence_high=0.8,
            expires_at=NOW + timedelta(days=1),
            evidence_refs=(item.ref(),),
        )
    with pytest.raises(ValidationError, match="recorded together"):
        PredictionRecord(
            created_at=NOW,
            prediction="partial outcome",
            probability=0.5,
            confidence_low=0.4,
            confidence_high=0.6,
            expires_at=NOW + timedelta(days=1),
            evidence_refs=(item.ref(),),
            actual_outcome="happened",
        )


def test_complete_record_graph_and_append_only_store(tmp_path: Path) -> None:
    ev = evidence()
    ctx = context(ev)
    pred = prediction(ev)
    rec = RecommendationRecord(
        created_at=NOW,
        recommendation="Proceed with governed implementation",
        alternatives=(
            RecommendationOption(
                option="defer",
                expected_benefit="less immediate work",
                expected_risk="delayed capability",
            ),
        ),
        rationale="The evidence and context support implementation.",
        expected_benefit="Canonical contracts",
        expected_risk="Migration complexity",
        confidence=0.9,
        evidence_refs=(ev.ref(),),
        context_ref=ctx.ref(),
    )
    decision = DecisionRecord(
        created_at=NOW,
        decision="Implement Milestone 3",
        decision_owner="Ryan",
        selected_option="proceed",
        expected_outcome="Validated CIR layer",
        success_metrics=("All tests pass",),
        recommendation_ref=rec.ref(),
        evidence_refs=(ev.ref(),),
    )
    learning = LearningEvent(
        created_at=NOW,
        observed_outcome="Milestone implementation completed",
        prediction_ref=pred.ref(),
        decision_ref=decision.ref(),
        delta_analysis="Outcome matched the prediction.",
        confidence_before=0.8,
        confidence_after=0.85,
        pattern_updates=("Governed incremental delivery is reliable",),
        model_version="5.0.0rc1",
        learning_eligible=True,
        eligibility_reason="Verified outcome with complete provenance",
    )
    store = SQLiteIntelligenceRecordStore(tmp_path / "records.db")
    store.initialize()
    store.append_many((ev, ctx, pred, rec, decision, learning))
    assert store.count() == 6
    assert store.resolve(rec.context_ref) == ctx
    store.append(ev)
    assert store.count() == 6

    changed = ev.model_copy(update={"statement": "changed"})
    with pytest.raises(IntegrityError):
        store.append(changed)


def test_unresolved_and_mismatched_references_are_rejected(tmp_path: Path) -> None:
    ev = evidence()
    ctx = context(ev)
    store = SQLiteIntelligenceRecordStore(tmp_path / "records.db")
    store.initialize()
    with pytest.raises(ReferenceResolutionError, match="unresolved reference"):
        store.append_many((ctx,))

    store.append(ev)
    bad_ref = ev.ref().model_copy(update={"integrity_hash": "sha256:" + "b" * 64})
    bad_context = ctx.model_copy(update={"evidence_refs": (bad_ref,), "integrity_hash": ""})
    with pytest.raises(ReferenceResolutionError, match="reference mismatch"):
        store.append_many((bad_context,))


def test_ineligible_learning_cannot_mutate_patterns() -> None:
    pred = prediction(evidence())
    with pytest.raises(ValidationError, match="cannot update patterns"):
        LearningEvent(
            created_at=NOW,
            observed_outcome="Unverified result",
            prediction_ref=pred.ref(),
            delta_analysis="Insufficient evidence",
            confidence_before=0.5,
            confidence_after=0.5,
            pattern_updates=("unsafe update",),
            model_version="5.0.0rc1",
            learning_eligible=False,
            eligibility_reason="Outcome is unverified",
        )


def test_explicit_migration_registry_rehashes_payload() -> None:
    migrator = RecordMigrator()
    migrator.register("0.9.0", "1.0.0", lambda value: {**value, "citation": "migrated"})
    payload = evidence().model_dump(mode="json")
    payload["schema_version"] = "0.9.0"
    migrated = migrator.migrate(payload, "1.0.0")
    assert migrated["schema_version"] == "1.0.0"
    assert migrated["citation"] == "migrated"
    assert "integrity_hash" not in migrated
    with pytest.raises(UnsupportedSchemaVersionError):
        migrator.migrate(payload, "2.0.0")


def test_json_payload_rejects_unknown_record_kind() -> None:
    payload = json.loads(evidence().model_dump_json())
    payload["kind"] = "unknown"
    with pytest.raises(ValueError):
        parse_record(payload)


def test_published_record_reference_schemas_cover_all_runtime_kinds() -> None:
    expected = {kind.value for kind in RecordKind}
    schema_paths = sorted(Path("schemas/intelligence").glob("*.schema.json"))

    assert schema_paths
    for schema_path in schema_paths:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        assert set(schema["$defs"]["RecordKind"]["enum"]) == expected
