from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from atlas_ros.adapters.llm import LLMAdapter
from atlas_ros.config.loader import load_config
from atlas_ros.contracts import ReasoningPackageV2
from atlas_ros.domain.models import Capture, RoutingRecommendation
from atlas_ros.engines.management_reasoning import ManagementReasoningEngine
from atlas_ros.services.record_routing import RecordRoutingService
from atlas_ros.services.routing_shadow import RoutingDifferential, RoutingShadowComparator


class RoutingMode(StrEnum):
    LEGACY = "legacy"
    SHADOW = "shadow"
    ATTENDED = "attended"
    SEMANTIC = "semantic"


@dataclass(frozen=True)
class SemanticRoutingEvidence:
    legacy: RoutingRecommendation
    semantic: RoutingRecommendation
    reasoning: ReasoningPackageV2
    differential: RoutingDifferential


class RoutingService:
    """Canonical reasoning-and-routing coordinator with controlled semantic modes."""

    def __init__(self, adapter: LLMAdapter, mode: RoutingMode | str = RoutingMode.LEGACY) -> None:
        self.adapter = adapter
        self.mode = RoutingMode(mode)
        self.reasoning_engine = ManagementReasoningEngine()
        self.routing_service = RecordRoutingService(load_config)
        self.shadow_comparator = RoutingShadowComparator()
        self.last_semantic_evidence: SemanticRoutingEvidence | None = None

    def plan(self, capture: Capture) -> RoutingRecommendation:
        legacy = self._legacy_plan(capture)
        if self.mode is RoutingMode.LEGACY:
            return legacy

        evidence = self.plan_semantic_evidence(capture, legacy=legacy)
        self.last_semantic_evidence = evidence
        if self.mode in {RoutingMode.SHADOW, RoutingMode.ATTENDED}:
            return legacy
        return evidence.semantic

    def plan_semantic(self, capture: Capture) -> RoutingRecommendation:
        evidence = self.plan_semantic_evidence(capture)
        self.last_semantic_evidence = evidence
        return evidence.semantic

    def plan_semantic_evidence(
        self,
        capture: Capture,
        *,
        legacy: RoutingRecommendation | None = None,
    ) -> SemanticRoutingEvidence:
        legacy_route = self._legacy_plan(capture) if legacy is None else legacy
        reasoning = self.reasoning_engine.reason_v2(capture)
        recommendation = self.reasoning_engine.recommendation_from_v2(reasoning)
        semantic = self.routing_service.apply(recommendation, reasoning)
        differential = self.shadow_comparator.compare(legacy_route, semantic, reasoning)
        return SemanticRoutingEvidence(
            legacy=legacy_route,
            semantic=semantic,
            reasoning=reasoning,
            differential=differential,
        )

    def _legacy_plan(self, capture: Capture) -> RoutingRecommendation:
        recommendation = self.adapter.recommend_route(capture)
        reasoning = self.reasoning_engine.reason(capture, recommendation)
        return self.routing_service.apply(recommendation, reasoning)
