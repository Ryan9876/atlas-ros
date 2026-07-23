from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from atlas_ros.intelligence.inference import GovernedInferenceEngine
from atlas_ros.intelligence.record_store import SQLiteIntelligenceRecordStore
from atlas_ros.intelligence.records import (
    AssumptionRecord,
    AssumptionStatus,
    AuthorityLevel,
    ClaimRecord,
    ClaimType,
    EvidenceEnvelope,
    InferenceMethod,
    InferenceRule,
    InferenceStep,
    InferenceTraceRecord,
    RecordKind,
    ValidationStatus,
    parse_record,
)

NOW = datetime(2026, 7, 22, 18, 0, tzinfo=UTC)
HASH = "sha256:" + "a" * 64


def evidence(n: int) -> EvidenceEnvelope:
    return EvidenceEnvelope(
        record_id=UUID(f"00000000-0000-4000-d000-{n:012d}"),
        created_at=NOW,
        statement=f"Evidence {n}",
        source_authority=AuthorityLevel.PRIMARY,
        confidence=0.98,
        observed_at=NOW,
        validation_status=ValidationStatus.VERIFIED,
        source_locator=f"source:{n}",
        source_content_hash=HASH,
        citation=f"citation:{n}",
    )


def claim(
    n: int,
    item: EvidenceEnvelope,
    *,
    confidence: float = 0.95,
    status: ValidationStatus = ValidationStatus.VERIFIED,
) -> ClaimRecord:
    return ClaimRecord(
        record_id=UUID(f"00000000-0000-4000-e000-{n:012d}"),
        created_at=NOW,
        statement=f"Claim {n}",
        claim_type=ClaimType.FACT,
        confidence=confidence,
        validation_status=status,
        evidence_refs=(item.ref(),),
    )


def rule(
    n: int = 1,
    *,
    minimum_premises: int = 2,
    reliability: float = 0.90,
    active: bool = True,
) -> InferenceRule:
    return InferenceRule(
        record_id=UUID(f"00000000-0000-4000-f000-{n:012d}"),
        created_at=NOW,
        name="Readiness convergence",
        description="Validated readiness claims imply release readiness.",
        method=InferenceMethod.DEDUCTIVE,
        minimum_premises=minimum_premises,
        reliability=reliability,
        active=active,
    )


def test_inference_rule_round_trip() -> None:
    record = rule()

    parsed = parse_record(record.model_dump(mode="json"))

    assert parsed == record
    assert parsed.verify_integrity()
    assert parsed.kind is RecordKind.INFERENCE_RULE


def test_engine_derives_evidence_backed_claim(tmp_path: Path) -> None:
    store = SQLiteIntelligenceRecordStore(tmp_path / "records.db")
    store.initialize()

    item1 = evidence(1)
    item2 = evidence(2)
    premise1 = claim(1, item1)
    premise2 = claim(2, item2, confidence=0.90)
    inference_rule = rule()
    store.append_many((item1, item2, premise1, premise2, inference_rule))

    outcome = GovernedInferenceEngine(store).infer(
        rule_ref=inference_rule.ref(),
        premise_refs=(premise1.ref(), premise2.ref()),
        conclusion_statement="The release is ready for governed deployment.",
        created_at=NOW,
    )

    assert outcome.conclusion.statement == ("The release is ready for governed deployment.")
    assert outcome.conclusion.claim_type is ClaimType.INTERPRETATION
    assert outcome.conclusion.confidence == pytest.approx(0.81)
    assert outcome.conclusion.validation_status is ValidationStatus.VERIFIED
    assert outcome.conclusion.evidence_refs == (
        item1.ref(),
        item2.ref(),
    )

    assert outcome.trace.valid
    assert outcome.trace.conclusion_ref == outcome.conclusion.ref()
    assert outcome.trace.rule_ref == inference_rule.ref()
    assert len(outcome.trace.steps) == 2
    assert outcome.trace.verify_integrity()

    store.append_many((outcome.conclusion, outcome.trace))
    assert store.resolve(outcome.trace.ref()) == outcome.trace


