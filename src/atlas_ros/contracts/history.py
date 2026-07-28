"""Typed contracts for governed historical retention and cleanup transactions."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from atlas_ros.contracts.digests import sha256_digest


class RetentionClassification(StrEnum):
    """Required fail-closed disposition classes for historical items."""

    PRESERVE_PERMANENTLY = "preserve_permanently"
    PRESERVE_FOR_ROLLBACK = "preserve_for_rollback"
    PRESERVE_FOR_AUDIT = "preserve_for_audit"
    PRESERVE_FOR_GOVERNANCE = "preserve_for_governance"
    PRESERVE_FOR_LEGAL_OR_SECURITY = "preserve_for_legal_or_security"
    MIGRATE_BEFORE_RETIREMENT = "migrate_before_retirement"
    ARCHIVE_OUTSIDE_ACTIVE_SURFACE = "archive_outside_active_surface"
    ELIGIBLE_FOR_DELETION = "eligible_for_deletion"
    UNCERTAIN = "uncertain_human_decision_required"


class CleanupAction(StrEnum):
    """Provider-neutral operations supported by the cleanup transaction model."""

    MIGRATE = "migrate"
    ARCHIVE = "archive"
    DELETE = "delete"


class DependencyRelationship(BaseModel):
    """One identity-bound dependency on a historical item."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    related_item_id: str = Field(min_length=1, max_length=512)
    relationship: str = Field(min_length=1, max_length=128)
    active_release_required: bool = False
    rollback_release_required: bool = False


class HistoricalItem(BaseModel):
    """Immutable item-level inventory record used for retention decisions."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_id: Literal["atlas.historical-item"] = "atlas.historical-item"
    schema_version: Literal["1.0"] = "1.0"
    item_id: str = Field(min_length=1, max_length=512)
    source_system: str = Field(min_length=1, max_length=128)
    source_location: str = Field(min_length=1, max_length=2048)
    immutable_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)
    release_family: str = Field(min_length=1, max_length=64)
    classification: RetentionClassification
    exclusion_reasons: tuple[str, ...] = ()
    dependencies: tuple[DependencyRelationship, ...] = ()
    legal_relevance: bool = False
    security_relevance: bool = False
    audit_relevance: bool = False
    governance_relevance: bool = False
    rollback_relevance: bool = False
    destination_location: str | None = Field(default=None, max_length=2048)
    uncertainty_reasons: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_retention(self) -> HistoricalItem:
        if len(set(self.exclusion_reasons)) != len(self.exclusion_reasons):
            raise ValueError("historical item contains duplicate exclusion reasons")
        if len(set(self.uncertainty_reasons)) != len(self.uncertainty_reasons):
            raise ValueError("historical item contains duplicate uncertainty reasons")
        if self.classification is RetentionClassification.UNCERTAIN:
            if not self.uncertainty_reasons:
                raise ValueError("uncertain historical item requires a human-decision reason")
            return self
        if self.uncertainty_reasons:
            raise ValueError("resolved historical item cannot retain uncertainty reasons")
        if (
            self.classification is RetentionClassification.MIGRATE_BEFORE_RETIREMENT
            and not self.destination_location
        ):
            raise ValueError("migration classification requires an exact destination")
        if (
            self.classification is RetentionClassification.ARCHIVE_OUTSIDE_ACTIVE_SURFACE
            and not self.destination_location
        ):
            raise ValueError("archive classification requires an exact destination")
        if self.classification is RetentionClassification.ELIGIBLE_FOR_DELETION:
            if any(
                (
                    self.legal_relevance,
                    self.security_relevance,
                    self.audit_relevance,
                    self.governance_relevance,
                    self.rollback_relevance,
                )
            ):
                raise ValueError("deletion-eligible item cannot carry retention relevance")
            if any(
                dependency.active_release_required or dependency.rollback_release_required
                for dependency in self.dependencies
            ):
                raise ValueError(
                    "deletion-eligible item cannot be required by active or rollback releases"
                )
        return self


class HistoricalInventory(BaseModel):
    """Digest-bound item inventory that destructive plans must reference exactly."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_id: Literal["atlas.historical-inventory"] = "atlas.historical-inventory"
    schema_version: Literal["1.0"] = "1.0"
    inventory_id: str = Field(min_length=1, max_length=256)
    items: tuple[HistoricalItem, ...] = Field(min_length=1)
    inventory_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def create(
        cls,
        *,
        inventory_id: str,
        items: tuple[HistoricalItem, ...],
        created_at: datetime | None = None,
    ) -> HistoricalInventory:
        values: dict[str, object] = {
            "inventory_id": inventory_id,
            "items": items,
            "inventory_digest": sha256_digest(_inventory_payload(items)),
        }
        if created_at is not None:
            values["created_at"] = created_at
        return cls.model_validate(values)

    @model_validator(mode="after")
    def validate_inventory(self) -> HistoricalInventory:
        item_ids = tuple(item.item_id for item in self.items)
        if len(set(item_ids)) != len(item_ids):
            raise ValueError("historical inventory contains duplicate item IDs")
        if sha256_digest(_inventory_payload(self.items)) != self.inventory_digest:
            raise ValueError("historical inventory digest does not match items")
        return self

    @property
    def total_bytes(self) -> int:
        return sum(item.size_bytes for item in self.items)


