from __future__ import annotations

from atlas_ros.adapters.llm import LLMAdapter
from atlas_ros.domain.models import Capture, RoutingRecommendation
from atlas_ros.engines.management_reasoning import ManagementReasoningEngine
from atlas_ros.services.record_routing import RecordRoutingService


class RoutingService:
    """Legacy W02 facade over separated reasoning and routing capabilities."""

    def __init__(self, adapter: LLMAdapter) -> None:
        self.adapter = adapter
        self.reasoning_engine = ManagementReasoningEngine(adapter)
        self.routing_service = RecordRoutingService()

    def plan(self, capture: Capture) -> RoutingRecommendation:
        recommendation = self.adapter.recommend_route(capture)
        reasoning = self.reasoning_engine.from_recommendation(capture, recommendation)
        return self.routing_service.apply(recommendation, reasoning)
