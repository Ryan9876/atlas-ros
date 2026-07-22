from __future__ import annotations

from datetime import UTC, datetime

import pytest

from atlas_ros.intelligence.calibration import (
    CalibrationCase,
    IntelligenceCalibrationEngine,
    IntelligenceCalibrationPolicy,
    IntelligenceDomain,
    IntelligenceJudgment,
)


def case(case_id: str, expected: str = "p1", domain: IntelligenceDomain = IntelligenceDomain.PRIORITY) -> CalibrationCase:
    return CalibrationCase(
        id=case_id,
        title=f"case {case_id}",
        domain=domain,
        expected_label=expected,
        scenario="A representative Ryan operating scenario.",
        authority_refs=("authority://test",),
    )


def judgment(case_id: str, predicted: str = "p1", confidence: float = 0.92, *, hallucination: bool = False) -> IntelligenceJudgment:
    return IntelligenceJudgment(
        case_id=case_id,
        evaluator_version="rie-cal-1.0",
        generated_at=datetime.now(UTC),
        predicted_label=predicted,
        confidence=confidence,
        evidence_refs=("authority://test",),
        explanation_score=0.95,
        evidence_completeness=0.98,
        hallucination=hallucination,
        accepted_by_reviewer=True,
    )


def test_calibration_report_accepts_strong_judgments() -> None:
    engine = IntelligenceCalibrationEngine(IntelligenceCalibrationPolicy(minimum_cases=2))
    report = engine.run((case("c1"), case("c2", domain=IntelligenceDomain.DECISION)), (judgment("c1"), judgment("c2")))
    assert report.release_eligible
    assert report.overall_accuracy == pytest.approx(1.0)
    assert report.overall_expected_calibration_error == pytest.approx(0.08)
    assert len(report.domains) == 2
    assert report.fingerprint


def test_low_accuracy_blocks_release_eligibility() -> None:
    engine = IntelligenceCalibrationEngine(IntelligenceCalibrationPolicy(minimum_cases=2))
    report = engine.run((case("c1"), case("c2")), (judgment("c1", predicted="p3", confidence=0.9), judgment("c2")))
    assert not report.release_eligible
    assert "overall accuracy below policy" in report.blocking_violations


def test_hallucination_blocks_release_eligibility() -> None:
    engine = IntelligenceCalibrationEngine(IntelligenceCalibrationPolicy(minimum_cases=1))
    report = engine.run((case("c1"),), (judgment("c1", hallucination=True),))
    assert not report.release_eligible
    assert "hallucination rate above policy" in report.blocking_violations


def test_duplicate_cases_are_rejected() -> None:
    engine = IntelligenceCalibrationEngine(IntelligenceCalibrationPolicy(minimum_cases=1))
    with pytest.raises(ValueError, match="duplicate calibration case ids"):
        engine.run((case("c1"), case("c1")), (judgment("c1"),))


def test_missing_judgment_is_rejected() -> None:
    engine = IntelligenceCalibrationEngine(IntelligenceCalibrationPolicy(minimum_cases=2))
    with pytest.raises(ValueError, match="cases without judgments"):
        engine.run((case("c1"), case("c2")), (judgment("c1"),))


def test_fixed_evaluator_version_required() -> None:
    engine = IntelligenceCalibrationEngine(IntelligenceCalibrationPolicy(minimum_cases=2))
    second = judgment("c2").model_copy(update={"evaluator_version": "rie-cal-2.0"})
    with pytest.raises(ValueError, match="fixed evaluator version"):
        engine.run((case("c1"), case("c2")), (judgment("c1"), second))


def test_regression_comparison_blocks_accuracy_loss() -> None:
    engine = IntelligenceCalibrationEngine(IntelligenceCalibrationPolicy(minimum_cases=2, maximum_accuracy_regression=0.01))
    cases = (case("c1"), case("c2"))
    baseline = engine.run(cases, (judgment("c1"), judgment("c2")))
    current = engine.run(cases, (judgment("c1"), judgment("c2", predicted="p3", confidence=0.95)))
    regression = engine.compare_regression(baseline, current)
    assert not regression.passed
    assert "accuracy regression exceeds policy" in regression.violations


def test_regression_requires_matching_dataset() -> None:
    engine = IntelligenceCalibrationEngine(IntelligenceCalibrationPolicy(minimum_cases=1))
    baseline = engine.run((case("c1"),), (judgment("c1"),))
    current = engine.run((case("c2"),), (judgment("c2"),))
    with pytest.raises(ValueError, match="different datasets"):
        engine.compare_regression(baseline, current)