def test_partial_assumption_reduces_inference_confidence(
    tmp_path: Path,
) -> None:
    store = SQLiteIntelligenceRecordStore(tmp_path / "records.db")
    store.initialize()

    item = evidence(1)
    premise = claim(1, item)
    assumption = AssumptionRecord(
        record_id=UUID("00000000-0000-4000-a100-000000000001"),
        created_at=NOW,
        assumption="Rollback validation remains current.",
        confidence=0.75,
        status=AssumptionStatus.PARTIAL,
        evidence_refs=(item.ref(),),
    )
    inference_rule = rule()
    store.append_many((item, premise, assumption, inference_rule))

    outcome = GovernedInferenceEngine(store).infer(
        rule_ref=inference_rule.ref(),
        premise_refs=(premise.ref(), assumption.ref()),
        conclusion_statement="Deployment is conditionally supportable.",
        created_at=NOW,
    )

    assert outcome.conclusion.validation_status is ValidationStatus.PARTIAL
    assert outcome.conclusion.confidence == pytest.approx(0.54)
    assert outcome.trace.validation_status is ValidationStatus.PARTIAL


def test_engine_rejects_insufficient_premises(tmp_path: Path) -> None:
    store = SQLiteIntelligenceRecordStore(tmp_path / "records.db")
    store.initialize()

    item = evidence(1)
    premise = claim(1, item)
    inference_rule = rule(minimum_premises=2)
    store.append_many((item, premise, inference_rule))

    with pytest.raises(ValueError, match="at least 2 premises"):
        GovernedInferenceEngine(store).infer(
            rule_ref=inference_rule.ref(),
            premise_refs=(premise.ref(),),
            conclusion_statement="Unsupported conclusion.",
            created_at=NOW,
        )


def test_engine_rejects_inactive_rule(tmp_path: Path) -> None:
    store = SQLiteIntelligenceRecordStore(tmp_path / "records.db")
    store.initialize()

    item = evidence(1)
    premise = claim(1, item)
    inference_rule = rule(
        minimum_premises=1,
        active=False,
    )
    store.append_many((item, premise, inference_rule))

    with pytest.raises(ValueError, match="inactive inference rules"):
        GovernedInferenceEngine(store).infer(
            rule_ref=inference_rule.ref(),
            premise_refs=(premise.ref(),),
            conclusion_statement="Unsupported conclusion.",
            created_at=NOW,
        )


def test_trace_rejects_noncontiguous_steps() -> None:
    item = evidence(1)
    premise = claim(1, item)
    inference_rule = rule(minimum_premises=1)
    conclusion = claim(2, item)

    with pytest.raises(
        ValidationError,
        match="step sequence must be contiguous",
    ):
        InferenceTraceRecord(
            created_at=NOW,
            rule_ref=inference_rule.ref(),
            premise_refs=(premise.ref(),),
            conclusion_ref=conclusion.ref(),
            steps=(
                InferenceStep(
                    sequence=2,
                    premise_ref=premise.ref(),
                    description="Invalid sequence.",
                    confidence=0.90,
                    validation_status=ValidationStatus.VERIFIED,
                ),
            ),
            confidence=0.80,
            validation_status=ValidationStatus.VERIFIED,
            valid=True,
            explanation="Invalid trace.",
        )


def test_inference_can_use_prior_inference_trace(
    tmp_path: Path,
) -> None:
    store = SQLiteIntelligenceRecordStore(tmp_path / "records.db")
    store.initialize()

    item1 = evidence(1)
    item2 = evidence(2)
    premise1 = claim(1, item1)
    premise2 = claim(2, item2)
    first_rule = rule(1)
    second_rule = rule(
        2,
        minimum_premises=1,
        reliability=0.95,
    )
    store.append_many(
        (
            item1,
            item2,
            premise1,
            premise2,
            first_rule,
            second_rule,
        )
    )

    first = GovernedInferenceEngine(store).infer(
        rule_ref=first_rule.ref(),
        premise_refs=(premise1.ref(), premise2.ref()),
        conclusion_statement="Initial readiness is established.",
        created_at=NOW,
    )
    store.append_many((first.conclusion, first.trace))

    second = GovernedInferenceEngine(store).infer(
        rule_ref=second_rule.ref(),
        premise_refs=(first.trace.ref(),),
        conclusion_statement="Deployment approval is supportable.",
        created_at=NOW,
    )

    assert second.trace.premise_refs == (first.trace.ref(),)
    assert second.conclusion.evidence_refs == (
        item1.ref(),
        item2.ref(),
    )
    assert second.conclusion.confidence == pytest.approx(first.trace.confidence * 0.95)
