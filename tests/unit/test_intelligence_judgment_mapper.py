from pathlib import Path

from atlas_ros.intelligence.benchmark_adapter import (
    BenchmarkScenarioCompiler,
)
from atlas_ros.intelligence.calibration import (
    CalibrationCase,
    IntelligenceDomain,
)
from atlas_ros.intelligence.judgment_mapper import JudgmentMapper
from atlas_ros.intelligence.reasoning import GovernedReasoningEngine


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
    assert judgment.confidence > 0.0
    assert judgment.evidence_refs == case.authority_refs
    assert judgment.evidence_completeness == 1.0
    assert judgment.explanation_score > 0.0
    assert not judgment.hallucination
    assert "Decision quality=" in judgment.notes
