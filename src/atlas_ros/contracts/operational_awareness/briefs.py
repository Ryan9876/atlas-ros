"""Exception-based operating brief contracts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from atlas_ros.contracts.advisory_v1 import ConfidenceAssessment, ProvenanceRecord
from atlas_ros.contracts.digests import sha256_digest

from .base import DigestBoundModel, Materiality
from .records import OperationalRecordRefV1


class MaterialChangeV1(DigestBoundModel):
    digest_field = "change_digest"

    contract_id: Literal["atlas.material-change"] = "atlas.material-change"
    schema_version: Literal["1.0"] = "1.0"
    record_reference: OperationalRecordRefV1
    previous_value: Any
    current_value: Any
    change_time: str
    materiality: Materiality
    reason_it_matters: str = Field(min_length=1, max_length=2_000)
    downstream_effect: str | None = Field(default=None, max_length=2_000)
    confidence: ConfidenceAssessment
    provenance: tuple[ProvenanceRecord, ...]
    change_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> MaterialChangeV1:
        return cls(change_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_digest(self) -> MaterialChangeV1:
        if not self.verify_digest():
            raise ValueError("material change digest mismatch")
        return self


class BriefItemV1(DigestBoundModel):
    digest_field = "item_digest"

    contract_id: Literal["atlas.operating-brief-item"] = "atlas.operating-brief-item"
    schema_version: Literal["1.0"] = "1.0"
    item_id: str = Field(min_length=1, max_length=512)
    record_reference: OperationalRecordRefV1
    conclusion: str = Field(min_length=1, max_length=2_000)
    item_type: str = Field(min_length=1, max_length=100)
    rank: int = Field(ge=1)
    materiality: Materiality
    evidence_refs: tuple[str, ...]
    confidence: ConfidenceAssessment
    item_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> BriefItemV1:
        return cls(item_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_digest(self) -> BriefItemV1:
        if not self.evidence_refs:
            raise ValueError("brief item requires evidence references")
        if not self.verify_digest():
            raise ValueError("brief item digest mismatch")
        return self


class OperatingBriefV1(DigestBoundModel):
    digest_field = "brief_digest"

    contract_id: Literal["atlas.operating-brief"] = "atlas.operating-brief"
    schema_version: Literal["1.0"] = "1.0"
    highest_value_next_action: BriefItemV1 | None = None
    decisions_requiring_ryan: tuple[BriefItemV1, ...] = ()
    new_or_worsened_blockers: tuple[BriefItemV1, ...] = ()
    delegated_work_requiring_follow_up: tuple[BriefItemV1, ...] = ()
    overdue_or_at_risk_commitments: tuple[BriefItemV1, ...] = ()
    stale_or_contradictory_work_state: tuple[BriefItemV1, ...] = ()
    material_completions: tuple[BriefItemV1, ...] = ()
    significant_changes: tuple[MaterialChangeV1, ...] = ()
    safe_to_ignore_summary: str
    overflow_summary: str
    source_snapshot_references: tuple[str, ...]
    brief_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> OperatingBriefV1:
        return cls(brief_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_brief(self) -> OperatingBriefV1:
        items = self.all_items()
        identities = tuple(item.item_id for item in items)
        if len(set(identities)) != len(identities):
            raise ValueError("operating brief repeats the same underlying issue")
        if not self.verify_digest():
            raise ValueError("operating brief digest mismatch")
        return self

    def all_items(self) -> tuple[BriefItemV1, ...]:
        head = () if self.highest_value_next_action is None else (self.highest_value_next_action,)
        return head + (
            self.decisions_requiring_ryan
            + self.new_or_worsened_blockers
            + self.delegated_work_requiring_follow_up
            + self.overdue_or_at_risk_commitments
            + self.stale_or_contradictory_work_state
            + self.material_completions
        )
