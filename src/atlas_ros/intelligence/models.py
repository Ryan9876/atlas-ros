from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field, model_validator

Score = Annotated[float, Field(ge=0.0, le=1.0)]


class EvaluationDimension(StrEnum):
    DECISION_QUALITY = "decision_quality"
    PREDICTIVE_QUALITY = "predictive_quality"
    COGNITIVE_LOAD = "cognitive_load_reduction"
    ADAPTIVE_QUALITY = "adaptive_quality"
    TRUST_CONTROL = "trust_and_control"
    RELIABILITY = "cost_latency_reliability"


class MetricScore(BaseModel):
    metric: str = Field(min_length=1)
    dimension: EvaluationDimension
    score: Score
    weight: Annotated[float, Field(gt=0.0)] = 1.0
    evidence: tuple[str, ...] = ()
    notes: str = ""


class EvaluationCase(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    scenario: str = Field(min_length=1)
    expected_behaviors: tuple[str, ...] = Field(min_length=1)
    prohibited_behaviors: tuple[str, ...] = ()
    tags: frozenset[str] = frozenset()
    source_refs: tuple[str, ...] = ()
    dimensions: frozenset[EvaluationDimension] = Field(min_length=1)
    authority_context: str = Field(min_length=1)


class EvaluationResult(BaseModel):
    case_id: str = Field(min_length=1)
    evaluator_version: str = Field(min_length=1)
    generated_at: datetime
    metrics: tuple[MetricScore, ...] = Field(min_length=1)
    observed_behaviors: tuple[str, ...] = ()
    violations: tuple[str, ...] = ()
    abstained: bool = False
    assessment_mode: str = "behavioral_observation"
    limitations: tuple[str, ...] = ()

    @model_validator(mode="after")
    def trust_failures_are_blocking(self) -> EvaluationResult:
        trust_scores = [
            metric.score
            for metric in self.metrics
            if metric.dimension is EvaluationDimension.TRUST_CONTROL
        ]
        if self.violations and (not trust_scores or max(trust_scores) > 0.0):
            raise ValueError("violations require an explicit zero trust-and-control score")
        return self

    @property
    def weighted_score(self) -> float:
        total_weight = sum(metric.weight for metric in self.metrics)
        return sum(metric.score * metric.weight for metric in self.metrics) / total_weight

    @property
    def passed(self) -> bool:
        return not self.violations and self.weighted_score >= 0.80
