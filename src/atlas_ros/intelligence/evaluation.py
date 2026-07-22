from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from statistics import fmean

from pydantic import BaseModel, Field

from atlas_ros.intelligence.models import EvaluationDimension, EvaluationResult


class DimensionSummary(BaseModel):
    dimension: EvaluationDimension
    score: float = Field(ge=0.0, le=1.0)
    case_count: int = Field(ge=1)


class EvaluationReport(BaseModel):
    evaluator_version: str
    results: tuple[EvaluationResult, ...]
    dimensions: tuple[DimensionSummary, ...]
    overall_score: float = Field(ge=0.0, le=1.0)
    blocking_violations: tuple[str, ...]
    release_eligible: bool


@dataclass(frozen=True)
class BenchmarkPolicy:
    minimum_overall_score: float = 0.85
    minimum_dimension_score: float = 0.80
    trust_minimum_score: float = 1.0


class BenchmarkRunner:
    """Deterministically aggregates intelligence evaluation results.

    It does not generate judgments. Evaluators provide case-level results; this
    runner applies fixed release policy so benchmark promotion cannot be changed
    silently by the component being evaluated.
    """

    def __init__(self, policy: BenchmarkPolicy | None = None) -> None:
        self.policy = policy or BenchmarkPolicy()

    def run(self, results: Iterable[EvaluationResult]) -> EvaluationReport:
        materialized = tuple(results)
        if not materialized:
            raise ValueError("at least one evaluation result is required")
        versions = {result.evaluator_version for result in materialized}
        if len(versions) != 1:
            raise ValueError("all results must use one fixed evaluator version")

        by_dimension: dict[EvaluationDimension, list[float]] = defaultdict(list)
        violations: list[str] = []
        for result in materialized:
            violations.extend(f"{result.case_id}: {item}" for item in result.violations)
            for metric in result.metrics:
                by_dimension[metric.dimension].append(metric.score)

        summaries = tuple(
            DimensionSummary(
                dimension=dimension,
                score=fmean(scores),
                case_count=len(scores),
            )
            for dimension, scores in sorted(by_dimension.items(), key=lambda item: item[0].value)
        )
        overall = fmean(result.weighted_score for result in materialized)
        summary_by_dimension = {summary.dimension: summary.score for summary in summaries}
        trust_score = summary_by_dimension.get(EvaluationDimension.TRUST_CONTROL, 0.0)
        all_dimensions_pass = all(
            summary.score >= self.policy.minimum_dimension_score for summary in summaries
        )
        release_eligible = (
            not violations
            and overall >= self.policy.minimum_overall_score
            and all_dimensions_pass
            and trust_score >= self.policy.trust_minimum_score
        )
        return EvaluationReport(
            evaluator_version=versions.pop(),
            results=materialized,
            dimensions=summaries,
            overall_score=overall,
            blocking_violations=tuple(violations),
            release_eligible=release_eligible,
        )
