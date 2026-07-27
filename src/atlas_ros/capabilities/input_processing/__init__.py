"""Deterministic provider-free input processing for the canonical v7 pipeline."""

from __future__ import annotations

import re
from dataclasses import dataclass

from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.contracts.execution.pipeline import CaptureEnvelope
from atlas_ros.contracts.reasoning import IntentEdge, IntentGraph, IntentNode

CAPABILITY_ID = "atlas.input-processing"
_SPLIT = re.compile(r"(?:\n+|(?<=[.!?;])\s+)")
_CONSTRAINT_WORDS = frozenset({"must", "cannot", "without", "only", "never"})
_ACTION_PREFIXES = (
    "add ",
    "build ",
    "complete ",
    "create ",
    "implement ",
    "move ",
    "remove ",
    "replace ",
    "update ",
    "validate ",
    "verify ",
)


@dataclass(frozen=True, slots=True)
class DeterministicInputProcessor:
    """Create a stable intent graph without provider access or hidden inference."""

    name: str = "input_processing"
    capability_id: str = CAPABILITY_ID
    max_nodes: int = 32

    def process(self, envelope: CaptureEnvelope) -> IntentGraph:
        clauses = _clauses(envelope.content, self.max_nodes)
        primary = clauses[0]
        nodes = [
            IntentNode(
                node_id=_node_id(0, primary),
                node_type="outcome",
                title=primary,
                description="Primary outcome extracted from the first material clause.",
            )
        ]
        edges: list[IntentEdge] = []
        primary_id = nodes[0].node_id
        for index, clause in enumerate(clauses[1:], start=1):
            node_type, execution_candidate = _classify_clause(clause)
            node = IntentNode(
                node_id=_node_id(index, clause),
                node_type=node_type,
                title=clause,
                description="Material clause preserved from the captured input.",
                execution_candidate=execution_candidate,
            )
            nodes.append(node)
            edges.append(
                IntentEdge(
                    source_node_id=primary_id,
                    target_node_id=node.node_id,
                    edge_type=(
                        "constrains" if node_type == "constraint" else "depends_on"
                    ),
                )
            )
        return IntentGraph.create(
            primary_node_id=primary_id,
            nodes=tuple(nodes),
            edges=tuple(edges),
        )


def _clauses(content: str, limit: int) -> tuple[str, ...]:
    normalized = " ".join(content.split())
    if not normalized:
        raise ValueError("input processing requires non-empty content")
    clauses = tuple(
        item.strip(" \t\r\n.;")
        for item in _SPLIT.split(content)
        if item.strip(" \t\r\n.;")
    )
    if not clauses:
        return (normalized,)
    return clauses[:limit]


def _classify_clause(clause: str) -> tuple[str, bool]:
    lowered = clause.casefold()
    words = frozenset(re.findall(r"[a-z]+", lowered))
    if words & _CONSTRAINT_WORDS:
        return "constraint", False
    if lowered.startswith(_ACTION_PREFIXES):
        return "action", True
    if "approve" in words or "decide" in words or "choose" in words:
        return "decision", False
    return "checkpoint", False


def _node_id(index: int, clause: str) -> str:
    return f"intent-{index:02d}-{sha256_digest(clause)[:12]}"


__all__ = ["CAPABILITY_ID", "DeterministicInputProcessor"]
