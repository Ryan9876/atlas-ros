from __future__ import annotations

from typing import Protocol

from atlas_ros.domain.models import Capture, RoutingRecommendation


class LLMAdapter(Protocol):
    """Reasoning-only boundary: implementations never receive connector write access."""

    def recommend_route(self, capture: Capture) -> RoutingRecommendation: ...


class FixtureLLMAdapter:
    def __init__(self, response: RoutingRecommendation) -> None:
        self.response = response

    def recommend_route(self, capture: Capture) -> RoutingRecommendation:
        return self.response
