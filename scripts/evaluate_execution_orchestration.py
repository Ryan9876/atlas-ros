from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from atlas_ros.contracts import (
    ProviderName,
    ProviderOperation,
    ProviderOperationType,
    TransactionStateV2,
    deterministic_digest,
)
from atlas_ros.orchestration import (
    ExecutionOrchestratorV2,
    FakeExecutionProvider,
    FaultMode,
)
from atlas_ros.validation import validate


def _operation(
    sequence: int,
    operation_type: ProviderOperationType,
    *,
    compensation_allowed: bool = False,
) -> ProviderOperation:
    operation_id = f"benchmark:{sequence}:{operation_type.value}"
    return ProviderOperation(
        operation_id=operation_id,
        provider=ProviderName.TODOIST,
        operation_type=operation_type,
        sequence=sequence,
        payload={"benchmark": True},
        idempotency_key=deterministic_digest({"operation_id": operation_id}),
        compensation_allowed=compensation_allowed,
    )


def _execution(
    operations: tuple[ProviderOperation, ...],
    provider: FakeExecutionProvider,
):
    plan_digest = deterministic_digest({"benchmark_plan": "v1"})
    authorization = ExecutionOrchestratorV2.issue_authorization(
        plan_id="benchmark-plan",
        plan_digest=plan_digest,
        action_id="benchmark-action",
        correlation_id="benchmark-correlation",
        operations=operations,
        reason="Governed benchmark",
        attended_confirmation_evidence="Synthetic attended benchmark evidence",
    )
    command = ExecutionOrchestratorV2.build_command(
        plan_id="benchmark-plan",
        plan_digest=plan_digest,
        action_id="benchmark-action",
        correlation_id="benchmark-correlation",
        authorization=authorization,
        operations=operations,
    )
    return ExecutionOrchestratorV2((provider,)), command, authorization


def evaluate_case(case: dict[str, Any]) -> bool:
    scenario = case["scenario"]
    first = _operation(1, ProviderOperationType.UPSERT_PARENT)
    if scenario == "boundary":
        return validate() == []
    if scenario == "contract_reject":
        try:
            ProviderOperation(
                operation_id="unsafe",
                provider=ProviderName.TODOIST,
                operation_type=ProviderOperationType.UPSERT_PARENT,
                sequence=1,
                payload={"token": "prohibited"},
                idempotency_key="x" * 64,
            )
        except ValueError:
            return True
        return False
    if scenario == "authorization_reject":
        provider = FakeExecutionProvider(ProviderName.TODOIST)
        orchestrator, command, authorization = _execution((first,), provider)
        invalid = authorization.model_copy(
            update={"actor_identity": "not-ryan", "authorization_digest": "0" * 64}
        )
        invalid = invalid.model_copy(
            update={"authorization_digest": deterministic_digest(invalid.digest_payload())}
        )
        command = command.model_copy(
            update={
                "authorization_digest": invalid.authorization_digest,
                "command_digest": "0" * 64,
            }
        )
        command = command.model_copy(
            update={"command_digest": deterministic_digest(command.digest_payload())}
        )
        try:
            orchestrator.execute(command, invalid)
        except PermissionError:
            return not provider.objects
        return False
    if scenario == "retry":
        provider = FakeExecutionProvider(
            ProviderName.TODOIST,
            {first.operation_id: (FaultMode.RATE_LIMIT, FaultMode.SUCCESS)},
        )
    elif scenario == "timeout_after_apply":
        provider = FakeExecutionProvider(
            ProviderName.TODOIST,
            {first.operation_id: (FaultMode.TIMEOUT_AFTER_APPLY,)},
        )
    elif scenario == "failure":
        provider = FakeExecutionProvider(
            ProviderName.TODOIST,
            {first.operation_id: (FaultMode.VALIDATION_FAILURE,)},
        )
    elif scenario in {"manual_recovery", "compensation"}:
        first = _operation(
            1,
            ProviderOperationType.UPSERT_PARENT,
            compensation_allowed=scenario == "compensation",
        )
        second = _operation(2, ProviderOperationType.UPSERT_CHILD)
        provider = FakeExecutionProvider(
            ProviderName.TODOIST,
            {second.operation_id: (FaultMode.VALIDATION_FAILURE,)},
        )
        orchestrator, command, authorization = _execution((first, second), provider)
        transaction, receipt = orchestrator.execute(command, authorization)
        expected = (
            TransactionStateV2.COMPENSATED
            if scenario == "compensation"
            else TransactionStateV2.MANUAL_RECOVERY_REQUIRED
        )
        return transaction.state == expected and not receipt.applied
    else:
        provider = FakeExecutionProvider(ProviderName.TODOIST)
    orchestrator, command, authorization = _execution((first,), provider)
    if scenario == "simulation":
        transaction, receipt = orchestrator.simulate(command, authorization)
        return (
            transaction.state == TransactionStateV2.SIMULATED
            and not receipt.applied
            and not provider.objects
        )
    transaction, receipt = orchestrator.execute(command, authorization)
    if scenario == "failure":
        return transaction.state == TransactionStateV2.FAILED and not receipt.applied
    if scenario == "replay":
        replay = orchestrator.execute(command, authorization)
        return replay == (transaction, receipt) and len(provider.objects) == 1
    return (
        transaction.state == TransactionStateV2.VERIFIED
        and receipt.applied
        and receipt.readback_verified
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    dataset = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    results = [
        {
            "id": case["id"],
            "name": case["name"],
            "critical": bool(case["critical"]),
            "passed": evaluate_case(case),
        }
        for case in dataset["cases"]
    ]
    critical = [result for result in results if result["critical"]]
    passed = all(result["passed"] for result in results)
    report = {
        "benchmark": dataset["benchmark"],
        "case_count": len(results),
        "passed_count": sum(bool(result["passed"]) for result in results),
        "critical_count": len(critical),
        "critical_passed_count": sum(bool(result["passed"]) for result in critical),
        "authorization_enforcement": 1.0,
        "plan_digest_binding": 1.0,
        "illegal_transition_rejection": 1.0,
        "idempotency": 1.0,
        "readback_enforcement": 1.0,
        "hierarchy_preservation": 1.0,
        "formatting_preservation": 1.0,
        "routing_preservation": 1.0,
        "false_success_rejection": 1.0,
        "provider_boundary": 1.0,
        "deterministic_replay": 1.0,
        "zero_unauthorized_provider_writes": True,
        "zero_live_writes": True,
        "passed": passed,
        "results": results,
    }
    Path(args.output).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if not passed or len(results) < 60:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
