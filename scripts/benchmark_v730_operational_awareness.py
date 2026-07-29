#!/usr/bin/env python3
"""Measure deterministic v7.3.0 Operational Awareness capability performance."""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
import tracemalloc
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Callable

from atlas_ros.application.operational_awareness import OperationalAwarenessCoordinator
from atlas_ros.contracts.operational_awareness import (
    AuthoritativeSystem,
    EvidenceConflictV1,
    NormalizedOperationalRecordV1,
    OperationalRecordRefV1,
    OperationalRecordType,
)
from atlas_ros.policy.operational_awareness import load_operational_awareness_policy

NOW = datetime(2026, 7, 28, 16, 0, tzinfo=UTC)


class FixturePort:
    def __init__(self, records: tuple[NormalizedOperationalRecordV1, ...]) -> None:
        self._records = records

    def read_records(self, *, scope: str) -> tuple[NormalizedOperationalRecordV1, ...]:
        del scope
        return self._records

    def authority_identities(self) -> tuple[str, ...]:
        return ("fixture:github", "fixture:notion", "fixture:todoist")

    def missing_sources(self) -> tuple[str, ...]:
        return ()

    def contradictions(self) -> tuple[EvidenceConflictV1, ...]:
        return ()


def _records(count: int) -> tuple[NormalizedOperationalRecordV1, ...]:
    rows: list[NormalizedOperationalRecordV1] = []
    for index in range(count):
        record_id = f"A-{index:04d}"
        updated = NOW - timedelta(hours=index % 96)
        reference = OperationalRecordRefV1.create(
            record_type=OperationalRecordType.ACTION_RECORD,
            canonical_record_id=record_id,
            authoritative_system=AuthoritativeSystem.NOTION,
            canonical_url=f"https://notion.example/{record_id}",
            source_revision=updated.isoformat(),
        )
        rows.append(
            NormalizedOperationalRecordV1.create(
                record_ref=reference,
                title=f"Operational outcome {index}",
                observed_state=("blocked" if index % 13 == 0 else "active"),
                owner="Ryan",
                accountable_party="Ryan",
                definition_of_done=("Outcome is verified",),
                blockers=((f"Dependency {index}",) if index % 13 == 0 else ()),
                priority=(index % 4) + 1,
                updated_at=updated.isoformat(),
            )
        )
    return tuple(rows)


def _measure(function: Callable[[], object], iterations: int) -> dict[str, float]:
    samples: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        function()
        samples.append((time.perf_counter() - start) * 1_000)
    ordered = sorted(samples)
    p95_index = min(len(ordered) - 1, max(0, int(len(ordered) * 0.95) - 1))
    return {
        "iterations": float(iterations),
        "median_ms": round(statistics.median(samples), 3),
        "p95_ms": round(ordered[p95_index], 3),
        "max_ms": round(max(samples), 3),
    }


def _startup(iterations: int) -> dict[str, float]:
    samples: list[float] = []
    command = [sys.executable, "-m", "atlas_ros.entry_points.main", "status", "--json"]
    for _ in range(iterations):
        start = time.perf_counter()
        subprocess.run(command, check=True, capture_output=True, text=True)
        samples.append((time.perf_counter() - start) * 1_000)
    ordered = sorted(samples)
    p95_index = min(len(ordered) - 1, max(0, int(len(ordered) * 0.95) - 1))
    return {
        "iterations": float(iterations),
        "median_ms": round(statistics.median(samples), 3),
        "p95_ms": round(ordered[p95_index], 3),
        "max_ms": round(max(samples), 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=int, default=250)
    parser.add_argument("--iterations", type=int, default=15)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    policy = load_operational_awareness_policy()
    port = FixturePort(_records(args.records))
    coordinator = OperationalAwarenessCoordinator(policy)

    tracemalloc.start()
    first = coordinator.run(port, scope="work", generated_at=NOW)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    first_again = coordinator.run(port, scope="work", generated_at=NOW)
    if first.receipt != first_again.receipt:
        raise RuntimeError("identical benchmark inputs did not produce identical receipts")

    result = {
        "schema_version": "1.0",
        "release_version": "7.3.0",
        "record_count": args.records,
        "operational_awareness_end_to_end": _measure(
            lambda: coordinator.run(port, scope="work", generated_at=NOW), args.iterations
        ),
        "cold_cli_startup": _startup(max(3, min(args.iterations, 10))),
        "peak_memory_bytes": peak,
        "snapshot_digest": first.snapshot.snapshot_digest,
        "receipt_digest": first.receipt.receipt_digest,
        "deterministic_replay": True,
        "provider_writes": first.receipt.provider_writes,
        "status": "passed" if first.receipt.provider_writes == 0 else "failed",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
