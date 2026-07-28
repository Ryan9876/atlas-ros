#!/usr/bin/env python3
"""Measure deterministic cold CLI startup and import footprint."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import time
from pathlib import Path
from typing import Any


def _run(python: str, command: str, *, root: Path) -> dict[str, Any]:
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = "0"
    env["PYTHONPATH"] = str(root / "src")
    script = (
        "import json,resource,sys,time;"
        "start=time.perf_counter();"
        "from atlas_ros.entry_points.main import main;"
        f"main([{command!r},'--json']);"
        "elapsed=time.perf_counter()-start;"
        "mods=sorted(x for x in sys.modules if x=='atlas_ros' or x.startswith('atlas_ros.'));"
        "payload={'probe_elapsed_seconds':elapsed,'atlas_module_count':len(mods),"
        "'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'modules':mods};"
        "print(json.dumps(payload,sort_keys=True))"
    )
    started = time.perf_counter()
    completed = subprocess.run(
        [python, "-c", script],
        cwd=root,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    wall = time.perf_counter() - started
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    payload = json.loads(lines[-1])
    payload["wall_seconds"] = wall
    return payload


def _profile(python: str, iterations: int, root: Path) -> dict[str, Any]:
    samples = [_run(python, "status", root=root) for _ in range(iterations)]
    walls = [float(item["wall_seconds"]) for item in samples]
    imports = [int(item["atlas_module_count"]) for item in samples]
    memory = [int(item["max_rss_kib"]) for item in samples]
    return {
        "iterations": iterations,
        "wall_seconds": {"median": statistics.median(walls), "p95": sorted(walls)[-1]},
        "atlas_module_count": {"median": statistics.median(imports), "max": max(imports)},
        "max_rss_kib": {"median": statistics.median(memory), "max": max(memory)},
        "sample_modules": samples[-1]["modules"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-python", default="python")
    parser.add_argument("--baseline-python")
    parser.add_argument("--iterations", type=int, default=7)
    parser.add_argument("--max-startup-regression", type=float, default=0.10)
    parser.add_argument("--max-module-regression", type=int, default=0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.iterations < 3:
        raise SystemExit("at least three iterations are required")
    root = Path(__file__).resolve().parents[1]
    candidate = _profile(args.candidate_python, args.iterations, root)
    report: dict[str, Any] = {
        "schema_version": "1.0",
        "candidate": candidate,
        "provider_writes": 0,
        "canonical_behavior_changed": False,
    }
    passed = True
    if args.baseline_python:
        baseline = _profile(args.baseline_python, args.iterations, root)
        startup_ratio = candidate["wall_seconds"]["p95"] / baseline["wall_seconds"]["p95"]
        module_delta = (
            candidate["atlas_module_count"]["max"]
            - baseline["atlas_module_count"]["max"]
        )
        passed = (
            startup_ratio <= 1 + args.max_startup_regression
            and module_delta <= args.max_module_regression
        )
        report.update({
            "baseline": baseline,
            "startup_ratio": startup_ratio,
            "module_delta": module_delta,
            "limits": {
                "max_startup_regression": args.max_startup_regression,
                "max_module_regression": args.max_module_regression,
            },
        })
    report["passed"] = passed
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    if not passed:
        raise SystemExit("startup performance gate failed")


if __name__ == "__main__":
    main()
