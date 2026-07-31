from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest

from atlas_ros.contracts.models import deterministic_digest
from atlas_ros.reconciliation.event_http import (
    EventReceiverApplication,
    EventReceiverConfig,
)
from atlas_ros.reconciliation.events import (
    ApprovalBinding,
    AutonomyMode,
    AutonomyPolicy,
    AutonomyPolicyEvaluator,
    CanonicalEventEnvelope,
    DurableEventQueue,
    EventBackstop,
    EventOperator,
    EventPlan,
    EventProcessor,
    EventProvider,
    EventState,
    FeedbackLoopGuard,
    MutationIntent,
    MutationKind,
    PolicyDecision,
    assess_universal_inbox,
    new_manual_envelope,
    notion_envelope,
    todoist_envelope,
    verify_notion_signature,
    verify_todoist_signature,
)
from atlas_ros.runtime.database import RuntimeDatabase

NOW = datetime(2026, 7, 31, 18, tzinfo=UTC)


class Clock:
    def __init__(self) -> None:
        self.now = NOW

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture
def runtime(tmp_path: Path) -> RuntimeDatabase:
    database = RuntimeDatabase(tmp_path / "runtime" / "atlas.db")
    database.initialize()
    return database


def envelope(
    *,
    delivery: str = "delivery-1",
    snapshot: str = "",
    depth: int = 0,
) -> CanonicalEventEnvelope:
    return CanonicalEventEnvelope(
        provider=EventProvider.TODOIST,
        event_type="item:updated",
        delivery_id=delivery,
        canonical_identity="todoist:item:task-1",
        canonical_object_id="task-1",
        provider_event_at=NOW,
        received_at=NOW,
        raw_payload_digest="a" * 64,
        normalized_snapshot_digest=snapshot,
        correlation_id=f"corr-{delivery}",
        policy_version="8.3.0-rc1",
        object_version="10",
        causal_depth=depth,
    )


def mutation(
    *,
    kind: MutationKind = MutationKind.NOTION_EXECUTION_PROJECTION,
    field: str = "execution_due_date",
    destination: str = "#Work",
    inferred: bool = False,
    other: bool = False,
    ryan_owned: bool = True,
) -> MutationIntent:
    return MutationIntent(
        mutation_id="mutation-1",
        kind=kind,
        provider=EventProvider.NOTION,
        object_id="page-1",
        field=field,
        expected_value="2026-08-01",
        desired_value="2026-08-02",
        idempotency_key="idem-1",
        destination=destination,
        inferred=inferred,
        affects_other_person=other,
        ryan_owned=ryan_owned,
    )


def plan(
    *mutations: MutationIntent,
    conflicts: tuple[str, ...] = (),
    mappings: int = 1,
    classification: str = "actionable",
) -> EventPlan:
    return EventPlan(
        event_ids=("event-1",),
        snapshot_digests=("b" * 64,),
        authority_version="8.2.1",
        policy_version="8.3.0-rc1",
        mutations=tuple(mutations),
        expected_checkpoint="checkpoint-1",
        correlation_id="corr-1",
        generated_at=NOW,
        expires_at=NOW + timedelta(minutes=15),
        conflicts=conflicts,
        canonical_mapping_count=mappings,
        classification=classification,
    )


