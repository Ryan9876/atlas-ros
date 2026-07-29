from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from atlas_ros.adapters.notion_operational_state import NotionOperationalStateAdapter
from atlas_ros.adapters.todoist_command_source import TodoistCommandSourceAdapter
from atlas_ros.adapters.todoist_operational_state import TodoistOperationalStateAdapter
from atlas_ros.application.command_lifecycle import CommandLifecycleCoordinator
from atlas_ros.application.operational_awareness import OperationalAwarenessCoordinator
from atlas_ros.capabilities.operational_awareness import (
    CommitmentIntelligence,
    ExecutionContextService,
    OperatingBriefService,
    OperationalSnapshotBuilder,
    WorkGraphHygieneService,
    WorkStateIntelligence,
)
from atlas_ros.contracts.advisory_v1 import ProvenanceRecord, ValueOrigin
from atlas_ros.contracts.operational_awareness import (
    AcceptanceState,
    AtlasCommandType,
    AuthorityLevel,
    AuthoritativeSystem,
    EvidenceConflictV1,
    FreshnessAssessmentV1,
    FreshnessState,
    Materiality,
    NormalizedOperationalRecordV1,
    OperationalEvidenceV1,
    OperationalRecordRefV1,
    OperationalRecordType,
    RepairClass,
)
from atlas_ros.planning.operational_awareness import OperationalLifecycleExecutionPlanner
from atlas_ros.policy.operational_awareness import load_operational_awareness_policy

NOW = datetime(2026, 7, 28, 16, 0, tzinfo=UTC)


def _record(
    record_id: str,
    title: str,
    *,
    record_type: OperationalRecordType = OperationalRecordType.ACTION_RECORD,
    parent: str | None = None,
    task_id: str | None = None,
    updated_at: datetime = NOW,
    **changes: object,
) -> NormalizedOperationalRecordV1:
    ref = OperationalRecordRefV1.create(
        record_type=record_type,
        canonical_record_id=record_id,
        authoritative_system=AuthoritativeSystem.NOTION,
        canonical_url=f"https://notion.example/{record_id}",
        parent_record_id=parent,
        source_revision=updated_at.isoformat(),
    )
    values: dict[str, object] = {
        "record_ref": ref,
        "title": title,
        "observed_state": "active",
        "owner": "Ryan",
        "accountable_party": "Ryan",
        "definition_of_done": ("verified outcome",),
        "updated_at": updated_at.isoformat(),
        "todoist_task_id": task_id,
    }
    values.update(changes)
    return NormalizedOperationalRecordV1.create(**values)


def _snapshot(
    *records: NormalizedOperationalRecordV1,
    contradictions: tuple[EvidenceConflictV1, ...] = (),
):
    return OperationalSnapshotBuilder(load_operational_awareness_policy()).build(
        records,
        scope="work",
        authority_identities=("github:authority", "notion:system-state", "todoist:read"),
        contradictions=contradictions,
        generated_at=NOW,
        replay_id="v730-test-replay",
    )


def _conflict(record: NormalizedOperationalRecordV1) -> EvidenceConflictV1:
    freshness = FreshnessAssessmentV1.create(
        state=FreshnessState.CONTRADICTED,
        evaluated_at=NOW.isoformat(),
        source_time=NOW.isoformat(),
        age_days=0.0,
        threshold_days=7.0,
        rationale="authoritative systems disagree",
    )
    provenance = (
        ProvenanceRecord(
            source_ref=record.record_ref.canonical_url or record.record_ref.canonical_record_id,
            origin=ValueOrigin.OBSERVED,
            observed_at=NOW.isoformat(),
        ),
    )
    observations = tuple(
        OperationalEvidenceV1.create(
            evidence_id=f"evidence:{value}",
            record_reference=record.record_ref,
            observed_fact="completed",
            observed_value=value == "true",
            observation_time=NOW.isoformat(),
            source_time=NOW.isoformat(),
            value_origin=ValueOrigin.OBSERVED,
            authority_level=(
                AuthorityLevel.AUTHORITATIVE_DYNAMIC
                if value == "true"
                else AuthorityLevel.EXECUTION
            ),
            freshness=freshness,
            provenance=provenance,
            redaction_state="not_redacted",
        )
        for value in ("true", "false")
    )
    return EvidenceConflictV1.create(
        conflicting_observations=observations,
        affected_field="completed",
        authority_comparison="Notion and Todoist disagree",
        materiality=Materiality.CRITICAL,
        safe_resolution=None,
        required_verification_or_decision="Verify Definition of Done and provider state",
    )


