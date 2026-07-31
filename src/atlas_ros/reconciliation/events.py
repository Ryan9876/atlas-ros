from __future__ import annotations

import base64
import hashlib
import hmac
import json
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, Protocol

from atlas_ros.contracts.models import deterministic_digest
from atlas_ros.reconciliation.state import (
    HISTORICAL_W04_DATA_SOURCE_ID,
    HISTORICAL_W04_DATABASE_ID,
)
from atlas_ros.runtime.database import RuntimeDatabase


class EventProvider(StrEnum):
    TODOIST = "todoist"
    NOTION = "notion"
    MANUAL = "manual"
    BACKSTOP = "backstop"


class EventState(StrEnum):
    RECEIVED = "received"
    VALIDATED = "validated"
    SNAPSHOT_LOADED = "snapshot_loaded"
    PLANNED = "planned"
    POLICY_EVALUATED = "policy_evaluated"
    APPLYING = "applying"
    READBACK_VERIFIED = "readback_verified"
    APPLIED = "applied"
    DUPLICATE = "duplicate"
    NO_CHANGE = "no_change"
    INFORMATIONAL = "informational"
    IGNORED = "ignored"
    AWAITING_APPROVAL = "awaiting_approval"
    BLOCKED = "blocked"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class AutonomyMode(StrEnum):
    MONITOR_ONLY = "monitor_only"
    BOUNDED_AUTO_APPLY = "bounded_auto_apply"
    PAUSED = "paused"


class PolicyDecision(StrEnum):
    AUTO_APPLY = "auto_apply"
    REQUIRE_ATTENDED_APPROVAL = "require_attended_approval"
    BLOCK = "block"


class MutationKind(StrEnum):
    NOTION_EXECUTION_PROJECTION = "notion_execution_projection"
    NOTION_STATUS_UPDATE = "notion_status_update"
    NOTION_LEDGER_WRITE = "notion_ledger_write"
    TODOIST_TASK_CREATE = "todoist_task_create"
    TODOIST_TASK_UPDATE = "todoist_task_update"
    TOMBSTONE = "tombstone"
    DELEGATION = "delegation"
    GOVERNANCE = "governance"
    DESTRUCTIVE = "destructive"


_TERMINAL_STATES = {
    EventState.APPLIED,
    EventState.DUPLICATE,
    EventState.NO_CHANGE,
    EventState.INFORMATIONAL,
    EventState.IGNORED,
    EventState.BLOCKED,
    EventState.DEAD_LETTER,
}

_TRANSITIONS: dict[EventState, frozenset[EventState]] = {
    EventState.RECEIVED: frozenset(
        {EventState.VALIDATED, EventState.BLOCKED, EventState.DUPLICATE}
    ),
    EventState.VALIDATED: frozenset(
        {
            EventState.SNAPSHOT_LOADED,
            EventState.BLOCKED,
            EventState.DUPLICATE,
            EventState.FAILED,
        }
    ),
    EventState.SNAPSHOT_LOADED: frozenset(
        {
            EventState.PLANNED,
            EventState.NO_CHANGE,
            EventState.INFORMATIONAL,
            EventState.IGNORED,
            EventState.FAILED,
        }
    ),
    EventState.PLANNED: frozenset({EventState.POLICY_EVALUATED, EventState.FAILED}),
    EventState.POLICY_EVALUATED: frozenset(
        {EventState.APPLYING, EventState.AWAITING_APPROVAL, EventState.BLOCKED, EventState.FAILED}
    ),
    EventState.AWAITING_APPROVAL: frozenset(
        {EventState.APPLYING, EventState.BLOCKED, EventState.PLANNED}
    ),
    EventState.APPLYING: frozenset(
        {EventState.READBACK_VERIFIED, EventState.FAILED, EventState.BLOCKED}
    ),
    EventState.READBACK_VERIFIED: frozenset({EventState.APPLIED, EventState.FAILED}),
    EventState.FAILED: frozenset(
        {EventState.VALIDATED, EventState.DEAD_LETTER, EventState.BLOCKED}
    ),
}


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def _json_digest(raw_body: bytes) -> str:
    return hashlib.sha256(raw_body).hexdigest()


