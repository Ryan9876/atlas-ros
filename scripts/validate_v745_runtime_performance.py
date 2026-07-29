#!/usr/bin/env python3
"""Deterministic equivalence and fixture-based performance validation for v7.4.5."""
from __future__ import annotations

import argparse
import json
import statistics
import time
import tracemalloc
from pathlib import Path

from atlas_ros.runtime_performance import (
    OperationalComputationGraphV1,
    OperationalComputationNodeV1,
    OperationalDependencyEdgeV1,
    ProviderReadMetricsV1,
    ReadRequirementV1,
    RuntimeDependencyDeclarationV1,
    build_operation_snapshot,
    compile_read_plan,
    compile_runtime_composition,
    plan_incremental_computation,
)
from atlas_ros.runtime_performance.contracts import ProviderReadReceiptV1, ProviderRecordV1


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * fraction))))
    return ordered[index]


def timed(callable_obj, samples: int = 100) -> tuple[list[float], int]:
    tracemalloc.start()
    durations: list[float] = []
    for _ in range(samples):
        started = time.perf_counter_ns()
        callable_obj()
        durations.append((time.perf_counter_ns() - started) / 1_000_000)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return durations, peak


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    requirements = [
        ReadRequirementV1(
            requesting_capability=f"capability-{index % 6}",
            provider="notion",
            record_type="action",
            record_identities=(f"record-{index % 20}",),
            required_fields=("status", "owner", "revision"),
            pagination_limit=100,
            batching_supported=True,
        )
        for index in range(200)
    ]
    read_plan = compile_read_plan(operation_id="benchmark", requirements=requirements)
    assert read_plan.expected_read_count == 20
    assert read_plan.duplicate_requests_removed == 180

    records = tuple(
        ProviderRecordV1(
            provider="notion",
            canonical_record_id=f"record-{index}",
            source_record_id=f"page-{index}",
            source_revision="r1",
            read_timestamp="2026-07-29T00:00:00Z",
            requested_fields=("status", "owner", "revision"),
            normalized_content={"status": "Open", "owner": "Ryan", "revision": "r1"},
            provenance=("fixture",),
        )
        for index in range(20)
    )
    receipts = (
        ProviderReadReceiptV1(
            provider="notion",
            request_id="coalesced-1",
            record_identities=tuple(f"record-{index}" for index in range(20)),
            requested_fields=("status", "owner", "revision"),
            returned_records=20,
            complete=True,
            pagination_complete=True,
            read_timestamp="2026-07-29T00:00:00Z",
        ),
    )
    snapshot = build_operation_snapshot(
        operation_id="benchmark",
        correlation_id="benchmark-correlation",
        requested_scope=("actions",),
        authoritative_release_identity="7.4.0@6d48b93",
        provider_records=records,
        provider_read_receipts=receipts,
    )
    assert len(snapshot.provider_records) == 20
    assert not snapshot.contradictory_record_ids

    declarations = tuple(
        RuntimeDependencyDeclarationV1(
            command="status",
            capability=f"capability-{index}",
            contracts=(f"contract-{index}",),
            policies=("authority",),
            schemas=(f"schema-{index}",),
            ports=("notion-read",),
            adapters=("notion",),
        )
        for index in range(6)
    )
    scoped = compile_runtime_composition(command="status", declarations=declarations)
    full = compile_runtime_composition(command="status", declarations=declarations, force_full=True)
    assert scoped.required_capabilities == full.required_capabilities
    assert scoped.required_contracts == full.required_contracts
    assert scoped.required_policies == full.required_policies
    assert scoped.required_schemas == full.required_schemas
    assert scoped.required_ports == full.required_ports
    assert scoped.required_adapters == full.required_adapters

    prior_nodes = tuple(
        OperationalComputationNodeV1(
            node_id=f"node-{index}",
            canonical_record_id=f"record-{index}",
            source_revision="r1",
            normalized_content_digest=f"content-{index}",
            policy_digest="policy-1",
            contract_version="1",
            capability_version="1",
        )
        for index in range(100)
    )
    current_nodes = tuple(
        node.model_copy(update={"source_revision": "r2"}) if node.node_id == "node-0" else node
        for node in prior_nodes
    )
    edges = tuple(
        OperationalDependencyEdgeV1(source_node_id=f"node-{index}", dependent_node_id=f"node-{index + 1}")
        for index in range(99)
    )
    graph = OperationalComputationGraphV1(
        nodes=current_nodes,
        edges=edges,
        authority_identity="authority-1",
        schema_identity="schema-1",
        redaction_policy_digest="redaction-1",
    )
    incremental = plan_incremental_computation(
        current_graph=graph,
        prior_nodes=prior_nodes,
        prior_authority_identity="authority-1",
        prior_schema_identity="schema-1",
        prior_redaction_policy_digest="redaction-1",
    )
    assert incremental.recompute_node_ids == tuple(f"node-{index}" for index in range(100))

    plan_times, plan_memory = timed(
        lambda: compile_read_plan(operation_id="benchmark", requirements=requirements)
    )
    snapshot_times, snapshot_memory = timed(
        lambda: build_operation_snapshot(
            operation_id="benchmark",
            correlation_id="benchmark-correlation",
            requested_scope=("actions",),
            authoritative_release_identity="7.4.0@6d48b93",
            provider_records=records,
            provider_read_receipts=receipts,
        )
    )
    composition_times, composition_memory = timed(
        lambda: compile_runtime_composition(command="status", declarations=declarations)
    )
    incremental_times, incremental_memory = timed(
        lambda: plan_incremental_computation(
            current_graph=graph,
            prior_nodes=prior_nodes,
            prior_authority_identity="authority-1",
            prior_schema_identity="schema-1",
            prior_redaction_policy_digest="redaction-1",
        )
    )

    provider_metrics = ProviderReadMetricsV1(
        provider_round_trips=read_plan.expected_read_count,
        records_requested=len(requirements),
        records_returned=len(records),
        duplicate_reads_eliminated=read_plan.duplicate_requests_removed,
    )
    report = {
        "schema_version": "performance-validation-report-v1",
        "status": "passed",
        "candidate_version": "7.4.5",
        "fixture_only": True,
        "provider_latency_measured": False,
        "provider_bytes_measured": False,
        "provider_read_metrics": provider_metrics.model_dump(mode="json"),
        "read_plan": {
            "p50_ms": statistics.median(plan_times),
            "p95_ms": percentile(plan_times, 0.95),
            "peak_memory_bytes": plan_memory,
        },
        "snapshot": {
            "p50_ms": statistics.median(snapshot_times),
            "p95_ms": percentile(snapshot_times, 0.95),
            "peak_memory_bytes": snapshot_memory,
        },
        "composition": {
            "p50_ms": statistics.median(composition_times),
            "p95_ms": percentile(composition_times, 0.95),
            "peak_memory_bytes": composition_memory,
            "scoped_full_equivalence": True,
        },
        "incremental": {
            "p50_ms": statistics.median(incremental_times),
            "p95_ms": percentile(incremental_times, 0.95),
            "peak_memory_bytes": incremental_memory,
            "incremental_full_equivalence": True,
        },
        "exclusions": {
            "pipeline_digest_semantics_changed": False,
            "runtime_concurrency_enabled": False,
            "resident_warm_session_created": False,
        },
    }
    Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
