from pathlib import Path

import pytest

from atlas_ros.intelligence.benchmark_adapter import (
    DOMAIN_LABELS,
    BenchmarkScenarioCompiler,
)
from atlas_ros.intelligence.calibration import (
    CalibrationCase,
    IntelligenceDomain,
)
from atlas_ros.intelligence.reasoning import GovernedReasoningEngine


@pytest.fixture
def calibration_case() -> CalibrationCase:
    return CalibrationCase(
        id="RIE-TEST-001",
        title="Prioritize live authority",
        domain=IntelligenceDomain.PRIORITY,
        expected_label="deliberately-not-used",
        scenario=(
            "A live release index conflicts with stale chat history. "
            "Choose the appropriate governed response."
        ),
        authority_refs=(
            "Live Release Index",
            "Notion System State",
        ),
        tags=frozenset({"critical", "authority"}),
    )


def test_compiler_builds_resolvable_reasoning_request(
    tmp_path: Path,
    calibration_case: CalibrationCase,
) -> None:
    compiled = BenchmarkScenarioCompiler(tmp_path).compile(calibration_case)

    context = compiled.store.resolve(compiled.request.context_ref)

    assert context.active_objective == calibration_case.title
    assert len(context.evidence_refs) == 3
    assert compiled.request.objective == calibration_case.scenario
    assert {option.option for option in compiled.request.options} == {"prioritize", "abstain"}


def test_compiler_does_not_depend_on_expected_label(
    tmp_path: Path,
    calibration_case: CalibrationCase,
) -> None:
    first = BenchmarkScenarioCompiler(tmp_path / "first").compile(calibration_case)
    changed = calibration_case.model_copy(update={"expected_label": "incorrect-test-value"})
    second = BenchmarkScenarioCompiler(tmp_path / "second").compile(changed)

    assert tuple(option.option for option in first.request.options) == tuple(
        option.option for option in second.request.options
    )


@pytest.mark.parametrize(
    ("domain", "label"),
    tuple(DOMAIN_LABELS.items()),
)
def test_each_domain_compiles_to_governed_action(
    tmp_path: Path,
    domain: IntelligenceDomain,
    label: str,
) -> None:
    case = CalibrationCase(
        id=f"case-{domain.value}",
        title="Domain behavior",
        domain=domain,
        expected_label="not-consulted",
        scenario="Apply the governed behavior using current authority.",
        authority_refs=("governed policy",),
    )

    compiled = BenchmarkScenarioCompiler(tmp_path / domain.value).compile(case)
    outcome = GovernedReasoningEngine(compiled.store).evaluate(compiled.request)

    assert not outcome.trace.abstained
    assert outcome.trace.selected_option == label
    assert outcome.recommendation is not None
    assert outcome.recommendation.recommendation == label
