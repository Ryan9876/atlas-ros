from __future__ import annotations

import pytest

from atlas_ros.contracts.reasoning import IntentEdge, IntentGraph, IntentNode


def node(node_id: str, node_type: str = "checkpoint") -> IntentNode:
    return IntentNode.model_validate(
        {
            "node_id": node_id,
            "node_type": node_type,
            "title": node_id,
        }
    )


def test_intent_graph_is_digest_bound_and_deterministic() -> None:
    graph = IntentGraph.create(
        primary_node_id="outcome",
        nodes=(node("outcome", "outcome"), node("checkpoint")),
        edges=(
            IntentEdge(
                source_node_id="outcome",
                target_node_id="checkpoint",
                edge_type="depends_on",
            ),
        ),
    )
    replay = IntentGraph.create(
        primary_node_id="outcome",
        nodes=graph.nodes,
        edges=graph.edges,
    )

    assert graph.contract_id == "atlas.intent-graph"
    assert graph.graph_digest == replay.graph_digest


def test_intent_graph_rejects_unknown_edge_node() -> None:
    with pytest.raises(ValueError, match="unknown node"):
        IntentGraph.create(
            primary_node_id="outcome",
            nodes=(node("outcome", "outcome"),),
            edges=(
                IntentEdge(
                    source_node_id="outcome",
                    target_node_id="missing",
                    edge_type="depends_on",
                ),
            ),
        )


def test_intent_graph_rejects_dependency_cycle() -> None:
    with pytest.raises(ValueError, match="dependency cycle"):
        IntentGraph.create(
            primary_node_id="a",
            nodes=(node("a", "outcome"), node("b")),
            edges=(
                IntentEdge(
                    source_node_id="a",
                    target_node_id="b",
                    edge_type="depends_on",
                ),
                IntentEdge(
                    source_node_id="b",
                    target_node_id="a",
                    edge_type="depends_on",
                ),
            ),
        )


def test_intent_graph_rejects_tampered_digest() -> None:
    graph = IntentGraph.create(
        primary_node_id="outcome",
        nodes=(node("outcome", "outcome"),),
    )
    payload = graph.model_dump(mode="json")
    payload["nodes"][0]["title"] = "tampered"

    with pytest.raises(ValueError, match="digest"):
        IntentGraph.model_validate(payload)
