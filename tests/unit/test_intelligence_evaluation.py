from datetime import UTC, datetime

import pytest

from atlas_ros.intelligence.evaluation import BenchmarkRunner
from atlas_ros.intelligence.models import (
    EvaluationCase,
    EvaluationDimension,
    EvaluationResult,
    MetricScore,
)


def result(*, trust: float = 1.0, decision: float = 0.9, violations: tuple[str, ...] = ()) -> EvaluationResult:
    return EvaluationResult(
        case_id="case-1",
        evaluator_version="rie-1.0",
        generated_at=datetime.now(UTC),
        metrics=(
            MetricScore(
                metric="decision",
                dimension=EvaluationDimension.DECISION_QUALITY,
                score=decision,
            ),
            MetricScore(
                metric="trust",
                dimension=EvaluationDimension.TRUST_CONTROL,
                score=trust,
            ),
        ),
        violations=violations,
    )


def test_case_requires_expected_behavior() -> None:
    with pytest.raises(ValueError):
        EvaluationCase(
            id="x",
            title="x",
            scenario="x",
            expected_behaviors=(),
            dimensions=frozenset({EvaluationDimension.DECISION_QUALITY}),
            authority_context="live authority",
        )


def test_result_weighted_score_and_pass() -> None:
    evaluation = result()
    assert evaluation.weighted_score == pytest.approx(0.95)
    assert evaluation.passed


def test_violation_requires_zero_trust_score() -> None:
    with pytest.raises(ValueError, match="zero trust"):
        result(violations=("authority violation",))


def test_runner_blocks_trust_regression() -> None:
    report = BenchmarkRunner().run((result(trust=0.9),))
    assert not report.release_eligible


def test_runner_accepts_eligible_results() -> None:
    report = BenchmarkRunner().run((result(),))
    assert report.release_eligible
    assert report.overall_score == pytest.approx(0.95)


def test_runner_requires_fixed_evaluator_version() -> None:
    second = result().model_copy(update={"evaluator_version": "rie-2.0"})
    with pytest.raises(ValueError, match="one fixed evaluator version"):
        BenchmarkRunner().run((result(), second))


def test_runner_requires_results() -> None:
    with pytest.raises(ValueError, match="at least one"):
        BenchmarkRunner().run(())
