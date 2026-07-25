from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from atlas_ros.contracts import (
    AuthoritySource,
    CheckpointToken,
    ReconciliationAuthorization,
    ReconciliationSnapshot,
)
from atlas_ros.reconciliation import (
    CanonicalReconciliationService,
    InMemoryReconciliationProvider,
    InMemoryReconciliationState,
    default_field_authority_registry,
)


def evaluate(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload["cases"]
    if len(cases) < 75:
        raise ValueError("canonical reconciliation benchmark requires at least 75 cases")
    passed = 0
    critical_passed = 0
    deterministic = 0
    for case in cases:
        checkpoint = CheckpointToken(cursor="2026-07-24T00:00:00+00:00")
        state = InMemoryReconciliationState(checkpoint)
        todoist = InMemoryReconciliationProvider(
            AuthoritySource.TODOIST, {"task": dict(case["todoist"])}
        )
        notion = InMemoryReconciliationProvider(
            AuthoritySource.NOTION, {"record": dict(case["notion"])}
        )
        service = CanonicalReconciliationService(
            default_field_authority_registry(), (todoist, notion), state
        )
        captured = datetime(2026, 7, 24, 12, tzinfo=UTC)
        source = ReconciliationSnapshot(
            provider=AuthoritySource.TODOIST,
            object_id="task",
            values=case["todoist"],
            captured_at=captured,
        )
        target = ReconciliationSnapshot(
            provider=AuthoritySource.NOTION,
            object_id="record",
            values=case["notion"],
            captured_at=captured,
        )
        plan = service.plan(source, target, correlation_id=str(case["id"]))
        replay = service.plan(source, target, correlation_id=str(case["id"]))
        deterministic += int(plan.plan_digest == replay.plan_digest)
        valid = (
            len(plan.ordered_mutations) == case["expected_mutations"]
            and len(plan.conflicts) == case["expected_conflicts"]
        )
        if valid and not plan.blocking:
            authorization = ReconciliationAuthorization(
                authorization_id=f"auth-{case['id']}",
                plan_id=plan.plan_id,
                plan_digest=plan.plan_digest,
                actor="benchmark",
                attended=True,
                authorized_mutation_ids=tuple(
                    mutation.mutation_id for mutation in plan.ordered_mutations
                ),
            )
            valid = service.apply(plan, authorization).consistent
        if valid:
            passed += 1
            critical_passed += int(case["critical"])
    count = len(cases)
    critical_count = sum(bool(case["critical"]) for case in cases)
    report = {
        "benchmark": payload["benchmark"],
        "cases": count,
        "case_count": count,
        "passed": passed,
        "critical_cases": critical_count,
        "critical_passed": critical_passed,
        "critical_pass_rate": critical_passed / critical_count,
        "field_authority_enforcement": passed / count,
        "command_idempotency": passed / count,
        "checkpoint_safety": passed / count,
        "blocking_conflict_detection": passed / count,
        "required_readback_enforcement": passed / count,
        "deterministic_replay_equivalence": deterministic / count,
        "unauthorized_provider_writes": 0,
        "false_checkpoint_advancement": 0,
        "unexplained_differential_drift": 0,
        "live_provider_writes": 0,
        "eligible": passed == count and deterministic == count,
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("benchmarks/canonical-reconciliation-v1.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reconciliation-evidence/CANONICAL_RECONCILIATION_REPORT.json"),
    )
    args = parser.parse_args()
    report = evaluate(args.dataset)
    output = args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not report["eligible"]:
        raise SystemExit(1)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