class HistoricalCleanupOperation(BaseModel):
    """One exact provider-neutral operation produced by cleanup planning."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    operation_id: str = Field(min_length=1, max_length=256)
    sequence: int = Field(ge=0)
    item_id: str = Field(min_length=1, max_length=512)
    action: CleanupAction
    source_location: str = Field(min_length=1, max_length=2048)
    destination_location: str | None = Field(default=None, max_length=2048)
    expected_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)
    idempotency_key: str = Field(min_length=1, max_length=512)

    @model_validator(mode="after")
    def validate_destination(self) -> HistoricalCleanupOperation:
        if (
            self.action in {CleanupAction.MIGRATE, CleanupAction.ARCHIVE}
            and not self.destination_location
        ):
            raise ValueError("migrate and archive operations require a destination")
        if self.action is CleanupAction.DELETE and self.destination_location is not None:
            raise ValueError("delete operations cannot declare a destination")
        return self


class HistoricalCleanupPlan(BaseModel):
    """Digest-bound cleanup plan that does not itself grant authorization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_id: Literal["atlas.historical-cleanup-plan"] = (
        "atlas.historical-cleanup-plan"
    )
    schema_version: Literal["1.0"] = "1.0"
    transaction_id: str = Field(min_length=1, max_length=256)
    inventory_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    operations: tuple[HistoricalCleanupOperation, ...] = ()
    blockers: tuple[str, ...] = ()
    plan_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(
        cls,
        *,
        transaction_id: str,
        inventory_digest: str,
        operations: tuple[HistoricalCleanupOperation, ...] = (),
        blockers: tuple[str, ...] = (),
    ) -> HistoricalCleanupPlan:
        return cls(
            transaction_id=transaction_id,
            inventory_digest=inventory_digest,
            operations=operations,
            blockers=blockers,
            plan_digest=sha256_digest(_plan_payload(operations, blockers)),
        )

    @model_validator(mode="after")
    def validate_plan(self) -> HistoricalCleanupPlan:
        if not self.operations and not self.blockers:
            raise ValueError("cleanup plan requires operations or blockers")
        sequences = tuple(operation.sequence for operation in self.operations)
        if sequences != tuple(range(len(self.operations))):
            raise ValueError("cleanup operations must use contiguous canonical sequence")
        item_ids = tuple(operation.item_id for operation in self.operations)
        if len(set(item_ids)) != len(item_ids):
            raise ValueError("cleanup plan contains duplicate item operations")
        keys = tuple(operation.idempotency_key for operation in self.operations)
        if len(set(keys)) != len(keys):
            raise ValueError("cleanup plan contains duplicate idempotency keys")
        if len(set(self.blockers)) != len(self.blockers):
            raise ValueError("cleanup plan contains duplicate blockers")
        if sha256_digest(_plan_payload(self.operations, self.blockers)) != self.plan_digest:
            raise ValueError("cleanup plan digest does not match operations and blockers")
        return self


