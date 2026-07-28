from __future__ import annotations

from datetime import UTC, datetime

import pytest

from atlas_ros.capabilities.historical_cleanup import HistoricalCleanupPlanner
from atlas_ros.contracts.history import (
    CleanupAction,
    CleanupAuthorization,
    HistoricalInventory,
    HistoricalItem,
    RetentionClassification,
)
from tools.release.historical_cleanup import (
    HistoricalCleanupExecutionError,
    InMemoryHistoricalStore,
    execute_cleanup,
)


def item(
    item_id: str,
    classification: RetentionClassification,
    *,
    destination: str | None = None,
    digest: str = "a" * 64,
    uncertainty: tuple[str, ...] = (),
) -> HistoricalItem:
    return HistoricalItem(
        item_id=item_id,
        source_system="Notion",
        source_location=f"notion://{item_id}",
        immutable_digest=digest,
        size_bytes=100,
        release_family="pre-v6",
        classification=classification,
        destination_location=destination,
        uncertainty_reasons=uncertainty,
    )


def inventory(*items: HistoricalItem) -> HistoricalInventory:
    return HistoricalInventory.create(
        inventory_id="history-2026-07-28",
        items=items,
        created_at=datetime(2026, 7, 28, tzinfo=UTC),
    )


def authorization(plan, *, destructive: bool = True) -> CleanupAuthorization:
    return CleanupAuthorization(
        authorization_id="ryan-history-cleanup-001",
        transaction_id=plan.transaction_id,
        inventory_digest=plan.inventory_digest,
        plan_digest=plan.plan_digest,
        exact_item_ids=tuple(operation.item_id for operation in plan.operations),
        allowed_actions=tuple(operation.action for operation in plan.operations),
        object_budget=len(plan.operations),
        byte_budget=sum(operation.size_bytes for operation in plan.operations),
        destructive_actions_authorized=destructive,
        authorized_at=datetime(2026, 7, 28, tzinfo=UTC),
    )


def test_planner_is_item_level_deterministic_and_fail_closed() -> None:
    source = inventory(
        item(
            "migrate",
            RetentionClassification.MIGRATE_BEFORE_RETIREMENT,
            destination="github://archive/migrate",
            digest="a" * 64,
        ),
        item(
            "archive",
            RetentionClassification.ARCHIVE_OUTSIDE_ACTIVE_SURFACE,
            destination="notion://archive/archive",
            digest="b" * 64,
        ),
        item("delete", RetentionClassification.ELIGIBLE_FOR_DELETION, digest="c" * 64),
        item(
            "uncertain",
            RetentionClassification.UNCERTAIN,
            uncertainty=("legal retention owner has not decided",),
            digest="d" * 64,
        ),
    )

    first = HistoricalCleanupPlanner().plan(source, transaction_id="cleanup-001")
    second = HistoricalCleanupPlanner().plan(source, transaction_id="cleanup-001")

    assert first == second
    assert tuple(operation.action for operation in first.operations) == (
        CleanupAction.ARCHIVE,
        CleanupAction.DELETE,
        CleanupAction.MIGRATE,
    )
    assert first.blockers == (
        "uncertain: human retention decision required: legal retention owner has not decided",
    )


def test_execution_requires_blocker_free_exact_authorization() -> None:
    source = inventory(
        item(
            "archive",
            RetentionClassification.ARCHIVE_OUTSIDE_ACTIVE_SURFACE,
            destination="notion://archive/archive",
        ),
        item(
            "uncertain",
            RetentionClassification.UNCERTAIN,
            uncertainty=("audit owner decision required",),
            digest="b" * 64,
        ),
    )
    plan = HistoricalCleanupPlanner().plan(source, transaction_id="cleanup-002")
    store = InMemoryHistoricalStore(items={"archive": ("present", "a" * 64)})

    with pytest.raises(HistoricalCleanupExecutionError, match="unresolved blockers"):
        execute_cleanup(plan, authorization(plan), store, dry_run=True)


def test_dry_run_and_exact_execution_are_readback_verified_and_idempotent() -> None:
    source = inventory(
        item(
            "archive",
            RetentionClassification.ARCHIVE_OUTSIDE_ACTIVE_SURFACE,
            destination="notion://archive/archive",
            digest="a" * 64,
        ),
        item("delete", RetentionClassification.ELIGIBLE_FOR_DELETION, digest="b" * 64),
        item(
            "migrate",
            RetentionClassification.MIGRATE_BEFORE_RETIREMENT,
            destination="github://archive/migrate",
            digest="c" * 64,
        ),
    )
    plan = HistoricalCleanupPlanner().plan(source, transaction_id="cleanup-003")
    auth = authorization(plan)
    store = InMemoryHistoricalStore(
        items={
            "archive": ("present", "a" * 64),
            "delete": ("present", "b" * 64),
            "migrate": ("present", "c" * 64),
        }
    )

    simulated = execute_cleanup(plan, auth, store, dry_run=True)
    assert simulated.status == "simulated"
    assert simulated.provider_writes == 0
    assert simulated.destructive_actions == 0

    receipt = execute_cleanup(plan, auth, store, dry_run=False)
    assert receipt.status == "completed"
    assert receipt.provider_writes == 3
    assert receipt.destructive_actions == 1
    assert all(result.verified for result in receipt.readback_results)

    replay = execute_cleanup(plan, auth, store, dry_run=False)
    assert replay.status == "completed"
    assert replay.provider_writes == 0
    assert replay.destructive_actions == 0


def test_deletion_eligibility_rejects_retention_relevance() -> None:
    with pytest.raises(ValueError, match="retention relevance"):
        HistoricalItem(
            item_id="protected",
            source_system="Notion",
            source_location="notion://protected",
            immutable_digest="f" * 64,
            size_bytes=1,
            release_family="v6",
            classification=RetentionClassification.ELIGIBLE_FOR_DELETION,
            audit_relevance=True,
        )
