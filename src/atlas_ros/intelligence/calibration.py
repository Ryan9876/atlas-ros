from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from statistics import fmean

from pydantic import BaseModel, ConfigDict, Field

Score = float


class IntelligenceDomain(StrEnum):
    PRIORITY = "priority_recommendation"
    RISK = "risk_prediction"
    DECISION = "decision_recommendation"
    ROOT_CAUSE = "root_cause_hypothesis"
    ACTION = "action_recommendation"
    EVIDENCE = "evidence_quality"
    EXPLANATION = "explanation_quality"
    LEARNING = "learning_effectiveness"


class CalibrationCase(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    domain: IntelligenceDomain
    expected_label: str = Field(min_length=1)
    scenario: str = Field(min_length=1)
    authority_refs: tuple[str, ...] = Field(default=(), min_length=1)
    tags: frozenset[str] = frozenset()
    weight: float = Field(default=1.0, gt=0.0)


class IntelligenceJudgment(BaseModel):
    model_config = ConfigDict(frozen=True)

    case_id: str = Field(min_length=1)
    evaluator_version: str = Field(min_length=1)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    predicted_label: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_refs: tuple[str, ...] = ()
    explanation_score: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence_completeness: float = Field(default=1.0, ge=0.0, le=1.0)
    hallucination: bool = False
    accepted_by_reviewer: bool | None = None
    notes: str = ""


class CaseOutcome(BaseModel):
    model_config = ConfigDict(frozen=True)

    case: CalibrationCase
    judgment: IntelligenceJudgment
    correct: bool
    reviewer_accepted: bool | None

    @property
    def weighted_correctness(self) -> float:
        return self.case.weight if self.correct else 0.0


class CalibrationBin(BaseModel):
    model_config = ConfigDict(frozen=True)

    lower: float = Field(ge=0.0, le=1.0)
    upper: float = Field(ge=0.0, le=1.0)
    case_count: int = Field(ge=0)
    mean_confidence: float = Field(ge=0.0, le=1.0)
    observed_accuracy: float = Field(ge=0.0, le=1.0)
    calibration_error: float = Field(ge=0.0, le=1.0)


class DomainCalibration(BaseModel):
    model_config = ConfigDict(frozen=True)

    domain: IntelligenceDomain
    case_count: int = Field(ge=1)
    accuracy: float = Field(ge=0.0, le=1.0)
    macro_precision: float = Field(ge=0.0, le=1.0)
    macro_recall: float = Field(ge=0.0, le=1.0)
    macro_f1: float = Field(ge=0.0, le=1.0)
    brier_score: float = Field(ge=0.0, le=1.0)
    expected_calibration_error: float = Field(ge=0.0, le=1.0)
    hallucination_rate: float = Field(ge=0.0, le=1.0)
    evidence_completeness: float = Field(ge=0.0, le=1.0)
    explanation_quality: float = Field(ge=0.0, le=1.0)
    reviewer_acceptance_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    bins: tuple[CalibrationBin, ...]


class IntelligenceCalibrationPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    minimum_accuracy: float = Field(default=0.85, ge=0.0, le=1.0)
    minimum_macro_f1: float = Field(default=0.80, ge=0.0, le=1.0)
    maximum_brier_score: float = Field(default=0.16, ge=0.0, le=1.0)
    maximum_expected_calibration_error: float = Field(default=0.10, ge=0.0, le=1.0)
    maximum_hallucination_rate: float = Field(default=0.01, ge=0.0, le=1.0)
    minimum_evidence_completeness: float = Field(default=0.95, ge=0.0, le=1.0)
    minimum_explanation_quality: float = Field(default=0.85, ge=0.0, le=1.0)
    maximum_accuracy_regression: float = Field(default=0.01, ge=0.0, le=1.0)
    minimum_cases: int = Field(default=1, ge=1)
    calibration_bins: int = Field(default=10, ge=2, le=20)


class IntelligenceCalibrationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    evaluator_version: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    dataset_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    case_count: int = Field(ge=1)
    overall_accuracy: float = Field(ge=0.0, le=1.0)
    overall_macro_f1: float = Field(ge=0.0, le=1.0)
    overall_brier_score: float = Field(ge=0.0, le=1.0)
    overall_expected_calibration_error: float = Field(ge=0.0, le=1.0)
    overall_hallucination_rate: float = Field(ge=0.0, le=1.0)
    overall_evidence_completeness: float = Field(ge=0.0, le=1.0)
    overall_explanation_quality: float = Field(ge=0.0, le=1.0)
    domains: tuple[DomainCalibration, ...]
    blocking_violations: tuple[str, ...]
    release_eligible: bool

    @property
    def fingerprint(self) -> str:
        payload = self.model_dump(mode="json", exclude={"generated_at"})
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


class CalibrationRegressionReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    baseline_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    current_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    accuracy_delta: float
    ece_delta: float
    hallucination_delta: float
    violations: tuple[str, ...]
    passed: bool


def _fingerprint_cases(cases: Sequence[CalibrationCase]) -> str:
    payload = [case.model_dump(mode="json") for case in sorted(cases, key=lambda item: item.id)]
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _macro_prf(expected: Sequence[str], predicted: Sequence[str]) -> tuple[float, float, float]:
    labels = sorted(set(expected) | set(predicted))
    precisions: list[float] = []
    recalls: list[float] = []
    f1s: list[float] = []
    for label in labels:
        tp = sum(e == label and p == label for e, p in zip(expected, predicted, strict=True))
        fp = sum(e != label and p == label for e, p in zip(expected, predicted, strict=True))
        fn = sum(e == label and p != label for e, p in zip(expected, predicted, strict=True))
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        precisions.append(precision)
        recalls.append(recall)
        f1s.append(f1)
    return fmean(precisions), fmean(recalls), fmean(f1s)


def _bins(
    outcomes: Sequence[CaseOutcome], policy: IntelligenceCalibrationPolicy
) -> tuple[CalibrationBin, ...]:
    bins: list[CalibrationBin] = []
    width = 1.0 / policy.calibration_bins
    for index in range(policy.calibration_bins):
        lower = index * width
        upper = 1.0 if index == policy.calibration_bins - 1 else (index + 1) * width
        selected = tuple(
            outcome
            for outcome in outcomes
            if lower <= outcome.judgment.confidence <= upper
            and (index == policy.calibration_bins - 1 or outcome.judgment.confidence < upper)
        )
        if not selected:
            bins.append(
                CalibrationBin(
                    lower=round(lower, 6),
                    upper=round(upper, 6),
                    case_count=0,
                    mean_confidence=0.0,
                    observed_accuracy=0.0,
                    calibration_error=0.0,
                )
            )
            continue
        mean_confidence = fmean(item.judgment.confidence for item in selected)
        accuracy = fmean(1.0 if item.correct else 0.0 for item in selected)
        bins.append(
            CalibrationBin(
                lower=round(lower, 6),
                upper=round(upper, 6),
                case_count=len(selected),
                mean_confidence=mean_confidence,
                observed_accuracy=accuracy,
                calibration_error=abs(mean_confidence - accuracy),
            )
        )
    return tuple(bins)


def _expected_calibration_error(bins: Sequence[CalibrationBin], total: int) -> float:
    if total <= 0:
        return 0.0
    return sum((item.case_count / total) * item.calibration_error for item in bins)


class IntelligenceCalibrationEngine:
    """Scores Atlas intelligence outputs against fixed ground-truth cases.

    The engine measures whether recommendations were correct, whether confidence
    was calibrated, whether evidence was complete, and whether hallucinations or
    explanation-quality problems should block release promotion.
    """

    def __init__(self, policy: IntelligenceCalibrationPolicy | None = None) -> None:
        self.policy = policy or IntelligenceCalibrationPolicy()

    @staticmethod
    def _join(
        cases: Sequence[CalibrationCase], judgments: Sequence[IntelligenceJudgment]
    ) -> tuple[CaseOutcome, ...]:
        case_ids = [case.id for case in cases]
        duplicates = sorted(case_id for case_id, count in Counter(case_ids).items() if count > 1)
        if duplicates:
            raise ValueError("duplicate calibration case ids: " + ", ".join(duplicates))
        judgment_ids = [judgment.case_id for judgment in judgments]
        duplicate_judgments = sorted(
            case_id for case_id, count in Counter(judgment_ids).items() if count > 1
        )
        if duplicate_judgments:
            raise ValueError("duplicate judgment case ids: " + ", ".join(duplicate_judgments))
        by_case = {case.id: case for case in cases}
        unknown = sorted(set(judgment_ids) - set(by_case))
        missing = sorted(set(by_case) - set(judgment_ids))
        if unknown:
            raise ValueError("judgments reference unknown cases: " + ", ".join(unknown))
        if missing:
            raise ValueError("cases without judgments: " + ", ".join(missing))
        outcomes: list[CaseOutcome] = []
        for judgment in sorted(judgments, key=lambda item: item.case_id):
            case = by_case[judgment.case_id]
            outcomes.append(
                CaseOutcome(
                    case=case,
                    judgment=judgment,
                    correct=judgment.predicted_label == case.expected_label,
                    reviewer_accepted=judgment.accepted_by_reviewer,
                )
            )
        return tuple(outcomes)

    def _domain_report(
        self, domain: IntelligenceDomain, outcomes: Sequence[CaseOutcome]
    ) -> DomainCalibration:
        expected = [item.case.expected_label for item in outcomes]
        predicted = [item.judgment.predicted_label for item in outcomes]
        precision, recall, f1 = _macro_prf(expected, predicted)
        bins = _bins(outcomes, self.policy)
        reviewer = [
            item.reviewer_accepted for item in outcomes if item.reviewer_accepted is not None
        ]
        return DomainCalibration(
            domain=domain,
            case_count=len(outcomes),
            accuracy=fmean(1.0 if item.correct else 0.0 for item in outcomes),
            macro_precision=precision,
            macro_recall=recall,
            macro_f1=f1,
            brier_score=fmean(
                (item.judgment.confidence - (1.0 if item.correct else 0.0)) ** 2
                for item in outcomes
            ),
            expected_calibration_error=_expected_calibration_error(bins, len(outcomes)),
            hallucination_rate=fmean(
                1.0 if item.judgment.hallucination else 0.0 for item in outcomes
            ),
            evidence_completeness=fmean(item.judgment.evidence_completeness for item in outcomes),
            explanation_quality=fmean(item.judgment.explanation_score for item in outcomes),
            reviewer_acceptance_rate=(
                fmean(1.0 if accepted else 0.0 for accepted in reviewer) if reviewer else None
            ),
            bins=bins,
        )

    def run(
        self, cases: Iterable[CalibrationCase], judgments: Iterable[IntelligenceJudgment]
    ) -> IntelligenceCalibrationReport:
        case_tuple = tuple(cases)
        judgment_tuple = tuple(judgments)
        if len(case_tuple) < self.policy.minimum_cases:
            raise ValueError(f"at least {self.policy.minimum_cases} calibration cases are required")
        versions = {judgment.evaluator_version for judgment in judgment_tuple}
        if len(versions) != 1:
            raise ValueError("all judgments must use one fixed evaluator version")
        outcomes = self._join(case_tuple, judgment_tuple)
        grouped: dict[IntelligenceDomain, list[CaseOutcome]] = defaultdict(list)
        for outcome in outcomes:
            grouped[outcome.case.domain].append(outcome)
        domain_reports = tuple(
            self._domain_report(domain, grouped[domain])
            for domain in sorted(grouped, key=lambda item: item.value)
        )
        overall_bins = _bins(outcomes, self.policy)
        precision, _recall, f1 = _macro_prf(
            [item.case.expected_label for item in outcomes],
            [item.judgment.predicted_label for item in outcomes],
        )
        _ = precision
        violations: list[str] = []
        overall_accuracy = fmean(1.0 if item.correct else 0.0 for item in outcomes)
        overall_brier = fmean(
            (item.judgment.confidence - (1.0 if item.correct else 0.0)) ** 2 for item in outcomes
        )
        overall_ece = _expected_calibration_error(overall_bins, len(outcomes))
        hallucination_rate = fmean(1.0 if item.judgment.hallucination else 0.0 for item in outcomes)
        evidence_completeness = fmean(item.judgment.evidence_completeness for item in outcomes)
        explanation_quality = fmean(item.judgment.explanation_score for item in outcomes)
        if overall_accuracy < self.policy.minimum_accuracy:
            violations.append("overall accuracy below policy")
        if f1 < self.policy.minimum_macro_f1:
            violations.append("overall macro F1 below policy")
        if overall_brier > self.policy.maximum_brier_score:
            violations.append("Brier score above policy")
        if overall_ece > self.policy.maximum_expected_calibration_error:
            violations.append("expected calibration error above policy")
        if hallucination_rate > self.policy.maximum_hallucination_rate:
            violations.append("hallucination rate above policy")
        if evidence_completeness < self.policy.minimum_evidence_completeness:
            violations.append("evidence completeness below policy")
        if explanation_quality < self.policy.minimum_explanation_quality:
            violations.append("explanation quality below policy")
        for domain in domain_reports:
            if domain.accuracy < self.policy.minimum_accuracy:
                violations.append(f"{domain.domain.value} accuracy below policy")
            if domain.expected_calibration_error > self.policy.maximum_expected_calibration_error:
                violations.append(f"{domain.domain.value} calibration error above policy")
        return IntelligenceCalibrationReport(
            evaluator_version=versions.pop(),
            dataset_fingerprint=_fingerprint_cases(case_tuple),
            case_count=len(case_tuple),
            overall_accuracy=overall_accuracy,
            overall_macro_f1=f1,
            overall_brier_score=overall_brier,
            overall_expected_calibration_error=overall_ece,
            overall_hallucination_rate=hallucination_rate,
            overall_evidence_completeness=evidence_completeness,
            overall_explanation_quality=explanation_quality,
            domains=domain_reports,
            blocking_violations=tuple(violations),
            release_eligible=not violations,
        )

    def compare_regression(
        self,
        baseline: IntelligenceCalibrationReport,
        current: IntelligenceCalibrationReport,
    ) -> CalibrationRegressionReport:
        if baseline.dataset_fingerprint != current.dataset_fingerprint:
            raise ValueError("calibration reports are from different datasets")
        violations: list[str] = []
        accuracy_delta = current.overall_accuracy - baseline.overall_accuracy
        ece_delta = (
            current.overall_expected_calibration_error - baseline.overall_expected_calibration_error
        )
        hallucination_delta = (
            current.overall_hallucination_rate - baseline.overall_hallucination_rate
        )
        if accuracy_delta < -self.policy.maximum_accuracy_regression:
            violations.append("accuracy regression exceeds policy")
        if ece_delta > self.policy.maximum_expected_calibration_error:
            violations.append("calibration error regression exceeds policy")
        if hallucination_delta > self.policy.maximum_hallucination_rate:
            violations.append("hallucination regression exceeds policy")
        return CalibrationRegressionReport(
            baseline_fingerprint=baseline.fingerprint,
            current_fingerprint=current.fingerprint,
            accuracy_delta=accuracy_delta,
            ece_delta=ece_delta,
            hallucination_delta=hallucination_delta,
            violations=tuple(violations),
            passed=not violations,
        )


def load_calibration_cases(path: Path) -> tuple[CalibrationCase, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("calibration case file must contain a JSON list")
    return tuple(CalibrationCase.model_validate(item) for item in payload)


def load_intelligence_judgments(path: Path) -> tuple[IntelligenceJudgment, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("intelligence judgment file must contain a JSON list")
    return tuple(IntelligenceJudgment.model_validate(item) for item in payload)


def load_calibration_report(path: Path) -> IntelligenceCalibrationReport:
    return IntelligenceCalibrationReport.model_validate_json(path.read_text(encoding="utf-8"))
