"""Compatibility binding to the accepted v7.5.2 clarification authority."""
from __future__ import annotations

from dataclasses import dataclass

from atlas_ros.contracts.clarification_compatibility import (
    ClarificationDecisionV752Compatibility,
    ClarificationStatusV752,
    ConsequenceAssessmentV752,
    ContextFamiliarityV752,
    EvidenceLevelV752,
    RelationshipClassificationV752,
)
from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.contracts.operational_awareness.clarification import (
    ClarificationAnalysisV1,
    ClarificationCompatibilityBindingV1,
    ClarificationContextV1,
)


@dataclass(frozen=True, slots=True)
class ClarificationCompatibilityAdapter:
    """Map v8.1 analysis into the accepted v7.5.2 decision shape."""

    def bind(
        self,
        analysis: ClarificationAnalysisV1,
        *,
        context: ClarificationContextV1 | None = None,
        familiarity: ContextFamiliarityV752 | None = None,
        consequence: ConsequenceAssessmentV752 | None = None,
    ) -> tuple[
        ClarificationDecisionV752Compatibility,
        ClarificationCompatibilityBindingV1,
    ]:
        bounded = context or ClarificationContextV1()
        familiarity_value = familiarity or ContextFamiliarityV752(
            user=0.5,
            domain=0.5,
            project=0.5,
            terminology=0.5,
            evidence_recency=0.5,
            interpretation_consistency=analysis.confidence.score or 0.0,
        )
        consequence_value = consequence or ConsequenceAssessmentV752(reversible=True)
        relationship = (
            RelationshipClassificationV752.NEEDS_CLARIFICATION
            if analysis.clarification_required
            else RelationshipClassificationV752.DISTINCT_OUTCOME
        )
        status = (
            ClarificationStatusV752.REQUIRED
            if analysis.clarification_required
            else ClarificationStatusV752.NOT_REQUIRED
        )
        decision = ClarificationDecisionV752Compatibility(
            original_capture=analysis.original_instruction,
            related_record_ids=bounded.related_record_ids,
            candidate_interpretations=tuple(
                candidate.normalized_instruction for candidate in analysis.candidates
            ),
            material_distinction=self._material_distinction(analysis),
            evidence_level=self._evidence_level(analysis),
            familiarity=familiarity_value,
            consequence=consequence_value,
            relationship=relationship,
            clarification_status=status,
            clarification_question=analysis.clarification_question,
            clarification_reason=analysis.question_basis,
            preserve_capture=True,
            todoist_write_allowed=False,
            provider_writes=0,
        )
        decision_digest = sha256_digest(decision.model_dump(mode="json"))
        binding = ClarificationCompatibilityBindingV1.create(
            analysis_digest=analysis.analysis_digest,
            predecessor_decision_digest=decision_digest,
            predecessor_relationship=decision.relationship.value,
            predecessor_status=decision.clarification_status.value,
        )
        return decision, binding

    @staticmethod
    def _material_distinction(analysis: ClarificationAnalysisV1) -> str:
        if analysis.question_basis:
            return analysis.question_basis
        if analysis.ambiguity_category.value != "none":
            return (
                "The term is preserved as a possible entity and does not require correction "
                "without additional evidence."
            )
        return "No material ambiguity requires clarification."

    @staticmethod
    def _evidence_level(analysis: ClarificationAnalysisV1) -> EvidenceLevelV752:
        score = analysis.confidence.score or 0.0
        if score >= 0.85:
            return EvidenceLevelV752.STRONG
        if score >= 0.45:
            return EvidenceLevelV752.PARTIAL
        return EvidenceLevelV752.MINIMAL
