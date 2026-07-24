from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from atlas_ros.config.loader import load_config
from atlas_ros.contracts import ReasoningPackage, ReasoningPackageV2
from atlas_ros.domain.models import Classification, RoutingRecommendation

ConfigLoader = Callable[[str], dict[str, Any]]
ReasoningContract = ReasoningPackage | ReasoningPackageV2


@dataclass(frozen=True)
class RoutingDecision:
    classification: Classification
    destination: str
    clarification_required: bool
    reason: str


class RecordRoutingService:
    """Applies deterministic record-placement policy to reasoning output."""

    def __init__(self, config_loader: ConfigLoader = load_config) -> None:
        self._config_loader = config_loader

    def decide(self, reasoning: ReasoningContract) -> RoutingDecision:
        config = self._config_loader("classifications")
        allowed = set(config["allowed"])
        if reasoning.classification not in allowed:
            raise ValueError("reasoning proposed prohibited classification")
        expected = config["destinations"][reasoning.classification]
        if reasoning.destination != expected:
            raise ValueError("reasoning proposed invalid destination")

        needs_clarification = (
            reasoning.requires_human_decision
            or reasoning.confidence < config["confidence_threshold"]
            or bool(reasoning.ambiguities)
        )
        if needs_clarification:
            return RoutingDecision(
                classification=Classification.NEEDS_CLARIFICATION,
                destination="universal_inbox",
                clarification_required=True,
                reason="Confidence, ambiguity, or explicit human-decision policy requires review.",
            )
        return RoutingDecision(
            classification=Classification(reasoning.classification),
            destination=reasoning.destination,
            clarification_required=False,
            reason="Reasoning output satisfied governed routing policy.",
        )

    def apply(
        self,
        recommendation: RoutingRecommendation,
        reasoning: ReasoningContract,
    ) -> RoutingRecommendation:
        decision = self.decide(reasoning)
        return recommendation.model_copy(
            update={
                "classification": decision.classification,
                "destination": decision.destination,
                "clarification_required": decision.clarification_required,
            }
        )
