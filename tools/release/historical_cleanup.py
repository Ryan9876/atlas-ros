"""Fail-closed execution model for exact historical cleanup transactions.

No live provider adapter is bundled here. The in-memory adapter exists only for
validation and deterministic simulation. A future provider adapter must satisfy
the same exact-operation, idempotency, readback, and receipt interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.contracts.history import (
    CleanupAction,
    CleanupAuthorization,
    HistoricalCleanupOperation,
    HistoricalCleanupPlan,
    HistoricalCleanupReceipt,
    HistoricalOperationResult,
    HistoricalReadbackResult,
)


class HistoricalCleanupExecutionError(ValueError):
    """Raised when an exact cleanup transaction cannot safely execute."""


class HistoricalCleanupStore(Protocol):
    """Minimum provider-neutral storage interface for cleanup transactions."""

    def read(self, item_id: str) -> tuple[str, str | None]:
        """Return observed state and digest for one exact item."""

    def apply(self, operation: HistoricalCleanupOperation) -> tuple[bool, str]:
        """Apply one operation and return changed plus resulting digest."""


@dataclass
class InMemoryHistoricalStore:
    """Deterministic validation fixture; never connects to a provider."""

    items: dict[str, tuple[str, str]]
    idempotency_results: dict[str, tuple[bool, str]] = field(default_factory=dict)

    def read(self, item_id: str) -> tuple[str, str | None]:
        value = self.items.get(item_id)
        if value is None:
            return ("deleted", None)
        return value

    def apply(self, operation: HistoricalCleanupOperation) -> tuple[bool, str]:
        prior = self.idempotency_results.get(operation.idempotency_key)
        if prior is not None:
            return (False, prior[1])
        current = self.items.get(operation.item_id)
        if current is None:
            if operation.action is CleanupAction.DELETE:
                result = (False, sha256_digest({"state": "deleted", "item": operation.item_id}))
                self.idempotency_results[operation.idempotency_key] = result
                return result
            raise HistoricalCleanupExecutionError(
                f"source item is missing: {operation.item_id}"
            )
        state, digest = current
        if digest != operation.expected_digest:
            raise HistoricalCleanupExecutionError(
                f"source digest changed before apply: {operation.item_id}"
            )
        if operation.action is CleanupAction.DELETE:
            del self.items[operation.item_id]
            result_digest = sha256_digest({"state": "deleted", "item": operation.item_id})
        elif operation.action is CleanupAction.ARCHIVE:
            self.items[operation.item_id] = ("archived", digest)
            result_digest = digest
        else:
            self.items[operation.item_id] = ("migrated", digest)
            result_digest = digest
        result = (state != self.items.get(operation.item_id, ("deleted", ""))[0], result_digest)
        self.idempotency_results[operation.idempotency_key] = result
        return result


def execute_cleanup(
    plan: HistoricalCleanupPlan,
    authorization: CleanupAuthorization,
    store: HistoricalCleanupStore,
    *,
    dry_run: bool,
) -> HistoricalCleanupReceipt:
    """Execute or simulate one exact cleanup plan with mandatory readback."""
    _validate_authorization(plan, authorization)
    operation_results: list[HistoricalOperationResult] = []
    readback_results: list[HistoricalReadbackResult] = []
    failures = 0

    for operation in plan.operations:
        if dry_run:
            operation_results.append(
                HistoricalOperationResult(
                    operation_id=operation.operation_id,
                    item_id=operation.item_id,
                    idempotency_key=operation.idempotency_key,
                    action=operation.action,
                    applied=False,
                    changed=False,
                    result_digest=sha256_digest(
                        {
                            "dry_run": True,
                            "operation": operation.model_dump(mode="json"),
                        }
                    ),
                )
            )
            state, digest = store.read(operation.item_id)
            verified = state != "unknown" and digest == operation.expected_digest
            readback_results.append(
                HistoricalReadbackResult(
                    operation_id=operation.operation_id,
                    item_id=operation.item_id,
                    observed_state=_state_value(state),
                    observed_digest=digest,
                    verified=verified,
                    error=None if verified else "dry-run source readback did not match inventory",
                )
            )
            if not verified:
                failures += 1
            continue

        try:
            changed, result_digest = store.apply(operation)
            operation_results.append(
                HistoricalOperationResult(
                    operation_id=operation.operation_id,
                    item_id=operation.item_id,
                    idempotency_key=operation.idempotency_key,
                    action=operation.action,
                    applied=True,
                    changed=changed,
                    result_digest=result_digest,
                )
            )
            state, observed_digest = store.read(operation.item_id)
            verified = _verify_readback(operation, state, observed_digest)
            readback_results.append(
                HistoricalReadbackResult(
                    operation_id=operation.operation_id,
                    item_id=operation.item_id,
                    observed_state=_state_value(state),
                    observed_digest=observed_digest,
                    verified=verified,
                    error=None if verified else "post-operation readback failed",
                )
            )
            if not verified:
                failures += 1
        except Exception as error:  # bounded item-level failure capture
            failures += 1
            error_text = str(error)
            operation_results.append(
                HistoricalOperationResult(
                    operation_id=operation.operation_id,
                    item_id=operation.item_id,
                    idempotency_key=operation.idempotency_key,
                    action=operation.action,
                    applied=False,
                    changed=False,
                    result_digest=sha256_digest(
                        {"operation_id": operation.operation_id, "error": error_text}
                    ),
                    error=error_text,
                )
            )
            state, observed_digest = store.read(operation.item_id)
            readback_results.append(
                HistoricalReadbackResult(
                    operation_id=operation.operation_id,
                    item_id=operation.item_id,
                    observed_state=_state_value(state),
                    observed_digest=observed_digest,
                    verified=False,
                    error=error_text,
                )
            )

    if dry_run:
        status = "simulated" if failures == 0 else "failed"
    elif not plan.operations:
        status = "failed"
    elif failures == 0:
        status = "completed"
    elif failures == len(plan.operations):
        status = "failed"
    else:
        status = "partial"
    writes = sum(item.changed for item in operation_results)
    destructive = sum(
        item.changed and item.action is CleanupAction.DELETE
        for item in operation_results
    )
    return HistoricalCleanupReceipt(
        transaction_id=plan.transaction_id,
        authorization_id=authorization.authorization_id,
        inventory_digest=plan.inventory_digest,
        plan_digest=plan.plan_digest,
        status=status,
        operation_results=tuple(operation_results),
        readback_results=tuple(readback_results),
        provider_writes=writes,
        destructive_actions=destructive,
    )


def _validate_authorization(
    plan: HistoricalCleanupPlan,
    authorization: CleanupAuthorization,
) -> None:
    if plan.blockers:
        raise HistoricalCleanupExecutionError(
            "cleanup plan has unresolved blockers: " + "; ".join(plan.blockers)
        )
    if authorization.transaction_id != plan.transaction_id:
        raise HistoricalCleanupExecutionError("authorization transaction does not match plan")
    if authorization.inventory_digest != plan.inventory_digest:
        raise HistoricalCleanupExecutionError("authorization inventory does not match plan")
    if authorization.plan_digest != plan.plan_digest:
        raise HistoricalCleanupExecutionError("authorization digest does not match plan")
    item_ids = tuple(operation.item_id for operation in plan.operations)
    if set(item_ids) != set(authorization.exact_item_ids):
        raise HistoricalCleanupExecutionError("authorization item set does not match plan")
    actions = {operation.action for operation in plan.operations}
    if not actions.issubset(set(authorization.allowed_actions)):
        raise HistoricalCleanupExecutionError("authorization action set does not cover plan")
    if len(plan.operations) > authorization.object_budget:
        raise HistoricalCleanupExecutionError("cleanup object budget would be exceeded")
    if sum(operation.size_bytes for operation in plan.operations) > authorization.byte_budget:
        raise HistoricalCleanupExecutionError("cleanup byte budget would be exceeded")
    if CleanupAction.DELETE in actions and not authorization.destructive_actions_authorized:
        raise HistoricalCleanupExecutionError("delete operations require destructive authorization")


def _verify_readback(
    operation: HistoricalCleanupOperation,
    state: str,
    digest: str | None,
) -> bool:
    if operation.action is CleanupAction.DELETE:
        return state == "deleted" and digest is None
    if operation.action is CleanupAction.ARCHIVE:
        return state == "archived" and digest == operation.expected_digest
    return state == "migrated" and digest == operation.expected_digest


def _state_value(
    state: str,
) -> Literal["present", "archived", "migrated", "deleted", "unknown"]:
    if state in {"present", "archived", "migrated", "deleted", "unknown"}:
        return state
    return "unknown"
