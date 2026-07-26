from __future__ import annotations

from collections.abc import Iterable

from atlas_ros.contracts.coherence_v1 import (
    CoherenceConditionResultV1,
    ConfidenceDimensionV1,
    ConfidenceSubject,
    ReasoningCoherenceResultV1,
)
from atlas_ros.contracts.models import deterministic_digest
from atlas_ros.contracts.semantic_v1 import ReasoningPackageV4
from atlas_ros.domain.models import Classification, ManagementWorkstream, ResponsibilityDomain


class ReasoningCoherenceGate:
    """Reconciles and validates reasoning metadata before management-plan approval."""

    _MATERIAL_CONFIDENCE_THRESHOLD = 0.75
    _HIGH_MODEL_CONFIDENCE = 0.90
    _CLARIFICATION_TERMS = (
        "needs clarification",
        "clarification required",
        "requires clarification",
        "must be clarified",
        "attended clarification",
    )

    def apply(
        self,
        reasoning: ReasoningPackageV4,
    ) -> tuple[ReasoningPackageV4, ReasoningCoherenceResultV1]:
        result = self.evaluate(reasoning)
        failures = tuple(
            condition.detail
            for condition in result.conditions
            if condition.material and not condition.passed
        )
        known_inputs = {
            **reasoning.known_inputs,
            "reasoning_coherence": result.model_dump(mode="json"),
        }
        updates: dict[str, object] = {
            "classification": result.resolved_classification,
            "destination": result.resolved_destination,
            "responsibility_domain": result.resolved_responsibility_domain,
            "workstream": result.resolved_workstream,
            "rationale": (result.explanation,),
            "known_inputs": known_inputs,
        }
        if result.passed:
            updates.update(
                {
                    "confidence": self._dimension(
                        result, ConfidenceSubject.CLASSIFICATION
                    ).confidence,
                    "challenge_status": (
                        "corrected" if self._resolution_changed(reasoning, result) else "accepted"
                    ),
                    "requires_human_decision": False,
                    "unresolved_planning_questions": (),
                    "intent_partition_ambiguities": (),
                }
            )
        else:
            updates.update(
                {
                    "challenge_status": "unresolved",
                    "requires_human_decision": True,
                    "unresolved_planning_questions": tuple(
                        dict.fromkeys((*reasoning.unresolved_planning_questions, *failures))
                    ),
                    "intent_partition_ambiguities": tuple(
                        dict.fromkeys((*reasoning.intent_partition_ambiguities, *failures))
                    ),
                }
            )
        payload = reasoning.model_dump(mode="python")
        payload.update(updates)
        return ReasoningPackageV4.model_validate(payload), result

    def evaluate(self, reasoning: ReasoningPackageV4) -> ReasoningCoherenceResultV1:
        resolution = self._resolve(reasoning)
        dimensions = self._dimensions(reasoning, resolution)
        low_dimensions = tuple(
            dimension.subject
            for dimension in dimensions
            if dimension.confidence < self._MATERIAL_CONFIDENCE_THRESHOLD
        )
        material_low = tuple(
            dimension.subject
            for dimension in dimensions
            if dimension.material
            and dimension.affects_execution_eligibility
            and dimension.confidence < self._MATERIAL_CONFIDENCE_THRESHOLD
        )
        original_text = " ".join(
            (
                *reasoning.rationale,
                reasoning.selection_rationale,
                reasoning.workstream,
                reasoning.destination,
            )
        ).casefold()
        clarification_language = any(term in original_text for term in self._CLARIFICATION_TERMS)
        governed_resolution = self._governed_resolution_available(reasoning)
        no_review_clarification = (
            not reasoning.requires_human_decision
            and clarification_language
            and not governed_resolution
        )
        model_workstream_conflict = (
            reasoning.selection_confidence >= self._HIGH_MODEL_CONFIDENCE
            and resolution["workstream"] == ManagementWorkstream.NEEDS_CLARIFICATION.value
            and not reasoning.requires_human_decision
        )
        unresolved_responsibility = (
            resolution["responsibility_domain"] == ResponsibilityDomain.UNRESOLVED.value
            and not reasoning.requires_human_decision
        )
        routing_conflict = (
            not reasoning.requires_human_decision
            and (
                resolution["classification"] == Classification.NEEDS_CLARIFICATION.value
                or "clarification" in resolution["destination"].casefold()
            )
        )
        checks = (
            self._condition(
                "clarification_state_consistency",
                not no_review_clarification,
                "clarification_state_conflict",
                "An approved no-review result cannot state that clarification is required.",
            ),
            self._condition(
                "planning_model_consistency",
                not model_workstream_conflict,
                "planning_model_workstream_conflict",
                "A high-confidence governed model cannot use the Needs Clarification workstream.",
            ),
            self._condition(
                "responsibility_consistency",
                not unresolved_responsibility,
                "unresolved_responsibility",
                "Material responsibility must be resolved or routed to attended review.",
            ),
            self._condition(
                "execution_decision_consistency",
                not material_low,
                "material_confidence_below_threshold",
                (
                    "Material confidence dimensions below the execution threshold: "
                    + ", ".join(subject.value for subject in material_low)
                    if material_low
                    else "All material confidence dimensions meet the execution threshold."
                ),
            ),
            self._condition(
                "routing_consistency",
                not routing_conflict,
                "routing_metadata_conflict",
                "Classification and destination must agree with the approved review state.",
            ),
            self._condition(
                "primary_outcome_present",
                bool(reasoning.primary_business_outcome.strip()),
                "primary_outcome_missing",
                "A coherent reasoning result requires a primary business outcome.",
            ),
        )
        passed = all(condition.passed for condition in checks if condition.material)
        explanation = self._explanation(reasoning, resolution, dimensions, passed)
        arguments: dict[str, object] = {
            "primary_business_outcome": reasoning.primary_business_outcome,
            "planning_model_id": reasoning.selected_planning_model_id,
            "confidence_dimensions": dimensions,
            "conditions": checks,
            "passed": passed,
            "review_required": not passed,
            "resolved_classification": resolution["classification"],
            "resolved_destination": resolution["destination"],
            "resolved_responsibility_domain": resolution["responsibility_domain"],
            "resolved_workstream": resolution["workstream"],
            "low_confidence_dimensions": low_dimensions,
            "explanation": explanation,
            "provider_writes": 0,
        }
        unsigned = ReasoningCoherenceResultV1(result_digest="0" * 64, **arguments)
        return ReasoningCoherenceResultV1(
            **arguments,
            result_digest=deterministic_digest(unsigned.digest_payload()),
        )

    def _resolve(self, reasoning: ReasoningPackageV4) -> dict[str, str]:
        if self._governed_resolution_available(reasoning):
            return {
                "classification": Classification.PROJECT.value,
                "destination": "Portfolio Projects",
                "responsibility_domain": ResponsibilityDomain.PROJECT_DELIVERY.value,
                "workstream": ManagementWorkstream.ACTIVE_PROJECTS.value,
            }
        return {
            "classification": reasoning.classification,
            "destination": reasoning.destination,
            "responsibility_domain": reasoning.responsibility_domain,
            "workstream": reasoning.workstream,
        }

    def _dimensions(
        self,
        reasoning: ReasoningPackageV4,
        resolution: dict[str, str],
    ) -> tuple[ConfidenceDimensionV1, ...]:
        governed_resolution = self._governed_resolution_available(reasoning)
        classification_confidence = (
            max(reasoning.confidence, 0.95) if governed_resolution else reasoning.confidence
        )
        responsibility_confidence = (
            min(reasoning.selection_confidence, 0.95)
            if governed_resolution
            else (
                reasoning.confidence
                if resolution["responsibility_domain"] != ResponsibilityDomain.UNRESOLVED.value
                else 0.0
            )
        )
        routing_confidence = (
            min(classification_confidence, responsibility_confidence)
            if resolution["classification"] != Classification.NEEDS_CLARIFICATION.value
            else 0.0
        )
        semantic_confidence = min(
            reasoning.intent_partition_confidence,
            reasoning.selection_confidence,
        )
        return (
            self._dimension_value(
                ConfidenceSubject.INTENT_PARTITION,
                reasoning.intent_partition_confidence,
                ("Intent Partition V1 confidence and ambiguity state.",),
                related=(ConfidenceSubject.PLANNING_MODEL, ConfidenceSubject.SEMANTIC_FIDELITY),
            ),
            self._dimension_value(
                ConfidenceSubject.PLANNING_MODEL,
                reasoning.selection_confidence,
                (reasoning.selection_rationale,),
                related=(ConfidenceSubject.INTENT_PARTITION, ConfidenceSubject.RESPONSIBILITY_RESOLUTION),
            ),
            self._dimension_value(
                ConfidenceSubject.CLASSIFICATION,
                classification_confidence,
                (
                    "Legacy classification evidence reconciled with governed planning-model evidence."
                    if governed_resolution
                    else "Responsibility-classification evidence."
                ,),
                related=(ConfidenceSubject.RESPONSIBILITY_RESOLUTION, ConfidenceSubject.ROUTING),
            ),
            self._dimension_value(
                ConfidenceSubject.RESPONSIBILITY_RESOLUTION,
                responsibility_confidence,
                (
                    "Controlled-technology-pilot governance resolves project-delivery responsibility."
                    if governed_resolution
                    else "Responsibility-domain classification evidence."
                ,),
                related=(ConfidenceSubject.PLANNING_MODEL, ConfidenceSubject.CLASSIFICATION),
            ),
            self._dimension_value(
                ConfidenceSubject.ROUTING,
                routing_confidence,
                ("Resolved classification, responsibility, and destination alignment.",),
                related=(ConfidenceSubject.CLASSIFICATION, ConfidenceSubject.RESPONSIBILITY_RESOLUTION),
            ),
            self._dimension_value(
                ConfidenceSubject.SEMANTIC_FIDELITY,
                semantic_confidence,
                ("Primary outcome and selected planning model are based on the same intent partition.",),
                related=(ConfidenceSubject.INTENT_PARTITION, ConfidenceSubject.PLANNING_MODEL),
            ),
        )

    def _dimension_value(
        self,
        subject: ConfidenceSubject,
        confidence: float,
        evidence_basis: tuple[str, ...],
        *,
        related: tuple[ConfidenceSubject, ...],
    ) -> ConfidenceDimensionV1:
        requires_review = confidence < self._MATERIAL_CONFIDENCE_THRESHOLD
        return ConfidenceDimensionV1(
            subject=subject,
            confidence=confidence,
            evidence_basis=evidence_basis,
            affects_execution_eligibility=True,
            requires_attended_review=requires_review,
            related_dimensions=related,
            material=True,
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
            reason_code=f"{code}_{'passed' if passed else 'failed'}",
            detail=detail,
            material=True,
        )

    @staticmethod
    def _governed_resolution_available(reasoning: ReasoningPackageV4) -> bool:
        return (
            reasoning.selected_planning_model_id == "controlled-technology-pilot"
            and reasoning.selection_confidence >= 0.90
            and bool(reasoning.primary_business_outcome.strip())
            and not reasoning.intent_partition_ambiguities
        )

    @staticmethod
    def _resolution_changed(
        reasoning: ReasoningPackageV4,
        result: ReasoningCoherenceResultV1,
    ) -> bool:
        return any(
            (
                reasoning.classification != result.resolved_classification,
                reasoning.destination != result.resolved_destination,
                reasoning.responsibility_domain != result.resolved_responsibility_domain,
                reasoning.workstream != result.resolved_workstream,
            )
        )

    @staticmethod
    def _dimension(
        result: ReasoningCoherenceResultV1,
        subject: ConfidenceSubject,
    ) -> ConfidenceDimensionV1:
        return next(dimension for dimension in result.confidence_dimensions if dimension.subject is subject)

    @staticmethod
    def _low_dimension_names(dimensions: Iterable[ConfidenceDimensionV1]) -> tuple[str, ...]:
        return tuple(
            dimension.subject.value
            for dimension in dimensions
            if dimension.confidence < ReasoningCoherenceGate._MATERIAL_CONFIDENCE_THRESHOLD
        )

    def _explanation(
        self,
        reasoning: ReasoningPackageV4,
        resolution: dict[str, str],
        dimensions: tuple[ConfidenceDimensionV1, ...],
        passed: bool,
    ) -> str:
        low = self._low_dimension_names(dimensions)
        current_count = len(reasoning.current_business_actions)
        delegated_count = len(reasoning.delegated_actions)
        conditional_count = len(reasoning.conditional_actions)
        clarification = "No" if passed else "Yes"
        confidence_note = (
            "All material confidence dimensions support execution."
            if not low
            else "Low confidence affects execution: " + ", ".join(low) + "."
        )
        return (
            f'Identified outcome: "{reasoning.primary_business_outcome}". '
            f"Selected planning model: {reasoning.selected_planning_model_id}. "
            f"Projected current actions: {current_count}. "
            f"Delegated or withheld actions: {delegated_count + conditional_count}. "
            f"Responsibility: {resolution['responsibility_domain']}; "
            f"workstream: {resolution['workstream']}. "
            f"Clarification required: {clarification}. {confidence_note}"
        )
