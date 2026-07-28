"""Provider-free decision support for Atlas ROS v7."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from atlas_ros.capabilities.interfaces import DecisionSupportResult
from atlas_ros.contracts.reasoning import IntentGraph

CAPABILITY_ID = "atlas.decision-support"


class DecisionSupportPort(Protocol):
    def evaluate(self, graph: IntentGraph) -> DecisionSupportResult: ...


@dataclass(frozen=True, slots=True)
class ExplicitDecisionSupportService:
    """Surface decision nodes and uncertainty without selecting or authorizing actions."""

    capability_id: str = CAPABILITY_ID

    def evaluate(self, graph: IntentGraph) -> DecisionSupportResult:
        decisions = tuple(node for node in graph.nodes if node.node_type == "decision")
        constraints = tuple(node.title for node in graph.nodes if node.node_type == "constraint")
        options = tuple(node.title for node in decisions)
        uncertainty = tuple(
            dict.fromkeys(
                [
                    *(f"constraint:{item}" for item in constraints),
                    *(
                        f"missing_evidence:{node.node_id}"
                        for node in decisions
                        if not node.evidence_refs
                    ),
                ]
            )
        )
        recommendation = options[0] if len(options) == 1 and not uncertainty else None
        return DecisionSupportResult(
            decision_required=bool(decisions),
            options=options,
            recommendation=recommendation,
            uncertainty=uncertainty,
        )


__all__ = [
    "CAPABILITY_ID",
    "DecisionSupportPort",
    "DecisionSupportResult",
    "ExplicitDecisionSupportService",
]
