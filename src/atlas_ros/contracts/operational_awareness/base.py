"""Shared immutable primitives for the Atlas ROS operational-awareness subsystem."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, ClassVar, cast

from pydantic import BaseModel, ConfigDict

from atlas_ros.contracts.digests import sha256_digest


class StrictModel(BaseModel):
    """Frozen fail-closed contract base."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class DigestBoundModel(StrictModel):
    """Contract whose identity is derived from its complete canonical payload."""

    digest_field: ClassVar[str]
    digest_excluded_fields: ClassVar[frozenset[str]] = frozenset()

    @classmethod
    def compute_digest(cls, values: dict[str, Any]) -> str:
        """Apply model defaults before hashing so serialized replay remains stable."""
        unsigned_values = dict(values)
        unsigned_values[cls.digest_field] = "0" * 64
        unsigned = cls.model_construct(**unsigned_values)
        return sha256_digest(unsigned.digest_payload())

    def digest_payload(self) -> dict[str, Any]:
        payload = self.model_dump(
            mode="json",
            exclude={self.digest_field, *self.digest_excluded_fields},
        )
        return cast(dict[str, Any], _strip_ephemeral_digest_fields(payload))

    def expected_digest(self) -> str:
        return sha256_digest(self.digest_payload())

    def verify_digest(self) -> bool:
        return bool(getattr(self, self.digest_field) == self.expected_digest())


def _strip_ephemeral_digest_fields(value: Any) -> Any:
    """Remove retrieval-only metadata recursively from canonical identities."""
    if isinstance(value, dict):
        return {
            key: _strip_ephemeral_digest_fields(item)
            for key, item in value.items()
            if key != "source_retrieved_at"
        }
    if isinstance(value, list):
        return [_strip_ephemeral_digest_fields(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_strip_ephemeral_digest_fields(item) for item in value)
    return value


class AuthoritativeSystem(StrEnum):
    GITHUB = "github"
    NOTION = "notion"
    TODOIST = "todoist"
    SQLITE = "sqlite"
    OTHER = "other"


class OperationalRecordType(StrEnum):
    ACTION_RECORD = "action_record"
    EXECUTION_STEP = "execution_step"
    DELEGATED_WORK = "delegated_work"
    PORTFOLIO_PROJECT = "portfolio_project"
    RISK_OR_BLOCKER = "risk_or_blocker"
    TODOIST_TASK = "todoist_task"
    PROVIDER_TRANSACTION_RECEIPT = "provider_transaction_receipt"
    DECISION_RECORD = "decision_record"
    REVIEW_RECORD = "review_record"


class AuthorityLevel(StrEnum):
    CANONICAL = "canonical"
    AUTHORITATIVE_DYNAMIC = "authoritative_dynamic"
    EXECUTION = "execution"
    SUPPORTING = "supporting"
    TEMPORARY = "temporary"


class FreshnessState(StrEnum):
    CURRENT = "current"
    AGING = "aging"
    STALE = "stale"
    CONTRADICTED = "contradicted"
    UNVERIFIABLE = "unverifiable"


class EffectiveWorkState(StrEnum):
    NOT_STARTED = "not_started"
    READY = "ready"
    ACTIVE = "active"
    WAITING = "waiting"
    BLOCKED = "blocked"
    DELEGATED = "delegated"
    REVIEW = "review"
    AWAITING_VALIDATION = "awaiting_validation"
    AWAITING_DECISION = "awaiting_decision"
    TECHNICALLY_COMPLETE = "technically_complete"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CommitmentType(StrEnum):
    RYAN_OWNED = "ryan_owned_commitment"
    MADE_TO_RYAN = "commitment_made_to_ryan"
    DELEGATED_OUTCOME = "delegated_outcome"
    REQUESTED_DECISION = "requested_decision"
    WAITING_DEPENDENCY = "waiting_dependency"
    VENDOR = "vendor_commitment"
    CROSS_FUNCTIONAL = "cross_functional_commitment"
    UNCONFIRMED_CONVERSATIONAL = "unconfirmed_conversational_commitment"


class AcceptanceState(StrEnum):
    UNCONFIRMED = "unconfirmed"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    SUPERSEDED = "superseded"
    NOT_REQUIRED = "not_required"


class FollowUpDisposition(StrEnum):
    NONE = "no_follow_up_needed"
    PREMATURE = "follow_up_premature"
    APPROPRIATE = "follow_up_appropriate"
    DEADLINE_AT_RISK = "deadline_at_risk"
    ESCALATION = "escalation_consideration"
    VERIFICATION = "verification_required"
    COMPLETED = "completed"


class Materiality(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class HygieneSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class RepairClass(StrEnum):
    NONE = "no_repair_required"
    INFORMATIONAL = "informational"
    BATCH = "attended_batch_repair_eligible"
    INDIVIDUAL = "individual_review_required"
    RYAN_DECISION = "ryan_decision_required"
    PROTECTED = "prohibited_or_protected"


class AtlasCommandType(StrEnum):
    DELEGATE = "delegate"
    UPDATE = "update"
    WAITING_ON = "waiting-on"
    BLOCKED = "blocked"
    RECEIVED = "received"
    APPROVED = "approved"
    COMPLETE = "complete"
    CANCEL = "cancel"


Digest = str
