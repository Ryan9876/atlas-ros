from pathlib import Path

from atlas_ros.intelligence.dataset import EvaluationSetValidator, validate_files
from atlas_ros.intelligence.models import EvaluationCase, EvaluationDimension

ROOT = Path(__file__).parents[2]
CASES = ROOT / "evaluation/ryan-intelligence-evaluation-set/v1.0/cases.json"
BASELINE = ROOT / "evaluation/ryan-intelligence-evaluation-set/v1.0/baseline-v4.5.3.json"


def test_versioned_evaluation_set_is_valid() -> None:
    validation = validate_files(CASES, BASELINE)
    assert validation.valid
    assert validation.case_count == 18
    assert validation.result_count == 18
    assert set(validation.covered_dimensions) == set(EvaluationDimension)


def test_duplicate_case_ids_are_rejected() -> None:
    case = EvaluationCase(
        id="duplicate",
        title="Duplicate",
        scenario="Scenario",
        expected_behaviors=("Expected",),
        source_refs=("source",),
        dimensions=frozenset(EvaluationDimension),
        authority_context="authority",
    )
    validation = EvaluationSetValidator().validate((case,) * 12)
    assert not validation.valid
    assert any("duplicate case ids" in error for error in validation.errors)


def test_source_reference_is_required_by_set_policy() -> None:
    cases = tuple(
        EvaluationCase(
            id=f"case-{index}",
            title="Case",
            scenario="Scenario",
            expected_behaviors=("Expected",),
            dimensions=frozenset(EvaluationDimension),
            authority_context="authority",
        )
        for index in range(12)
    )
    validation = EvaluationSetValidator().validate(cases)
    assert not validation.valid
    assert any("source reference" in error for error in validation.errors)
