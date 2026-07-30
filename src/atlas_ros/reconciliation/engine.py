from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from atlas_ros.contracts import deterministic_digest
from atlas_ros.contracts.reconciliation_v2 import (
    AuthoritySource,
    CheckpointToken,
    ConflictType,
    FieldAuthorityRegistry,
    OperationStatus,
    ReconciliationAuthorization,
    ReconciliationConflict,
    ReconciliationMutationV2,
    ReconciliationOperationResult,
    ReconciliationPlanV2,
    ReconciliationReceiptV2,
    ReconciliationResultV2,
    ReconciliationSnapshot,
    UpdateDirection,
)


class ReconciliationProviderPort(Protocol):
    provider: AuthoritySource

    def apply(self, mutation: ReconciliationMutationV2) -> None: ...

    def readback(self, mutation: ReconciliationMutationV2) -> Any: ...


@dataclass(init=False)
class InMemoryReconciliationState:
    """Checkpoint plus keys for provider writes that returned successfully.

    A successful provider return is recorded before readback. A later mismatch or
    readback exception does not prove that the write failed, so the key remains and
    any retry must read back before issuing another provider write. ``applied_keys``
    remains as a compatibility alias for previously serialized or test-facing state.
    """

    checkpoint: CheckpointToken
    successful_write_keys: set[str] = field(default_factory=set)

    def __init__(
        self,
        checkpoint: CheckpointToken,
        successful_write_keys: set[str] | None = None,
        *,
        applied_keys: set[str] | None = None,
    ) -> None:
        if successful_write_keys is not None and applied_keys is not None:
            raise ValueError("provide only successful_write_keys or legacy applied_keys")
        self.checkpoint = checkpoint
        self.successful_write_keys = set(successful_write_keys or applied_keys or ())

    @property
    def applied_keys(self) -> set[str]:
        """Compatibility alias; use successful_write_keys in new code."""
        return self.successful_write_keys

    @applied_keys.setter
    def applied_keys(self, value: set[str]) -> None:
        self.successful_write_keys = value


@dataclass
class InMemoryReconciliationProvider:
    provider: AuthoritySource
    objects: dict[str, dict[str, Any]] = field(default_factory=dict)
    fail_before_write: set[str] = field(default_factory=set)
    mismatch_after_write: set[str] = field(default_factory=set)
    raise_during_readback: set[str] = field(default_factory=set)
    apply_calls: dict[str, int] = field(default_factory=dict)

    def apply(self, mutation: ReconciliationMutationV2) -> None:
        self.apply_calls[mutation.mutation_id] = self.apply_calls.get(mutation.mutation_id, 0) + 1
        if mutation.mutation_id in self.fail_before_write:
            raise RuntimeError("provider operation failed before write")
        self.objects.setdefault(mutation.object_id, {})[mutation.field] = mutation.desired_value

    def readback(self, mutation: ReconciliationMutationV2) -> Any:
        if mutation.mutation_id in self.raise_during_readback:
            raise RuntimeError("provider readback failed")
        if mutation.mutation_id in self.mismatch_after_write:
            return {"mismatch": True}
        return self.objects.get(mutation.object_id, {}).get(mutation.field)


def _normalize(value: Any, kind: str) -> Any:
    if kind == "text":
        return "" if value is None else str(value).strip()
    if kind == "boolean":
        return bool(value)
    if kind == "priority":
        text = str(value).upper().strip()
        return text if text in {"P1", "P2", "P3", "P4"} else value
    if kind == "date" and isinstance(value, str):
        return value.replace("Z", "+00:00")
    return value