class CleanupAuthorization(BaseModel):
    """Exact attended authorization for one historical cleanup transaction."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    authorization_id: str = Field(min_length=1, max_length=256)
    transaction_id: str = Field(min_length=1, max_length=256)
    inventory_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    plan_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    exact_item_ids: tuple[str, ...] = Field(min_length=1)
    allowed_actions: tuple[CleanupAction, ...] = Field(min_length=1)
    object_budget: int = Field(gt=0)
    byte_budget: int = Field(ge=0)
    destructive_actions_authorized: bool = False
    authorized_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_authorization(self) -> CleanupAuthorization:
        if len(set(self.exact_item_ids)) != len(self.exact_item_ids):
            raise ValueError("authorization contains duplicate item IDs")
        if len(set(self.allowed_actions)) != len(self.allowed_actions):
            raise ValueError("authorization contains duplicate actions")
        if CleanupAction.DELETE in self.allowed_actions and not self.destructive_actions_authorized:
            raise ValueError("delete authorization must explicitly allow destructive actions")
        return self


class HistoricalOperationResult(BaseModel):
    """Write-side result for one historical cleanup operation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    operation_id: str
    item_id: str
    idempotency_key: str
    action: CleanupAction
    applied: bool
    changed: bool
    result_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    error: str | None = None


class HistoricalReadbackResult(BaseModel):
    """Independent post-operation readback for one item."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    operation_id: str
    item_id: str
    observed_state: Literal["present", "archived", "migrated", "deleted", "unknown"]
    observed_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    verified: bool
    error: str | None = None


class HistoricalCleanupReceipt(BaseModel):
    """Complete item-level cleanup transaction receipt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_id: Literal["atlas.historical-cleanup-receipt"] = (
        "atlas.historical-cleanup-receipt"
    )
    schema_version: Literal["1.0"] = "1.0"
    transaction_id: str
    authorization_id: str
    inventory_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    plan_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: Literal["simulated", "completed", "partial", "failed"]
    operation_results: tuple[HistoricalOperationResult, ...]
    readback_results: tuple[HistoricalReadbackResult, ...]
    provider_writes: int = Field(ge=0)
    destructive_actions: int = Field(ge=0)
    completed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_receipt(self) -> HistoricalCleanupReceipt:
        result_ids = tuple(item.operation_id for item in self.operation_results)
        readback_ids = tuple(item.operation_id for item in self.readback_results)
        if len(set(result_ids)) != len(result_ids):
            raise ValueError("cleanup receipt contains duplicate operation results")
        if len(set(readback_ids)) != len(readback_ids):
            raise ValueError("cleanup receipt contains duplicate readback results")
        if set(result_ids) != set(readback_ids):
            raise ValueError("cleanup receipt write and readback operation sets disagree")
        changed = sum(result.changed for result in self.operation_results)
        if self.provider_writes != changed:
            raise ValueError("provider write count does not match operation results")
        destructive = sum(
            result.changed and result.action is CleanupAction.DELETE
            for result in self.operation_results
        )
        if self.destructive_actions != destructive:
            raise ValueError("destructive count does not match delete operation results")
        return self


def _inventory_payload(items: tuple[HistoricalItem, ...]) -> list[dict[str, object]]:
    return [item.model_dump(mode="json") for item in items]


def _plan_payload(
    operations: tuple[HistoricalCleanupOperation, ...],
    blockers: tuple[str, ...],
) -> dict[str, object]:
    return {
        "operations": [operation.model_dump(mode="json") for operation in operations],
        "blockers": list(blockers),
    }
