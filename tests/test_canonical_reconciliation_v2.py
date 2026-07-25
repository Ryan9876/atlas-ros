from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from atlas_ros.contracts import (
    AuthoritySource,
    CheckpointToken,
    FieldAuthorityRegistry,
    FieldAuthorityRule,
    ReconciliationAuthorization,
    ReconciliationCommand,
    ReconciliationPlanV2,
    ReconciliationReceiptV2,
    ReconciliationSnapshot,
    UpdateDirection,
)
from atlas_ros.reconciliation import (
    CanonicalReconciliationService,
    InMemoryReconciliationProvider,
    InMemoryReconciliationState,
    default_field_authority_registry,
)


def checkpoint(cursor: str = "2026-07-24T00:00:00+00:00") -> CheckpointToken:
    return CheckpointToken(cursor=cursor)


def snapshots(
    todoist_values: dict[str, object],
    notion_values: dict[str, object],
) -> tuple[ReconciliationSnapshot, ReconciliationSnapshot]:
    captured = datetime(2026, 7, 24, 12, tzinfo=UTC)
    return (
        ReconciliationSnapshot(
            provider=AuthoritySource.TODOIST,
            object_id="task-1",
            values=todoist_values,
            version="todoist-v1",
            captured_at=captured,
        ),
        ReconciliationSnapshot(
            provider=AuthoritySource.NOTION,
            object_id="page-1",
            values=notion_values,
            version="notion-v1",
            captured_at=captured,
        ),
    )


def service(
    *,
    todoist_objects: dict[str, dict[str, object]] | None = None,
    notion_objects: dict[str, dict[str, object]] | None = None,
) -> tuple[
    CanonicalReconciliationService,
    InMemoryReconciliationState,
    InMemoryReconciliationProvider,
    InMemoryReconciliationProvider,
]:
    state = InMemoryReconciliationState(checkpoint())
    todoist = InMemoryReconciliationProvider(
        AuthoritySource.TODOIST, todoist_objects or {"task-1": {}}
    )
    notion = InMemoryReconciliationProvider(
        AuthoritySource.NOTION, notion_objects or {"page-1": {}}
    )
    return (
        CanonicalReconciliationService(
            default_field_authority_registry(), (todoist, notion), state
        ),
        state,
        todoist,
        notion,
    )


def authorize(plan: ReconciliationPlanV2, *, attended: bool = True) -> ReconciliationAuthorization:
    return ReconciliationAuthorization(
        authorization_id="auth-1",
        plan_id=plan.plan_id,
        plan_digest=plan.plan_digest,
        actor="Ryan",
        attended=attended,
        authorized_mutation_ids=tuple(
            mutation.mutation_id for mutation in plan.ordered_mutations
        ),
    )


def test_default_registry_is_complete_and_digest_bound() -> None:
    registry = default_field_authority_registry()
    assert registry.policy_version == "2.0.0"
    assert len(registry.rules) == 21
    assert len(registry.policy_digest) == 64
    assert registry.rule_for("execution_due_date").authority is AuthoritySource.TODOIST
    assert registry.rule_for("responsibility").authority is AuthoritySource.NOTION
    assert registry.rule_for("sync_state").direction is UpdateDirection.DERIVE_ONLY
    with pytest.raises(KeyError, match="unknown reconciliation field"):
        registry.rule_for("mystery")


def test_registry_rejects_duplicate_fields() -> None:
    rule = FieldAuthorityRule(
        field="x",
        authority=AuthoritySource.NOTION,
        direction=UpdateDirection.NOTION_TO_TODOIST,
    )
    with pytest.raises(ValidationError, match="must be unique"):
        FieldAuthorityRegistry(policy_version="x", rules=(rule, rule))


def test_checkpoint_is_integrity_protected() -> None:
    token = CheckpointToken(cursor="2026-07-24", applied_event_ids=("b", "a"))
    assert len(token.integrity_digest) == 64
    with pytest.raises(ValidationError, match="integrity digest mismatch"):
        CheckpointToken(cursor="2026-07-24", integrity_digest="0" * 64)


