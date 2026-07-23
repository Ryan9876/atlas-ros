from pathlib import Path

import pytest

from atlas_ros.intelligence.benchmark_adapter import (
    BenchmarkScenarioCompiler,
)
from atlas_ros.intelligence.calibration import (
    CalibrationCase,
    IntelligenceDomain,
)
from atlas_ros.intelligence.judgment_mapper import JudgmentMapper
from atlas_ros.intelligence.reasoning import (
    GovernedReasoningEngine,
    ReasoningOutcome,
    ReasoningTrace,
)


def test_mapper_creates_grounded_judgment(tmp_path: Path) -> None:
    case = CalibrationCase(
        id="RIE-TEST-002",
        title="Escalate material risk",
        domain=IntelligenceDomain.RISK,
        expected_label="not-read",
        scenario="Material production risk requires governed escalation.",
        authority_refs=("production risk register",),
    )

    compiled = BenchmarkScenarioCompiler(tmp_path).compile(case)
    outcome = GovernedReasoningEngine(compiled.store).evaluate(compiled.request)

    judgment = JudgmentMapper("test-evaluator").map(compiled, outcome)

    assert judgment.case_id == case.id
    assert judgment.predicted_label == "escalate"
    assert outcome.recommendation is not None
    adjusted_score_total = sum(item.adjusted_score for item in outcome.trace.ranked_options)
    assert judgment.confidence == pytest.approx(
        outcome.trace.ranked_options[0].adjusted_score / adjusted_score_total
    )
    assert judgment.confidence > outcome.recommendation.confidence
    assert judgment.evidence_refs == case.authority_refs
    assert judgment.evidence_completeness == 1.0
    assert judgment.explanation_score > 0.0
    assert not judgment.hallucination
    assert "Decision quality=" in judgment.notes


def test_abstention_confidence_uses_trace_uncertainty() -> None:
    outcome = ReasoningOutcome(
        trace=ReasoningTrace(
            objective="Do not force an unsupported result",
            evidence=(),
            ranked_options=(),
            selected_option=None,
            abstained=True,
            explanation="Evidence is insufficient.",
            uncertainty=0.84,
        ),
        recommendation=None,
    )

    assert JudgmentMapper._selection_confidence(outcome) == 0.84


def test_selection_confidence_is_zero_when_adjusted_scores_are_zero(
    tmp_path: Path,
) -> None:
    case = CalibrationCase(
        id="RIE-TEST-003",
        title="Act on governed evidence",
        domain=IntelligenceDomain.ACTION,
        expected_label="act",
        scenario="Use the governed evidence.",
        authority_refs=("authoritative policy",),
    )
    compiled = BenchmarkScenarioCompiler(tmp_path).compile(case)
    outcome = GovernedReasoningEngine(compiled.store).evaluate(compiled.request)
    assert outcome.recommendation is not None
    zero_score_trace = outcome.trace.model_copy(
        update={
            "ranked_options": tuple(
                option.model_copy(update={"adjusted_score": 0.0})
                for option in outcome.trace.ranked_options
            )
        }
    )

    assert (
        JudgmentMapper._selection_confidence(
            ReasoningOutcome(
                trace=zero_score_trace,
                recommendation=outcome.recommendation,
            )
        )
        == 0.0
    )
