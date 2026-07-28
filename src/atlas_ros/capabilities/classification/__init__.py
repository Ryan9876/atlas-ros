"""Deterministic provider-free classification for Atlas ROS v7."""

from __future__ import annotations

from dataclasses import dataclass

from atlas_ros.capabilities.interfaces import ClassificationPort, ClassificationResult
from atlas_ros.contracts.reasoning import IntentGraph

CAPABILITY_ID = "atlas.classification"


@dataclass(frozen=True, slots=True)
class DeterministicClassificationService:
    """Classify the stable intent graph without provider access or hidden inference."""

    capability_id: str = CAPABILITY_ID

    def classify(self, graph: IntentGraph) -> ClassificationResult:
        node_types = {node.node_type for node in graph.nodes}
        action_count = sum(
            node.node_type == "action" and node.execution_candidate for node in graph.nodes
        )
        if action_count:
            classification = "executable_work"
            destination = "Work"
            workstream = "Active Projects"
            confidence = 0.96
        elif "decision" in node_types:
            classification = "decision_support"
            destination = "Work"
            workstream = "Leadership & Team"
            confidence = 0.92
        elif "constraint" in node_types:
            classification = "constraint_review"
            destination = "Work"
            workstream = "Operations"
            confidence = 0.88
        else:
            classification = "reference_context"
            destination = "Notion"
            workstream = "Reference"
            confidence = 0.84
        findings = tuple(
            sorted(
                {
                    "blocked_edge_present"
                    for edge in graph.edges
                    if edge.edge_type == "blocks"
                }
            )
        )
        return ClassificationResult(
            classification=classification,
            destination=destination,
            responsibility_domain="ryan_owned",
            workstream=workstream,
            confidence=confidence,
            findings=findings,
        )


__all__ = [
    "CAPABILITY_ID",
    "ClassificationPort",
    "ClassificationResult",
    "DeterministicClassificationService",
]
