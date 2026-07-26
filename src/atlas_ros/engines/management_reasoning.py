from __future__ import annotations

from atlas_ros.config.loader import load_config
from atlas_ros.contracts import (
    CaptureEnvelope,
    PlanningModelCandidate,
    ReasoningPackage,
    ReasoningPackageV2,
    ReasoningPackageV3,
    ReasoningPackageV4,
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
from atlas_ros.engines.intent_partitioning import IntentPartitioner
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
        self._partitioner = IntentPartitioner()

    def reason(
        self,
        capture: Capture,
        recommendation: RoutingRecommendation,
    ) -> ReasoningPackage:
        """Project semantic reasoning into the historical V1 evidence contract."""
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

    def reason_v4(self, capture: Capture) -> ReasoningPackageV4:
        """Partition business intent from controls before selecting a planning model."""
        reasoning_v2 = self.reason_v2(capture)
        combined = "\n".join(
            value for value in (capture.content, capture.additional_context) if value.strip()
        )
        partition = self._partitioner.partition(
            combined, correlation_id=reasoning_v2.correlation_id
        )
        audit_primary = self._is_audit_primary(partition.primary_business_outcome)
        is_pilot = (
            self._is_controlled_pilot(partition.primary_business_outcome)
            and not audit_primary
        )
        candidates = (
            PlanningModelCandidate(
                model_id="controlled-technology-pilot",
                version_constraint="^3.0.0",
                confidence=0.99 if is_pilot else 0.20,
                rationale=(
                    "Primary outcome is a controlled technology pilot."
                    if is_pilot
                    else "No controlled-pilot signal was identified."
                ),
            ),
            PlanningModelCandidate(
                model_id="single-business-outcome",
                version_constraint="^3.0.0",
                confidence=0.20 if is_pilot else 0.95,
                rationale="Provider-neutral single-outcome model for non-pilot business work.",
            ),
        )
        selected = "controlled-technology-pilot" if is_pilot else "single-business-outcome"
        version = "^3.0.0"
        known_inputs: dict[str, object] = {
            "owner": "Ryan",
            "desired_outcome": partition.primary_business_outcome,
            "primary_business_outcome": partition.primary_business_outcome,
            "technology": self._technology_from_outcome(partition.primary_business_outcome),
            "current_business_actions": partition.current_business_actions,
            "delegated_actions": partition.delegated_actions,
            "conditional_actions": partition.conditional_actions,
            "evaluation_context": partition.evaluation_context,
            "audit_requirements": partition.audit_requirements,
            "execution_constraints": partition.execution_constraints,
            "reference_context": partition.reference_context,
            "intent_partition_digest": partition.partition_digest,
        }
        selected_v3 = self.select_planning_model(
            reasoning_v2,
            normalized_intent=partition.primary_business_outcome or combined,
            management_pattern=(
                "Controlled Technology Pilot" if is_pilot else reasoning_v2.workstream
            ),
            candidates=candidates,
            selected_model_id=selected,
            selected_version_constraint=version,
            selection_method="policy_selected",
            selection_confidence=0.99 if is_pilot else 0.80,
            selection_rationale=(
                "Selected from the governed primary business outcome, excluding "
                "evaluation, audit, and execution-control clauses."
            ),
            constraints=partition.execution_constraints,
            known_inputs=known_inputs,
            unresolved_questions=partition.ambiguities,
        )
        return ReasoningPackageV4.from_v3(
            selected_v3,
            partition,
            responsibility_domain=reasoning_v2.responsibility_domain,
            workstream=reasoning_v2.workstream,
            activity_summary=reasoning_v2.activity_summary,
            confidence=reasoning_v2.confidence,
            operating_context=reasoning_v2.operating_context,
            operating_context_confidence=reasoning_v2.operating_context_confidence,
            decisive_evidence=tuple(reasoning_v2.decisive_evidence),
            rationale=tuple(reasoning_v2.rationale),
            challenge_status=reasoning_v2.challenge_status,
        )

    @staticmethod
    def _is_controlled_pilot(value: str) -> bool:
        lowered = value.casefold()
        return any(
            signal in lowered
            for signal in (
                " pilot",
                "pilot ",
                "proof of concept",
                "poc",
                "controlled trial",
                "limited deployment",
                "validation pilot",
            )
        )

    @staticmethod
    def _is_audit_primary(value: str) -> bool:
        lowered = value.casefold()
        return (
            lowered.startswith(("produce ", "generate ", "prepare ", "review "))
            and any(token in lowered for token in ("audit", "report", "receipt", "reconciliation"))
        )

    @staticmethod
    def _technology_from_outcome(value: str) -> str:
        technology = value.strip()
        if technology.casefold().startswith("launch the "):
            technology = technology[11:]
        if technology.casefold().endswith(" pilot"):
            technology = technology[:-6]
        return technology.strip()

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
