from __future__ import annotations

from dataclasses import dataclass

from atlas_ros.domain.models import RoutingRecommendation


@dataclass(frozen=True)
class RoutingDifferential:
    equivalent: bool
    fields: tuple[str, ...]


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
    ) -> RoutingDifferential:
        differences = tuple(
            field for field in self._FIELDS if getattr(legacy, field) != getattr(semantic, field)
        )
        return RoutingDifferential(equivalent=not differences, fields=differences)
