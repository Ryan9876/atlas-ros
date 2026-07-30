from __future__ import annotations

from datetime import UTC, datetime

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


def snapshots() -> tuple[ReconciliationSnapshot, ReconciliationSnapshot]:
    captured = datetime(2026, 7, 29, 12, tzinfo=UTC)
    return (
        ReconciliationSnapshot(
            provider=AuthoritySource.TODOIST,
            object_id="task-1",
            values={"execution_priority": "P1"},
            version="todoist-v1",
            captured_at=captured,
        ),
        ReconciliationSnapshot(
            provider=AuthoritySource.NOTION,
            object_id="page-1",
            values={"execution_priority": "P4"},
            version="notion-v1",
            captured_at=captured,
        ),
    )


def authorize(plan):  # type: ignore[no-untyped-def]
    return ReconciliationAuthorization(
        authorization_id="auth-v780",
        plan_id=plan.plan_id,
        plan_digest=plan.plan_digest,
        actor="Ryan",
        attended=True,
        authorized_mutation_ids=tuple(item.mutation_id for item in plan.ordered_mutations),
    )


def setup():  # type: ignore[no-untyped-def]
    checkpoint = CheckpointToken(cursor="2026-07-29T00:00:00+00:00")
    state = InMemoryReconciliationState(checkpoint)
    notion = InMemoryReconciliationProvider(
        AuthoritySource.NOTION,
        {"page-1": {"execution_priority": "P4"}},
    )
    todoist = InMemoryReconciliationProvider(AuthoritySource.TODOIST, {"task-1": {}})
    service = CanonicalReconciliationService(
        default_field_authority_registry(),
        (todoist, notion),
        state,
    )
    plan = service.plan(*snapshots(), correlation_id="corr-v780")
    return service, state, notion, plan


def test_failure_before_write_does_not_record_successful_key() -> None:
    service, state, notion, plan = setup()
    mutation = plan.ordered_mutations[0]
    notion.fail_before_write.add(mutation.mutation_id)

    result = service.apply(plan, authorize(plan))

    assert not result.consistent
    assert mutation.idempotency_key not in state.successful_write_keys
    assert state.checkpoint == plan.expected_checkpoint


def test_write_success_and_readback_mismatch_retains_key_and_avoids_duplicate_apply() -> None:
    service, state, notion, plan = setup()
    mutation = plan.ordered_mutations[0]
    notion.mismatch_after_write.add(mutation.mutation_id)

    failed = service.apply(plan, authorize(plan))

    assert not failed.consistent
    assert mutation.idempotency_key in state.successful_write_keys
    assert notion.apply_calls[mutation.mutation_id] == 1
    assert state.checkpoint == plan.expected_checkpoint

    notion.mismatch_after_write.clear()
    recovered = service.apply(plan, authorize(plan))

    assert recovered.consistent
    assert notion.apply_calls[mutation.mutation_id] == 1
    assert recovered.receipt.operation_results[0].status.value == "already_applied"
    assert state.checkpoint != plan.expected_checkpoint


def test_write_success_and_readback_exception_retains_key_and_recovers_by_readback() -> None:
    service, state, notion, plan = setup()
    mutation = plan.ordered_mutations[0]
    notion.raise_during_readback.add(mutation.mutation_id)

    failed = service.apply(plan, authorize(plan))

    assert not failed.consistent
    assert mutation.idempotency_key in state.successful_write_keys
    assert notion.apply_calls[mutation.mutation_id] == 1
    assert state.checkpoint == plan.expected_checkpoint

    notion.raise_during_readback.clear()
    recovered = service.apply(plan, authorize(plan))

    assert recovered.consistent
    assert notion.apply_calls[mutation.mutation_id] == 1
    assert recovered.receipt.checkpoint_advanced


def test_legacy_applied_keys_constructor_remains_compatible() -> None:
    state = InMemoryReconciliationState(
        CheckpointToken(cursor="2026-07-29T00:00:00+00:00"),
        applied_keys={"legacy-key"},
    )

    assert state.successful_write_keys == {"legacy-key"}
    assert state.applied_keys is state.successful_write_keys