def test_v730_contracts_are_digest_bound_and_replay_safe() -> None:
    record = _record("A-1", "Persistent outcome")
    assert record.verify_digest()
    replay = NormalizedOperationalRecordV1.model_validate(record.model_dump(mode="json"))
    assert replay == record
    assert replay.verify_digest()
    assert _snapshot(record).snapshot_digest == _snapshot(record).snapshot_digest


def test_completed_child_does_not_complete_parent() -> None:
    parent = _record("A-1", "Persistent outcome", child_ids=("S-1",))
    child = _record(
        "S-1",
        "Completed child",
        record_type=OperationalRecordType.EXECUTION_STEP,
        parent="A-1",
        completed=True,
        observed_state="completed",
        completion_evidence=("provider receipt",),
    )
    states = WorkStateIntelligence(load_operational_awareness_policy()).estimate_all(
        _snapshot(parent, child)
    )
    by_id = {item.record_reference.canonical_record_id: item for item in states}
    assert by_id["S-1"].effective_state.value == "completed"
    assert by_id["A-1"].effective_state.value == "active"


def test_technical_completion_and_conflict_fail_closed() -> None:
    record = _record(
        "A-1",
        "Await approval",
        technically_complete=True,
        approval_required=True,
        approval_received=False,
    )
    conflict = _conflict(record)
    state = WorkStateIntelligence(load_operational_awareness_policy()).estimate_all(
        _snapshot(record, contradictions=(conflict,))
    )[0]
    assert state.effective_state.value == "awaiting_validation"
    assert state.freshness.state == FreshnessState.CONTRADICTED
    assert state.conflicting_evidence == (conflict,)


def test_commitments_preserve_acceptance_and_ambiguous_language() -> None:
    policy = load_operational_awareness_policy()
    engine = CommitmentIntelligence(policy)
    first = engine.candidate_from_text(
        "Maybe Tina can review this", source_ref="note:1", observed_at=NOW
    )
    second = engine.candidate_from_text(
        "Maybe Tina can review this", source_ref="note:1", observed_at=NOW
    )
    assert first == second
    assert first.ambiguity
    assert first.proposed_commitment_type.value == "unconfirmed_conversational_commitment"
    delegated = _record(
        "D-1",
        "Firewall findings",
        record_type=OperationalRecordType.DELEGATED_WORK,
        delegated=True,
        responsible_party="Tina",
        acceptance_status=AcceptanceState.UNCONFIRMED,
        expected_outcome="Provide findings",
        checkpoint="2026-07-27T16:00:00+00:00",
    )
    snapshot = _snapshot(delegated)
    states = WorkStateIntelligence(policy).estimate_all(snapshot)
    assessment = engine.assess_all(snapshot, states)[0]
    assert assessment.acceptance_status == AcceptanceState.UNCONFIRMED
    assert assessment.follow_up_disposition.value == "verification_required"


def test_brief_is_exception_only_deterministic_and_budgeted() -> None:
    policy = load_operational_awareness_policy()
    records = tuple(
        _record(
            f"A-{index:02d}",
            f"Blocked outcome {index}",
            observed_state="blocked",
            blockers=(f"blocker-{index}",),
            priority=1 if index == 0 else 2,
        )
        for index in range(14)
    )
    snapshot = _snapshot(*records)
    states = WorkStateIntelligence(policy).estimate_all(snapshot)
    brief = OperatingBriefService(policy).generate(snapshot, states, ())
    item_count = 1 + sum(
        len(items)
        for items in (
            brief.decisions_requiring_ryan,
            brief.new_or_worsened_blockers,
            brief.delegated_work_requiring_follow_up,
            brief.overdue_or_at_risk_commitments,
            brief.stale_or_contradictory_work_state,
            brief.material_completions,
        )
    )
    assert item_count == policy.brief.item_budget
    assert brief.highest_value_next_action is not None
    assert "4 additional" in brief.overflow_summary
    assert brief == OperatingBriefService(policy).generate(snapshot, states, ())


