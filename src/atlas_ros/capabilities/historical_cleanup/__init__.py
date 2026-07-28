"""Provider-free planning for governed historical cleanup transactions."""

from __future__ import annotations

from dataclasses import dataclass

from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.contracts.history import (
    CleanupAction,
    HistoricalCleanupOperation,
    HistoricalCleanupPlan,
    HistoricalInventory,
    RetentionClassification,
)

CAPABILITY_ID = "atlas.historical-cleanup-planning"


class HistoricalCleanupPlanningError(ValueError):
    """Raised when cleanup planning cannot preserve retention and rollback rules."""


@dataclass(frozen=True, slots=True)
class HistoricalCleanupPlanner:
    """Compile a deterministic cleanup plan without authorizing or executing it."""

    def plan(
        self,
        inventory: HistoricalInventory,
        *,
        transaction_id: str,
        include_actions: tuple[CleanupAction, ...] = (
            CleanupAction.MIGRATE,
            CleanupAction.ARCHIVE,
            CleanupAction.DELETE,
        ),
    ) -> HistoricalCleanupPlan:
        if not transaction_id.strip():
            raise HistoricalCleanupPlanningError("an exact cleanup transaction ID is required")
        if len(set(include_actions)) != len(include_actions):
            raise HistoricalCleanupPlanningError("included cleanup actions must be unique")

        operations: list[HistoricalCleanupOperation] = []
        blockers: list[str] = []
        for item in sorted(inventory.items, key=lambda value: value.item_id):
            action = _action_for(item.classification)
            if action is None:
                if item.classification is RetentionClassification.UNCERTAIN:
                    blockers.append(
                        f"{item.item_id}: human retention decision required: "
                        + "; ".join(item.uncertainty_reasons)
                    )
                continue
            if action not in include_actions:
                blockers.append(f"{item.item_id}: {action.value} is outside requested plan scope")
                continue
            if any(
                dependency.active_release_required or dependency.rollback_release_required
                for dependency in item.dependencies
            ):
                blockers.append(
                    f"{item.item_id}: active or rollback dependency prevents cleanup"
                )
                continue
            operation_payload = {
                "transaction_id": transaction_id,
                "item_id": item.item_id,
                "action": action.value,
                "source_location": item.source_location,
                "destination_location": item.destination_location,
                "expected_digest": item.immutable_digest,
            }
            operations.append(
                HistoricalCleanupOperation(
                    operation_id=(
                        "history-" + sha256_digest(operation_payload)[:24]
                    ),
                    sequence=len(operations),
                    item_id=item.item_id,
                    action=action,
                    source_location=item.source_location,
                    destination_location=item.destination_location,
                    expected_digest=item.immutable_digest,
                    size_bytes=item.size_bytes,
                    idempotency_key=(
                        f"{transaction_id}:{item.item_id}:{item.immutable_digest}:{action.value}"
                    ),
                )
            )
        return HistoricalCleanupPlan.create(
            transaction_id=transaction_id,
            inventory_digest=inventory.inventory_digest,
            operations=tuple(operations),
            blockers=tuple(blockers),
        )


def _action_for(classification: RetentionClassification) -> CleanupAction | None:
    if classification is RetentionClassification.MIGRATE_BEFORE_RETIREMENT:
        return CleanupAction.MIGRATE
    if classification is RetentionClassification.ARCHIVE_OUTSIDE_ACTIVE_SURFACE:
        return CleanupAction.ARCHIVE
    if classification is RetentionClassification.ELIGIBLE_FOR_DELETION:
        return CleanupAction.DELETE
    return None
