from datetime import UTC, datetime

import pytest

from atlas_ros.intelligence.evaluation import BenchmarkRunner
from atlas_ros.intelligence.models import (
    EvaluationCase,
    EvaluationDimension,
    EvaluationResult,
    MetricScore,
)
from atlas_ros.intelligence.release_readiness import (
    AdversarialRequirement,
    BenchmarkDataset,
    EvidenceGate,
    GateStatus,
    IntelligenceReleaseReadiness,
    ReadinessDecision,
    RegressionBaseline,
)


def case(case_id: str, *tags: str) -> EvaluationCase:
    return EvaluationCase(
        id=case_id,
        title=case_id,
        scenario="scenario",
        expected_behaviors=("abstain safely",),
        tags=frozenset(tags),
        dimensions=frozenset({EvaluationDimension.TRUST_CONTROL}),
        authority_context="live authority",
    )


def result(case_id: str, decision: float = 0.9, trust: float = 1.0) -> EvaluationResult:
    return EvaluationResult(
        case_id=case_id,
        evaluator_version="rie-1",
        generated_at=datetime.now(UTC),
        metrics=(
            MetricScore(
                metric="decision", dimension=EvaluationDimension.DECISION_QUALITY, score=decision
            ),
            MetricScore(metric="trust", dimension=EvaluationDimension.TRUST_CONTROL, score=trust),
        ),
    )


def dataset() -> BenchmarkDataset:
    return BenchmarkDataset(
        dataset_id="rie",
        version="1",
        cases=(case("a", "authority-conflict"), case("b", "prompt-injection")),
    )


def benchmark():
    return BenchmarkRunner().run((result("a"), result("b")))


def baseline(ds: BenchmarkDataset, overall: float = 0.95) -> RegressionBaseline:
    return RegressionBaseline(
        baseline_id="base",
        dataset_fingerprint=ds.fingerprint,
        overall_score=overall,
        dimension_scores={
            EvaluationDimension.DECISION_QUALITY: 0.9,
            EvaluationDimension.TRUST_CONTROL: 1.0,
        },
    )


def test_dataset_fingerprint_is_order_independent() -> None:
    first = dataset()
    second = BenchmarkDataset(dataset_id="rie", version="1", cases=tuple(reversed(first.cases)))
    assert first.fingerprint == second.fingerprint


def test_dataset_rejects_duplicate_cases() -> None:
    with pytest.raises(ValueError, match="unique"):
        BenchmarkDataset(dataset_id="x", version="1", cases=(case("a"), case("a")))


def test_regression_passes_within_tolerance() -> None:
    ds = dataset()
    report = IntelligenceReleaseReadiness.compare_regression(benchmark(), baseline(ds), ds)
    assert report.passed


def test_regression_blocks_material_drop() -> None:
    ds = dataset()
    weak = BenchmarkRunner().run((result("a", decision=0.80), result("b", decision=0.80)))
    report = IntelligenceReleaseReadiness.compare_regression(weak, baseline(ds), ds)
    assert not report.passed
    assert report.violations


def test_regression_requires_matching_dataset() -> None:
    ds = dataset()
    wrong = baseline(ds).model_copy(update={"dataset_fingerprint": "0" * 64})
    with pytest.raises(ValueError, match="does not match"):
        IntelligenceReleaseReadiness.compare_regression(benchmark(), wrong, ds)


def test_adversarial_coverage_detects_missing_categories() -> None:
    report = IntelligenceReleaseReadiness.assess_adversarial_coverage(
        dataset(),
        (
            AdversarialRequirement(tag="authority-conflict"),
            AdversarialRequirement(tag="data-poisoning"),
        ),
    )
    assert not report.passed
    assert report.missing == ("data-poisoning: 0/1",)


def test_candidate_ready_requires_all_gates() -> None:
    ds = dataset()
    bench = benchmark()
    regression = IntelligenceReleaseReadiness.compare_regression(bench, baseline(ds), ds)
    adversarial = IntelligenceReleaseReadiness.assess_adversarial_coverage(
        ds,
        (
            AdversarialRequirement(tag="authority-conflict"),
            AdversarialRequirement(tag="prompt-injection"),
        ),
    )
    assessment = IntelligenceReleaseReadiness.synthesize(
        release_id="v5",
        dataset=ds,
        benchmark=bench,
        regression=regression,
        adversarial=adversarial,
        gates=(EvidenceGate(name="tests", status=GateStatus.PASS),),
    )
    assert assessment.decision is ReadinessDecision.CANDIDATE_READY


def test_not_run_blocking_gate_is_not_ready() -> None:
    ds = dataset()
    bench = benchmark()
    assessment = IntelligenceReleaseReadiness.synthesize(
        release_id="v5",
        dataset=ds,
        benchmark=bench,
        regression=IntelligenceReleaseReadiness.compare_regression(bench, baseline(ds), ds),
        adversarial=IntelligenceReleaseReadiness.assess_adversarial_coverage(
            ds, (AdversarialRequirement(tag="prompt-injection"),)
        ),
        gates=(EvidenceGate(name="mypy", status=GateStatus.NOT_RUN),),
    )
    assert assessment.decision is ReadinessDecision.NOT_READY
    assert "gate mypy is not_run" in assessment.blocking_reasons


def test_nonblocking_not_run_yields_development_validated() -> None:
    ds = dataset()
    bench = benchmark()
    assessment = IntelligenceReleaseReadiness.synthesize(
        release_id="v5",
        dataset=ds,
        benchmark=bench,
        regression=IntelligenceReleaseReadiness.compare_regression(bench, baseline(ds), ds),
        adversarial=IntelligenceReleaseReadiness.assess_adversarial_coverage(
            ds, (AdversarialRequirement(tag="prompt-injection"),)
        ),
        gates=(EvidenceGate(name="independent-review", status=GateStatus.NOT_RUN, blocking=False),),
    )
    assert assessment.decision is ReadinessDecision.DEVELOPMENT_VALIDATED
