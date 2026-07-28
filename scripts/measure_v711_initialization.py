#!/usr/bin/env python3
"""Measure deterministic Atlas ROS v7.1.1 cold and warm Quick Initialization."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from atlas_ros.contracts.authority import (
    IntegrationInventorySnapshot,
    IntegrationStatusSnapshot,
    SystemStateSnapshot,
)
from atlas_ros.kernel.bootstrap import quick_initialize
from atlas_ros.kernel.digests import sha256_digest
from atlas_ros.runtime.warm import WarmRuntimeCache, WarmRuntimeConfig
from tools.release.authority_compiler import (
    ActiveReleaseSpec,
    AuthorityCompilationSpec,
    RollbackReleaseSpec,
    compile_authority,
)


class MeasuredAuthorityReader:
    def __init__(self, values: dict[tuple[str, str], str]) -> None:
        self.values = values
        self.read_count = 0
        self.bytes_read = 0

    def read_text(self, path: PurePosixPath, *, ref: str) -> str:
        value = self.values[(path.as_posix(), ref)]
        self.read_count += 1
        self.bytes_read += len(value.encode("utf-8"))
        return value


class MeasuredDynamicReader:
    def __init__(self) -> None:
        now = datetime(2026, 7, 28, 20, 0, tzinfo=UTC)
        self.system_state = SystemStateSnapshot(
            active_version="7.1.0",
            immediate_rollback_version="7.0.1",
            authority_model_version="7.0",
            published_workspace_valid=True,
            last_verified_at=now,
        )
        self.inventory = IntegrationInventorySnapshot(
            integrations=tuple(
                IntegrationStatusSnapshot(
                    name=name,
                    required=True,
                    connection_status="connected",
                    approval_status="approved",
                    acceptance_status="passed",
                    lifecycle_status="production",
                    current=True,
                    least_privilege_verified=True,
                )
                for name in ("GitHub", "Notion", "Todoist")
            ),
            last_verified_at=now,
        )
        self.read_count = 0
        self.bytes_read = 0

    def read_system_state(self, url: str) -> SystemStateSnapshot:
        del url
        self.read_count += 1
        self.bytes_read += len(self.system_state.model_dump_json().encode("utf-8"))
        return self.system_state

    def read_integration_inventory(self, reference: str) -> IntegrationInventorySnapshot:
        del reference
        self.read_count += 1
        self.bytes_read += len(self.inventory.model_dump_json().encode("utf-8"))
        return self.inventory


class MeasuredLivenessReader:
    def __init__(self) -> None:
        self.read_count = 0

    def read_connector_liveness(self, names: frozenset[str]) -> dict[str, bool]:
        if names != frozenset({"Todoist"}):
            raise ValueError("v7.1.1 liveness probe must be Todoist-only")
        self.read_count += 1
        return {"Todoist": True}


def fixture() -> tuple[dict[tuple[str, str], str], str]:
    commit = "a" * 40
    manifest_path = "release/RELEASE_MANIFEST_V710.md"
    manifest = (
        "# Atlas ROS v7.1.0\n"
        "Integration Inventory authority: https://app.notion.com/p/inventory\n"
        "Integration Inventory data source: "
        "collection://46af021f-eb9a-4eba-b10c-4523e70df0c3\n"
    )
    compiled = compile_authority(
        AuthorityCompilationSpec(
            active=ActiveReleaseSpec(
                version="7.1.0",
                immutable_commit=commit,
                tag="v7.1.0",
                manifest_path=manifest_path,
                manifest_url=(
                    f"https://github.com/Ryan9876/atlas-ros/blob/{commit}/"
                    f"{manifest_path}"
                ),
                manifest_sha256=sha256_digest(manifest),
                release_url="https://github.com/Ryan9876/atlas-ros/releases/tag/v7.1.0",
                source_sha256="b" * 64,
                wheel_sha256="c" * 64,
            ),
            rollback=RollbackReleaseSpec(
                version="7.0.1",
                immutable_commit="d" * 40,
                tag="v7.0.1",
                release_url="https://github.com/Ryan9876/atlas-ros/releases/tag/v7.0.1",
            ),
            notion_system_state_url="https://app.notion.com/p/system-state",
            last_promotion_transaction_id="v711-performance-fixture",
            last_verified_at="2026-07-28T20:00:00Z",
        )
    )
    return (
        {
            ("governance/AUTHORITY.json", "HEAD"): compiled.authority_json,
            ("governance/RELEASE_INDEX.md", "HEAD"): compiled.release_index_markdown,
            (manifest_path, commit): manifest,
        },
        commit,
    )


def percentile(values: list[float], percentile_value: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * percentile_value)))
    return ordered[index]


def run_once(
    values: dict[tuple[str, str], str],
    *,
    cache: WarmRuntimeCache | None,
) -> tuple[float, Any, dict[str, int]]:
    authority = MeasuredAuthorityReader(values)
    dynamic = MeasuredDynamicReader()
    liveness = MeasuredLivenessReader()
    started = time.perf_counter()
    result = quick_initialize(
        authority,
        dynamic,
        liveness,
        warm_cache=cache,
        warm_auth_token=("v711-performance" if cache is not None else None),
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    if result.receipt.status not in {"READY", "READY_WITH_WARNINGS"}:
        raise RuntimeError(result.receipt.blocked_condition or "initialization blocked")
    return (
        elapsed_ms,
        result,
        {
            "github_reads": authority.read_count,
            "dynamic_reads": dynamic.read_count,
            "todoist_reads": liveness.read_count,
            "bytes_read": authority.bytes_read + dynamic.bytes_read,
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=25)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.iterations < 3:
        raise SystemExit("--iterations must be at least 3")

    values, _ = fixture()
    cold_times: list[float] = []
    cold_metrics: list[dict[str, int]] = []
    cold_result = None
    for _ in range(args.iterations):
        elapsed, result, metrics = run_once(values, cache=None)
        cold_times.append(elapsed)
        cold_metrics.append(metrics)
        cold_result = result

    with tempfile.TemporaryDirectory(prefix="atlas-v711-warm-") as temporary:
        token = "v711-performance"
        cache = WarmRuntimeCache(
            WarmRuntimeConfig(
                root=Path(temporary),
                auth_token_sha256=hashlib.sha256(token.encode()).hexdigest(),
                ttl_seconds=300,
                max_entries=4,
            )
        )
        run_once(values, cache=cache)  # Prime the immutable snapshot.
        warm_times: list[float] = []
        warm_metrics: list[dict[str, int]] = []
        warm_result = None
        for _ in range(args.iterations):
            elapsed, result, metrics = run_once(values, cache=cache)
            warm_times.append(elapsed)
            warm_metrics.append(metrics)
            warm_result = result

    assert cold_result is not None and warm_result is not None
    if cold_result.context != warm_result.context:
        raise RuntimeError("cold and warm initialization contexts differ")

    def summarized(times: list[float], metrics: list[dict[str, int]]) -> dict[str, Any]:
        return {
            "p50_ms": round(statistics.median(times), 4),
            "p95_ms": round(percentile(times, 0.95), 4),
            "minimum_ms": round(min(times), 4),
            "maximum_ms": round(max(times), 4),
            "github_reads_per_run": metrics[-1]["github_reads"],
            "dynamic_reads_per_run": metrics[-1]["dynamic_reads"],
            "todoist_reads_per_run": metrics[-1]["todoist_reads"],
            "estimated_bytes_per_run": metrics[-1]["bytes_read"],
        }

    report = {
        "schema_version": "1.0",
        "scope": "deterministic_in_process_quick_initialization",
        "release_candidate": "7.1.1",
        "active_production_release": "7.1.0",
        "iterations": args.iterations,
        "cold": summarized(cold_times, cold_metrics),
        "warm": summarized(warm_times, warm_metrics),
        "canonical_context_equivalent": True,
        "provider_writes": 0,
        "google_drive_reads": 0,
        "notes": [
            "This benchmark measures Atlas orchestration and validation, "
            "not remote connector latency.",
            "Warm initialization still reads live AUTHORITY.json and live mutable state.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
