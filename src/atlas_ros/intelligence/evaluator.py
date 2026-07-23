from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from tempfile import TemporaryDirectory

from atlas_ros.intelligence.benchmark_adapter import (
    BenchmarkScenarioCompiler,
)
from atlas_ros.intelligence.calibration import (
    CalibrationCase,
    IntelligenceJudgment,
)
from atlas_ros.intelligence.judgment_mapper import JudgmentMapper
from atlas_ros.intelligence.reasoning import GovernedReasoningEngine

DEFAULT_EVALUATOR_VERSION = "rie-cal-2.0"


class IntelligenceEvaluator:
    """Runs calibration cases through the governed reasoning engine."""

    def __init__(
        self,
        evaluator_version: str = DEFAULT_EVALUATOR_VERSION,
    ) -> None:
        self.evaluator_version = evaluator_version

    def evaluate(self, case: CalibrationCase) -> IntelligenceJudgment:
        with TemporaryDirectory(prefix="atlas-rie-") as temporary_directory:
            compiler = BenchmarkScenarioCompiler(Path(temporary_directory))
            compiled = compiler.compile(case)

            engine = GovernedReasoningEngine(compiled.store)
            outcome = engine.evaluate(compiled.request)

            mapper = JudgmentMapper(self.evaluator_version)
            return mapper.map(compiled, outcome)


class IntelligenceEvaluationRunner:
    """Runs the governed evaluator across a calibration dataset."""

    def __init__(
        self,
        evaluator: IntelligenceEvaluator | None = None,
    ) -> None:
        self.evaluator = evaluator or IntelligenceEvaluator()

    def run(
        self,
        cases: Iterable[CalibrationCase],
    ) -> tuple[IntelligenceJudgment, ...]:
        return tuple(self.evaluator.evaluate(case) for case in cases)


def create_judgment(
    *,
    case: CalibrationCase,
    predicted_label: str,
    confidence: float,
    evidence_refs: tuple[str, ...],
    explanation_score: float,
    evidence_completeness: float,
    hallucination: bool,
    accepted_by_reviewer: bool | None = None,
    notes: str = "",
    evaluator_version: str = DEFAULT_EVALUATOR_VERSION,
) -> IntelligenceJudgment:
    """Construct and validate an intelligence judgment."""

    return IntelligenceJudgment(
        case_id=case.id,
        evaluator_version=evaluator_version,
        predicted_label=predicted_label,
        confidence=confidence,
        evidence_refs=evidence_refs,
        explanation_score=explanation_score,
        evidence_completeness=evidence_completeness,
        hallucination=hallucination,
        accepted_by_reviewer=accepted_by_reviewer,
        notes=notes,
    )
