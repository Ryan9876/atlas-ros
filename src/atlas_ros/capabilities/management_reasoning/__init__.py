"""Deterministic provider-free management reasoning for Atlas ROS v7."""

from __future__ import annotations

from dataclasses import dataclass

from atlas_ros.capabilities.interfaces import (
    ManagementReasoningPort,
    ManagementReasoningResult,
)
from atlas_ros.contracts.reasoning import IntentGraph

CAPABILITY_ID = "atlas.management-reasoning"


@dataclass(frozen=True, slots=True)
class DeterministicManagementReasoningService:
    """Separate current actions, decisions, constraints, and blockers explicitly."""

    capability_id: str = CAPABILITY_ID

    def reason(self, graph: IntentGraph) -> ManagementReasoningResult:
        primary = graph.require_node(graph.primary_node_id)
        current_actions = tuple(
            node.title
            for node in graph.nodes
            if node.node_type == "action" and node.execution_candidate
        )
        delegated_actions = tuple(
            node.title
            for node in graph.nodes
            if node.node_type == "action" and not node.execution_candidate
        )
        conditional_actions = tuple(
            node.title for node in graph.nodes if node.node_type == "decision"
        )
        blocker_ids = {
            edge.target_node_id for edge in graph.edges if edge.edge_type == "blocks"
        }
        blockers = tuple(
            node.title
            for node in graph.nodes
            if node.node_type == "constraint" or node.node_id in blocker_ids
        )
        return ManagementReasoningResult(
            primary_outcome=primary.title,
            current_actions=current_actions,
            delegated_actions=delegated_actions,
            conditional_actions=conditional_actions,
            blockers=blockers,
        )


__all__ = [
    "CAPABILITY_ID",
    "DeterministicManagementReasoningService",
    "ManagementReasoningPort",
    "ManagementReasoningResult",
]
