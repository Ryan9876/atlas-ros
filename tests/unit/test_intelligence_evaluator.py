import pytest

from atlas_ros.intelligence.benchmark_adapter import DOMAIN_LABELS
from atlas_ros.intelligence.calibration import (
    CalibrationCase,
    IntelligenceCalibrationEngine,
    IntelligenceDomain,
)
from atlas_ros.intelligence.evaluator import (
    IntelligenceEvaluationRunner,
    IntelligenceEvaluator,
)


def case(
    case_id: str,
    domain: IntelligenceDomain,
) -> CalibrationCase:
    return CalibrationCase(
        id=case_id,
        title=f"Evaluate {domain.value}",
        domain=domain,
        expected_label=DOMAIN_LABELS[domain],
        scenario=("Use the supplied governed authority to select the appropriate response."),
        authority_refs=(
            "authoritative policy",
            "system state",
            "release manifest",
        ),
    )


@pytest.mark.parametrize(
    ("domain", "expected"),
    tuple(DOMAIN_LABELS.items()),
)
def test_evaluator_generates_domain_judgment(
    domain: IntelligenceDomain,
    expected: str,
) -> None:
    judgment = IntelligenceEvaluator().evaluate(case(f"case-{domain.value}", domain))

    assert judgment.predicted_label == expected
    assert judgment.confidence > 0.0
    assert judgment.explanation_score >= 0.85
    assert judgment.evidence_completeness == 1.0
    assert not judgment.hallucination


def test_runner_and_calibration_work_end_to_end() -> None:
    cases = tuple(
        case(f"case-{index}", domain) for index, domain in enumerate(IntelligenceDomain, start=1)
    )

    judgments = IntelligenceEvaluationRunner().run(cases)
    report = IntelligenceCalibrationEngine().run(cases, judgments)

    assert len(judgments) == len(cases)
    assert report.case_count == len(cases)
    assert report.overall_accuracy == 1.0
    assert report.overall_brier_score <= 0.16
    assert report.overall_expected_calibration_error <= 0.10
    assert report.overall_hallucination_rate == 0.0
    assert report.release_eligible


def test_evaluator_does_not_read_expected_label() -> None:
    original = case("case-independent", IntelligenceDomain.ACTION)
    altered = original.model_copy(update={"expected_label": "intentionally-wrong"})

    first = IntelligenceEvaluator().evaluate(original)
    second = IntelligenceEvaluator().evaluate(altered)

    assert first.predicted_label == "act"
    assert second.predicted_label == "act"
