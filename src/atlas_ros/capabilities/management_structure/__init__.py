"""Deterministic provider-free management structure for Atlas ROS v7."""

from __future__ import annotations

from dataclasses import dataclass

from atlas_ros.capabilities.interfaces import (
    ManagementReasoningResult,
    ManagementStructurePort,
    ManagementStructureResult,
)

CAPABILITY_ID = "atlas.management-structure"


@dataclass(frozen=True, slots=True)
class DeterministicManagementStructureService:
    """Preserve outcome and action relationships without creating provider records."""

    capability_id: str = CAPABILITY_ID

    def structure(
        self,
        reasoning: ManagementReasoningResult,
    ) -> ManagementStructureResult:
        sections: list[str] = []
        relationships: list[tuple[str, str]] = []
        categories = (
            ("Current Actions", reasoning.current_actions),
            ("Delegated Actions", reasoning.delegated_actions),
            ("Conditional Actions", reasoning.conditional_actions),
            ("Blockers", reasoning.blockers),
        )
        for section, items in categories:
            if not items:
                continue
            sections.append(section)
            relationships.extend((section, item) for item in items)
        return ManagementStructureResult(
            parent_title=reasoning.primary_outcome,
            sections=tuple(sections),
            relationships=tuple(relationships),
        )


__all__ = [
    "CAPABILITY_ID",
    "DeterministicManagementStructureService",
    "ManagementStructurePort",
    "ManagementStructureResult",
]
