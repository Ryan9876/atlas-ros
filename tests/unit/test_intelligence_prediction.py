from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from atlas_ros.intelligence.prediction import (
    CalibrationEvaluator,
    CalibrationObservation,
    DriftStatus,
    ForecastRequest,
    ForecastResolution,
    GovernedPredictionEngine,
    OutcomeObservation,
)
from atlas_ros.intelligence.record_store import SQLiteIntelligenceRecordStore
from atlas_ros.intelligence.records import AuthorityLevel, EvidenceEnvelope, ValidationStatus

NOW = datetime(2026, 7, 22, 8, 0, tzinfo=UTC)
HASH = "sha256:" + "b" * 64


def ev(n: int, confidence: float = .9, status: ValidationStatus = ValidationStatus.VERIFIED):
    return EvidenceEnvelope(
        record_id=UUID(f"00000000-0000-4000-a000-{n:012d}"),
        created_at=NOW,
        statement=f"Evidence {n}",
        source_authority=AuthorityLevel.PRIMARY,
        confidence=confidence,
        observed_at=NOW,
        validation_status=status,
        source_content_hash=HASH,
    )


def setup(tmp_path: Path):
    store = SQLiteIntelligenceRecordStore(tmp_path / "records.db")
    store.initialize()
    evidence = ev(1)
    store.append(evidence)
    return store, evidence


def request(evidence, **kwargs):
    values = dict(
        prediction="Milestone will complete on schedule",
        probability=.75,
        confidence_low=.55,
        confidence_high=.9,
        expires_at=NOW + timedelta(days=14),
        evidence_refs=(evidence.ref(),),
    )
    values.update(kwargs)
    return ForecastRequest(**values)


def test_issue_forecast_from_qualified_evidence(tmp_path: Path):
    store, evidence = setup(tmp_path)
    outcome = GovernedPredictionEngine(store).issue(request(evidence), created_at=NOW)
    assert outcome.trace.issued
    assert outcome.prediction is not None
    assert outcome.prediction.verify_integrity()
    assert outcome.prediction.probability == .75


def test_withhold_forecast_when_evidence_is_weak(tmp_path: Path):
    store = SQLiteIntelligenceRecordStore(tmp_path / "records.db")
    store.initialize()
    weak = ev(2, confidence=.2, status=ValidationStatus.REJECTED)
    store.append(weak)
    outcome = GovernedPredictionEngine(store).issue(request(weak), created_at=NOW)
    assert not outcome.trace.issued
    assert outcome.prediction is None
    assert not outcome.trace.evidence[0].usable


def test_request_rejects_invalid_interval(tmp_path: Path):
    _, evidence = setup(tmp_path)
    with pytest.raises(ValidationError, match="inside confidence interval"):
        request(evidence, probability=.9, confidence_low=.1, confidence_high=.8)


def test_issue_rejects_expired_horizon(tmp_path: Path):
    store, evidence = setup(tmp_path)
    with pytest.raises(ValueError, match="after creation"):
        GovernedPredictionEngine(store).issue(
            request(evidence, expires_at=NOW - timedelta(seconds=1)), created_at=NOW
        )


def test_capture_positive_outcome_and_learning_event(tmp_path: Path):
    store, evidence = setup(tmp_path)
    forecast = GovernedPredictionEngine(store).issue(request(evidence), created_at=NOW).prediction
    assert forecast is not None
    store.append(forecast)
    calibration, learning = GovernedPredictionEngine(store).observe(
        OutcomeObservation(
            prediction_ref=forecast.ref(),
            resolution=ForecastResolution.POSITIVE,
            observed_at=NOW + timedelta(days=1),
            source="validated result",
        )
    )
    assert calibration is not None
    assert calibration.actual == 1
    assert calibration.brier_score == pytest.approx(.0625)
    assert learning.learning_eligible
    assert learning.verify_integrity()


def test_invalid_outcome_is_excluded_from_calibration(tmp_path: Path):
    store, evidence = setup(tmp_path)
    forecast = GovernedPredictionEngine(store).issue(request(evidence), created_at=NOW).prediction
    assert forecast is not None
    store.append(forecast)
    calibration, learning = GovernedPredictionEngine(store).observe(
        OutcomeObservation(
            prediction_ref=forecast.ref(),
            resolution=ForecastResolution.INVALID,
            observed_at=NOW + timedelta(days=1),
            source="source unavailable",
        )
    )
    assert calibration is None
    assert not learning.learning_eligible
    assert not learning.pattern_updates


def obs(n: int, probability: float, actual: int, covered: bool = True):
    from atlas_ros.intelligence.records import RecordKind, RecordRef

    return CalibrationObservation(
        prediction_ref=RecordRef(
            record_id=UUID(f"00000000-0000-4000-a100-{n:012d}"),
            kind=RecordKind.PREDICTION,
            integrity_hash="sha256:" + f"{n:064x}"[-64:],
        ),
        probability=probability,
        actual=actual,
        brier_score=(probability - actual) ** 2,
        absolute_error=abs(probability - actual),
        interval_covered=covered,
        observed_at=NOW,
    )


def test_calibration_report_and_quality():
    report = CalibrationEvaluator.report((obs(1, .8, 1), obs(2, .2, 0), obs(3, .7, 1)))
    assert report.count == 3
    assert report.brier_score < .1
    assert report.interval_coverage == 1
    assert report.expected_calibration_error >= 0
    assert CalibrationEvaluator.predictive_quality(report) > .8


def test_empty_report_and_invalid_bin_count():
    report = CalibrationEvaluator.report(())
    assert report.count == 0
    assert CalibrationEvaluator.predictive_quality(report) == 0
    with pytest.raises(ValueError, match="positive"):
        CalibrationEvaluator.report((), bin_count=0)


def test_drift_detection_stable_warning_and_drift():
    baseline = tuple(obs(i, .9 if i % 2 else .1, 1 if i % 2 else 0) for i in range(1, 7))
    stable = tuple(obs(i + 10, .89 if i % 2 else .11, 1 if i % 2 else 0) for i in range(1, 7))
    bad = tuple(obs(i + 20, .9 if i % 2 else .1, 0 if i % 2 else 1) for i in range(1, 7))
    assert CalibrationEvaluator.detect_drift(baseline[:2], stable[:2]).status is DriftStatus.INSUFFICIENT_DATA
    assert CalibrationEvaluator.detect_drift(baseline, stable).status is DriftStatus.STABLE
    assert CalibrationEvaluator.detect_drift(baseline, bad).status is DriftStatus.DRIFT
    warning = CalibrationEvaluator.detect_drift(
        baseline,
        stable,
        warning_threshold=.001,
        drift_threshold=.9,
    )
    assert warning.status is DriftStatus.WARNING


def test_drift_rejects_invalid_minimum_samples():
    with pytest.raises(ValueError, match="positive"):
        CalibrationEvaluator.detect_drift((), (), minimum_samples=0)