@pytest.mark.parametrize(
    ("kind", "body", "argument"),
    [
        ("update", "progress", ""),
        ("delegate", "", "to Bill"),
        ("risk", "dependency risk", ""),
        ("blocker", "waiting for vendor", ""),
        ("dependency", "approval", ""),
        ("issue", "provider mismatch", ""),
        ("unblock", "resolved", ""),
        ("checkpoint", "", "2026-07-30"),
    ],
)
def test_governed_commands_have_deterministic_idempotency(
    kind: str, body: str, argument: str
) -> None:
    command = ReconciliationCommand(
        event_id="event-1", kind=kind, body=body, argument=argument  # type: ignore[arg-type]
    )
    duplicate = command.model_copy()
    assert command.idempotency_key == duplicate.idempotency_key


def test_commands_fail_closed_for_missing_content_and_invalid_checkpoint() -> None:
    with pytest.raises(ValidationError, match="requires content"):
        ReconciliationCommand(event_id="e", kind="blocker")
    with pytest.raises(ValidationError, match="valid ISO date"):
        ReconciliationCommand(event_id="e", kind="checkpoint", argument="tomorrow")


def test_plan_enforces_field_authority_both_directions() -> None:
    engine, _, _, _ = service()
    todoist, notion = snapshots(
        {"execution_priority": "P1", "responsibility": "stale"},
        {"execution_priority": "P4", "responsibility": "Network leadership"},
    )
    plan = engine.plan(todoist, notion, correlation_id="corr-1")
    assert [(item.provider, item.field, item.desired_value) for item in plan.ordered_mutations] == [
        (AuthoritySource.NOTION, "execution_priority", "P1"),
        (AuthoritySource.TODOIST, "responsibility", "Network leadership"),
    ]
    assert not plan.conflicts
    assert len(plan.plan_digest) == 64


def test_equivalent_reordered_snapshots_have_identical_plan() -> None:
    engine, _, _, _ = service()
    a = snapshots(
        {"execution_due_date": "2026-08-01", "execution_priority": "P1"},
        {"execution_due_date": "2026-08-02", "execution_priority": "P3"},
    )
    b = snapshots(
        {"execution_priority": "P1", "execution_due_date": "2026-08-01"},
        {"execution_priority": "P3", "execution_due_date": "2026-08-02"},
    )
    first = engine.plan(*a, correlation_id="corr")
    second = engine.plan(*b, correlation_id="corr")
    assert first.plan_id == second.plan_id
    assert first.plan_digest == second.plan_digest


def test_unknown_field_creates_blocking_conflict_and_no_mutation() -> None:
    engine, _, _, _ = service()
    todoist, notion = snapshots({"unknown": "x"}, {"unknown": "y"})
    plan = engine.plan(todoist, notion, correlation_id="corr")
    assert plan.blocking
    assert not plan.ordered_mutations
    assert plan.conflicts[0].conflict_type.value == "field_authority_violation"
    assert len(plan.conflicts[0].conflict_digest) == 64


def test_successful_apply_requires_attended_exact_plan_and_readback() -> None:
    engine, state, todoist_provider, notion_provider = service(
        todoist_objects={"task-1": {"responsibility": "old"}},
        notion_objects={"page-1": {"execution_priority": "P4"}},
    )
    todoist, notion = snapshots(
        {"execution_priority": "P1", "responsibility": "old"},
        {"execution_priority": "P4", "responsibility": "Lead network services"},
    )
    plan = engine.plan(todoist, notion, correlation_id="corr")
    result = engine.apply(plan, authorize(plan))
    assert result.consistent
    assert result.receipt.applied_count == 2
    assert result.receipt.verified_count == 2
    assert result.receipt.checkpoint_advanced
    assert notion_provider.objects["page-1"]["execution_priority"] == "P1"
    assert todoist_provider.objects["task-1"]["responsibility"] == "Lead network services"
    assert state.checkpoint != plan.expected_checkpoint
    assert len(result.receipt.receipt_digest) == 64


