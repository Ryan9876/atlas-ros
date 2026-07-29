"""Provider-write-free compatibility adapters and migration proposals for v7.6.0."""
from __future__ import annotations

from enum import StrEnum
from typing import Literal, Protocol

from pydantic import Field

from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.intent_memory_v760 import (
    EvidenceSourceKind,
    FreshnessState,
    GovernedIntentEvidenceV1,
    IntentContextKeyV1,
    IntentScopeV1,
    StrictContract,
)


class V750EvidenceLike(Protocol):
    evidence_id: str
    context_key: str
    interpretation: str
    confirmed: bool
    corrected_by_user: bool
    stale: bool
    contradictory: bool


class V752EventLike(Protocol):
    operation_id: str
    correlation_id: str
    initial_decision_digest: str
    user_response: str | None
    final_confirmed_interpretation: str | None


class MigrationDisposition(StrEnum):
    CREATE = "create"
    SKIP = "skip"


class SourceEvidenceRecordV1(StrictContract):
    source_system: str = Field(min_length=1)
    source_record_id: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    source_reference: str = Field(min_length=1)
    source_digest: str = Field(min_length=64, max_length=64)
    attributable: bool
    confirmed: bool
    interpretation: str | None = None
    occurred_at: str | None = None
    context: IntentContextKeyV1 | None = None
    stale: bool = False
    contradictory: bool = False
    retired: bool = False
    speculative: bool = False


class IntentMigrationItemV1(StrictContract):
    source_system: str
    source_record_id: str
    source_digest: str = Field(min_length=64, max_length=64)
    disposition: MigrationDisposition
    reason: str
    proposed_evidence: GovernedIntentEvidenceV1 | None = None

    @property
    def deterministic_digest(self) -> str:
        return sha256_digest(self.model_dump(mode="json"))


class IntentMigrationProposalV1(StrictContract):
    schema_version: str = "1.0"
    proposal_id: str
    input_snapshot_digest: str = Field(min_length=64, max_length=64)
    source_data_sources: tuple[str, ...]
    destination_target_keys: tuple[str, ...]
    existing_destination_evidence_ids: tuple[str, ...]
    items: tuple[IntentMigrationItemV1, ...]
    create_count: int = Field(ge=0)
    update_count: int = Field(ge=0)
    skip_count: int = Field(ge=0)
    provider_write_count: Literal[0] = 0
    todoist_write_count: Literal[0] = 0
    idempotent: Literal[True] = True

    @property
    def proposed_output_digest(self) -> str:
        return sha256_digest(
            {
                "created": [
                    item.proposed_evidence.model_dump(mode="json")
                    for item in self.items
                    if item.disposition is MigrationDisposition.CREATE and item.proposed_evidence
                ],
                "existing": self.existing_destination_evidence_ids,
            }
        )

    @property
    def deterministic_digest(self) -> str:
        return sha256_digest(self.model_dump(mode="json"))


def adapt_v750_evidence(
    source: V750EvidenceLike,
    *,
    scope: IntentScopeV1,
    source_reference: str,
    source_digest: str,
    confirmed_at: str,
) -> GovernedIntentEvidenceV1 | None:
    if not source.confirmed or source.stale or source.contradictory:
        return None
    context = IntentContextKeyV1(
        context_id=f"v750:{source.context_key}",
        scope=scope,
        behavior=source.interpretation,
    )
    return GovernedIntentEvidenceV1(
        evidence_id=f"v760:v750:{source.evidence_id}",
        context_key=context,
        confirmed_interpretation=source.interpretation,
        represented_behavior=source.interpretation,
        source_kind=EvidenceSourceKind.ATTRIBUTABLE_HISTORY,
        source_reference=source_reference,
        source_digest=source_digest,
        confirmation_count=1,
        correction_count=1 if source.corrected_by_user else 0,
        contradiction_count=0,
        confidence=0.85 if source.corrected_by_user else 0.75,
        first_confirmed_at=confirmed_at,
        last_confirmed_at=confirmed_at,
        freshness_state=FreshnessState.CURRENT,
        inference_eligible=True,
        provenance=(source_reference, source_digest),
    )


