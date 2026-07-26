from __future__ import annotations

from atlas_ros.contracts.coherence_v1 import (
    CoherenceConditionResultV1,
    ConfidenceDimensionV1,
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
    """Resolve and validate one governed conclusion before management approval."""

    def apply(
        self, reasoning: ReasoningPackageV4
    ) -> tuple[ReasoningPackageV4, ReasoningCoherenceResultV1]:
        is_governed_pilot = (
            reasoning.selected_planning_model_id == "controlled-technology-pilot"
            and reasoning.selection_confidence >= 0.90
            and bool(reasoning.primary_business_outcome)
            and not reasoning.intent_partition_ambiguities
        )
        classification = "project" if is_governed_pilot else reasoning.classification
        destination = (
            self._expected_destination(classification) or reasoning.destination
            if is_governed_pilot
            else reasoning.destination
        )
        responsibility = (
            "project_delivery" if is_governed_pilot else reasoning.responsibility_domain
        )
        workstream = "Active Projects" if is_governed_pilot else reasoning.workstream
        legacy_confidence = (
            max(reasoning.confidence, 0.95)
            if is_governed_pilot
            else reasoning.confidence
        )
        review_pending = bool(
            reasoning.intent_partition_ambiguities
            or reasoning.unresolved_planning_questions
        )
        dimensions = self._confidence_dimensions(
            reasoning,
            classification_confidence=(0.95 if is_governed_pilot else legacy_confidence),
            responsibility_confidence=(0.95 if is_governed_pilot else legacy_confidence),
            routing_confidence=(0.95 if is_governed_pilot else legacy_confidence),
            requires_review=review_pending,
            is_governed_pilot=is_governed_pilot,
        )
        provisional_payload = reasoning.model_dump(mode="python")
        provisional_payload.update(
            {
                "classification": classification,
                "destination": destination,
                "responsibility_domain": responsibility,
                "workstream": workstream,
                "confidence": legacy_confidence,
                "rationale": (
                    (
                        "Atlas selected the controlled-technology-pilot model and resolved "
                        "project-delivery responsibility from governed model evidence."
                    )
                    if is_governed_pilot
                    else (
                        "Atlas retained the governed classification and "
                        "responsibility evidence."
                    )
                ,),
                "challenge_status": (
                    "corrected" if is_governed_pilot else reasoning.challenge_status
                ),
                "requires_human_decision": review_pending,
                "confidence_dimensions": dimensions,
                "coherence_result": None,
                "user_facing_summary": "Reasoning coherence evaluation is pending.",
            }
        )
        provisional = ReasoningPackageV4.model_validate(provisional_payload)
        result = self.evaluate(provisional)
        final_review = review_pending or result.review_required
        questions = tuple(
            dict.fromkeys(
                (
                    *provisional.unresolved_planning_questions,
                    *(
                        f"Reasoning coherence: {item}."
                        for item in result.material_contradictions
                    ),
                )
            )
        )
        ambiguities = (
            provisional.intent_partition_ambiguities
            if not result.review_required
            else tuple(
                dict.fromkeys(
                    (
                        *provisional.intent_partition_ambiguities,
                        *result.material_contradictions,
                    )
                )
            )
        )
        final_payload = provisional.model_dump(mode="python")
        final_payload.update(
            {
                "requires_human_decision": final_review,
                "unresolved_planning_questions": questions,
                "intent_partition_ambiguities": ambiguities,
                "coherence_result": result,
                "user_facing_summary": result.user_facing_summary,
            }
        )
        final = ReasoningPackageV4.model_validate(final_payload)
        return final, result

    def evaluate(self, reasoning: ReasoningPackageV4) -> ReasoningCoherenceResultV1:
        explanation = " ".join(
            (*reasoning.rationale, reasoning.user_facing_summary)
        ).casefold()
        says_clarification = any(
            term in explanation for term in _CLARIFICATION_TERMS
        )
        high_model_confidence = reasoning.selection_confidence >= 0.85
        unresolved_responsibility = reasoning.responsibility_domain == "unresolved"
        unresolved_workstream = reasoning.workstream == "Needs Clarification"
        expected_destination = self._expected_destination(reasoning.classification)
        route_consistent = (
            expected_destination is None or reasoning.destination == expected_destination
        )
        dimensions = {
            item.dimension: item for item in reasoning.confidence_dimensions
        }
        complete_dimensions = dimensions.keys() >= _REQUIRED_DIMENSIONS
        material_confidence_consistent = all(
            not (
                item.affects_execution_eligibility
                and item.score < 0.75
                and not item.requires_attended_review
            )
            for item in dimensions.values()
        )
        checks = (
            self._condition(
                "clarification_state_consistency",
                reasoning.requires_human_decision or not says_clarification,
                "clarification_state_consistent",
                "No-review reasoning cannot state that clarification is required.",
            ),
            self._condition(
                "planning_model_consistency",
                not high_model_confidence
                or not (unresolved_responsibility or unresolved_workstream)
                or reasoning.requires_human_decision,
                "planning_model_consistent",
                (
                    "High-confidence governed model selection cannot silently coexist "
                    "with unresolved responsibility or workstream metadata."
                ),
            ),
            self._condition(
                "responsibility_consistency",
                not unresolved_responsibility
                or reasoning.requires_human_decision,
                "responsibility_consistent",
                (
                    "Unresolved responsibility must require attended review before "
                    "execution eligibility."
                ),
            ),
            self._condition(
                "execution_decision_consistency",
                material_confidence_consistent,
                "execution_decision_consistent",
                (
                    "Execution-affecting low confidence must be marked for "
                    "attended review."
                ),
            ),
            self._condition(
                "routing_consistency",
                route_consistent,
                "routing_consistent",
                (
                    "Classification and destination must resolve to the same "
                    "governed route."
                ),
            ),
            self._condition(
                "confidence_dimension_completeness",
                complete_dimensions,
                "confidence_dimensions_complete",
                "All governed confidence dimensions must be explicit.",
            ),
        )
        failures = tuple(
            item.condition for item in checks if item.material and not item.passed
        )
        passed = not failures
        summary = self._summary(reasoning, failures)
        values: dict[str, object] = {
            "conditions": checks,
            "passed": passed,
            "review_required": not passed,
            "material_contradictions": failures,
            "non_blocking_findings": (),
            "user_facing_summary": summary,
        }
        unsigned = ReasoningCoherenceResultV1(
            **values,
            result_digest="0" * 64,
        )
        return ReasoningCoherenceResultV1(
            **values,
            result_digest=deterministic_digest(unsigned.digest_payload()),
        )

    @staticmethod
    def _condition(
        name: str,
        passed: bool,
        code: str,
        detail: str,
    ) -> CoherenceConditionResultV1:
        return CoherenceConditionResultV1(
            condition=name,
            passed=passed,
            material=True,
            reason_code=f"{code}_{'passed' if passed else 'failed'}",
            detail=detail,
        )

    @staticmethod
    def _confidence_dimensions(
        reasoning: ReasoningPackageV4,
        *,
        classification_confidence: float,
        responsibility_confidence: float,
        routing_confidence: float,
        requires_review: bool,
        is_governed_pilot: bool,
    ) -> tuple[ConfidenceDimensionV1, ...]:
        model_evidence = (
            "Governed controlled-technology-pilot model evidence."
            if is_governed_pilot
            else "Governed single-business-outcome model evidence."
        )
        values = (
            (
                "intent_partition",
                "Primary business outcome and instruction-role separation",
                reasoning.intent_partition_confidence,
                "Intent Partition V1 deterministic role precedence.",
            ),
            (
                "planning_model",
                "Governed planning-model selection",
                reasoning.selection_confidence,
                model_evidence,
            ),
            (
                "classification",
                "Canonical record classification",
                classification_confidence,
                model_evidence,
            ),
            (
                "responsibility_resolution",
                "Accountable responsibility domain",
                responsibility_confidence,
                model_evidence,
            ),
            (
                "routing",
                "Canonical management destination",
                routing_confidence,
                "Classification-to-destination policy mapping.",
            ),
            (
                "semantic_fidelity",
                "Pre-plan semantic eligibility",
                min(
                    reasoning.intent_partition_confidence,
                    reasoning.selection_confidence,
                ),
                "Primary outcome and control-plane separation evidence.",
            ),
        )
        return tuple(
            ConfidenceDimensionV1(
                dimension=dimension,  # type: ignore[arg-type]
                subject=subject,
                score=score,
                evidence_basis=(evidence,),
                affects_execution_eligibility=True,
                requires_attended_review=requires_review and score < 0.75,
                relationship=(
                    "Must agree with the other governed confidence dimensions.",
                ),
            )
            for dimension, subject, score, evidence in values
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
    def _summary(
        reasoning: ReasoningPackageV4,
        failures: tuple[str, ...],
    ) -> str:
        delegated = "Delegated implementation remains outside current execution."
        conditional = (
            "Conditional work remains withheld until its trigger is satisfied."
        )
        if failures:
            joined = ", ".join(failures)
            return (
                f"Atlas identified '{reasoning.primary_business_outcome}' and selected "
                f"'{reasoning.selected_planning_model_id}', but attended review is "
                f"required because reasoning coherence failed: {joined}. No provider "
                "execution is eligible."
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
            "technical ownership and low-risk targets, and controls, evidence, "
            "and rollback."
            if reasoning.selected_planning_model_id == "controlled-technology-pilot"
            else (
                "It retained the explicit primary business outcome as the current "
                "execution path."
            )
        )
        return (
            f"Atlas identified '{reasoning.primary_business_outcome}' and selected "
            f"'{reasoning.selected_planning_model_id}'. {current_path} {delegated} "
            f"{conditional} {clarification}{low_note}"
        )
