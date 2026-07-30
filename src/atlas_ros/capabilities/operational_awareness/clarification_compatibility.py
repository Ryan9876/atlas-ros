"""Compatibility binding to the accepted v7.5.2 clarification authority."""
from __future__ import annotations

from dataclasses import dataclass

from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.contracts.operational_awareness.clarification import (
    ClarificationAnalysisV1,
    ClarificationCompatibilityBindingV1,
    ClarificationContextV1,
)
from atlas_ros.intent_learning_v750 import (
    ClarificationDecisionV1,
    ClarificationStatus,
    ConsequenceAssessmentV1,
    ContextFamiliarityV1,
    EvidenceLevel,
    RelationshipClassification,
)


@dataclass(frozen=True, slots=True)
class ClarificationCompatibilityAdapter:
    """Map v8.1 analysis into the accepted v7.5.2 decision contract."""

    def bind(
        self,
        analysis: ClarificationAnalysisV1,
        *,
        context: ClarificationContextV1 | None = None,
        familiarity: ContextFamiliarityV1 | None = None,
        consequence: ConsequenceAssessmentV1 | None = None,
    ) -> tuple[ClarificationDecisionV1, ClarificationCompatibilityBindingV1]:
        bounded = context or ClarificationContextV1()
        familiarity_value = familiarity or ContextFamiliarityV1(
            user=0.5,
            domain=0.5,
            project=0.5,
            terminology=0.5,
            evidence_recency=0.5,
            interpretation_consistency=analysis.confidence.score or 0.0,
        )
        consequence_value = consequence or ConsequenceAssessmentV1(reversible=True)
        relationship = (
            RelationshipClassification.NEEDS_CLARIFICATION
            if analysis.clarification_required
            else RelationshipClassification.DISTINCT_OUTCOME
        )
        status = (
            ClarificationStatus.REQUIRED
            if analysis.clarification_required
            else ClarificationStatus.NOT_REQUIRED
        )
        decision = ClarificationDecisionV1(
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
    def _evidence_level(analysis: ClarificationAnalysisV1) -> EvidenceLevel:
        score = analysis.confidence.score or 0.0
        if score >= 0.85:
            return EvidenceLevel.STRONG
        if score >= 0.45:
            return EvidenceLevel.PARTIAL
        return EvidenceLevel.MINIMAL
