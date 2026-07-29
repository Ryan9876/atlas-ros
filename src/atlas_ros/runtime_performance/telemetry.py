"""Governed aggregate telemetry contracts for the Runtime Performance Foundation."""
from __future__ import annotations

from pydantic import Field, model_validator

from atlas_ros.runtime_performance.contracts import (
    ImmutableContract,
    PerformanceObservationV1,
)


class IncrementalComputationMetricsV1(ImmutableContract):
    schema_version: str = "incremental-computation-metrics-v1"
    total_nodes: int = Field(ge=0)
    changed_nodes: int = Field(ge=0)
    evaluated_nodes: int = Field(ge=0)
    reused_nodes: int = Field(ge=0)
    full_recomputation: bool
    duration_ms: float = Field(ge=0)
    full_recomputation_duration_ms: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_counts(self) -> IncrementalComputationMetricsV1:
        if self.changed_nodes > self.total_nodes:
            raise ValueError("changed nodes cannot exceed total nodes")
        if self.evaluated_nodes + self.reused_nodes != self.total_nodes:
            raise ValueError("evaluated and reused nodes must account for every node")
        if self.full_recomputation and self.reused_nodes:
            raise ValueError("full recomputation cannot report reused nodes")
        return self


class PerformanceValidationReportV1(ImmutableContract):
    schema_version: str = "performance-validation-report-v1"
    candidate_version: str
    baseline_release_identity: str
    candidate_release_identity: str
    observations: tuple[PerformanceObservationV1, ...]
    incremental_metrics: tuple[IncrementalComputationMetricsV1, ...] = Field(
        default_factory=tuple
    )
    p50_latency_ms: dict[str, float] = Field(default_factory=dict)
    p95_latency_ms: dict[str, float] = Field(default_factory=dict)
    memory_bytes: dict[str, int] = Field(default_factory=dict)
    provider_write_count: int = Field(default=0, ge=0)
    canonical_output_equivalent: bool
    scoped_full_equivalent: bool
    incremental_full_equivalent: bool
    final_validation_reduced: bool = False
    provider_latency_measured: bool = False
    provider_bytes_measured: bool = False
    warnings: tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def enforce_acceptance_boundary(self) -> PerformanceValidationReportV1:
        if self.provider_write_count:
            raise ValueError("runtime performance validation cannot increase provider writes")
        if self.final_validation_reduced:
            raise ValueError("runtime performance validation cannot reduce final validation")
        if not (
            self.canonical_output_equivalent
            and self.scoped_full_equivalent
            and self.incremental_full_equivalent
        ):
            raise ValueError("performance acceptance requires semantic equivalence")
        return self