def test_context_resumption_is_evidence_backed_or_unknown() -> None:
    policy = load_operational_awareness_policy()
    known = _record(
        "A-1",
        "Resume work",
        extra={
            "where_execution_stopped": "Validation step 3",
            "last_confirmed_action": "Schema compiled",
            "next_action": "Run compatibility tests",
            "resumption_evidence": ["receipt:123"],
        },
    )
    unknown = _record("A-2", "Unknown resumption")
    snapshot = _snapshot(known, unknown)
    states = WorkStateIntelligence(policy).estimate_all(snapshot)
    service = ExecutionContextService(policy)
    assert (
        service.resume(snapshot, states, record_id="A-1").where_execution_stopped
        == "Validation step 3"
    )
    missing = service.resume(snapshot, states, record_id="A-2")
    assert missing.where_execution_stopped is None
    assert missing.minimum_verification_required


def test_hygiene_is_deterministic_protects_history_and_only_proposes() -> None:
    policy = load_operational_awareness_policy()
    duplicate_a = _record("A-1", "Same action", task_id="T-1")
    duplicate_b = _record("A-2", "Same action", task_id="T-1")
    protected = _record(
        "R-1",
        "Historical review",
        record_type=OperationalRecordType.REVIEW_RECORD,
        protected_history=True,
        observed_state="blocked",
    )
    snapshot = _snapshot(duplicate_a, duplicate_b, protected)
    states = WorkStateIntelligence(policy).estimate_all(snapshot)
    service = WorkGraphHygieneService(policy)
    first = service.scan(snapshot, states)
    assert first == service.scan(snapshot, states)
    assert {item.rule_id for item in first} >= {
        "duplicate-record",
        "duplicate-todoist-representation",
        "blocked-without-blocker",
    }
    protected_finding = next(
        item
        for item in first
        if item.affected_records[0].canonical_record_id == "R-1"
    )
    assert protected_finding.repair_eligibility == RepairClass.PROTECTED
    with pytest.raises(PermissionError):
        service.propose(protected_finding)
    proposal = service.propose(
        next(
            item
            for item in first
            if item.repair_eligibility != RepairClass.PROTECTED
        )
    )
    assert proposal.expected_provider_operations
    assert "authorization" in " ".join(proposal.preconditions)


def _delegation_snapshot(*, active_checkpoints: tuple[str, ...] = ()):
    parent = _record(
        "A-1",
        "Update firewall rules",
        task_id="P-1",
        child_ids=("S-1",),
        extra={"active_ryan_checkpoint_ids": active_checkpoints},
    )
    source = _record(
        "S-1",
        "Delegate firewall review",
        record_type=OperationalRecordType.EXECUTION_STEP,
        parent="A-1",
        task_id="S-1-TASK",
        completed=True,
        completion_evidence=("explicit command",),
    )
    return _snapshot(parent, source)


def test_command_lifecycle_preserves_parent_projects_one_checkpoint_and_replays() -> None:
    source = TodoistCommandSourceAdapter().extract(
        {
            "id": "S-1-TASK",
            "parent_id": "P-1",
            "updated_at": NOW.isoformat(),
            "content": "@atlas delegate: Tina",
            "description": (
                "outcome: Provide firewall findings\n"
                "done-when: Findings documented\n"
                "follow-up: Friday"
            ),
        }
    )
    coordinator = CommandLifecycleCoordinator(
        load_operational_awareness_policy(), OperationalLifecycleExecutionPlanner()
    )
    first = coordinator.prepare(source, _delegation_snapshot(active_checkpoints=("OLD-1",)))
    second = coordinator.prepare(source, _delegation_snapshot(active_checkpoints=("OLD-1",)))
    assert first == second
    assert first.command.command_type == AtlasCommandType.DELEGATE
    assert first.lifecycle_plan is not None
    assert first.canonical_plan is not None
    assert first.lifecycle_plan.next_action_projection.preserves_parent
    assert first.lifecycle_plan.next_action_projection.active_checkpoint_count_after == 1
    assert first.lifecycle_plan.next_action_projection.replaces_task_ids == ("OLD-1",)
    assert all(
        operation.target != "P-1" or operation.action != "complete"
        for operation in first.canonical_plan.operations
    )
    assert first.receipt.provider_write_count == 0


