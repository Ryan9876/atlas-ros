from __future__ import annotations

from atlas_ros.adapters.llm import LLMAdapter
from atlas_ros.config.loader import load_config
from atlas_ros.domain.models import Capture, Classification, RoutingRecommendation


class RoutingService:
    def __init__(self, adapter: LLMAdapter) -> None:
        self.adapter = adapter

    def plan(self, capture: Capture) -> RoutingRecommendation:
        recommendation = self.adapter.recommend_route(capture)
        config = load_config("classifications")
        allowed = set(config["allowed"])
        if recommendation.classification.value not in allowed:
            raise ValueError("AI proposed prohibited classification")
        expected = config["destinations"][recommendation.classification.value]
        if recommendation.destination != expected:
            raise ValueError("AI proposed invalid destination")
        if (
            recommendation.clarification_required
            or recommendation.confidence < config["confidence_threshold"]
            or recommendation.ambiguities
        ):
            return recommendation.model_copy(
                update={
                    "classification": Classification.NEEDS_CLARIFICATION,
                    "destination": "universal_inbox",
                    "clarification_required": True,
                }
            )
        return recommendation