@dataclass(frozen=True)
class CanonicalEventEnvelope:
    provider: EventProvider
    event_type: str
    delivery_id: str
    canonical_identity: str
    canonical_object_id: str
    provider_event_at: datetime
    received_at: datetime
    raw_payload_digest: str
    correlation_id: str
    policy_version: str
    schema_version: str = "8.3"
    object_version: str = ""
    initiator_id: str = ""
    execution_surface: str = "Automation"
    normalized_snapshot_digest: str = ""
    causation_id: str = ""
    causal_depth: int = 0
    source_checkpoint: str = ""
    origin_marker: str = ""
    object_ids: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        required = {
            "event_type": self.event_type,
            "delivery_id": self.delivery_id,
            "canonical_identity": self.canonical_identity,
            "canonical_object_id": self.canonical_object_id,
            "raw_payload_digest": self.raw_payload_digest,
            "correlation_id": self.correlation_id,
            "policy_version": self.policy_version,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(f"event envelope fields are required: {', '.join(missing)}")
        if len(self.raw_payload_digest) != 64:
            raise ValueError("raw payload digest must be SHA-256")
        if self.normalized_snapshot_digest and len(self.normalized_snapshot_digest) != 64:
            raise ValueError("normalized snapshot digest must be SHA-256")
        if self.causal_depth < 0:
            raise ValueError("causal depth cannot be negative")

    @property
    def event_id(self) -> str:
        identity = {
            "schema_version": self.schema_version,
            "provider": self.provider.value,
            "delivery_id": self.delivery_id,
            "canonical_identity": self.canonical_identity,
        }
        return f"evt:{deterministic_digest(identity)}"

    def evidence(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "provider": self.provider.value,
            "event_type": self.event_type,
            "delivery_id": self.delivery_id,
            "canonical_identity": self.canonical_identity,
            "canonical_object_id": self.canonical_object_id,
            "object_ids": dict(sorted(self.object_ids.items())),
            "object_version": self.object_version,
            "provider_event_at": _iso(self.provider_event_at),
            "received_at": _iso(self.received_at),
            "initiator_id": self.initiator_id,
            "execution_surface": self.execution_surface,
            "raw_payload_digest": self.raw_payload_digest,
            "normalized_snapshot_digest": self.normalized_snapshot_digest,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "causal_depth": self.causal_depth,
            "source_checkpoint": self.source_checkpoint,
            "policy_version": self.policy_version,
            "origin_marker": self.origin_marker,
        }


@dataclass(frozen=True)
class MutationIntent:
    mutation_id: str
    kind: MutationKind
    provider: EventProvider
    object_id: str
    field: str
    expected_value: Any
    desired_value: Any
    idempotency_key: str
    destination: str = ""
    ryan_owned: bool = True
    inferred: bool = False
    affects_other_person: bool = False
    reversible: bool = True
    readback_required: bool = True


@dataclass(frozen=True)
class EventPlan:
    event_ids: tuple[str, ...]
    snapshot_digests: tuple[str, ...]
    authority_version: str
    policy_version: str
    mutations: tuple[MutationIntent, ...]
    expected_checkpoint: str
    correlation_id: str
    generated_at: datetime
    expires_at: datetime
    conflicts: tuple[str, ...] = ()
    classification: str = "actionable"
    canonical_mapping_count: int = 1
    plan_digest: str = ""

    def __post_init__(self) -> None:
        payload = {
            "event_ids": sorted(self.event_ids),
            "snapshot_digests": sorted(self.snapshot_digests),
            "authority_version": self.authority_version,
            "policy_version": self.policy_version,
            "mutations": [
                {
                    **item.__dict__,
                    "kind": item.kind.value,
                    "provider": item.provider.value,
                }
                for item in self.mutations
            ],
            "expected_checkpoint": self.expected_checkpoint,
            "correlation_id": self.correlation_id,
            "expires_at": _iso(self.expires_at),
            "conflicts": self.conflicts,
            "classification": self.classification,
            "canonical_mapping_count": self.canonical_mapping_count,
        }
        expected = deterministic_digest(payload)
        if self.plan_digest and not hmac.compare_digest(self.plan_digest, expected):
            raise ValueError("event plan digest mismatch")
        object.__setattr__(self, "plan_digest", expected)


@dataclass(frozen=True)
class PolicyResult:
    decision: PolicyDecision
    reasons: tuple[str, ...]
    policy_version: str


@dataclass(frozen=True)
class AutonomyPolicy:
    version: str = "8.3.0-rc1"
    mode: AutonomyMode = AutonomyMode.MONITOR_ONLY
    approved_destinations: frozenset[str] = frozenset({"#Work", "#Personal"})
    max_mutations_per_event: int = 6
    max_universal_inbox_subtasks: int = 5
    max_causal_depth: int = 4
    authority_agrees: bool = True
    kill_switch: bool = True


class AutonomyPolicyEvaluator:
    _AUTO_KINDS = frozenset(
        {
            MutationKind.NOTION_EXECUTION_PROJECTION,
            MutationKind.NOTION_STATUS_UPDATE,
            MutationKind.NOTION_LEDGER_WRITE,
            MutationKind.TODOIST_TASK_CREATE,
            MutationKind.TODOIST_TASK_UPDATE,
        }
    )
    _BLOCKED_FIELDS = frozenset(
        {
            "credential",
            "permission",
            "integration_scope",
            "message",
            "email",
            "calendar",
            "release_authority",
            "live_network",
        }
    )

    def __init__(self, policy: AutonomyPolicy) -> None:
        self.policy = policy

    def evaluate(self, envelope: CanonicalEventEnvelope, plan: EventPlan) -> PolicyResult:
        blocked: list[str] = []
        approval: list[str] = []
        serialized = json.dumps(
            {
                "event": envelope.evidence(),
                "plan": plan.plan_digest,
                "mutations": [item.__dict__ for item in plan.mutations],
            },
            default=str,
            sort_keys=True,
        )
        if not self.policy.authority_agrees:
            blocked.append("authority disagreement")
        if HISTORICAL_W04_DATABASE_ID in serialized or HISTORICAL_W04_DATA_SOURCE_ID in serialized:
            blocked.append("historical W04 identity is prohibited")
        if envelope.causal_depth > self.policy.max_causal_depth:
            blocked.append("maximum causal depth exceeded")
        if plan.canonical_mapping_count != 1:
            blocked.append("canonical mapping is missing or ambiguous")
        if plan.conflicts:
            blocked.append("plan contains unresolved conflicts")
        for mutation in plan.mutations:
            if mutation.kind in {MutationKind.DESTRUCTIVE, MutationKind.GOVERNANCE}:
                blocked.append(f"{mutation.kind.value} mutation is prohibited")
            if mutation.field in self._BLOCKED_FIELDS:
                blocked.append(f"{mutation.field} action is prohibited")
            if mutation.kind is MutationKind.TOMBSTONE:
                approval.append("provider deletion requires attended review")
            if mutation.kind is MutationKind.DELEGATION or mutation.affects_other_person:
                approval.append("delegation or another person's workload requires approval")
            if mutation.inferred:
                approval.append("material field inference requires approval")
            if (
                mutation.destination
                and mutation.destination not in self.policy.approved_destinations
            ):
                approval.append("destination is outside approved Ryan-owned scope")
            if not mutation.ryan_owned:
                approval.append("object is not Ryan-owned")
            if not mutation.reversible:
                approval.append("mutation is not safely reversible")
            if mutation.kind not in self._AUTO_KINDS and mutation.kind not in {
                MutationKind.TOMBSTONE,
                MutationKind.DELEGATION,
            }:
                approval.append("mutation type is not auto-apply allowlisted")
        if len(plan.mutations) > self.policy.max_mutations_per_event:
            approval.append("mutation limit exceeded")
        if blocked:
            return PolicyResult(
                PolicyDecision.BLOCK, tuple(sorted(set(blocked))), self.policy.version
            )
        if self.policy.kill_switch or self.policy.mode in {
            AutonomyMode.MONITOR_ONLY,
            AutonomyMode.PAUSED,
        }:
            approval.append("runtime is monitor-only or automatic application is paused")
        if approval:
            return PolicyResult(
                PolicyDecision.REQUIRE_ATTENDED_APPROVAL,
                tuple(sorted(set(approval))),
                self.policy.version,
            )
        return PolicyResult(PolicyDecision.AUTO_APPLY, (), self.policy.version)


@dataclass(frozen=True)
class ApprovalBinding:
    approval_id: str
    actor: str
    event_ids: tuple[str, ...]
    snapshot_digests: tuple[str, ...]
    plan_digest: str
    authority_version: str
    policy_version: str
    expires_at: datetime
    approved_at: datetime

    def validate(self, plan: EventPlan, *, now: datetime | None = None) -> None:
        current = now or _utcnow()
        if current >= self.expires_at:
            raise PermissionError("approval expired")
        checks = {
            "event set": tuple(sorted(plan.event_ids)) == tuple(sorted(self.event_ids)),
            "snapshots": tuple(sorted(plan.snapshot_digests))
            == tuple(sorted(self.snapshot_digests)),
            "plan digest": hmac.compare_digest(plan.plan_digest, self.plan_digest),
            "authority": plan.authority_version == self.authority_version,
            "policy": plan.policy_version == self.policy_version,
        }
        failed = [name for name, valid in checks.items() if not valid]
        if failed:
            raise PermissionError(f"approval no longer binds exact plan: {', '.join(failed)}")


@dataclass(frozen=True)
class QueueAcceptance:
    event_id: str
    state: EventState
    duplicate_of: str = ""


@dataclass(frozen=True)
class ClaimedEvent:
    envelope: CanonicalEventEnvelope
    state: EventState
    attempt_count: int
    evidence: Mapping[str, Any]


class DurableEventQueue:
    def __init__(self, database: RuntimeDatabase, *, clock: Any = _utcnow) -> None:
        self.database = database
        self.clock = clock

    def accept(self, envelope: CanonicalEventEnvelope) -> QueueAcceptance:
        now = self.clock()
        event_id = envelope.event_id
        duplicate_of = ""
        state = EventState.RECEIVED
        with self.database.connect() as db:
            delivery = db.execute(
                "SELECT event_id FROM event_reconciliation_event "
                "WHERE provider=? AND delivery_id=?",
                (envelope.provider.value, envelope.delivery_id),
            ).fetchone()
            if delivery is not None:
                return QueueAcceptance(str(delivery[0]), EventState.DUPLICATE, str(delivery[0]))
            if envelope.normalized_snapshot_digest:
                semantic = db.execute(
                    "SELECT event_id FROM event_reconciliation_event WHERE provider=? "
                    "AND canonical_identity=? AND object_version=? "
                    "AND normalized_snapshot_digest=? "
                    "ORDER BY received_at LIMIT 1",
                    (
                        envelope.provider.value,
                        envelope.canonical_identity,
                        envelope.object_version,
                        envelope.normalized_snapshot_digest,
                    ),
                ).fetchone()
                if semantic is not None:
                    state = EventState.DUPLICATE
                    duplicate_of = str(semantic[0])
            db.execute(
                "INSERT INTO event_reconciliation_event("
                "event_id,schema_version,provider,event_type,delivery_id,canonical_identity,"
                "canonical_object_id,object_version,provider_event_at,received_at,initiator_id,"
                "execution_surface,raw_payload_digest,normalized_snapshot_digest,correlation_id,"
                "causation_id,causal_depth,source_checkpoint,policy_version,origin_marker,state,"
                "duplicate_of,evidence_json,updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    event_id,
                    envelope.schema_version,
                    envelope.provider.value,
                    envelope.event_type,
                    envelope.delivery_id,
                    envelope.canonical_identity,
                    envelope.canonical_object_id,
                    envelope.object_version,
                    _iso(envelope.provider_event_at),
                    _iso(envelope.received_at),
                    envelope.initiator_id,
                    envelope.execution_surface,
                    envelope.raw_payload_digest,
                    envelope.normalized_snapshot_digest,
                    envelope.correlation_id,
                    envelope.causation_id,
                    envelope.causal_depth,
                    envelope.source_checkpoint,
                    envelope.policy_version,
                    envelope.origin_marker,
                    state.value,
                    duplicate_of or None,
                    json.dumps(envelope.evidence(), sort_keys=True, separators=(",", ":")),
                    _iso(now),
                ),
            )
        return QueueAcceptance(event_id, state, duplicate_of)

    def claim(
        self, worker_id: str, *, lease_for: timedelta = timedelta(seconds=60)
    ) -> ClaimedEvent | None:
        now = self.clock()
        expires = now + lease_for
        with self.database.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM event_reconciliation_event WHERE "
                "state IN ('received','failed') "
                "AND (next_attempt_at IS NULL OR next_attempt_at<=?) "
                "AND (lease_expires_at IS NULL OR lease_expires_at<=?) "
                "AND NOT EXISTS (SELECT 1 FROM event_object_lease object_lease "
                "WHERE object_lease.provider=event_reconciliation_event.provider "
                "AND object_lease.canonical_object_id="
                "event_reconciliation_event.canonical_object_id "
                "AND object_lease.expires_at>?) "
                "ORDER BY received_at,event_id LIMIT 1",
                (_iso(now), _iso(now), _iso(now)),
            ).fetchone()
            if row is None:
                return None
            updated = db.execute(
                "UPDATE event_reconciliation_event SET "
                "lease_holder=?,lease_expires_at=?,updated_at=? "
                "WHERE event_id=? AND (lease_expires_at IS NULL OR lease_expires_at<=?)",
                (worker_id, _iso(expires), _iso(now), row["event_id"], _iso(now)),
            )
            if updated.rowcount != 1:
                return None
            db.execute(
                "INSERT INTO event_object_lease("
                "provider,canonical_object_id,holder,event_id,expires_at) VALUES(?,?,?,?,?) "
                "ON CONFLICT(provider,canonical_object_id) DO UPDATE SET "
                "holder=excluded.holder,event_id=excluded.event_id,"
                "expires_at=excluded.expires_at",
                (
                    row["provider"],
                    row["canonical_object_id"],
                    worker_id,
                    row["event_id"],
                    _iso(expires),
                ),
            )
        evidence = json.loads(str(row["evidence_json"]))
        envelope = envelope_from_evidence(evidence)
        return ClaimedEvent(
            envelope, EventState(str(row["state"])), int(row["attempt_count"]), evidence
        )

    def transition(
        self,
        event_id: str,
        new_state: EventState,
        *,
        worker_id: str = "",
        plan_digest: str = "",
        decision: PolicyDecision | None = None,
        reason: str = "",
    ) -> None:
        now = self.clock()
        with self.database.connect() as db:
            row = db.execute(
                "SELECT state,lease_holder,lease_expires_at FROM "
                "event_reconciliation_event WHERE event_id=?",
                (event_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown event: {event_id}")
            current = EventState(str(row["state"]))
            if current in _TERMINAL_STATES:
                raise RuntimeError(f"terminal event cannot transition: {current.value}")
            if new_state not in _TRANSITIONS.get(current, frozenset()):
                raise RuntimeError(
                    f"invalid event transition: {current.value} -> {new_state.value}"
                )
            holder = str(row["lease_holder"] or "")
            if holder and worker_id and holder != worker_id:
                raise PermissionError("event lease is held by another worker")
            releases_lease = new_state in _TERMINAL_STATES or new_state in {
                EventState.AWAITING_APPROVAL,
                EventState.FAILED,
            }
            db.execute(
                "UPDATE event_reconciliation_event SET state=?,plan_digest=?,decision=?,reason=?,"
                "lease_holder=?,lease_expires_at=?,updated_at=? WHERE event_id=?",
                (
                    new_state.value,
                    plan_digest,
                    decision.value if decision else "",
                    reason,
                    None if releases_lease else (holder or None),
                    None if releases_lease else row["lease_expires_at"],
                    _iso(now),
                    event_id,
                ),
            )
            if releases_lease:
                db.execute(
                    "DELETE FROM event_object_lease WHERE event_id=?",
                    (event_id,),
                )

    def bind_snapshot(
        self,
        event_id: str,
        snapshot_digest: str,
        *,
        object_version: str = "",
    ) -> str:
        """Attach current-state evidence and find an earlier semantic duplicate."""
        if len(snapshot_digest) != 64:
            raise ValueError("normalized snapshot digest must be SHA-256")
        with self.database.connect() as db:
            row = db.execute(
                "SELECT provider,canonical_identity,object_version FROM "
                "event_reconciliation_event WHERE event_id=?",
                (event_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown event: {event_id}")
            version = object_version or str(row["object_version"])
            duplicate = db.execute(
                "SELECT event_id FROM event_reconciliation_event WHERE event_id<>? "
                "AND provider=? AND canonical_identity=? AND object_version=? "
                "AND normalized_snapshot_digest=? ORDER BY received_at LIMIT 1",
                (
                    event_id,
                    row["provider"],
                    row["canonical_identity"],
                    version,
                    snapshot_digest,
                ),
            ).fetchone()
            db.execute(
                "UPDATE event_reconciliation_event SET normalized_snapshot_digest=?,"
                "object_version=?,updated_at=? WHERE event_id=?",
                (snapshot_digest, version, _iso(self.clock()), event_id),
            )
        return str(duplicate[0]) if duplicate is not None else ""

    def fail(
        self,
        event_id: str,
        error: str,
        *,
        max_attempts: int = 5,
        base_backoff: timedelta = timedelta(seconds=30),
    ) -> EventState:
        now = self.clock()
        with self.database.connect() as db:
            row = db.execute(
                "SELECT attempt_count,state FROM event_reconciliation_event WHERE event_id=?",
                (event_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown event: {event_id}")
            attempts = int(row["attempt_count"]) + 1
            state = EventState.DEAD_LETTER if attempts >= max_attempts else EventState.FAILED
            next_attempt = None
            if state is EventState.FAILED:
                delay = base_backoff * (2 ** (attempts - 1))
                next_attempt = _iso(now + min(delay, timedelta(hours=1)))
            db.execute(
                "UPDATE event_reconciliation_event SET state=?,attempt_count=?,next_attempt_at=?,"
                "reason=?,lease_holder=NULL,lease_expires_at=NULL,updated_at=? WHERE event_id=?",
                (state.value, attempts, next_attempt, error[:1000], _iso(now), event_id),
            )
            db.execute("DELETE FROM event_object_lease WHERE event_id=?", (event_id,))
        return state

    def record_receipt(self, event_id: str, plan_digest: str, receipt: Mapping[str, Any]) -> str:
        receipt_id = f"receipt:{deterministic_digest(receipt)}"
        with self.database.connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO event_reconciliation_receipt("
                "receipt_id,event_id,plan_digest,receipt_json,created_at) VALUES(?,?,?,?,?)",
                (
                    receipt_id,
                    event_id,
                    plan_digest,
                    json.dumps(receipt, sort_keys=True),
                    _iso(self.clock()),
                ),
            )
        return receipt_id

    def metrics(self) -> dict[str, Any]:
        now = self.clock()
        with self.database.connect() as db:
            counts = {
                str(row["state"]): int(row["count"])
                for row in db.execute(
                    "SELECT state,COUNT(*) AS count FROM event_reconciliation_event GROUP BY state"
                )
            }
            oldest = db.execute(
                "SELECT received_at FROM event_reconciliation_event WHERE state NOT IN "
                "('applied','duplicate','no_change','informational','ignored',"
                "'blocked','dead_letter') "
                "ORDER BY received_at LIMIT 1"
            ).fetchone()
        age = 0.0
        if oldest is not None:
            age = max(0.0, (now - datetime.fromisoformat(str(oldest[0]))).total_seconds())
        return {"counts": counts, "queue_oldest_age_seconds": age}


def envelope_from_evidence(evidence: Mapping[str, Any]) -> CanonicalEventEnvelope:
    return CanonicalEventEnvelope(
        provider=EventProvider(str(evidence["provider"])),
        event_type=str(evidence["event_type"]),
        delivery_id=str(evidence["delivery_id"]),
        canonical_identity=str(evidence["canonical_identity"]),
        canonical_object_id=str(evidence["canonical_object_id"]),
        provider_event_at=datetime.fromisoformat(str(evidence["provider_event_at"])),
        received_at=datetime.fromisoformat(str(evidence["received_at"])),
        raw_payload_digest=str(evidence["raw_payload_digest"]),
        correlation_id=str(evidence["correlation_id"]),
        policy_version=str(evidence["policy_version"]),
        schema_version=str(evidence.get("schema_version", "8.3")),
        object_version=str(evidence.get("object_version", "")),
        initiator_id=str(evidence.get("initiator_id", "")),
        execution_surface=str(evidence.get("execution_surface", "Automation")),
        normalized_snapshot_digest=str(evidence.get("normalized_snapshot_digest", "")),
        causation_id=str(evidence.get("causation_id", "")),
        causal_depth=int(evidence.get("causal_depth", 0)),
        source_checkpoint=str(evidence.get("source_checkpoint", "")),
        origin_marker=str(evidence.get("origin_marker", "")),
        object_ids={str(k): str(v) for k, v in dict(evidence.get("object_ids", {})).items()},
    )


def verify_todoist_signature(raw_body: bytes, signature: str, client_secret: str) -> bool:
    if not raw_body or not signature or not client_secret:
        return False
    expected = base64.b64encode(
        hmac.new(client_secret.encode(), raw_body, hashlib.sha256).digest()
    ).decode()
    return hmac.compare_digest(signature, expected)


def verify_notion_signature(raw_body: bytes, signature: str, verification_token: str) -> bool:
    if not raw_body or not signature.startswith("sha256=") or not verification_token:
        return False
    expected = (
        "sha256=" + hmac.new(verification_token.encode(), raw_body, hashlib.sha256).hexdigest()
    )
    return hmac.compare_digest(signature, expected)


def todoist_envelope(
    raw_body: bytes,
    headers: Mapping[str, str],
    *,
    client_secret: str,
    policy_version: str,
    received_at: datetime | None = None,
) -> CanonicalEventEnvelope:
    signature = headers.get("x-todoist-hmac-sha256", "")
    if not verify_todoist_signature(raw_body, signature, client_secret):
        raise PermissionError("invalid Todoist webhook signature")
    delivery_id = headers.get("x-todoist-delivery-id", "")
    if not delivery_id:
        raise ValueError("Todoist delivery ID is required")
    payload = json.loads(raw_body)
    if not isinstance(payload, dict):
        raise ValueError("Todoist webhook payload must be an object")
    event_type = str(payload.get("event_name", ""))
    allowed = {
        "item:added",
        "item:updated",
        "item:completed",
        "item:uncompleted",
        "item:deleted",
        "note:added",
        "note:updated",
        "note:deleted",
    }
    if event_type not in allowed:
        raise ValueError("unsupported Todoist event type")
    data = payload.get("event_data")
    if not isinstance(data, dict) or not data.get("id"):
        raise ValueError("Todoist event object identity is required")
    object_id = str(data["id"])
    parent_id = str(data.get("parent_id") or data.get("item_id") or object_id)
    triggered = datetime.fromisoformat(str(payload.get("triggered_at", "")).replace("Z", "+00:00"))
    return CanonicalEventEnvelope(
        provider=EventProvider.TODOIST,
        event_type=event_type,
        delivery_id=delivery_id,
        canonical_identity=f"todoist:{event_type.split(':')[0]}:{object_id}",
        canonical_object_id=parent_id,
        provider_event_at=triggered,
        received_at=received_at or _utcnow(),
        raw_payload_digest=_json_digest(raw_body),
        correlation_id=f"todoist:{delivery_id}",
        policy_version=policy_version,
        object_version=str(payload.get("version", "")),
        initiator_id=str((payload.get("initiator") or {}).get("id", "")),
        object_ids={"object_id": object_id, "parent_id": parent_id},
    )


def notion_envelope(
    raw_body: bytes,
    headers: Mapping[str, str],
    *,
    verification_token: str,
    policy_version: str,
    received_at: datetime | None = None,
) -> CanonicalEventEnvelope:
    signature = headers.get("x-notion-signature", "")
    if not verify_notion_signature(raw_body, signature, verification_token):
        raise PermissionError("invalid Notion webhook signature")
    payload = json.loads(raw_body)
    if not isinstance(payload, dict):
        raise ValueError("Notion webhook payload must be an object")
    event_type = str(payload.get("type", ""))
    allowed = {
        "page.created",
        "page.content_updated",
        "page.properties_updated",
        "data_source.content_updated",
    }
    if event_type not in allowed:
        raise ValueError("unsupported Notion event type")
    entity = payload.get("entity") or payload.get("data")
    if not isinstance(entity, dict) or not entity.get("id"):
        raise ValueError("Notion event object identity is required")
    object_id = str(entity["id"])
    delivery_id = str(payload.get("id") or headers.get("x-notion-delivery-id") or "")
    if not delivery_id:
        raise ValueError("Notion event delivery identity is required")
    timestamp = str(payload.get("timestamp") or payload.get("created_time") or "")
    provider_event_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return CanonicalEventEnvelope(
        provider=EventProvider.NOTION,
        event_type=event_type,
        delivery_id=delivery_id,
        canonical_identity=f"notion:page:{object_id}",
        canonical_object_id=object_id,
        provider_event_at=provider_event_at,
        received_at=received_at or _utcnow(),
        raw_payload_digest=_json_digest(raw_body),
        correlation_id=f"notion:{delivery_id}",
        policy_version=policy_version,
        initiator_id=str((payload.get("authors") or [{}])[0].get("id", "")),
        object_ids={"page_id": object_id},
    )


class SnapshotLoader(Protocol):
    def load_current(self, envelope: CanonicalEventEnvelope) -> Mapping[str, Any]: ...


class ScopedEventPlanner(Protocol):
    def plan(self, envelope: CanonicalEventEnvelope, snapshot: Mapping[str, Any]) -> EventPlan: ...


class PlannedEventApplier(Protocol):
    def apply_and_readback(self, plan: EventPlan) -> Mapping[str, Any]: ...


class EventProcessor:
    """Coordinates event control while canonical ROS services retain business planning."""

    def __init__(
        self,
        queue: DurableEventQueue,
        snapshots: SnapshotLoader,
        planner: ScopedEventPlanner,
        applier: PlannedEventApplier,
        policy: AutonomyPolicyEvaluator,
    ) -> None:
        self.queue = queue
        self.snapshots = snapshots
        self.planner = planner
        self.applier = applier
        self.policy = policy

    def process(self, claimed: ClaimedEvent, worker_id: str) -> EventState:
        event_id = claimed.envelope.event_id
        try:
            start = (
                EventState.VALIDATED
                if claimed.state is EventState.RECEIVED
                else EventState.VALIDATED
            )
            self.queue.transition(event_id, start, worker_id=worker_id)
            snapshot = self.snapshots.load_current(claimed.envelope)
            snapshot_digest = deterministic_digest(snapshot)
            envelope = CanonicalEventEnvelope(
                **{**claimed.envelope.__dict__, "normalized_snapshot_digest": snapshot_digest}
            )
            duplicate_of = self.queue.bind_snapshot(
                event_id,
                snapshot_digest,
                object_version=envelope.object_version,
            )
            if duplicate_of:
                self.queue.transition(
                    event_id,
                    EventState.DUPLICATE,
                    worker_id=worker_id,
                    reason=f"semantic duplicate of {duplicate_of}",
                )
                return EventState.DUPLICATE
            self.queue.transition(event_id, EventState.SNAPSHOT_LOADED, worker_id=worker_id)
            plan = self.planner.plan(envelope, snapshot)
            if plan.classification == "informational":
                self.queue.transition(event_id, EventState.INFORMATIONAL, worker_id=worker_id)
                return EventState.INFORMATIONAL
            if not plan.mutations and not plan.conflicts:
                self.queue.transition(event_id, EventState.NO_CHANGE, worker_id=worker_id)
                return EventState.NO_CHANGE
            self.queue.transition(
                event_id,
                EventState.PLANNED,
                worker_id=worker_id,
                plan_digest=plan.plan_digest,
            )
            result = self.policy.evaluate(envelope, plan)
            self.queue.transition(
                event_id,
                EventState.POLICY_EVALUATED,
                worker_id=worker_id,
                plan_digest=plan.plan_digest,
                decision=result.decision,
                reason="; ".join(result.reasons),
            )
            if result.decision is PolicyDecision.BLOCK:
                self.queue.transition(
                    event_id,
                    EventState.BLOCKED,
                    worker_id=worker_id,
                    reason="; ".join(result.reasons),
                )
                return EventState.BLOCKED
            if result.decision is PolicyDecision.REQUIRE_ATTENDED_APPROVAL:
                self.queue.transition(
                    event_id,
                    EventState.AWAITING_APPROVAL,
                    worker_id=worker_id,
                    plan_digest=plan.plan_digest,
                    decision=result.decision,
                    reason="; ".join(result.reasons),
                )
                return EventState.AWAITING_APPROVAL
            self.queue.transition(
                event_id,
                EventState.APPLYING,
                worker_id=worker_id,
                plan_digest=plan.plan_digest,
            )
            current = self.snapshots.load_current(envelope)
            if deterministic_digest(current) != snapshot_digest:
                raise RuntimeError("snapshot changed after planning; re-plan required")
            receipt = self.applier.apply_and_readback(plan)
            if not bool(receipt.get("consistent")):
                raise RuntimeError("provider readback did not verify complete transaction")
            self.queue.record_receipt(event_id, plan.plan_digest, receipt)
            self.queue.transition(
                event_id,
                EventState.READBACK_VERIFIED,
                worker_id=worker_id,
                plan_digest=plan.plan_digest,
            )
            self.queue.transition(
                event_id,
                EventState.APPLIED,
                worker_id=worker_id,
                plan_digest=plan.plan_digest,
            )
            return EventState.APPLIED
        except (PermissionError, ValueError) as exc:
            self.queue.fail(event_id, str(exc), max_attempts=1)
            return EventState.DEAD_LETTER
        except Exception as exc:
            return self.queue.fail(event_id, str(exc))


@dataclass(frozen=True)
class UniversalInboxAssessment:
    eligible: bool
    decision: PolicyDecision
    reasons: tuple[str, ...]


def assess_universal_inbox(
    item: Mapping[str, Any],
    *,
    policy: AutonomyPolicy,
    approved_creator_ids: Sequence[str],
) -> UniversalInboxAssessment:
    reasons: list[str] = []
    blocked: list[str] = []
    if str(item.get("data_source_id", "")) in {
        HISTORICAL_W04_DATABASE_ID,
        HISTORICAL_W04_DATA_SOURCE_ID,
    }:
        blocked.append("historical W04 identity is prohibited")
    if str(item.get("classification", "")) in {"prohibited", "destructive"}:
        blocked.append("capture is prohibited")
    if str(item.get("creator_id", "")) not in approved_creator_ids:
        reasons.append("capture creator is not approved")
    destination = str(item.get("destination", ""))
    if destination not in policy.approved_destinations:
        reasons.append("destination must be explicit #Work or #Personal")
    if not str(item.get("outcome", "")).strip() or not str(item.get("task", "")).strip():
        reasons.append("outcome and task content must be explicit")
    if bool(item.get("delegated")) or not bool(item.get("ryan_owned", True)):
        reasons.append("responsibility must remain Ryan-owned")
    if bool(item.get("inferred_material_fields")):
        reasons.append("material fields cannot be inferred")
    subtasks = item.get("subtasks") or ()
    if not isinstance(subtasks, Sequence) or isinstance(subtasks, str | bytes):
        reasons.append("subtasks must be a bounded sequence")
    elif len(subtasks) > policy.max_universal_inbox_subtasks:
        reasons.append("Universal Inbox subtask limit exceeded")
    if bool(item.get("duplicate")):
        reasons.append("duplicate work already exists")
    if blocked:
        return UniversalInboxAssessment(False, PolicyDecision.BLOCK, tuple(sorted(set(blocked))))
    if reasons:
        return UniversalInboxAssessment(
            False,
            PolicyDecision.REQUIRE_ATTENDED_APPROVAL,
            tuple(sorted(set(reasons))),
        )
    if policy.mode is not AutonomyMode.BOUNDED_AUTO_APPLY or policy.kill_switch:
        return UniversalInboxAssessment(
            False,
            PolicyDecision.REQUIRE_ATTENDED_APPROVAL,
            ("runtime is monitor-only or automatic application is paused",),
        )
    return UniversalInboxAssessment(True, PolicyDecision.AUTO_APPLY, ())


class FeedbackLoopGuard:
    def __init__(self, database: RuntimeDatabase, *, clock: Any = _utcnow) -> None:
        self.database = database
        self.clock = clock

    def remember(
        self,
        *,
        provider: EventProvider,
        object_id: str,
        correlation_id: str,
        expected_snapshot_digest: str,
        ttl: timedelta = timedelta(hours=24),
    ) -> str:
        fingerprint = deterministic_digest(
            {
                "provider": provider.value,
                "object_id": object_id,
                "correlation_id": correlation_id,
                "expected": expected_snapshot_digest,
            }
        )
        now = self.clock()
        with self.database.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO event_outbound_fingerprint("
                "fingerprint,provider,canonical_object_id,correlation_id,"
                "expected_snapshot_digest,created_at,expires_at) "
                "VALUES(?,?,?,?,?,?,?)",
                (
                    fingerprint,
                    provider.value,
                    object_id,
                    correlation_id,
                    expected_snapshot_digest,
                    _iso(now),
                    _iso(now + ttl),
                ),
            )
        return fingerprint

    def classify(
        self,
        *,
        provider: EventProvider,
        object_id: str,
        correlation_id: str,
        actual_snapshot_digest: str,
    ) -> str:
        now = self.clock()
        with self.database.connect() as db:
            row = db.execute(
                "SELECT expected_snapshot_digest FROM event_outbound_fingerprint WHERE provider=? "
                "AND canonical_object_id=? AND correlation_id=? AND expires_at>? "
                "ORDER BY created_at DESC LIMIT 1",
                (provider.value, object_id, correlation_id, _iso(now)),
            ).fetchone()
        if row is None:
            return "external_or_unknown"
        if hmac.compare_digest(str(row[0]), actual_snapshot_digest):
            return "self_originated_verified"
        return "concurrent_change_reconcile"


class IncrementalEventSource(Protocol):
    def changes_since(
        self, provider: EventProvider, checkpoint: str
    ) -> tuple[Sequence[CanonicalEventEnvelope], str]: ...


@dataclass(frozen=True)
class BackstopResult:
    provider: EventProvider
    prior_checkpoint: str
    resulting_checkpoint: str
    accepted: int
    duplicates: int


class EventBackstop:
    """Bounded incremental convergence path that shares the webhook queue."""

    def __init__(self, queue: DurableEventQueue, source: IncrementalEventSource) -> None:
        self.queue = queue
        self.source = source

    def run(self, provider: EventProvider, checkpoint: str) -> BackstopResult:
        events, resulting_checkpoint = self.source.changes_since(provider, checkpoint)
        accepted = 0
        duplicates = 0
        for event in events:
            if event.provider not in {provider, EventProvider.BACKSTOP}:
                raise ValueError("backstop returned an event for the wrong provider")
            result = self.queue.accept(event)
            if result.state is EventState.DUPLICATE:
                duplicates += 1
            else:
                accepted += 1
        return BackstopResult(
            provider=provider,
            prior_checkpoint=checkpoint,
            resulting_checkpoint=resulting_checkpoint,
            accepted=accepted,
            duplicates=duplicates,
        )


class EventOperator:
    """Attended queue controls. This layer never plans or invents provider writes."""

    def __init__(self, database: RuntimeDatabase, queue: DurableEventQueue) -> None:
        self.database = database
        self.queue = queue

    def set_control(self, key: str, value: str) -> None:
        if key not in {
            "ingress",
            "planning",
            "auto_apply",
            "approval",
            "backstop",
            "replay",
            "kill_switch",
            "mode",
        }:
            raise ValueError("unknown event runtime control")
        with self.database.connect() as db:
            db.execute(
                "INSERT INTO event_runtime_control(control_key,control_value,updated_at) "
                "VALUES(?,?,?) ON CONFLICT(control_key) DO UPDATE SET "
                "control_value=excluded.control_value,updated_at=excluded.updated_at",
                (key, value, _iso(self.queue.clock())),
            )

    def controls(self) -> dict[str, str]:
        with self.database.connect() as db:
            return {
                str(row["control_key"]): str(row["control_value"])
                for row in db.execute(
                    "SELECT control_key,control_value FROM event_runtime_control "
                    "ORDER BY control_key"
                )
            }

    def pause_auto_apply(self) -> None:
        self.set_control("kill_switch", "true")
        self.set_control("auto_apply", "disabled")

    def resume_auto_apply(self, *, exact_policy_activation_authorized: bool) -> None:
        if not exact_policy_activation_authorized:
            raise PermissionError("exact production policy activation is required")
        self.set_control("kill_switch", "false")
        self.set_control("auto_apply", "enabled")

    def reject(self, event_id: str, *, actor: str, reason: str) -> None:
        if not actor or not reason:
            raise ValueError("attended rejection requires actor and reason")
        self.queue.transition(
            event_id,
            EventState.BLOCKED,
            reason=f"rejected by {actor}: {reason}",
        )

    def release_dead_letter(self, event_id: str, *, actor: str, reason: str) -> None:
        if not actor or not reason:
            raise ValueError("dead-letter release requires actor and reason")
        now = self.queue.clock()
        with self.database.connect() as db:
            row = db.execute(
                "SELECT state FROM event_reconciliation_event WHERE event_id=?",
                (event_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown event: {event_id}")
            if EventState(str(row["state"])) is not EventState.DEAD_LETTER:
                raise RuntimeError("only dead-letter events can be released")
            db.execute(
                "UPDATE event_reconciliation_event SET state='failed',attempt_count=0,"
                "next_attempt_at=?,reason=?,updated_at=? WHERE event_id=?",
                (
                    _iso(now),
                    f"released by {actor}: {reason}",
                    _iso(now),
                    event_id,
                ),
            )

    def inspect(self, event_id: str) -> dict[str, Any]:
        with self.database.connect() as db:
            row = db.execute(
                "SELECT * FROM event_reconciliation_event WHERE event_id=?",
                (event_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown event: {event_id}")
            receipts = [
                dict(receipt)
                for receipt in db.execute(
                    "SELECT receipt_id,plan_digest,receipt_json,created_at "
                    "FROM event_reconciliation_receipt WHERE event_id=? ORDER BY created_at",
                    (event_id,),
                )
            ]
        result = dict(row)
        result["evidence"] = json.loads(str(result.pop("evidence_json")))
        result["receipts"] = receipts
        return result


def new_manual_envelope(
    *,
    event_type: str,
    object_id: str,
    policy_version: str,
    source_checkpoint: str = "",
) -> CanonicalEventEnvelope:
    now = _utcnow()
    delivery_id = str(uuid.uuid4())
    raw = json.dumps(
        {"event_type": event_type, "object_id": object_id, "delivery_id": delivery_id},
        sort_keys=True,
    ).encode()
    return CanonicalEventEnvelope(
        provider=EventProvider.MANUAL,
        event_type=event_type,
        delivery_id=delivery_id,
        canonical_identity=f"manual:{event_type}:{object_id}",
        canonical_object_id=object_id,
        provider_event_at=now,
        received_at=now,
        raw_payload_digest=_json_digest(raw),
        correlation_id=f"manual:{delivery_id}",
        policy_version=policy_version,
        execution_surface="CLI",
        source_checkpoint=source_checkpoint,
    )