def adapt_v752_event(
    source: V752EventLike,
    *,
    scope: IntentScopeV1,
    source_reference: str,
    source_digest: str,
    confirmed_at: str,
) -> GovernedIntentEvidenceV1 | None:
    if not source.user_response or not source.final_confirmed_interpretation:
        return None
    context = IntentContextKeyV1(
        context_id=f"v752:{source.correlation_id}",
        scope=scope,
        behavior=source.final_confirmed_interpretation,
    )
    return GovernedIntentEvidenceV1(
        evidence_id=f"v760:v752:{source.operation_id}",
        context_key=context,
        confirmed_interpretation=source.final_confirmed_interpretation,
        represented_behavior=source.final_confirmed_interpretation,
        source_kind=EvidenceSourceKind.ATTRIBUTABLE_HISTORY,
        source_reference=source_reference,
        source_digest=source_digest,
        confirmation_count=1,
        correction_count=0,
        contradiction_count=0,
        confidence=0.80,
        first_confirmed_at=confirmed_at,
        last_confirmed_at=confirmed_at,
        freshness_state=FreshnessState.CURRENT,
        inference_eligible=True,
        provenance=(source.initial_decision_digest, source_reference),
    )


def build_migration_proposal(
    *,
    proposal_id: str,
    source_records: tuple[SourceEvidenceRecordV1, ...],
    source_data_sources: tuple[str, ...],
    destination_target_keys: tuple[str, ...],
    existing_destination_evidence_ids: tuple[str, ...] = (),
) -> IntentMigrationProposalV1:
    snapshot_payload = tuple(
        sorted(
            (record.source_system, record.source_record_id, record.source_digest)
            for record in source_records
        )
    )
    snapshot_digest = sha256_digest(snapshot_payload)
    existing = set(existing_destination_evidence_ids)
    items: list[IntentMigrationItemV1] = []
    for record in sorted(
        source_records,
        key=lambda item: (item.source_system, item.source_record_id),
    ):
        reason = _skip_reason(record)
        proposed: GovernedIntentEvidenceV1 | None = None
        disposition = MigrationDisposition.SKIP
        if reason is None:
            assert record.context is not None
            assert record.interpretation is not None
            assert record.occurred_at is not None
            identity_digest = sha256_digest(
                (record.source_system, record.source_record_id)
            )
            evidence_id = f"v760:migrated:{identity_digest[:24]}"
            if evidence_id in existing:
                reason = "idempotent_existing_destination_evidence"
            else:
                proposed = GovernedIntentEvidenceV1(
                    evidence_id=evidence_id,
                    context_key=record.context,
                    confirmed_interpretation=record.interpretation,
                    represented_behavior=record.interpretation,
                    source_kind=EvidenceSourceKind.ATTRIBUTABLE_HISTORY,
                    source_reference=record.source_reference,
                    source_digest=record.source_digest,
                    confirmation_count=1,
                    correction_count=0,
                    contradiction_count=0,
                    confidence=0.75,
                    first_confirmed_at=record.occurred_at,
                    last_confirmed_at=record.occurred_at,
                    freshness_state=FreshnessState.CURRENT,
                    inference_eligible=True,
                    provenance=(record.source_reference, record.source_digest),
                )
                disposition = MigrationDisposition.CREATE
                reason = "confirmed_attributable_scoped_evidence"
        assert reason is not None
        items.append(
            IntentMigrationItemV1(
                source_system=record.source_system,
                source_record_id=record.source_record_id,
                source_digest=record.source_digest,
                disposition=disposition,
                reason=reason,
                proposed_evidence=proposed,
            )
        )
    create_count = sum(item.disposition is MigrationDisposition.CREATE for item in items)
    skip_count = len(items) - create_count
    return IntentMigrationProposalV1(
        proposal_id=proposal_id,
        input_snapshot_digest=snapshot_digest,
        source_data_sources=tuple(sorted(source_data_sources)),
        destination_target_keys=tuple(sorted(destination_target_keys)),
        existing_destination_evidence_ids=tuple(sorted(existing_destination_evidence_ids)),
        items=tuple(items),
        create_count=create_count,
        update_count=0,
        skip_count=skip_count,
    )


def _skip_reason(record: SourceEvidenceRecordV1) -> str | None:
    if record.speculative:
        return "speculative_interpretation_excluded"
    if not record.attributable:
        return "unattributable_source_excluded"
    if not record.confirmed:
        return "unconfirmed_source_excluded"
    if record.stale:
        return "stale_source_excluded"
    if record.contradictory:
        return "contradictory_source_excluded"
    if record.retired:
        return "retired_source_excluded"
    if not record.interpretation or not record.occurred_at or record.context is None:
        return "incomplete_source_excluded"
    return None
