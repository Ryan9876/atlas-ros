from __future__ import annotations

from atlas_ros.contracts.coherence_v1 import (
    CoherenceConditionResultV1,
    ReasoningCoherenceResultV1,
)
from atlas_ros.contracts.models import deterministic_digest
from atlas_ros.contracts.semantic_v1 import ReasoningPackageV4

_REQUIRED_DIMENSIONS = {
    "intent_partition",
    "planning_model",
    "classification",
    "responsibility_resolution",
    "routing",
    "semantic_fidelity",
}
_CLARIFICATION_TERMS = (
    "needs clarification",
    "clarification required",
    "requires clarification",
    "clarify before",
    "attended clarification",
)


class ReasoningCoherenceGate:
    """Validate one governed conclusion across reasoning and execution metadata."""

    def evaluate(self, reasoning: ReasoningPackageV4) -> ReasoningCoherenceResultV1:
        explanation = " ".join((*reasoning.rationale, reasoning.user_facing_summary)).casefold()
        says_clarification = any(term in explanation for term in _CLARIFICATION_TERMS)
        high_model_confidence = reasoning.selection_confidence >= 0.85
        unresolved_responsibility = reasoning.responsibility_domain == "unresolved"
        unresolved_workstream = reasoning.workstream == "Needs Clarification"
        expected_destination = self._expected_destination(reasoning.classification)
        route_consistent = (
            expected_destination is None or reasoning.destination == expected_destination
        )
        dimensions = {item.dimension: item for item in reasoning.confidence_dimensions}
        complete_dimensions = _REQUIRED_DIMENSIONS <= dimensions.keys()
        responsibility_dimension = dimensions.get("responsibility_resolution")
        material_responsibility_low = (
            responsibility_dimension is None
            or (
                responsibility_dimension.affects_execution_eligibility
                and responsibility_dimension.score < 0.75
                and not responsibility_dimension.requires_attended_review
            )
        )

        checks = (
            (
                "clarification_state_consistency",
                reasoning.requires_human_decision or not says_clarification,
                True,
                "clarification_state_consistent",
                "No-review reasoning cannot state that clarification is required.",
            ),
            (
                "planning_model_consistency",
                not high_model_confidence
                or not (unresolved_responsibility or unresolved_workstream)
                or reasoning.requires_human_decision,
                True,
                "planning_model_consistent",
                (
                    "High-confidence governed model selection cannot silently coexist with "
                    "unresolved responsibility or workstream metadata."
                ),
            ),
            (
                "responsibility_consistency",
                not unresolved_responsibility
                or reasoning.requires_human_decision,
                True,
                "responsibility_consistent",
                (
                    "Unresolved responsibility must require attended review before "
                    "execution eligibility."
                ),
            ),
            (
                "execution_decision_consistency",
                not material_responsibility_low,
                True,
                "execution_decision_consistent",
                "Execution-affecting low confidence must be marked for attended review.",
            ),
            (
                "routing_consistency",
                route_consistent,
                True,
                "routing_consistent",
                "Classification and destination must resolve to the same governed route.",
            ),
            (
                "confidence_dimension_completeness",
                complete_dimensions,
                True,
                "confidence_dimensions_complete",
                "All governed confidence dimensions must be explicit.",
            ),
        )
        conditions = tuple(
            CoherenceConditionResultV1(
                condition=name,
                passed=passed,
                material=material,
                reason_code=f"{code}_{'passed' if passed else 'failed'}",
                detail=detail,
            )
            for name, passed, material, code, detail in checks
        )
        failures = tuple(item.condition for item in conditions if item.material and not item.passed)
        passed = not failures
        summary = self._summary(reasoning, failures)
        unsigned = ReasoningCoherenceResultV1(
            conditions=conditions,
            passed=passed,
            review_required=not passed,
            material_contradictions=failures,
            non_blocking_findings=(),
            user_facing_summary=summary,
            result_digest="0" * 64,
        )
        return ReasoningCoherenceResultV1(
            conditions=conditions,
            passed=passed,
            review_required=not passed,
            material_contradictions=failures,
            non_blocking_findings=(),
            user_facing_summary=summary,
            result_digest=deterministic_digest(unsigned.digest_payload()),
        )

    @staticmethod
    def _expected_destination(classification: str) -> str | None:
        return {
            "action": "action_records",
            "project": "portfolio_projects",
            "delegated_work": "delegated_work",
            "risk": "risks_and_blockers",
            "decision": "decision_log",
            "reference": "reference",
            "needs_clarification": "universal_inbox",
        }.get(classification)

    @staticmethod
    def _summary(reasoning: ReasoningPackageV4, failures: tuple[str, ...]) -> str:
        delegated = "Delegated implementation remains outside current execution."
        conditional = "Conditional work remains withheld until its trigger is satisfied."
        if failures:
            joined = ", ".join(failures)
            return (
                f"Atlas identified '{reasoning.primary_business_outcome}' and selected "
                f"'{reasoning.selected_planning_model_id}', but attended review is required "
                f"because reasoning coherence failed: {joined}. No provider execution is eligible."
            )
        low_non_blocking = [
            item.dimension
            for item in reasoning.confidence_dimensions
            if item.score < 0.75 and not item.affects_execution_eligibility
        ]
        low_note = (
            f" Low non-blocking confidence remains in: {', '.join(low_non_blocking)}."
            if low_non_blocking
            else ""
        )
        clarification = (
            "Attended clarification is required for unresolved governed inputs."
            if reasoning.requires_human_decision
            else "No clarification is needed."
        )
        current_path = (
            "It selected the governed current path for scope and success measures, "
            "technical ownership and low-risk targets, and controls, evidence, and rollback."
            if reasoning.selected_planning_model_id == "controlled-technology-pilot"
            else "It retained the explicit primary business outcome as the current execution path."
        )
        return (
            f"Atlas identified '{reasoning.primary_business_outcome}' and selected "
            f"'{reasoning.selected_planning_model_id}'. {current_path} {delegated} "
            f"{conditional} {clarification}{low_note}"
        )
