from __future__ import annotations

from dataclasses import dataclass

from atlas_ros.contracts import ReasoningPackageV2
from atlas_ros.domain.models import RoutingRecommendation


@dataclass(frozen=True)
class RoutingDifferential:
    equivalent: bool
    fields: tuple[str, ...]
    semantic_responsibility_domain: str = ""
    semantic_workstream: str = ""
    semantic_operating_context: str = ""
    semantic_confidence: float = 0.0
    semantic_rationale: str = ""
    semantic_fallback_reason: str = ""


class RoutingShadowComparator:
    """Compares legacy and semantic routing outputs without changing authority."""

    _FIELDS = (
        "classification",
        "destination",
        "confidence",
        "desired_outcome",
        "ryan_next_action",
        "delegated_outcome",
        "owner",
        "definition_of_done",
        "risk_flags",
        "security_flags",
        "ambiguities",
        "clarification_required",
    )

    def compare(
        self,
        legacy: RoutingRecommendation,
        semantic: RoutingRecommendation,
        reasoning: ReasoningPackageV2 | None = None,
    ) -> RoutingDifferential:
        differences = tuple(
            field for field in self._FIELDS if getattr(legacy, field) != getattr(semantic, field)
        )
        return RoutingDifferential(
            equivalent=not differences,
            fields=differences,
            semantic_responsibility_domain=(
                reasoning.responsibility_domain if reasoning is not None else ""
            ),
            semantic_workstream=reasoning.workstream if reasoning is not None else "",
            semantic_operating_context=(
                reasoning.operating_context if reasoning is not None else ""
            ),
            semantic_confidence=reasoning.confidence if reasoning is not None else 0.0,
            semantic_rationale=(
                reasoning.rationale[0] if reasoning is not None and reasoning.rationale else ""
            ),
            semantic_fallback_reason=(
                reasoning.fallback_reason if reasoning is not None else ""
            ),
        )
