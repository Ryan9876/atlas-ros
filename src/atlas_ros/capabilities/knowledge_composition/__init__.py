"""Deterministic provider-free knowledge composition for Atlas ROS v7."""

from __future__ import annotations

from dataclasses import dataclass

from atlas_ros.capabilities.interfaces import (
    KnowledgeCompositionPort,
    KnowledgeCompositionResult,
)
from atlas_ros.contracts.reasoning import IntentGraph

CAPABILITY_ID = "atlas.knowledge-composition"


@dataclass(frozen=True, slots=True)
class DeterministicKnowledgeCompositionService:
    """Preserve graph facts and evidence without consulting external providers."""

    capability_id: str = CAPABILITY_ID

    def compose(self, graph: IntentGraph) -> KnowledgeCompositionResult:
        references = tuple(
            dict.fromkeys(
                reference
                for node in graph.nodes
                for reference in node.evidence_refs
            )
        )
        facts = tuple(node.title for node in graph.nodes)
        assumptions = tuple(
            f"execution_candidate:{node.node_id}"
            for node in graph.nodes
            if node.execution_candidate
        )
        conflicts = tuple(
            f"{edge.source_node_id}:blocks:{edge.target_node_id}"
            for edge in graph.edges
            if edge.edge_type == "blocks"
        )
        return KnowledgeCompositionResult(
            references=references,
            facts=facts,
            assumptions=assumptions,
            conflicts=conflicts,
        )


__all__ = [
    "CAPABILITY_ID",
    "DeterministicKnowledgeCompositionService",
    "KnowledgeCompositionPort",
    "KnowledgeCompositionResult",
]
