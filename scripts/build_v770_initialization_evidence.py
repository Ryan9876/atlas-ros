#!/usr/bin/env python3
"""Build deterministic v7.7.0 Initialization Circuit Breaker evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
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
from atlas_ros.kernel.initialization_circuit_breaker import (
    InitializationAlreadyTerminal,
    InitializationCapability,
    InitializationOperation,
)
from atlas_ros.runtime.warm import WarmRuntimeCache, WarmRuntimeConfig
from tools.release.authority_compiler import (
    ActiveReleaseSpec,
    AuthorityCompilationSpec,
    RollbackReleaseSpec,
    compile_authority,
)

ACTIVE_VERSION = "7.6.1"
ACTIVE_COMMIT = "9" * 40
ROLLBACK_VERSION = "7.6.0"
ROLLBACK_COMMIT = "a" * 40


class DeterministicTimer:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        self.value += 0.001
        return self.value


class EvidenceAuthorityReader:
    def __init__(self, values: dict[tuple[str, str], str]) -> None:
        self.values = values
        self.reads: list[tuple[str, str]] = []

    def read_text(self, path: PurePosixPath, *, ref: str) -> str:
        key = (path.as_posix(), ref)
        self.reads.append(key)
        return self.values[key]


class EvidenceDynamicReader:
    def __init__(self) -> None:
        now = datetime(2026, 7, 29, 20, 0, tzinfo=UTC)
        self.system_state = SystemStateSnapshot(
            active_version=ACTIVE_VERSION,
            immediate_rollback_version=ROLLBACK_VERSION,
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
        self.system_state_reads: list[str] = []
        self.inventory_reads: list[str] = []

    def read_system_state(self, url: str) -> SystemStateSnapshot:
        self.system_state_reads.append(url)
        return self.system_state

    def read_integration_inventory(self, reference: str) -> IntegrationInventorySnapshot:
        self.inventory_reads.append(reference)
        return self.inventory


class EvidenceLivenessReader:
    def __init__(self, *, todoist_live: bool = True) -> None:
        self.todoist_live = todoist_live
        self.reads: list[frozenset[str]] = []

    def read_connector_liveness(self, names: frozenset[str]) -> dict[str, bool]:
        self.reads.append(names)
        if names != frozenset({"Todoist"}):
            raise AssertionError("liveness target broadened beyond Todoist")
        return {"Todoist": self.todoist_live}


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def compiled_reader() -> EvidenceAuthorityReader:
    manifest_path = "release/RELEASE_MANIFEST_V761.md"
    manifest = (
        "# Atlas ROS v7.6.1 Immutable Release Manifest\n"
        "Integration Inventory authority: https://app.notion.com/p/inventory\n"
        "Integration Inventory data source: collection://inventory-source\n"
    )
    compiled = compile_authority(
        AuthorityCompilationSpec(
            active=ActiveReleaseSpec(
                version=ACTIVE_VERSION,
                immutable_commit=ACTIVE_COMMIT,
                tag=f"v{ACTIVE_VERSION}",
                manifest_path=manifest_path,
                manifest_url=(
                    "https://github.com/Ryan9876/atlas-ros/blob/"
                    f"{ACTIVE_COMMIT}/{manifest_path}"
                ),
                manifest_sha256=sha256_digest(manifest),
                release_url=(
                    "https://github.com/Ryan9876/atlas-ros/releases/tag/"
                    f"v{ACTIVE_VERSION}"
                ),
                source_sha256="b" * 64,
                wheel_sha256="c" * 64,
            ),
            rollback=RollbackReleaseSpec(
                version=ROLLBACK_VERSION,
                immutable_commit=ROLLBACK_COMMIT,
                tag=f"v{ROLLBACK_VERSION}",
                release_url=(
                    "https://github.com/Ryan9876/atlas-ros/releases/tag/"
                    f"v{ROLLBACK_VERSION}"
                ),
            ),
            notion_system_state_url="https://app.notion.com/p/system-state",
            last_promotion_transaction_id="v761-active-predecessor",
            last_verified_at="2026-07-29T20:00:00-04:00",
        )
    )
    return EvidenceAuthorityReader(
        {
            ("governance/AUTHORITY.json", "HEAD"): compiled.authority_json,
            ("governance/RELEASE_INDEX.md", "HEAD"): (
                compiled.release_index_markdown
            ),
            (manifest_path, ACTIVE_COMMIT): manifest,
        }
    )


def cache(root: Path) -> WarmRuntimeCache:
    token = "v770-candidate-evidence-token"
    return WarmRuntimeCache(
        WarmRuntimeConfig(
            root=root,
            auth_token_sha256=hashlib.sha256(token.encode()).hexdigest(),
            ttl_seconds=300,
            max_entries=2,
        )
    )


def terminal_lock_proof(operation: InitializationOperation) -> dict[str, Any]:
    provider_calls = 0

    def forbidden_provider() -> dict[str, bool]:
        nonlocal provider_calls
        provider_calls += 1
        return {"Todoist": True}

    try:
        operation.execute_external(
            capability=InitializationCapability.TODOIST_LIVENESS_READ,
            target="todoist:connector-liveness",
            provider=forbidden_provider,
            initiator="post-terminal-adversarial-probe",
        )
    except InitializationAlreadyTerminal as error:
        return {
            "schema_version": "v770-terminal-lock-proof-v1",
            "terminal_status": error.terminal_status,
            "operation_id": error.operation_id,
            "attempted_capability": error.attempted_capability,
            "target": error.target,
            "rejection_reason": error.rejection_reason,
            "sequence": error.sequence,
            "provider_invoked": error.provider_invoked,
            "observed_provider_calls": provider_calls,
            "post_terminal_executed_calls": operation.post_terminal_executed_calls,
            "rejected_calls": [
                item.model_dump(mode="json") for item in operation.rejected_calls()
            ],
            "status": "passed",
        }
    raise AssertionError("post-terminal provider call was not rejected")


def run_ready(
    *,
    operation_id: str,
    warm_cache: WarmRuntimeCache,
    auth_token: str,
) -> tuple[dict[str, Any], InitializationOperation, EvidenceAuthorityReader]:
    authority = compiled_reader()
    dynamic = EvidenceDynamicReader()
    liveness = EvidenceLivenessReader()
    operation = InitializationOperation(operation_id=operation_id)
    result = quick_initialize(
        authority,
        dynamic,
        liveness,
        warm_cache=warm_cache,
        warm_auth_token=auth_token,
        timer=DeterministicTimer(),
        operation=operation,
    )
    if result.receipt.status not in {"READY", "READY_WITH_WARNINGS"}:
        raise AssertionError(result.receipt.blocked_condition)
    return result.receipt.model_dump(mode="json"), operation, authority


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-directory", type=Path, default=Path("build"))
    args = parser.parse_args()
    output = args.output_directory.resolve()
    output.mkdir(parents=True, exist_ok=True)
    auth_token = "v770-candidate-evidence-token"

    with tempfile.TemporaryDirectory(prefix="atlas-v770-warm-") as temporary:
        warm_cache = cache(Path(temporary))
        cold, cold_operation, cold_reader = run_ready(
            operation_id="v770-cold-evidence",
            warm_cache=warm_cache,
            auth_token=auth_token,
        )
        warm, warm_operation, warm_reader = run_ready(
            operation_id="v770-warm-evidence",
            warm_cache=warm_cache,
            auth_token=auth_token,
        )

    if cold["execution_path"] != "cold" or cold["external_read_count"] != 6:
        raise AssertionError("cold evidence does not prove exactly six reads")
    if warm["execution_path"] != "warm" or warm["external_read_count"] != 4:
        raise AssertionError("warm evidence does not prove exactly four reads")
    if cold["provider_writes"] != 0 or warm["provider_writes"] != 0:
        raise AssertionError("provider write boundary failed")
    if cold["google_drive_reads"] != 0 or warm["google_drive_reads"] != 0:
        raise AssertionError("Google Drive boundary failed")
    if cold_reader.reads != [
        ("governance/AUTHORITY.json", "HEAD"),
        ("governance/RELEASE_INDEX.md", "HEAD"),
        ("release/RELEASE_MANIFEST_V761.md", ACTIVE_COMMIT),
    ]:
        raise AssertionError("cold GitHub read sequence is not exact")
    if warm_reader.reads != [("governance/AUTHORITY.json", "HEAD")]:
        raise AssertionError("warm GitHub path performed excess reads")

    cold_lock = terminal_lock_proof(cold_operation)
    warm_lock = terminal_lock_proof(warm_operation)
    if cold_lock["observed_provider_calls"] != 0 or warm_lock["observed_provider_calls"] != 0:
        raise AssertionError("terminal lock invoked a provider")

    write_json(output / "V770_COLD_INITIALIZATION_RECEIPT.json", cold)
    write_json(output / "V770_WARM_INITIALIZATION_RECEIPT.json", warm)
    write_json(output / "V770_COLD_TERMINAL_LOCK_PROOF.json", cold_lock)
    write_json(output / "V770_WARM_TERMINAL_LOCK_PROOF.json", warm_lock)
    write_json(
        output / "V770_INITIALIZATION_EVIDENCE_INDEX.json",
        {
            "schema_version": "v770-initialization-evidence-index-v1",
            "status": "passed",
            "active_predecessor": ACTIVE_VERSION,
            "rollback_predecessor": ROLLBACK_VERSION,
            "cold_external_reads": cold["external_read_count"],
            "warm_external_reads": warm["external_read_count"],
            "cold_trace": cold["actual_trace"],
            "warm_trace": warm["actual_trace"],
            "cold_budget_passed": cold["budget_result"],
            "warm_budget_passed": warm["budget_result"],
            "terminal_lock_proofs": [cold_lock, warm_lock],
            "provider_writes": 0,
            "google_drive_reads": 0,
            "post_terminal_executed_calls": 0,
            "general_searches": 0,
            "plugin_skill_reads": 0,
        },
    )


if __name__ == "__main__":
    main()