class CanonicalReconciliationService:
    """Provider-neutral deterministic planning and fail-closed application."""

    def __init__(
        self,
        registry: FieldAuthorityRegistry,
        providers: tuple[ReconciliationProviderPort, ...],
        state: InMemoryReconciliationState,
    ) -> None:
        self.registry = registry
        self.providers = {provider.provider: provider for provider in providers}
        self.state = state

    def plan(
        self,
        todoist: ReconciliationSnapshot,
        notion: ReconciliationSnapshot,
        *,
        correlation_id: str,
    ) -> ReconciliationPlanV2:
        snapshot_payload = {
            "todoist": todoist.snapshot_digest,
            "notion": notion.snapshot_digest,
            "policy": self.registry.policy_digest,
            "checkpoint": self.state.checkpoint.integrity_digest,
        }
        plan_id = f"recon-plan-{deterministic_digest(snapshot_payload)[:32]}"
        mutations: list[ReconciliationMutationV2] = []
        conflicts: list[ReconciliationConflict] = []
        fields = sorted(set(todoist.values) | set(notion.values))
        for field_name in fields:
            try:
                rule = self.registry.rule_for(field_name)
            except KeyError:
                conflicts.append(
                    ReconciliationConflict(
                        conflict_id=f"conflict-{deterministic_digest((plan_id, field_name))[:32]}",
                        plan_id=plan_id,
                        object_id=notion.object_id,
                        field_or_command=field_name,
                        source_value=todoist.values.get(field_name),
                        target_value=notion.values.get(field_name),
                        conflict_type=ConflictType.FIELD_AUTHORITY_VIOLATION,
                        suggested_resolution="Add an explicit authority rule or remove the field.",
                        evidence=("unknown-field",),
                    )
                )
                continue
            if rule.direction is UpdateDirection.DERIVE_ONLY:
                continue
            source = todoist if rule.authority is AuthoritySource.TODOIST else notion
            target = notion if rule.authority is AuthoritySource.TODOIST else todoist
            source_value = _normalize(source.values.get(field_name), rule.normalization)
            target_value = _normalize(target.values.get(field_name), rule.normalization)
            if source_value == target_value:
                continue
            provider = target.provider
            payload = {
                "plan": plan_id,
                "provider": provider,
                "object": target.object_id,
                "field": field_name,
                "desired": source_value,
                "policy": self.registry.policy_digest,
            }
            digest = deterministic_digest(payload)
            mutations.append(
                ReconciliationMutationV2(
                    mutation_id=f"recon-mutation-{digest[:32]}",
                    provider=provider,
                    object_id=target.object_id,
                    field=field_name,
                    expected_value=target_value,
                    desired_value=source_value,
                    authority=rule.authority,
                    readback_required=rule.readback_required,
                    idempotency_key=f"reconciliation:{digest}",
                )
            )
        return ReconciliationPlanV2(
            plan_id=plan_id,
            correlation_id=correlation_id,
            authority_policy_version=self.registry.policy_version,
            authority_policy_digest=self.registry.policy_digest,
            source_snapshots=(todoist, notion),
            target_snapshots=(notion, todoist),
            ordered_mutations=tuple(mutations),
            conflicts=tuple(conflicts),
            required_human_decisions=tuple(
                conflict.suggested_resolution for conflict in conflicts
            ),
            expected_checkpoint=self.state.checkpoint,
        )

    def apply(
        self,
        plan: ReconciliationPlanV2,
        authorization: ReconciliationAuthorization,
    ) -> ReconciliationResultV2:
        if not authorization.attended:
            raise PermissionError("reconciliation requires attended authorization")
        if authorization.plan_id != plan.plan_id or authorization.plan_digest != plan.plan_digest:
            raise PermissionError("authorization is not bound to the exact reconciliation plan")
        expected_ids = tuple(mutation.mutation_id for mutation in plan.ordered_mutations)
        if tuple(authorization.authorized_mutation_ids) != expected_ids:
            raise PermissionError("authorization mutation scope mismatch")
        if self.state.checkpoint != plan.expected_checkpoint:
            raise RuntimeError("stale reconciliation checkpoint")
        if plan.blocking:
            raise RuntimeError("blocking reconciliation conflicts prevent application")

        before = self.state.checkpoint
        results: list[ReconciliationOperationResult] = []
        try:
            for mutation in plan.ordered_mutations:
                provider = self.providers.get(mutation.provider)
                if provider is None:
                    raise RuntimeError(f"provider unavailable: {mutation.provider}")
                write_succeeded = mutation.idempotency_key in self.state.successful_write_keys
                if not write_succeeded:
                    provider.apply(mutation)
                    # Record only after provider apply returns. Do not remove this key if
                    # readback later fails: the external write may have succeeded.
                    self.state.successful_write_keys.add(mutation.idempotency_key)
                actual = provider.readback(mutation)
                verified = actual == mutation.desired_value
                results.append(
                    ReconciliationOperationResult(
                        mutation_id=mutation.mutation_id,
                        provider=mutation.provider,
                        object_id=mutation.object_id,
                        status=(
                            OperationStatus.ALREADY_APPLIED
                            if write_succeeded and verified
                            else OperationStatus.APPLIED
                            if verified
                            else OperationStatus.READBACK_MISMATCH
                        ),
                        expected_value=mutation.desired_value,
                        actual_value=actual,
                        verified=verified,
                        error="" if verified else "provider readback mismatch",
                    )
                )
                if not verified:
                    raise RuntimeError("provider readback mismatch")
            next_cursor = max(
                (snapshot.captured_at for snapshot in plan.source_snapshots),
                default=datetime.now(UTC),
            ).isoformat()
            resulting = CheckpointToken(
                cursor=next_cursor,
                applied_event_ids=tuple(sorted(self.state.successful_write_keys)),
            )
            self.state.checkpoint = resulting
            receipt_digest = deterministic_digest(
                (plan.plan_digest, authorization.authorization_digest)
            )
            receipt = ReconciliationReceiptV2(
                receipt_id=f"recon-receipt-{receipt_digest[:32]}",
                plan_id=plan.plan_id,
                plan_digest=plan.plan_digest,
                authorization_id=authorization.authorization_id,
                authorization_digest=authorization.authorization_digest,
                correlation_id=plan.correlation_id,
                authority_policy_version=plan.authority_policy_version,
                source_checkpoint=before,
                resulting_checkpoint=resulting,
                planned_count=len(plan.ordered_mutations),
                applied_count=len(plan.ordered_mutations),
                verified_count=len(plan.ordered_mutations),
                conflict_count=0,
                ignored_count=len(plan.ignored_items),
                operation_results=tuple(results),
                checkpoint_advanced=True,
                consistent=True,
            )
            return ReconciliationResultV2(plan=plan, receipt=receipt)
        except Exception as exc:
            # Preserve the prior checkpoint until every write is verified. Successful
            # write keys remain so retry performs readback before any duplicate apply.
            self.state.checkpoint = before
            if not results or results[-1].verified:
                results.append(
                    ReconciliationOperationResult(
                        mutation_id=(
                            plan.ordered_mutations[len(results)].mutation_id
                            if len(results) < len(plan.ordered_mutations)
                            else "application"
                        ),
                        provider=(
                            plan.ordered_mutations[len(results)].provider
                            if len(results) < len(plan.ordered_mutations)
                            else AuthoritySource.DERIVED
                        ),
                        object_id=(
                            plan.ordered_mutations[len(results)].object_id
                            if len(results) < len(plan.ordered_mutations)
                            else "reconciliation"
                        ),
                        status=OperationStatus.FAILED,
                        verified=False,
                        error=str(exc),
                    )
                )
            receipt = ReconciliationReceiptV2(
                receipt_id=(
                    f"recon-receipt-{deterministic_digest((plan.plan_digest, str(exc)))[:32]}"
                ),
                plan_id=plan.plan_id,
                plan_digest=plan.plan_digest,
                authorization_id=authorization.authorization_id,
                authorization_digest=authorization.authorization_digest,
                correlation_id=plan.correlation_id,
                authority_policy_version=plan.authority_policy_version,
                source_checkpoint=before,
                resulting_checkpoint=before,
                planned_count=len(plan.ordered_mutations),
                applied_count=sum(
                    result.status in {OperationStatus.APPLIED, OperationStatus.ALREADY_APPLIED}
                    for result in results
                ),
                verified_count=sum(result.verified for result in results),
                conflict_count=len(plan.conflicts),
                ignored_count=len(plan.ignored_items),
                operation_results=tuple(results),
                checkpoint_advanced=False,
                recovery_instructions=(
                    "Read provider state before retrying from the preserved checkpoint.",
                ),
                consistent=False,
            )
            return ReconciliationResultV2(plan=plan, receipt=receipt)
