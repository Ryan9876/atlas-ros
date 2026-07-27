"""Stable provider-neutral reasoning contracts for the canonical v7 pipeline."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from atlas_ros.contracts.digests import sha256_digest

IntentNodeType = Literal[
    "outcome",
    "checkpoint",
    "constraint",
    "decision",
    "action",
]
IntentEdgeType = Literal["depends_on", "constrains", "enables", "blocks"]


class IntentNode(BaseModel):
    """One immutable semantic node in a canonical intent graph."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    node_id: str = Field(min_length=1, max_length=128)
    node_type: IntentNodeType
    title: str = Field(min_length=1, max_length=512)
    description: str = Field(default="", max_length=4_000)
    execution_candidate: bool = False
    evidence_refs: tuple[str, ...] = ()


class IntentEdge(BaseModel):
    """One directed relationship between two intent nodes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_node_id: str = Field(min_length=1, max_length=128)
    target_node_id: str = Field(min_length=1, max_length=128)
    edge_type: IntentEdgeType

    @model_validator(mode="after")
    def reject_self_reference(self) -> IntentEdge:
        if self.source_node_id == self.target_node_id:
            raise ValueError("intent edge cannot reference the same node")
        return self


class IntentGraph(BaseModel):
    """Digest-bound semantic graph emitted by canonical input processing."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_id: Literal["atlas.intent-graph"] = "atlas.intent-graph"
    schema_version: Literal["1.0"] = "1.0"
    primary_node_id: str = Field(min_length=1, max_length=128)
    nodes: tuple[IntentNode, ...] = Field(min_length=1)
    edges: tuple[IntentEdge, ...] = ()
    graph_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(
        cls,
        *,
        primary_node_id: str,
        nodes: tuple[IntentNode, ...],
        edges: tuple[IntentEdge, ...] = (),
    ) -> IntentGraph:
        values: dict[str, Any] = {
            "primary_node_id": primary_node_id,
            "nodes": nodes,
            "edges": edges,
        }
        values["graph_digest"] = sha256_digest(_graph_payload(values))
        return cls.model_validate(values)

    @model_validator(mode="after")
    def validate_graph(self) -> IntentGraph:
        node_ids = tuple(node.node_id for node in self.nodes)
        if len(set(node_ids)) != len(node_ids):
            raise ValueError("intent graph contains duplicate node IDs")
        known = set(node_ids)
        if self.primary_node_id not in known:
            raise ValueError("primary intent node is not present in graph")
        edge_keys = tuple(
            (edge.source_node_id, edge.target_node_id, edge.edge_type)
            for edge in self.edges
        )
        if len(set(edge_keys)) != len(edge_keys):
            raise ValueError("intent graph contains duplicate edges")
        for edge in self.edges:
            if edge.source_node_id not in known or edge.target_node_id not in known:
                raise ValueError("intent edge references an unknown node")
        _reject_dependency_cycles(self.nodes, self.edges)
        payload = {
            "primary_node_id": self.primary_node_id,
            "nodes": self.nodes,
            "edges": self.edges,
        }
        if sha256_digest(_graph_payload(payload)) != self.graph_digest:
            raise ValueError("intent graph digest does not match graph contents")
        return self


def _graph_payload(values: dict[str, Any]) -> dict[str, Any]:
    nodes = values["nodes"]
    edges = values["edges"]
    return {
        "primary_node_id": values["primary_node_id"],
        "nodes": [
            node.model_dump(mode="json") if isinstance(node, IntentNode) else node
            for node in nodes
        ],
        "edges": [
            edge.model_dump(mode="json") if isinstance(edge, IntentEdge) else edge
            for edge in edges
        ],
    }


def _reject_dependency_cycles(
    nodes: tuple[IntentNode, ...],
    edges: tuple[IntentEdge, ...],
) -> None:
    dependencies: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        if edge.edge_type == "depends_on":
            dependencies[edge.source_node_id].add(edge.target_node_id)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> None:
        if node_id in visiting:
            raise ValueError("intent graph contains a dependency cycle")
        if node_id in visited:
            return
        visiting.add(node_id)
        for dependency in sorted(dependencies[node_id]):
            visit(dependency)
        visiting.remove(node_id)
        visited.add(node_id)

    for node in nodes:
        visit(node.node_id)
