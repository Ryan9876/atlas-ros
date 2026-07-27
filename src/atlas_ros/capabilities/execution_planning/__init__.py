"""Sole provider-neutral execution planning authority for Atlas ROS v7."""

from __future__ import annotations

from dataclasses import dataclass

from atlas_ros.capabilities.interfaces import ProposedExecutionPlan
from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.contracts.execution.transaction import PlannedProviderOperation
from atlas_ros.contracts.reasoning import IntentGraph

CAPABILITY_ID = "atlas.execution-planning"


@dataclass(frozen=True, slots=True)
class ExecutionPlanningService:
    """Bind explicit provider requests to action nodes without authorizing execution."""

    capability_id: str = CAPABILITY_ID

    def plan(
        self,
        graph: IntentGraph,
        requests: tuple[PlannedProviderOperation, ...],
    ) -> ProposedExecutionPlan:
        action_ids = {
            node.node_id
            for node in graph.nodes
            if node.node_type == "action" and node.execution_candidate
        }
        operation_payload = [item.model_dump(mode="json") for item in requests]
        operation_digest = sha256_digest(operation_payload)
        if not requests:
            blockers = tuple(
                f"explicit_provider_operation_required:{node_id}"
                for node_id in sorted(action_ids)
            )
            return ProposedExecutionPlan(
                plan_id=f"plan-{graph.graph_digest[:20]}",
                source_graph_digest=graph.graph_digest,
                operations=(),
                blockers=blockers,
                plan_digest=operation_digest,
            )
        sequences = tuple(item.sequence for item in requests)
        if sequences != tuple(range(len(requests))):
            raise ValueError("planned provider operations must use canonical sequence")
        operation_ids = tuple(item.operation_id for item in requests)
        if len(set(operation_ids)) != len(operation_ids):
            raise ValueError("execution plan contains duplicate operation IDs")
        idempotency_keys = tuple(item.idempotency_key for item in requests)
        if len(set(idempotency_keys)) != len(idempotency_keys):
            raise ValueError("execution plan contains duplicate idempotency keys")
        unknown = sorted(set(operation_ids) - action_ids)
        if unknown:
            raise ValueError(
                "provider operations must reference execution-candidate action nodes: "
                + ", ".join(unknown)
            )
        identity_payload = {
            "source_graph_digest": graph.graph_digest,
            "operation_digest": operation_digest,
        }
        return ProposedExecutionPlan(
            plan_id=f"plan-{sha256_digest(identity_payload)[:20]}",
            source_graph_digest=graph.graph_digest,
            operations=requests,
            blockers=(),
            plan_digest=operation_digest,
        )


__all__ = ["CAPABILITY_ID", "ExecutionPlanningService"]
