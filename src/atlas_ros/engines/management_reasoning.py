from __future__ import annotations

from atlas_ros.contracts import CaptureEnvelope, ReasoningPackage
from atlas_ros.domain.models import Capture, RoutingRecommendation


class ManagementReasoningEngine:
    """Produces provider-independent reasoning without connector or adapter access."""

    def reason(
        self,
        capture: Capture,
        recommendation: RoutingRecommendation,
    ) -> ReasoningPackage:
        envelope = CaptureEnvelope(
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
