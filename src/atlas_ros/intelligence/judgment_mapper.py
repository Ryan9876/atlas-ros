from __future__ import annotations

from atlas_ros.intelligence.benchmark_adapter import CompiledBenchmarkCase
from atlas_ros.intelligence.calibration import IntelligenceJudgment
from atlas_ros.intelligence.reasoning import (
    GovernedReasoningEngine,
    ReasoningOutcome,
)


class JudgmentMapper:
    """Maps governed reasoning outcomes to calibration judgments."""

    def __init__(self, evaluator_version: str) -> None:
        self.evaluator_version = evaluator_version

    def map(
        self,
        compiled: CompiledBenchmarkCase,
        outcome: ReasoningOutcome,
    ) -> IntelligenceJudgment:
        trace = outcome.trace
        predicted_label = trace.selected_option or "abstain"

        usable_evidence = sum(item.usable for item in trace.evidence)
        evidence_total = len(trace.evidence)
        evidence_completeness = usable_evidence / evidence_total if evidence_total else 0.0

        decision_quality = GovernedReasoningEngine.decision_quality(trace)
        explanation_score = self._explanation_score(outcome)
        confidence = self._selection_confidence(outcome)

        hallucination = predicted_label not in compiled.permitted_labels

        notes = (
            f"{trace.explanation} "
            f"Decision quality={decision_quality:.3f}; "
            f"uncertainty={trace.uncertainty:.3f}; "
            f"usable evidence={usable_evidence}/{evidence_total}."
        )

        return IntelligenceJudgment(
            case_id=compiled.case.id,
            evaluator_version=self.evaluator_version,
            predicted_label=predicted_label,
            confidence=confidence,
            evidence_refs=compiled.evidence_refs,
            explanation_score=explanation_score,
            evidence_completeness=evidence_completeness,
            hallucination=hallucination,
            notes=notes,
        )

    @staticmethod
    def _selection_confidence(outcome: ReasoningOutcome) -> float:
        """Return confidence that the evaluator selected the correct label.

        Recommendation confidence is an absolute action-safety score. It
        intentionally includes evidence, claim, and graph-support penalties,
        so it must not be interpreted as the probability that the leading
        option outranked its alternatives correctly. Calibration judgments
        instead use the leading option's share of the non-negative adjusted
        scores.
        """

        trace = outcome.trace
        if outcome.recommendation is None:
            return trace.uncertainty

        adjusted_scores = tuple(
            max(0.0, option.adjusted_score) for option in trace.ranked_options
        )
        score_total = sum(adjusted_scores)
        if not adjusted_scores or score_total <= 0.0:
            return 0.0

        return adjusted_scores[0] / score_total

    @staticmethod
    def _explanation_score(outcome: ReasoningOutcome) -> float:
        trace = outcome.trace
        if not trace.explanation.strip():
            return 0.0

        score = 0.45

        if trace.ranked_options:
            score += 0.20

        if len(trace.ranked_options) >= 2:
            score += 0.15

        if outcome.recommendation is not None:
            if outcome.recommendation.rationale.strip():
                score += 0.10
            if outcome.recommendation.expected_benefit.strip():
                score += 0.05
            if outcome.recommendation.expected_risk.strip():
                score += 0.05

        return min(1.0, score)