def test_command_ambiguity_and_missing_assignee_fail_closed() -> None:
    source = TodoistCommandSourceAdapter().extract(
        {
            "id": "S-1-TASK",
            "parent_id": "P-1",
            "updated_at": NOW.isoformat(),
            "content": "@atlas delegate",
            "description": "outcome: Provide findings\ndone-when: Findings documented",
        }
    )
    result = CommandLifecycleCoordinator(
        load_operational_awareness_policy(), OperationalLifecycleExecutionPlanner()
    ).prepare(
        source, _delegation_snapshot()
    )
    assert result.interpretation.blockers == ("resolve the assignee identity",)
    assert result.lifecycle_plan is None
    assert result.canonical_plan is None
    assert result.receipt.provider_write_count == 0


def test_parent_closes_only_after_verified_definition_of_done() -> None:
    policy = load_operational_awareness_policy()
    incomplete_parent = _record("A-1", "Outcome", task_id="P-1", completion_evidence=())
    complete_parent = _record(
        "A-2",
        "Outcome 2",
        task_id="P-2",
        completion_evidence=("verified receipt",),
        approval_received=True,
    )
    source_one = _record(
        "S-1",
        "Complete",
        record_type=OperationalRecordType.EXECUTION_STEP,
        parent="A-1",
        task_id="T-1",
    )
    source_two = _record(
        "S-2",
        "Complete",
        record_type=OperationalRecordType.EXECUTION_STEP,
        parent="A-2",
        task_id="T-2",
    )
    coordinator = CommandLifecycleCoordinator(policy, OperationalLifecycleExecutionPlanner())
    first = coordinator.prepare(
        TodoistCommandSourceAdapter().extract(
            {
                "id": "T-1",
                "parent_id": "P-1",
                "updated_at": NOW.isoformat(),
                "content": "@atlas complete",
            }
        ),
        _snapshot(incomplete_parent, source_one),
    )
    second = coordinator.prepare(
        TodoistCommandSourceAdapter().extract(
            {
                "id": "T-2",
                "parent_id": "P-2",
                "updated_at": NOW.isoformat(),
                "content": "@atlas complete",
            }
        ),
        _snapshot(complete_parent, source_two),
    )
    assert first.lifecycle_plan is not None and second.lifecycle_plan is not None
    assert not any(
        item.action == "complete_parent_after_definition_of_done"
        for item in first.lifecycle_plan.todoist_operations
    )
    assert any(
        item.action == "complete_parent_after_definition_of_done"
        for item in second.lifecycle_plan.todoist_operations
    )


@dataclass
class _ReadPort:
    records: tuple[NormalizedOperationalRecordV1, ...]

    def read_records(self, *, scope: str) -> tuple[NormalizedOperationalRecordV1, ...]:
        assert scope == "work"
        return self.records

    def authority_identities(self) -> tuple[str, ...]:
        return ("github", "notion", "todoist")

    def missing_sources(self) -> tuple[str, ...]:
        return ()

    def contradictions(self) -> tuple[EvidenceConflictV1, ...]:
        return ()


def test_coordinator_and_adapters_prove_zero_live_writes() -> None:
    notion = NotionOperationalStateAdapter().normalize(
        [
            {
                "id": "A-1",
                "last_edited_time": NOW.isoformat(),
                "title": "Outcome",
                "state": "active",
                "definition_of_done": ["done"],
            }
        ]
    )
    todoist = TodoistOperationalStateAdapter().normalize(
        [
            {
                "id": "T-1",
                "updated_at": NOW.isoformat(),
                "content": "Checkpoint",
                "completed": False,
                "definition_of_done": ["done"],
            }
        ]
    )
    result = OperationalAwarenessCoordinator(load_operational_awareness_policy()).run(
        _ReadPort(notion + todoist), scope="work", generated_at=NOW
    )
    assert result.receipt.provider_writes == 0
    assert all(item.provider_writes == 0 for item in result.receipt.stage_receipts)
    assert result.receipt.verify_digest()


def test_required_evaluation_scenario_inventory_is_complete() -> None:
    path = Path("tests/fixtures/operational-awareness/v730-scenarios.json")
    fixture = json.loads(path.read_text())
    assert fixture["scenario_count"] == 51
    assert len(fixture["scenarios"]) == 51
    assert all(item["live_provider_writes"] == 0 for item in fixture["scenarios"])
