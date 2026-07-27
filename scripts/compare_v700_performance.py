#!/usr/bin/env python3
"""Compare equivalent provider-neutral execution-planning performance for v7 and v6.5."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any


def _run_once(python: Path, dataset: Path, output: Path) -> float:
    started = time.perf_counter_ns()
    completed = subprocess.run(
        [
            str(python),
            "scripts/evaluate_execution_planning.py",
            "--dataset",
            str(dataset),
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
    if completed.returncode != 0:
        raise RuntimeError(
            f"benchmark failed for {python}: {completed.stderr or completed.stdout}"
        )
    payload: dict[str, Any] = json.loads(output.read_text(encoding="utf-8"))
    if payload.get("status") != "passed":
        raise RuntimeError(f"benchmark did not pass for {python}: {payload}")
    return elapsed_ms


def _measure(python: Path, dataset: Path, iterations: int, root: Path) -> list[float]:
    warmup = root / f"warmup-{python.parent.name}.json"
    _run_once(python, dataset, warmup)
    results: list[float] = []
    for index in range(iterations):
        output = root / f"run-{python.parent.name}-{index}.json"
        results.append(_run_once(python, dataset, output))
    return results


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(fraction * len(ordered)) - 1)
    return ordered[index]


def compare(
    *,
    candidate_python: Path,
    baseline_python: Path,
    dataset: Path,
    iterations: int,
    max_regression: float,
) -> dict[str, Any]:
    if iterations < 3:
        raise ValueError("at least three measured iterations are required")
    with tempfile.TemporaryDirectory(prefix="atlas-v700-performance-") as directory:
        root = Path(directory)
        candidate = _measure(candidate_python, dataset, iterations, root)
        baseline = _measure(baseline_python, dataset, iterations, root)
    candidate_p95 = _percentile(candidate, 0.95)
    baseline_p95 = _percentile(baseline, 0.95)
    regression = (candidate_p95 - baseline_p95) / baseline_p95
    return {
        "schema_version": "1.0",
        "benchmark": "execution-planning-v1-equivalent-process-runtime",
        "iterations": iterations,
        "candidate": {
            "python": str(candidate_python),
            "measurements_ms": candidate,
            "p50_ms": _percentile(candidate, 0.50),
            "p95_ms": candidate_p95,
        },
        "baseline": {
            "version": "6.5.0",
            "python": str(baseline_python),
            "measurements_ms": baseline,
            "p50_ms": _percentile(baseline, 0.50),
            "p95_ms": baseline_p95,
        },
        "p95_regression_fraction": regression,
        "maximum_allowed_regression_fraction": max_regression,
        "provider_writes": 0,
        "status": "passed" if regression <= max_regression else "failed",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-python", type=Path, required=True)
    parser.add_argument("--baseline-python", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--iterations", type=int, default=7)
    parser.add_argument("--max-regression", type=float, default=0.10)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = compare(
        candidate_python=args.candidate_python,
        baseline_python=args.baseline_python,
        dataset=args.dataset,
        iterations=args.iterations,
        max_regression=args.max_regression,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if result["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
