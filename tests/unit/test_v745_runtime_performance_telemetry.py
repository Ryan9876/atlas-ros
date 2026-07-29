from __future__ import annotations

import pytest
from pydantic import ValidationError

from atlas_ros.runtime_performance import (
    IncrementalComputationMetricsV1,
    PerformanceObservationV1,
    PerformanceValidationReportV1,
)


def _observation() -> PerformanceObservationV1:
    return PerformanceObservationV1(
        operation_id="op-1",
        release_identity="7.4.5@candidate",
        workload="fixture",
        initialization_duration_ms=1.0,
        memory_bytes=1024,
    )


def test_incremental_metrics_account_for_all_nodes() -> None:
    metrics = IncrementalComputationMetricsV1(
        total_nodes=10,
        changed_nodes=2,
        evaluated_nodes=4,
        reused_nodes=6,
        full_recomputation=False,
        duration_ms=2.0,
        full_recomputation_duration_ms=5.0,
    )
    assert metrics.total_nodes == metrics.evaluated_nodes + metrics.reused_nodes


def test_incremental_metrics_reject_invalid_counts() -> None:
    with pytest.raises(ValidationError, match="account for every node"):
        IncrementalComputationMetricsV1(
            total_nodes=10,
            changed_nodes=2,
            evaluated_nodes=3,
            reused_nodes=6,
            full_recomputation=False,
            duration_ms=2.0,
        )


def test_performance_report_requires_equivalence_and_zero_writes() -> None:
    report = PerformanceValidationReportV1(
        candidate_version="7.4.5",
        baseline_release_identity="7.4.0@immutable",
        candidate_release_identity="7.4.5@candidate",
        observations=(_observation(),),
        p50_latency_ms={"snapshot": 1.0},
        p95_latency_ms={"snapshot": 2.0},
        memory_bytes={"snapshot": 1024},
        canonical_output_equivalent=True,
        scoped_full_equivalent=True,
        incremental_full_equivalent=True,
    )
    assert report.provider_write_count == 0

    with pytest.raises(ValidationError, match="provider writes"):
        PerformanceValidationReportV1(
            candidate_version="7.4.5",
            baseline_release_identity="7.4.0@immutable",
            candidate_release_identity="7.4.5@candidate",
            observations=(_observation(),),
            provider_write_count=1,
            canonical_output_equivalent=True,
            scoped_full_equivalent=True,
            incremental_full_equivalent=True,
        )

    with pytest.raises(ValidationError, match="semantic equivalence"):
        PerformanceValidationReportV1(
            candidate_version="7.4.5",
            baseline_release_identity="7.4.0@immutable",
            candidate_release_identity="7.4.5@candidate",
            observations=(_observation(),),
            canonical_output_equivalent=True,
            scoped_full_equivalent=False,
            incremental_full_equivalent=True,
        )
