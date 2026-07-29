"""Deterministic provider-write-free baseline reporting for Atlas ROS v7.5.2."""

from __future__ import annotations

from atlas_ros.clarification_evaluation_v752 import (
    ClarificationEvaluationCaseV1,
    ClarificationEvaluationReportV1,
    build_report,
)


def recommend_thresholds(
    cases: tuple[ClarificationEvaluationCaseV1, ...],
) -> tuple[str, ...]:
    """Recommend review thresholds from observed evidence without creating policy."""

    if not cases:
        return ("Collect a non-empty retained corpus before proposing acceptance thresholds.",)
    report = build_report(
        feature_mode="shadow",
        snapshot_digest=cases[0].event.snapshot_digest,
        cases=cases,
    )
    metrics = report.metrics
    recommendations: list[str] = []
    if metrics.repeated_questions:
        recommendations.append(
            "Review repeated-question rate observed in "
            f"{metrics.repeated_questions}/{metrics.total_cases} cases."
        )
    if metrics.no_material_change_questions:
        recommendations.append(
            "Review questions that produced no material change before setting a "
            "clarification-frequency target."
        )
    if metrics.task_suppression_prevented or metrics.duplicate_task_creation_prevented:
        recommendations.append(
            "Preserve consequence controls because observed questions prevented "
            "incorrect execution-path effects."
        )
    if not recommendations:
        recommendations.append(
            "Retain the observed baseline and gather additional representative cases "
            "before setting thresholds."
        )
    return tuple(recommendations)


def build_baseline_report(
    *,
    snapshot_digest: str,
    cases: tuple[ClarificationEvaluationCaseV1, ...],
) -> ClarificationEvaluationReportV1:
    """Create a deterministic retained-artifact report with evidence-based recommendations."""

    return build_report(
        feature_mode="shadow",
        snapshot_digest=snapshot_digest,
        cases=cases,
        recommended_thresholds=recommend_thresholds(cases),
    )