def test_todoist_signature_and_supported_event_parse() -> None:
    payload = {
        "event_name": "item:updated",
        "user_id": "ryan",
        "event_data": {"id": "task-1", "parent_id": None},
        "initiator": {"id": "ryan"},
        "triggered_at": "2026-07-31T18:00:00Z",
        "version": "10",
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    signature = base64.b64encode(hmac.new(b"secret", raw, hashlib.sha256).digest()).decode()
    assert verify_todoist_signature(raw, signature, "secret")
    parsed = todoist_envelope(
        raw,
        {"x-todoist-hmac-sha256": signature, "x-todoist-delivery-id": "delivery-1"},
        client_secret="secret",
        policy_version="8.3.0-rc1",
        received_at=NOW,
    )
    assert parsed.canonical_object_id == "task-1"
    assert parsed.initiator_id == "ryan"
    assert parsed.raw_payload_digest == hashlib.sha256(raw).hexdigest()


def test_invalid_todoist_signature_fails_closed() -> None:
    with pytest.raises(PermissionError, match="invalid Todoist"):
        todoist_envelope(
            b"{}",
            {"x-todoist-hmac-sha256": "bad", "x-todoist-delivery-id": "delivery"},
            client_secret="secret",
            policy_version="8.3.0-rc1",
        )


def test_notion_signature_and_change_signal_parse() -> None:
    payload = {
        "id": "notion-delivery-1",
        "type": "page.created",
        "entity": {"id": "page-1"},
        "authors": [{"id": "ryan"}],
        "timestamp": "2026-07-31T18:00:00Z",
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    signature = "sha256=" + hmac.new(b"verification", raw, hashlib.sha256).hexdigest()
    assert verify_notion_signature(raw, signature, "verification")
    parsed = notion_envelope(
        raw,
        {"x-notion-signature": signature},
        verification_token="verification",
        policy_version="8.3.0-rc1",
        received_at=NOW,
    )
    assert parsed.event_type == "page.created"
    assert parsed.canonical_object_id == "page-1"


def test_invalid_and_unsupported_notion_event_fails_closed() -> None:
    raw = json.dumps(
        {"id": "d", "type": "comment.created", "entity": {"id": "p"}, "timestamp": NOW.isoformat()}
    ).encode()
    signature = "sha256=" + hmac.new(b"token", raw, hashlib.sha256).hexdigest()
    with pytest.raises(ValueError, match="unsupported Notion"):
        notion_envelope(
            raw,
            {"x-notion-signature": signature},
            verification_token="token",
            policy_version="8.3.0-rc1",
        )


def test_queue_persists_before_acceptance_and_deduplicates_delivery(
    runtime: RuntimeDatabase,
) -> None:
    queue = DurableEventQueue(runtime, clock=Clock())
    first = queue.accept(envelope())
    duplicate = queue.accept(envelope())
    assert first.state is EventState.RECEIVED
    assert duplicate.state is EventState.DUPLICATE
    assert duplicate.event_id == first.event_id
    with runtime.connect() as db:
        count = db.execute("SELECT COUNT(*) FROM event_reconciliation_event").fetchone()[0]
    assert count == 1


def test_semantic_duplicate_is_retained_without_duplicate_work(runtime: RuntimeDatabase) -> None:
    queue = DurableEventQueue(runtime, clock=Clock())
    digest = "b" * 64
    first = queue.accept(envelope(delivery="d1", snapshot=digest))
    second = queue.accept(envelope(delivery="d2", snapshot=digest))
    assert second.state is EventState.DUPLICATE
    assert second.duplicate_of == first.event_id
    with runtime.connect() as db:
        count = db.execute("SELECT COUNT(*) FROM event_reconciliation_event").fetchone()[0]
    assert count == 2


def test_event_identity_is_stable_when_current_snapshot_is_attached() -> None:
    original = envelope()
    enriched = CanonicalEventEnvelope(
        **{**original.__dict__, "normalized_snapshot_digest": "b" * 64}
    )
    assert enriched.event_id == original.event_id


def test_claim_serializes_and_lease_expiry_recovers(runtime: RuntimeDatabase) -> None:
    clock = Clock()
    queue = DurableEventQueue(runtime, clock=clock)
    queue.accept(envelope())
    assert queue.claim("worker-1", lease_for=timedelta(seconds=30)) is not None
    assert queue.claim("worker-2") is None
    clock.now += timedelta(seconds=31)
    assert queue.claim("worker-2") is not None


def test_aggregate_lease_serializes_distinct_events_for_one_object(
    runtime: RuntimeDatabase,
) -> None:
    queue = DurableEventQueue(runtime, clock=Clock())
    queue.accept(envelope(delivery="d1"))
    queue.accept(envelope(delivery="d2"))
    claimed = queue.claim("worker-1")
    assert claimed is not None
    assert queue.claim("worker-2") is None
    queue.fail(claimed.envelope.event_id, "retry")
    assert queue.claim("worker-2") is not None


def test_invalid_state_transition_is_rejected(runtime: RuntimeDatabase) -> None:
    queue = DurableEventQueue(runtime, clock=Clock())
    accepted = queue.accept(envelope())
    with pytest.raises(RuntimeError, match="invalid event transition"):
        queue.transition(accepted.event_id, EventState.APPLIED)


def test_retry_backoff_and_dead_letter(runtime: RuntimeDatabase) -> None:
    queue = DurableEventQueue(runtime, clock=Clock())
    accepted = queue.accept(envelope())
    assert queue.fail(accepted.event_id, "temporary", max_attempts=2) is EventState.FAILED
    assert queue.fail(accepted.event_id, "poison", max_attempts=2) is EventState.DEAD_LETTER
    assert queue.metrics()["counts"]["dead_letter"] == 1


def test_monitor_only_requires_approval_for_allowlisted_mutation() -> None:
    evaluator = AutonomyPolicyEvaluator(AutonomyPolicy())
    result = evaluator.evaluate(envelope(), plan(mutation()))
    assert result.decision is PolicyDecision.REQUIRE_ATTENDED_APPROVAL
    assert "monitor-only" in result.reasons[0]


def test_bounded_policy_auto_applies_exact_allowlist() -> None:
    evaluator = AutonomyPolicyEvaluator(
        AutonomyPolicy(mode=AutonomyMode.BOUNDED_AUTO_APPLY, kill_switch=False)
    )
    assert evaluator.evaluate(envelope(), plan(mutation())).decision is PolicyDecision.AUTO_APPLY


@pytest.mark.parametrize(
    "changed",
    [
        mutation(kind=MutationKind.DELEGATION),
        mutation(inferred=True),
        mutation(other=True),
        mutation(destination="#Shared"),
        mutation(ryan_owned=False),
        mutation(kind=MutationKind.TOMBSTONE),
    ],
)
def test_consequential_mutations_require_attended_approval(changed: MutationIntent) -> None:
    evaluator = AutonomyPolicyEvaluator(
        AutonomyPolicy(mode=AutonomyMode.BOUNDED_AUTO_APPLY, kill_switch=False)
    )
    assert (
        evaluator.evaluate(envelope(), plan(changed)).decision
        is PolicyDecision.REQUIRE_ATTENDED_APPROVAL
    )


@pytest.mark.parametrize(
    "blocked_plan",
    [
        plan(mutation(kind=MutationKind.DESTRUCTIVE)),
        plan(mutation(field="credential")),
        plan(mutation(), conflicts=("authority conflict",)),
        plan(mutation(), mappings=2),
    ],
)
def test_prohibited_or_conflicting_plans_block(blocked_plan: EventPlan) -> None:
    evaluator = AutonomyPolicyEvaluator(
        AutonomyPolicy(mode=AutonomyMode.BOUNDED_AUTO_APPLY, kill_switch=False)
    )
    assert evaluator.evaluate(envelope(), blocked_plan).decision is PolicyDecision.BLOCK


def test_authority_disagreement_and_causal_loop_block() -> None:
    evaluator = AutonomyPolicyEvaluator(
        AutonomyPolicy(
            mode=AutonomyMode.BOUNDED_AUTO_APPLY,
            kill_switch=False,
            authority_agrees=False,
        )
    )
    assert evaluator.evaluate(envelope(depth=5), plan(mutation())).decision is PolicyDecision.BLOCK


def test_approval_binds_exact_plan_and_expires() -> None:
    planned = plan(mutation())
    approval = ApprovalBinding(
        approval_id="approval-1",
        actor="Ryan",
        event_ids=planned.event_ids,
        snapshot_digests=planned.snapshot_digests,
        plan_digest=planned.plan_digest,
        authority_version=planned.authority_version,
        policy_version=planned.policy_version,
        approved_at=NOW,
        expires_at=NOW + timedelta(minutes=10),
    )
    approval.validate(planned, now=NOW)
    with pytest.raises(PermissionError, match="expired"):
        approval.validate(planned, now=NOW + timedelta(minutes=11))
    stale = EventPlan(**{**planned.__dict__, "expected_checkpoint": "changed", "plan_digest": ""})
    with pytest.raises(PermissionError, match="plan digest"):
        approval.validate(stale, now=NOW)


def test_universal_inbox_exact_capture_is_eligible_only_after_activation() -> None:
    item = {
        "data_source_id": "universal-inbox",
        "creator_id": "ryan",
        "destination": "#Personal",
        "outcome": "Renew passport",
        "task": "Submit renewal application",
        "subtasks": ["Take photo"],
        "ryan_owned": True,
    }
    monitor = assess_universal_inbox(item, policy=AutonomyPolicy(), approved_creator_ids=("ryan",))
    assert monitor.decision is PolicyDecision.REQUIRE_ATTENDED_APPROVAL
    active = assess_universal_inbox(
        item,
        policy=AutonomyPolicy(mode=AutonomyMode.BOUNDED_AUTO_APPLY, kill_switch=False),
        approved_creator_ids=("ryan",),
    )
    assert active.eligible
    assert active.decision is PolicyDecision.AUTO_APPLY


def test_universal_inbox_ambiguity_and_limits_require_approval() -> None:
    assessment = assess_universal_inbox(
        {
            "data_source_id": "universal-inbox",
            "creator_id": "unknown",
            "destination": "",
            "outcome": "",
            "task": "something",
            "subtasks": list(range(6)),
            "delegated": True,
            "inferred_material_fields": True,
        },
        policy=AutonomyPolicy(mode=AutonomyMode.BOUNDED_AUTO_APPLY, kill_switch=False),
        approved_creator_ids=("ryan",),
    )
    assert not assessment.eligible
    assert assessment.decision is PolicyDecision.REQUIRE_ATTENDED_APPROVAL
    assert len(assessment.reasons) >= 5


def test_feedback_loop_only_suppresses_exact_expected_readback(runtime: RuntimeDatabase) -> None:
    guard = FeedbackLoopGuard(runtime, clock=Clock())
    guard.remember(
        provider=EventProvider.NOTION,
        object_id="page-1",
        correlation_id="corr-1",
        expected_snapshot_digest="a" * 64,
    )
    assert (
        guard.classify(
            provider=EventProvider.NOTION,
            object_id="page-1",
            correlation_id="corr-1",
            actual_snapshot_digest="a" * 64,
        )
        == "self_originated_verified"
    )
    assert (
        guard.classify(
            provider=EventProvider.NOTION,
            object_id="page-1",
            correlation_id="corr-1",
            actual_snapshot_digest="b" * 64,
        )
        == "concurrent_change_reconcile"
    )


class Snapshots:
    def __init__(self) -> None:
        self.value: dict[str, Any] = {"execution_due_date": "2026-08-02"}

    def load_current(self, event: CanonicalEventEnvelope) -> dict[str, Any]:
        del event
        return dict(self.value)


class Planner:
    def __init__(self, snapshots: Snapshots, *, classification: str = "actionable") -> None:
        self.snapshots = snapshots
        self.classification = classification

    def plan(self, event: CanonicalEventEnvelope, snapshot: dict[str, Any]) -> EventPlan:
        return EventPlan(
            event_ids=(event.event_id,),
            snapshot_digests=(deterministic_digest(snapshot),),
            authority_version="8.2.1",
            policy_version="8.3.0-rc1",
            mutations=() if self.classification == "informational" else (mutation(),),
            expected_checkpoint="checkpoint",
            correlation_id=event.correlation_id,
            generated_at=NOW,
            expires_at=NOW + timedelta(minutes=10),
            classification=self.classification,
        )


class Applier:
    def __init__(self, *, consistent: bool = True) -> None:
        self.consistent = consistent
        self.calls = 0

    def apply_and_readback(self, planned: EventPlan) -> dict[str, Any]:
        self.calls += 1
        return {"consistent": self.consistent, "plan_digest": planned.plan_digest}


def test_event_processor_monitor_only_performs_zero_provider_writes(
    runtime: RuntimeDatabase,
) -> None:
    queue = DurableEventQueue(runtime, clock=Clock())
    queue.accept(envelope())
    claimed = queue.claim("worker")
    assert claimed is not None
    snapshots = Snapshots()
    applier = Applier()
    processor = EventProcessor(
        queue,
        snapshots,
        Planner(snapshots),
        applier,
        AutonomyPolicyEvaluator(AutonomyPolicy()),
    )
    assert processor.process(claimed, "worker") is EventState.AWAITING_APPROVAL
    assert applier.calls == 0


def test_event_processor_auto_apply_rechecks_snapshot_and_records_receipt(
    runtime: RuntimeDatabase,
) -> None:
    queue = DurableEventQueue(runtime, clock=Clock())
    accepted = queue.accept(envelope())
    claimed = queue.claim("worker")
    assert claimed is not None
    snapshots = Snapshots()
    applier = Applier()
    processor = EventProcessor(
        queue,
        snapshots,
        Planner(snapshots),
        applier,
        AutonomyPolicyEvaluator(
            AutonomyPolicy(mode=AutonomyMode.BOUNDED_AUTO_APPLY, kill_switch=False)
        ),
    )
    assert processor.process(claimed, "worker") is EventState.APPLIED
    assert applier.calls == 1
    with runtime.connect() as db:
        receipt_count = db.execute(
            "SELECT COUNT(*) FROM event_reconciliation_receipt WHERE event_id=?",
            (accepted.event_id,),
        ).fetchone()[0]
    assert receipt_count == 1


def test_event_processor_informational_event_never_writes(runtime: RuntimeDatabase) -> None:
    queue = DurableEventQueue(runtime, clock=Clock())
    queue.accept(envelope())
    claimed = queue.claim("worker")
    assert claimed is not None
    snapshots = Snapshots()
    applier = Applier()
    processor = EventProcessor(
        queue,
        snapshots,
        Planner(snapshots, classification="informational"),
        applier,
        AutonomyPolicyEvaluator(
            AutonomyPolicy(mode=AutonomyMode.BOUNDED_AUTO_APPLY, kill_switch=False)
        ),
    )
    assert processor.process(claimed, "worker") is EventState.INFORMATIONAL
    assert applier.calls == 0


class ChangingSnapshots(Snapshots):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def load_current(self, event: CanonicalEventEnvelope) -> dict[str, Any]:
        self.calls += 1
        if self.calls > 1:
            self.value["execution_due_date"] = "2026-08-03"
        return super().load_current(event)


def test_stale_snapshot_replans_without_provider_write(runtime: RuntimeDatabase) -> None:
    queue = DurableEventQueue(runtime, clock=Clock())
    queue.accept(envelope())
    claimed = queue.claim("worker")
    assert claimed is not None
    snapshots = ChangingSnapshots()
    applier = Applier()
    processor = EventProcessor(
        queue,
        snapshots,
        Planner(snapshots),
        applier,
        AutonomyPolicyEvaluator(
            AutonomyPolicy(mode=AutonomyMode.BOUNDED_AUTO_APPLY, kill_switch=False)
        ),
    )
    assert processor.process(claimed, "worker") is EventState.FAILED
    assert applier.calls == 0


def test_readback_mismatch_preserves_event_for_recovery(runtime: RuntimeDatabase) -> None:
    queue = DurableEventQueue(runtime, clock=Clock())
    queue.accept(envelope())
    claimed = queue.claim("worker")
    assert claimed is not None
    snapshots = Snapshots()
    applier = Applier(consistent=False)
    processor = EventProcessor(
        queue,
        snapshots,
        Planner(snapshots),
        applier,
        AutonomyPolicyEvaluator(
            AutonomyPolicy(mode=AutonomyMode.BOUNDED_AUTO_APPLY, kill_switch=False)
        ),
    )
    assert processor.process(claimed, "worker") is EventState.FAILED
    assert applier.calls == 1
    assert queue.metrics()["counts"]["failed"] == 1


def test_manual_replay_uses_same_canonical_envelope() -> None:
    manual = new_manual_envelope(
        event_type="repair",
        object_id="task-1",
        policy_version="8.3.0-rc1",
        source_checkpoint="checkpoint-1",
    )
    assert manual.provider is EventProvider.MANUAL
    assert manual.source_checkpoint == "checkpoint-1"
    assert len(manual.event_id) == 68


class BackstopSource:
    def __init__(self, events: tuple[CanonicalEventEnvelope, ...]) -> None:
        self.events = events

    def changes_since(
        self, provider: EventProvider, checkpoint: str
    ) -> tuple[tuple[CanonicalEventEnvelope, ...], str]:
        assert provider is EventProvider.TODOIST
        assert checkpoint == "cursor-1"
        return self.events, "cursor-2"


def test_backstop_uses_same_queue_and_reports_duplicate(runtime: RuntimeDatabase) -> None:
    queue = DurableEventQueue(runtime, clock=Clock())
    event = envelope()
    queue.accept(event)
    result = EventBackstop(queue, BackstopSource((event,))).run(EventProvider.TODOIST, "cursor-1")
    assert result.resulting_checkpoint == "cursor-2"
    assert result.accepted == 0
    assert result.duplicates == 1


def test_operator_kill_switch_requires_exact_activation(runtime: RuntimeDatabase) -> None:
    queue = DurableEventQueue(runtime, clock=Clock())
    operator = EventOperator(runtime, queue)
    operator.pause_auto_apply()
    assert operator.controls()["kill_switch"] == "true"
    with pytest.raises(PermissionError, match="exact production policy"):
        operator.resume_auto_apply(exact_policy_activation_authorized=False)
    operator.resume_auto_apply(exact_policy_activation_authorized=True)
    assert operator.controls()["auto_apply"] == "enabled"


def test_dead_letter_release_is_attended_and_auditable(runtime: RuntimeDatabase) -> None:
    queue = DurableEventQueue(runtime, clock=Clock())
    accepted = queue.accept(envelope())
    queue.fail(accepted.event_id, "poison", max_attempts=1)
    operator = EventOperator(runtime, queue)
    operator.release_dead_letter(accepted.event_id, actor="Ryan", reason="fixture corrected")
    inspected = operator.inspect(accepted.event_id)
    assert inspected["state"] == "failed"
    assert "released by Ryan" in inspected["reason"]


def call_wsgi(
    app: EventReceiverApplication,
    *,
    path: str,
    body: bytes = b"",
    headers: dict[str, str] | None = None,
    method: str = "POST",
) -> tuple[str, dict[str, Any]]:
    status = ""

    def start_response(value: str, response_headers: list[tuple[str, str]]) -> None:
        nonlocal status
        status = value
        assert response_headers

    environ: dict[str, Any] = {
        "PATH_INFO": path,
        "REQUEST_METHOD": method,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": BytesIO(body),
    }
    for name, value in (headers or {}).items():
        environ["HTTP_" + name.upper().replace("-", "_")] = value
    response = b"".join(app(environ, start_response))
    return status, json.loads(response)


def test_receiver_stays_unready_and_rejects_ingress_until_activation(
    runtime: RuntimeDatabase,
) -> None:
    app = EventReceiverApplication(
        DurableEventQueue(runtime),
        EventReceiverConfig("todoist", "notion", "8.3.0-rc1"),
    )
    assert call_wsgi(app, path="/healthz", method="GET")[0] == "200 OK"
    assert call_wsgi(app, path="/readyz", method="GET")[0] == "503 Service Unavailable"
    assert call_wsgi(app, path="/webhooks/todoist", body=b"{}")[0] == "503 Service Unavailable"


def test_receiver_persists_todoist_event_before_success(runtime: RuntimeDatabase) -> None:
    payload = {
        "event_name": "item:updated",
        "event_data": {"id": "task-1"},
        "triggered_at": NOW.isoformat(),
        "version": "10",
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    signature = base64.b64encode(hmac.new(b"secret", raw, hashlib.sha256).digest()).decode()
    app = EventReceiverApplication(
        DurableEventQueue(runtime),
        EventReceiverConfig("secret", "notion", "8.3.0-rc1", ingress_enabled=True),
    )
    status, response = call_wsgi(
        app,
        path="/webhooks/todoist",
        body=raw,
        headers={
            "x-todoist-hmac-sha256": signature,
            "x-todoist-delivery-id": "delivery-http",
        },
    )
    assert status == "200 OK"
    with runtime.connect() as db:
        persisted = db.execute(
            "SELECT state FROM event_reconciliation_event WHERE event_id=?",
            (response["event_id"],),
        ).fetchone()
    assert persisted[0] == "received"


def test_reference_queue_acceptance_meets_ten_second_target(runtime: RuntimeDatabase) -> None:
    queue = DurableEventQueue(runtime, clock=Clock())
    started = time.perf_counter()
    for index in range(200):
        queue.accept(envelope(delivery=f"burst-{index}"))
    elapsed = time.perf_counter() - started
    assert elapsed < 10
    assert queue.metrics()["counts"]["received"] == 200
