from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


INPUTS = (
    "Task = arista cloud vision code upgrade automation pilot.",
    "CloudVision code upgrade automation pilot with no downtime",
    "Upgrade CloudVision while reducing downtime and documenting the process",
    "Pilot for automating Cisco code upgrades",
    "Migrate the network monitoring platform to a new service",
)


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = min(len(ordered) - 1, int(round((len(ordered) - 1) * percentile)))
    return ordered[position]


def _measure_candidate(iterations: int, warmup: int) -> dict[str, float]:
    from atlas_ros.engines import AdaptiveInputProcessingPipelineV62

    pipeline = AdaptiveInputProcessingPipelineV62()
    for _ in range(warmup):
        for value in INPUTS:
            pipeline.process(value)
    durations: list[float] = []
    for _ in range(iterations):
        for value in INPUTS:
            started = time.perf_counter()
            pipeline.process(value)
            durations.append((time.perf_counter() - started) * 1_000)
    return _statistics(durations)


def _measure_baseline(
    baseline_source: Path,
    iterations: int,
    warmup: int,
) -> dict[str, float]:
    program = f"""
import json
import statistics
import time
from atlas_ros.domain.models import Capture
from atlas_ros.engines import KnowledgeCompositionEngine, ManagementReasoningEngine, ManagementStructureEngine, ReasoningCoherenceGate
from atlas_ros.models import load_default_registries
inputs = {INPUTS!r}
models, modules = load_default_registries()
reasoner = ManagementReasoningEngine()
gate = ReasoningCoherenceGate()
composer = KnowledgeCompositionEngine(modules, models)
structurer = ManagementStructureEngine(models)
def execute(value):
    reasoning = reasoner.reason_v4(Capture(content=value))
    gate.evaluate(reasoning)
    knowledge = composer.compose_v2(reasoning)
    structurer.structure_v3(reasoning, knowledge)
for _ in range({warmup}):
    for value in inputs:
        execute(value)
durations = []
for _ in range({iterations}):
    for value in inputs:
        started = time.perf_counter()
        execute(value)
        durations.append((time.perf_counter() - started) * 1000)
ordered = sorted(durations)
def percentile(value):
    index = min(len(ordered) - 1, int(round((len(ordered) - 1) * value)))
    return ordered[index]
print(json.dumps({{
    'minimum': min(durations),
    'mean': statistics.fmean(durations),
    'median': statistics.median(durations),
    'p50': percentile(0.50),
    'p95': percentile(0.95),
    'maximum': max(durations),
}}))
"""
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(baseline_source / "src")
    completed = subprocess.run(
        [sys.executable, "-c", program],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    return {key: float(value) for key, value in json.loads(completed.stdout).items()}


def _statistics(durations: list[float]) -> dict[str, float]:
    return {
        "minimum": min(durations, default=0.0),
        "mean": statistics.fmean(durations) if durations else 0.0,
        "median": statistics.median(durations) if durations else 0.0,
        "p50": _percentile(durations, 0.50),
        "p95": _percentile(durations, 0.95),
        "maximum": max(durations, default=0.0),
    }


def compare(
    baseline_source: Path,
    iterations: int,
    warmup: int,
    max_regression: float,
) -> dict[str, Any]:
    baseline = _measure_baseline(baseline_source, iterations, warmup)
    candidate = _measure_candidate(iterations, warmup)
    p95_ratio = candidate["p95"] / baseline["p95"] if baseline["p95"] else float("inf")
    regression = p95_ratio - 1
    return {
        "baseline": "Atlas ROS v6.1.1 full semantic reasoning path",
        "candidate": "Atlas ROS v6.2 adaptive input-processing path",
        "inputs": INPUTS,
        "iterations_per_input": iterations,
        "warmup_iterations_per_input": warmup,
        "baseline_ms": baseline,
        "candidate_ms": candidate,
        "p95_ratio": p95_ratio,
        "p95_regression": regression,
        "maximum_allowed_regression": max_regression,
        "passed": regression <= max_regression,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--warmup", type=int, default=20)
    parser.add_argument("--max-regression", type=float, default=0.20)
    args = parser.parse_args()
    report = compare(
        args.baseline_source,
        args.iterations,
        args.warmup,
        args.max_regression,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