def test_unattended_and_wrong_scope_authorizations_are_rejected() -> None:
    engine, _, _, _ = service()
    plan = engine.plan(
        *snapshots({"execution_priority": "P1"}, {"execution_priority": "P4"}),
        correlation_id="corr",
    )
    with pytest.raises(PermissionError, match="attended"):
        engine.apply(plan, authorize(plan, attended=False))
    wrong_plan = authorize(plan).model_copy(update={"plan_digest": "0" * 64})
    with pytest.raises(PermissionError, match="exact reconciliation plan"):
        engine.apply(plan, wrong_plan)
    wrong_scope = authorize(plan).model_copy(update={"authorized_mutation_ids": ()})
    with pytest.raises(PermissionError, match="mutation scope"):
        engine.apply(plan, wrong_scope)


def test_blocking_conflict_and_stale_checkpoint_prevent_application() -> None:
    engine, state, _, _ = service()
    conflict_plan = engine.plan(
        *snapshots({"unknown": "a"}, {"unknown": "b"}), correlation_id="corr"
    )
    with pytest.raises(RuntimeError, match="blocking reconciliation conflicts"):
        engine.apply(conflict_plan, authorize(conflict_plan))
    valid_plan = engine.plan(
        *snapshots({"execution_priority": "P1"}, {"execution_priority": "P4"}),
        correlation_id="corr",
    )
    state.checkpoint = checkpoint("2026-07-25")
    with pytest.raises(RuntimeError, match="stale reconciliation checkpoint"):
        engine.apply(valid_plan, authorize(valid_plan))


def test_readback_mismatch_preserves_checkpoint_and_is_retryable() -> None:
    engine, state, _, notion_provider = service(
        notion_objects={"page-1": {"execution_priority": "P4"}}
    )
    plan = engine.plan(
        *snapshots({"execution_priority": "P1"}, {"execution_priority": "P4"}),
        correlation_id="corr",
    )
    mutation = plan.ordered_mutations[0]
    notion_provider.mismatch_after_write.add(mutation.mutation_id)
    failed = engine.apply(plan, authorize(plan))
    assert not failed.consistent
    assert not failed.receipt.checkpoint_advanced
    assert state.checkpoint == plan.expected_checkpoint
    assert mutation.idempotency_key in state.applied_keys
    notion_provider.mismatch_after_write.clear()
    recovered = engine.apply(plan, authorize(plan))
    assert recovered.consistent
    assert recovered.receipt.operation_results[0].status.value == "already_applied"


def test_provider_failure_before_write_preserves_checkpoint() -> None:
    engine, state, _, notion_provider = service(
        notion_objects={"page-1": {"execution_priority": "P4"}}
    )
    plan = engine.plan(
        *snapshots({"execution_priority": "P1"}, {"execution_priority": "P4"}),
        correlation_id="corr",
    )
    notion_provider.fail_before_write.add(plan.ordered_mutations[0].mutation_id)
    result = engine.apply(plan, authorize(plan))
    assert not result.consistent
    assert result.receipt.applied_count == 0
    assert state.checkpoint == plan.expected_checkpoint


def test_missing_provider_returns_fail_closed_receipt() -> None:
    state = InMemoryReconciliationState(checkpoint())
    engine = CanonicalReconciliationService(default_field_authority_registry(), (), state)
    plan = engine.plan(
        *snapshots({"execution_priority": "P1"}, {"execution_priority": "P4"}),
        correlation_id="corr",
    )
    result = engine.apply(plan, authorize(plan))
    assert not result.consistent
    assert result.receipt.operation_results[0].error == "provider unavailable: notion"


def test_plan_authorization_and_receipt_digests_reject_tampering() -> None:
    engine, _, _, _ = service()
    plan = engine.plan(
        *snapshots({"execution_priority": "P1"}, {"execution_priority": "P4"}),
        correlation_id="corr",
    )
    with pytest.raises(ValidationError, match="plan digest mismatch"):
        ReconciliationPlanV2(**{**plan.model_dump(), "plan_digest": "0" * 64})
    authorization = authorize(plan)
    with pytest.raises(ValidationError, match="authorization digest mismatch"):
        ReconciliationAuthorization(
            **{**authorization.model_dump(), "authorization_digest": "0" * 64}
        )
    success = engine.apply(plan, authorization).receipt
    with pytest.raises(ValidationError, match="receipt digest mismatch"):
        ReconciliationReceiptV2(**{**success.model_dump(), "receipt_digest": "0" * 64})
