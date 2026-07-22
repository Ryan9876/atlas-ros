from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from statistics import fmean

from pydantic import BaseModel, ConfigDict, Field, model_validator

from atlas_ros.intelligence.record_store import SQLiteIntelligenceRecordStore
from atlas_ros.intelligence.records import (
    AuthorityLevel,
    EvidenceEnvelope,
    LearningEvent,
    PredictionRecord,
    RecordRef,
    ValidationStatus,
)


class ForecastResolution(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    INVALID = "invalid"


class ForecastRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    prediction: str = Field(min_length=1)
    probability: float = Field(ge=0.0, le=1.0)
    confidence_low: float = Field(ge=0.0, le=1.0)
    confidence_high: float = Field(ge=0.0, le=1.0)
    expires_at: datetime
    evidence_refs: tuple[RecordRef, ...] = Field(min_length=1)
    assumptions: tuple[str, ...] = ()
    minimum_evidence_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    minimum_evidence_strength: float = Field(default=0.35, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_interval(self) -> ForecastRequest:
        if not self.confidence_low <= self.probability <= self.confidence_high:
            raise ValueError("probability must fall inside confidence interval")
        return self


class ForecastEvidenceAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_ref: RecordRef
    authority_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    usable: bool
    reason: str = Field(min_length=1)


class ForecastTrace(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence: tuple[ForecastEvidenceAssessment, ...]
    evidence_strength: float = Field(ge=0.0, le=1.0)
    interval_width: float = Field(ge=0.0, le=1.0)
    issued: bool
    explanation: str = Field(min_length=1)


@dataclass(frozen=True)
class ForecastOutcome:
    trace: ForecastTrace
    prediction: PredictionRecord | None


class OutcomeObservation(BaseModel):
    model_config = ConfigDict(frozen=True)

    prediction_ref: RecordRef
    resolution: ForecastResolution
    observed_at: datetime
    source: str = Field(min_length=1)
    notes: str = ""

    @model_validator(mode="after")
    def validate_reference(self) -> OutcomeObservation:
        from atlas_ros.intelligence.records import RecordKind

        if self.prediction_ref.kind is not RecordKind.PREDICTION:
            raise ValueError("prediction_ref must reference a prediction record")
        return self


class CalibrationObservation(BaseModel):
    model_config = ConfigDict(frozen=True)

    prediction_ref: RecordRef
    probability: float = Field(ge=0.0, le=1.0)
    actual: int = Field(ge=0, le=1)
    brier_score: float = Field(ge=0.0, le=1.0)
    absolute_error: float = Field(ge=0.0, le=1.0)
    interval_covered: bool
    observed_at: datetime


class CalibrationBin(BaseModel):
    model_config = ConfigDict(frozen=True)

    lower: float = Field(ge=0.0, le=1.0)
    upper: float = Field(ge=0.0, le=1.0)
    count: int = Field(ge=0)
    mean_probability: float = Field(ge=0.0, le=1.0)
    observed_rate: float = Field(ge=0.0, le=1.0)
    calibration_gap: float = Field(ge=0.0, le=1.0)


class CalibrationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    count: int = Field(ge=0)
    brier_score: float = Field(ge=0.0, le=1.0)
    mean_absolute_error: float = Field(ge=0.0, le=1.0)
    interval_coverage: float = Field(ge=0.0, le=1.0)
    expected_calibration_error: float = Field(ge=0.0, le=1.0)
    bins: tuple[CalibrationBin, ...]


class DriftStatus(StrEnum):
    INSUFFICIENT_DATA = "insufficient_data"
    STABLE = "stable"
    WARNING = "warning"
    DRIFT = "drift"


class DriftReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: DriftStatus
    baseline_count: int = Field(ge=0)
    recent_count: int = Field(ge=0)
    brier_delta: float
    calibration_delta: float
    explanation: str = Field(min_length=1)


_AUTHORITY = {
    AuthorityLevel.PRIMARY: 1.0,
    AuthorityLevel.AUTHORITATIVE_APPLICATION: 0.95,
    AuthorityLevel.GOVERNED_INTERNAL: 0.85,
    AuthorityLevel.USER_PROVIDED: 0.75,
    AuthorityLevel.INFERRED: 0.45,
    AuthorityLevel.UNVERIFIED: 0.20,
}


class GovernedPredictionEngine:
    """Issues and resolves evidence-qualified probabilistic forecasts."""

    def __init__(self, record_store: SQLiteIntelligenceRecordStore) -> None:
        self.record_store = record_store

    def issue(self, request: ForecastRequest, *, created_at: datetime | None = None) -> ForecastOutcome:
        created = created_at or datetime.now(UTC)
        if request.expires_at <= created:
            raise ValueError("forecast expiration must be after creation")
        assessments: list[ForecastEvidenceAssessment] = []
        for ref in request.evidence_refs:
            record = self.record_store.resolve(ref)
            if not isinstance(record, EvidenceEnvelope):
                raise ValueError("evidence_refs must resolve to EvidenceEnvelope")
            usable = (
                record.validation_status is not ValidationStatus.REJECTED
                and record.confidence >= request.minimum_evidence_confidence
            )
            assessments.append(
                ForecastEvidenceAssessment(
                    evidence_ref=ref,
                    authority_score=_AUTHORITY[record.source_authority],
                    confidence=record.confidence,
                    usable=usable,
                    reason=(
                        "usable verified or qualified evidence"
                        if usable
                        else "rejected or below confidence threshold"
                    ),
                )
            )
        usable_assessments = [
            item for item in assessments if item.usable
        ]
        strength = (
            sum(
                item.authority_score * item.confidence
                for item in usable_assessments
            )
            / len(usable_assessments)
            if usable_assessments
            else 0.0
        )
        width = request.confidence_high - request.confidence_low
        issued = (
            bool(usable_assessments)
            and strength >= request.minimum_evidence_strength
        )
        explanation = (
            "Forecast issued from qualified evidence with explicit probability and interval."
            if issued
            else "Forecast withheld because qualified evidence strength was insufficient."
        )
        trace = ForecastTrace(
            evidence=tuple(assessments),
            evidence_strength=strength,
            interval_width=width,
            issued=issued,
            explanation=explanation,
        )
        if not issued:
            return ForecastOutcome(trace=trace, prediction=None)
        record = PredictionRecord(
            created_at=created,
            prediction=request.prediction,
            probability=request.probability,
            confidence_low=request.confidence_low,
            confidence_high=request.confidence_high,
            assumptions=request.assumptions,
            expires_at=request.expires_at,
            evidence_refs=request.evidence_refs,
        )
        return ForecastOutcome(trace=trace, prediction=record)

    def observe(
        self,
        observation: OutcomeObservation,
        *,
        model_version: str = "5.0.0rc1",
    ) -> tuple[CalibrationObservation | None, LearningEvent]:
        prediction = self.record_store.resolve(observation.prediction_ref)
        if not isinstance(prediction, PredictionRecord):
            raise ValueError("prediction_ref must resolve to PredictionRecord")
        if observation.observed_at < prediction.created_at:
            raise ValueError("outcome cannot predate prediction")
        if observation.resolution is ForecastResolution.INVALID:
            learning = LearningEvent(
                created_at=observation.observed_at,
                observed_outcome=f"invalid forecast: {observation.notes or observation.source}",
                prediction_ref=prediction.ref(),
                delta_analysis="Forecast excluded from calibration because outcome validity failed.",
                confidence_before=prediction.probability,
                confidence_after=prediction.probability,
                model_version=model_version,
                learning_eligible=False,
                eligibility_reason="invalid or unresolvable outcome",
            )
            return None, learning
        actual = 1 if observation.resolution is ForecastResolution.POSITIVE else 0
        error = abs(prediction.probability - actual)
        calibration = CalibrationObservation(
            prediction_ref=prediction.ref(),
            probability=prediction.probability,
            actual=actual,
            brier_score=(prediction.probability - actual) ** 2,
            absolute_error=error,
            interval_covered=prediction.confidence_low <= actual <= prediction.confidence_high,
            observed_at=observation.observed_at,
        )
        learning = LearningEvent(
            created_at=observation.observed_at,
            observed_outcome=observation.resolution.value,
            prediction_ref=prediction.ref(),
            delta_analysis=f"Probability error={error:.4f}; Brier={calibration.brier_score:.4f}.",
            confidence_before=prediction.probability,
            confidence_after=max(0.0, 1.0 - error),
            pattern_updates=("update prediction calibration statistics",),
            model_version=model_version,
            learning_eligible=True,
            eligibility_reason="valid resolved probabilistic forecast",
        )
        return calibration, learning


class CalibrationEvaluator:
    @staticmethod
    def report(observations: Sequence[CalibrationObservation], *, bin_count: int = 10) -> CalibrationReport:
        if bin_count < 1:
            raise ValueError("bin_count must be positive")
        if not observations:
            return CalibrationReport(
                count=0,
                brier_score=0.0,
                mean_absolute_error=0.0,
                interval_coverage=0.0,
                expected_calibration_error=0.0,
                bins=(),
            )
        bins: list[CalibrationBin] = []
        total = len(observations)
        ece = 0.0
        for index in range(bin_count):
            lower = index / bin_count
            upper = (index + 1) / bin_count
            members = [
                item
                for item in observations
                if lower <= item.probability < upper or (index == bin_count - 1 and item.probability == 1.0)
            ]
            if not members:
                continue
            mean_probability = fmean(item.probability for item in members)
            observed_rate = fmean(item.actual for item in members)
            gap = abs(mean_probability - observed_rate)
            ece += len(members) / total * gap
            bins.append(
                CalibrationBin(
                    lower=lower,
                    upper=upper,
                    count=len(members),
                    mean_probability=mean_probability,
                    observed_rate=observed_rate,
                    calibration_gap=gap,
                )
            )
        return CalibrationReport(
            count=total,
            brier_score=fmean(item.brier_score for item in observations),
            mean_absolute_error=fmean(item.absolute_error for item in observations),
            interval_coverage=fmean(1.0 if item.interval_covered else 0.0 for item in observations),
            expected_calibration_error=ece,
            bins=tuple(bins),
        )

    @staticmethod
    def detect_drift(
        baseline: Sequence[CalibrationObservation],
        recent: Sequence[CalibrationObservation],
        *,
        minimum_samples: int = 5,
        warning_threshold: float = 0.05,
        drift_threshold: float = 0.10,
    ) -> DriftReport:
        if minimum_samples < 1:
            raise ValueError("minimum_samples must be positive")
        if len(baseline) < minimum_samples or len(recent) < minimum_samples:
            return DriftReport(
                status=DriftStatus.INSUFFICIENT_DATA,
                baseline_count=len(baseline),
                recent_count=len(recent),
                brier_delta=0.0,
                calibration_delta=0.0,
                explanation="Insufficient resolved forecasts for drift evaluation.",
            )
        baseline_report = CalibrationEvaluator.report(baseline)
        recent_report = CalibrationEvaluator.report(recent)
        brier_delta = recent_report.brier_score - baseline_report.brier_score
        calibration_delta = (
            recent_report.expected_calibration_error - baseline_report.expected_calibration_error
        )
        degradation = max(brier_delta, calibration_delta)
        if degradation >= drift_threshold:
            status = DriftStatus.DRIFT
            explanation = "Predictive quality degradation exceeds the drift threshold."
        elif degradation >= warning_threshold:
            status = DriftStatus.WARNING
            explanation = "Predictive quality degradation exceeds the warning threshold."
        else:
            status = DriftStatus.STABLE
            explanation = "No material predictive-quality drift detected."
        return DriftReport(
            status=status,
            baseline_count=len(baseline),
            recent_count=len(recent),
            brier_delta=brier_delta,
            calibration_delta=calibration_delta,
            explanation=explanation,
        )

    @staticmethod
    def predictive_quality(report: CalibrationReport) -> float:
        if report.count == 0:
            return 0.0
        return max(
            0.0,
            min(
                1.0,
                1.0
                - 0.45 * report.brier_score
                - 0.35 * report.expected_calibration_error
                - 0.20 * (1.0 - report.interval_coverage),
            ),
        )
