"""Deterministic provider-free record routing for Atlas ROS v7."""

from __future__ import annotations

from dataclasses import dataclass

from atlas_ros.capabilities.interfaces import (
    ClassificationResult,
    ManagementStructureResult,
    RecordRoutingPort,
    RoutingDecision,
)

CAPABILITY_ID = "atlas.record-routing"
_ALLOWED_WORK_SECTIONS = frozenset(
    {
        "Leadership & Team",
        "Active Projects",
        "Operations",
        "Waiting on Others",
        "Development & Learning",
    }
)


@dataclass(frozen=True, slots=True)
class DeterministicRecordRoutingService:
    """Select governed destinations without writing or changing responsibility."""

    capability_id: str = CAPABILITY_ID

    def route(
        self,
        classification: ClassificationResult,
        structure: ManagementStructureResult,
    ) -> RoutingDecision:
        if classification.destination == "Work":
            section = (
                classification.workstream
                if classification.workstream in _ALLOWED_WORK_SECTIONS
                else "Operations"
            )
            destination = f"Todoist:#Work/{section}"
        elif classification.destination == "Personal":
            destination = "Todoist:#Personal"
        else:
            destination = "Notion:Universal Inbox"
        review_required = bool(classification.findings) or not structure.parent_title.strip()
        return RoutingDecision(
            destination=destination,
            rationale=(
                f"{classification.classification} classified for "
                f"{classification.responsibility_domain}; no provider write performed."
            ),
            review_required=review_required,
        )


__all__ = [
    "CAPABILITY_ID",
    "DeterministicRecordRoutingService",
    "RecordRoutingPort",
    "RoutingDecision",
]
