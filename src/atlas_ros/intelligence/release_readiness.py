from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from atlas_ros.intelligence.evaluation import EvaluationReport
from atlas_ros.intelligence.models import EvaluationCase, EvaluationDimension


class GateStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    NOT_RUN = "not_run"


class ReadinessDecision(StrEnum):
    NOT_READY = "not_ready"
    DEVELOPMENT_VALIDATED = "development_validated"
    CANDIDATE_READY = "candidate_ready"


class BenchmarkDataset(BaseModel):
    model_config = ConfigDict(frozen=True)

    dataset_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    cases: tuple[EvaluationCase, ...] = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def unique_cases(self) -> BenchmarkDataset:
        ids = [case.id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("benchmark case identifiers must be unique")
        return self

    @property
    def fingerprint(self) -> str:
        payload = {
            "dataset_id": self.dataset_id,
            "version": self.version,
            "cases": [case.model_dump(mode="json") for case in sorted(self.cases, key=lambda item: item.id)],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


class RegressionBaseline(BaseModel):
    model_config = ConfigDict(frozen=True)

    baseline_id: str = Field(min_length=1)
    dataset_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    overall_score: float = Field(ge=0.0, le=1.0)
    dimension_scores: Mapping[EvaluationDimension, float]
    maximum_overall_regression: float = Field(default=0.02, ge=0.0, le=1.0)
    maximum_dimension_regression: float = Field(default=0.03, ge=0.0, le=1.0)


class RegressionReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    overall_delta: float
    dimension_deltas: Mapping[EvaluationDimension, float]
    violations: tuple[str, ...]
    passed: bool


class AdversarialRequirement(BaseModel):
    model_config = ConfigDict(frozen=True)

    tag: str = Field(min_length=1)
    minimum_cases: int = Field(default=1, ge=1)


class AdversarialCoverageReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    counts: Mapping[str, int]
    missing: tuple[str, ...]
    passed: bool


class EvidenceGate(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    status: GateStatus
    evidence: tuple[str, ...] = ()
    blocking: bool = True


class ReleaseEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    release_id: str = Field(min_length=1)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    dataset_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    benchmark_score: float = Field(ge=0.0, le=1.0)
    regression_passed: bool
    adversarial_passed: bool
    gates: tuple[EvidenceGate, ...]
    limitations: tuple[str, ...] = ()


class ReadinessAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    decision: ReadinessDecision
    blocking_reasons: tuple[str, ...]
    evidence: ReleaseEvidence


class IntelligenceReleaseReadiness:
    """Applies fixed, non-self-modifying gates to v5 intelligence evidence."""

    @staticmethod
    def compare_regression(report: EvaluationReport, baseline: RegressionBaseline, dataset: BenchmarkDataset) -> RegressionReport:
        if baseline.dataset_fingerprint != dataset.fingerprint:
            raise ValueError("regression baseline does not match benchmark dataset")
        current = {item.dimension: item.score for item in report.dimensions}
        deltas = {
            dimension: current.get(dimension, 0.0) - score
            for dimension, score in baseline.dimension_scores.items()
        }
        violations: list[str] = []
        overall_delta = report.overall_score - baseline.overall_score
        if overall_delta < -baseline.maximum_overall_regression:
            violations.append(f"overall regression {overall_delta:.4f} exceeds policy")
        for dimension, delta in sorted(deltas.items(), key=lambda item: item[0].value):
            if delta < -baseline.maximum_dimension_regression:
                violations.append(f"{dimension.value} regression {delta:.4f} exceeds policy")
        return RegressionReport(
            overall_delta=overall_delta,
            dimension_deltas=deltas,
            violations=tuple(violations),
            passed=not violations,
        )

    @staticmethod
    def assess_adversarial_coverage(dataset: BenchmarkDataset, requirements: Sequence[AdversarialRequirement]) -> AdversarialCoverageReport:
        counts = {requirement.tag: sum(requirement.tag in case.tags for case in dataset.cases) for requirement in requirements}
        missing = tuple(
            f"{requirement.tag}: {counts[requirement.tag]}/{requirement.minimum_cases}"
            for requirement in requirements
            if counts[requirement.tag] < requirement.minimum_cases
        )
        return AdversarialCoverageReport(counts=counts, missing=missing, passed=not missing)

    @staticmethod
    def synthesize(
        *,
        release_id: str,
        dataset: BenchmarkDataset,
        benchmark: EvaluationReport,
        regression: RegressionReport,
        adversarial: AdversarialCoverageReport,
        gates: Sequence[EvidenceGate],
        limitations: Sequence[str] = (),
    ) -> ReadinessAssessment:
        blocking: list[str] = []
        if not benchmark.release_eligible:
            blocking.append("benchmark release policy failed")
        if not regression.passed:
            blocking.extend(regression.violations)
        if not adversarial.passed:
            blocking.extend(f"adversarial coverage missing {item}" for item in adversarial.missing)
        for gate in gates:
            if gate.blocking and gate.status is not GateStatus.PASS:
                blocking.append(f"gate {gate.name} is {gate.status.value}")
        evidence = ReleaseEvidence(
            release_id=release_id,
            dataset_fingerprint=dataset.fingerprint,
            benchmark_score=benchmark.overall_score,
            regression_passed=regression.passed,
            adversarial_passed=adversarial.passed,
            gates=tuple(gates),
            limitations=tuple(limitations),
        )
        if blocking:
            decision = ReadinessDecision.NOT_READY
        elif any(gate.status is GateStatus.NOT_RUN for gate in gates):
            decision = ReadinessDecision.DEVELOPMENT_VALIDATED
        else:
            decision = ReadinessDecision.CANDIDATE_READY
        return ReadinessAssessment(decision=decision, blocking_reasons=tuple(blocking), evidence=evidence)
