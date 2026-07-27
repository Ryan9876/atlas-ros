from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, cast

from atlas_ros.contracts import IntentNodeType
from atlas_ros.engines import AdaptiveInputProcessingPipelineV62


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round((len(ordered) - 1) * percentile)))
    return ordered[index]


def evaluate(dataset_path: Path) -> dict[str, Any]:
    dataset = cast(dict[str, Any], json.loads(dataset_path.read_text(encoding="utf-8")))
    cases = cast(list[dict[str, Any]], dataset["cases"])
    pipeline = AdaptiveInputProcessingPipelineV62()
    results: list[dict[str, Any]] = []
    durations: list[float] = []
    group_fingerprints: dict[str, set[str]] = {}
    provider_writes = 0

    for case in cases:
        started = time.perf_counter()
        result = pipeline.process(str(case["input"]))
        duration_ms = (time.perf_counter() - started) * 1_000
        durations.append(duration_ms)
        provider_writes += result.provider_writes
        projected = set(result.projection.projected_node_ids)
        checkpoint_titles = tuple(
            node.title
            for node in result.intent_graph.nodes
            if node.node_id in projected
            and node.node_type == IntentNodeType.CURRENT_CHECKPOINT
        )
        expected_parent = str(case.get("expected_parent", result.outcomes.primary.text))
        expected_count = int(case["expected_checkpoint_count"])
        expected_model = str(case["expected_model"])
        expected_clarification = str(case["expected_clarification"])
        should_project = bool(case["should_project"])
        checks = {
            "parent": result.outcomes.primary.text == expected_parent,
            "planning_model": result.planning_model == expected_model,
            "checkpoint_count": len(checkpoint_titles) == expected_count,
            "clarification": result.clarification.status.value == expected_clarification,
            "projection_state": bool(projected) == should_project,
            "provider_writes_zero": result.provider_writes == 0,
            "execution_unauthorized": result.execution_authorized is False,
            "package_digest": result.verify_digest(),
            "control_plane_excluded": all(
                node.node_type
                in {
                    IntentNodeType.PRIMARY_OUTCOME,
                    IntentNodeType.SECONDARY_OUTCOME,
                    IntentNodeType.CURRENT_CHECKPOINT,
                }
                for node in result.intent_graph.nodes
                if node.node_id in projected
            ),
        }
        rerun = pipeline.process(str(case["input"]))
        checks["deterministic_replay"] = rerun.package_digest == result.package_digest
        group = str(case.get("group", ""))
        if group:
            group_fingerprints.setdefault(group, set()).add(
                result.canonical_intent.semantic_fingerprint
            )
        results.append(
            {
                "id": str(case["id"]),
                "passed": all(checks.values()),
                "checks": checks,
                "duration_ms": round(duration_ms, 6),
                "parent": result.outcomes.primary.text,
                "planning_model": result.planning_model,
                "checkpoint_titles": checkpoint_titles,
                "clarification": result.clarification.status.value,
                "risk": result.risk_profile.overall_level.value,
                "projection_band": result.projection.band.value,
                "semantic_fingerprint": result.canonical_intent.semantic_fingerprint,
                "package_digest": result.package_digest,
            }
        )

    group_invariance = {
        group: len(fingerprints) == 1
        for group, fingerprints in group_fingerprints.items()
    }
    passed = all(item["passed"] for item in results) and all(group_invariance.values())
    return {
        "benchmark": str(dataset["benchmark"]),
        "architecture": str(dataset["architecture"]),
        "passed": passed,
        "case_count": len(results),
        "passed_cases": sum(bool(item["passed"]) for item in results),
        "failed_cases": [item["id"] for item in results if not item["passed"]],
        "group_invariance": group_invariance,
        "provider_writes": provider_writes,
        "performance_ms": {
            "minimum": round(min(durations, default=0.0), 6),
            "p50": round(_percentile(durations, 0.50), 6),
            "p95": round(_percentile(durations, 0.95), 6),
            "maximum": round(max(durations, default=0.0), 6),
        },
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = evaluate(args.dataset)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
