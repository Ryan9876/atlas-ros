from __future__ import annotations

from atlas_ros.config.loader import load_config
from atlas_ros.contracts import (
    CaptureEnvelope,
    PlanningModelCandidate,
    ReasoningPackage,
    ReasoningPackageV2,
    ReasoningPackageV3,
)
from atlas_ros.domain.models import (
    Capture,
    ChallengeStatus,
    Classification,
    ManagementWorkstream,
    OperatingContext,
    ResponsibilityDomain,
    RoutingRecommendation,
)
from atlas_ros.engines.classification_explainability import ClassificationExplainability
from atlas_ros.engines.manager_intent import ManagerIntentInferer
from atlas_ros.engines.responsibility_classification import ResponsibilityClassifier


class ManagementReasoningEngine:
    """Produces provider-independent responsibility-aware reasoning."""

    def __init__(self) -> None:
        self._intelligence_config = load_config("classification-intelligence")
        self._routing_config = load_config("classifications")
        self._classifier = ResponsibilityClassifier(self._intelligence_config)
        self._explainability = ClassificationExplainability(self._intelligence_config)
        self._intent = ManagerIntentInferer(self._intelligence_config)

    def reason(
        self,
        capture: Capture,
        recommendation: RoutingRecommendation,
    ) -> ReasoningPackage:
        """Preserve the v1 compatibility contract for existing W02 consumers."""
        envelope = self._capture_envelope(capture)
        rationale = [
            f"Recommended classification: {recommendation.classification.value}",
            f"Recommended destination: {recommendation.destination}",
        ]
        return ReasoningPackage(
            correlation_id=envelope.correlation_id,
            source_component="engines.management_reasoning",
            classification=recommendation.classification.value,
            destination=recommendation.destination,
            confidence=recommendation.confidence,
            rationale=rationale,
            ambiguities=list(recommendation.ambiguities),
            requires_human_decision=recommendation.clarification_required,
        )

    def reason_v2(self, capture: Capture) -> ReasoningPackageV2:
        """Classify responsibility, record type, workstream, and context independently."""
        envelope = self._capture_envelope(capture)
        assessment = self._classifier.classify(capture.content, capture.additional_context)
        intent = self._intent.infer(
            f"{capture.content}\n{capture.additional_context}",
            assessment.responsibility_domain,
        )
        ambiguities = list(assessment.ambiguities)
        if intent.ambiguity:
            ambiguities.append(intent.ambiguity)

        confidence_threshold = float(
            self._intelligence_config["confidence"]["responsibility_minimum"]
        )
        requires_human_decision = (
            assessment.responsibility_domain is ResponsibilityDomain.UNRESOLVED
            or assessment.confidence < confidence_threshold
            or bool(assessment.ambiguities)
        )
        fallback_reason = ""
        if assessment.responsibility_domain is ResponsibilityDomain.UNRESOLVED:
            fallback_reason = "No governed responsibility signal was strong enough to classify."
        elif assessment.confidence < confidence_threshold:
            fallback_reason = "Responsibility confidence is below the governed canonical threshold."
        elif assessment.ambiguities:
            fallback_reason = "Conflicting responsibility evidence requires attended review."

        explanation = self._explainability.explain(
            responsibility_domain=assessment.responsibility_domain,
            workstream=assessment.workstream,
            rationale_basis=assessment.rationale_basis,
            evidence=assessment.evidence,
            ambiguities=assessment.ambiguities,
            confidence=assessment.confidence,
        )
        destination = self._destination_for(assessment.classification)
        evidence = list(assessment.evidence) + list(intent.evidence)
        operating_context = (
            "" if intent.context is OperatingContext.UNRESOLVED else intent.context.value
        )
        activity = self._activity_summary(capture.content)
        return ReasoningPackageV2(
            correlation_id=envelope.correlation_id,
            source_component="engines.management_reasoning",
            classification=assessment.classification.value,
            destination=destination,
            responsibility_domain=assessment.responsibility_domain.value,
            desired_outcome=self._desired_outcome(assessment.workstream, activity),
            workstream=assessment.workstream.value,
            activity_summary=activity,
            operating_context=operating_context,
            operating_context_confidence=(intent.confidence if operating_context else 0.0),
            confidence=assessment.confidence,
            decisive_evidence=evidence,
            rationale=[explanation],
            ambiguities=ambiguities,
            challenge_status=ChallengeStatus.UNCHALLENGED.value,
            fallback_reason=fallback_reason,
            requires_human_decision=requires_human_decision,
        )

    def recommendation_from_v2(self, reasoning: ReasoningPackageV2) -> RoutingRecommendation:
        return RoutingRecommendation(
            classification=Classification(reasoning.classification),
            destination=reasoning.destination,
            confidence=reasoning.confidence,
            desired_outcome=reasoning.desired_outcome,
            owner="Ryan",
            ambiguities=list(reasoning.ambiguities),
            clarification_required=reasoning.requires_human_decision,
        )

    @staticmethod
    def select_planning_model(
        reasoning: ReasoningPackageV2,
        *,
        normalized_intent: str,
        management_pattern: str,
        candidates: tuple[PlanningModelCandidate, ...],
        selected_model_id: str,
        selected_version_constraint: str = "*",
        selection_method: str = "user_selected",
        selection_confidence: float = 1.0,
        selection_rationale: str,
        assumptions: tuple[str, ...] = (),
        constraints: tuple[str, ...] = (),
        stakeholders: tuple[str, ...] = (),
        known_inputs: dict[str, object] | None = None,
        unresolved_questions: tuple[str, ...] = (),
    ) -> ReasoningPackageV3:
        """Add an authoritative planning selection without changing v2 semantics."""
        if selection_method not in {"inferred", "user_selected", "policy_selected"}:
            raise ValueError(f"unsupported selection method: {selection_method}")
        alternatives = tuple(
            candidate.model_id
            for candidate in candidates
            if candidate.model_id != selected_model_id
        )
        return ReasoningPackageV3(
            correlation_id=reasoning.correlation_id,
            created_at=reasoning.created_at,
            source_component="engines.management_reasoning",
            classification=reasoning.classification,
            destination=reasoning.destination,
            normalized_intent=normalized_intent,
            management_pattern=management_pattern,
            candidate_planning_models=candidates,
            selected_planning_model_id=selected_model_id,
            selected_planning_model_version_constraint=selected_version_constraint,
            selection_method=selection_method,  # type: ignore[arg-type]
            selection_confidence=selection_confidence,
            selection_rationale=selection_rationale,
            alternatives_considered=alternatives,
            planning_assumptions=assumptions,
            planning_constraints=constraints,
            known_stakeholders=stakeholders,
            known_inputs=known_inputs or {},
            unresolved_planning_questions=unresolved_questions,
            requires_human_decision=bool(unresolved_questions),
        )

    @staticmethod
    def _capture_envelope(capture: Capture) -> CaptureEnvelope:
        return CaptureEnvelope(
            correlation_id=capture.correlation_id,
            source_component="capture.service",
            content=capture.content,
            source=capture.source,
            context={
                "due_date_input": capture.due_date_input,
                "delegation_input": capture.delegation_input,
                "additional_context": capture.additional_context,
            },
        )

    def _destination_for(self, classification: Classification) -> str:
        return str(self._routing_config["destinations"][classification.value])

    @staticmethod
    def _activity_summary(content: str) -> str:
        normalized = " ".join(content.split())
        return normalized[:1000]

    @staticmethod
    def _desired_outcome(workstream: ManagementWorkstream, activity: str) -> str:
        templates = {
            ManagementWorkstream.LEADERSHIP_AND_TEAM: (
                "The person or team is enabled and the accountable leadership outcome is complete."
            ),
            ManagementWorkstream.ACTIVE_PROJECTS: (
                "The defined project outcome advances with clear ownership and evidence."
            ),
            ManagementWorkstream.OPERATIONS: (
                "The operational service is stable, controlled, and verified."
            ),
            ManagementWorkstream.WAITING_ON_OTHERS: (
                "The external dependency is resolved or has a governed follow-up path."
            ),
            ManagementWorkstream.DEVELOPMENT_AND_LEARNING: (
                "The targeted knowledge or capability is demonstrably improved."
            ),
            ManagementWorkstream.NEEDS_CLARIFICATION: (
                "The accountable responsibility and intended outcome are clarified."
            ),
        }
        return f"{templates[workstream]} Activity: {activity}"[:10000]
