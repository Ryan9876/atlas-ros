from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from atlas_ros.adapters.delegated_lifecycle_mapping import (
    DelegatedLifecycleProviderMapper,
)
from atlas_ros.adapters.todoist_command_source import TodoistCommandSourceAdapter
from atlas_ros.application.command_lifecycle import CommandLifecycleCoordinator
from atlas_ros.capabilities.operational_awareness import OperationalSnapshotBuilder
from atlas_ros.contracts.operational_awareness import (
    AtlasCommandType,
    AuthoritativeSystem,
    NormalizedOperationalRecordV1,
    OperationalRecordRefV1,
    OperationalRecordType,
)
from atlas_ros.planning.operational_awareness import OperationalLifecycleExecutionPlanner
from atlas_ros.policy.operational_awareness import load_operational_awareness_policy
from atlas_ros.reconciliation.delegated_lifecycle import DelegatedLifecycleReconciler

NOW = datetime(2026, 7, 30, 17, 0, tzinfo=UTC)
FIXTURES = json.loads(
    Path("tests/fixtures/operational-awareness/v800-task-update-delegation.json").read_text()
)


def _record(
    record_id: str,
    title: str,
    *,
    record_type: OperationalRecordType = OperationalRecordType.ACTION_RECORD,
    parent: str | None = None,
    task_id: str | None = None,
    active_checkpoints: tuple[str, ...] = (),
    definition_of_done: tuple[str, ...] = (),
    completion_evidence: tuple[str, ...] = (),
) -> NormalizedOperationalRecordV1:
    ref = OperationalRecordRefV1.create(
        record_type=record_type,
        canonical_record_id=record_id,
        authoritative_system=AuthoritativeSystem.NOTION,
        canonical_url=f"https://notion.example/{record_id}",
        parent_record_id=parent,
        source_revision=NOW.isoformat(),
    )
    return NormalizedOperationalRecordV1.create(
        record_ref=ref,
        title=title,
        observed_state="active",
        owner="Ryan",
        accountable_party="Ryan",
        definition_of_done=definition_of_done,
        completion_evidence=completion_evidence,
        updated_at=NOW.isoformat(),
        todoist_task_id=task_id,
        extra={"active_ryan_checkpoint_ids": active_checkpoints},
    )


def _snapshot(*, active_checkpoints: tuple[str, ...] = ()):
    parent = _record(
        "A-1",
        "Workday access request 276412207",
        task_id="P-1",
        active_checkpoints=active_checkpoints,
    )
    source = _record(
        "S-1",
        "Workday access task update",
        record_type=OperationalRecordType.EXECUTION_STEP,
        parent="A-1",
        task_id="S-1-TASK",
    )
    return OperationalSnapshotBuilder(load_operational_awareness_policy()).build(
        (parent, source),
        scope="work",
        authority_identities=("github", "notion", "todoist"),
        generated_at=NOW,
        replay_id="v800-conformance",
    )


def _prepare(text: str, *, active_checkpoints: tuple[str, ...] = ()):
    source = TodoistCommandSourceAdapter().extract(
        {
            "id": "S-1-TASK",
            "parent_id": "P-1",
            "updated_at": NOW.isoformat(),
            "content": text,
        }
    )
    return CommandLifecycleCoordinator(
        load_operational_awareness_policy(),
        OperationalLifecycleExecutionPlanner(),
    ).prepare(source, _snapshot(active_checkpoints=active_checkpoints))


def _positive(case_id: str) -> dict[str, object]:
    return next(item for item in FIXTURES["positive_delegation"] if item["id"] == case_id)


def test_01_existing_explicit_delegation_remains_compatible() -> None:
    result = _prepare(
        "@atlas delegate: Tina\n"
        "outcome: Provide firewall findings\n"
        "done-when: Findings documented\n"
        "follow-up: Friday"
    )
    assert result.normalization is None
    assert result.command.command_type == AtlasCommandType.DELEGATE
    assert result.interpretation.responsible_party == "Tina"
    assert result.interpretation.follow_up_checkpoint == "Friday"
    assert result.lifecycle_plan is not None


def test_02_qualified_natural_update_normalizes_to_delegate() -> None:
    case = _positive("natural-detailed")
    result = _prepare(str(case["text"]))
    assert result.normalization is not None
    assert result.normalization.classification == AtlasCommandType.DELEGATE
    assert result.command.command_type == AtlasCommandType.DELEGATE
    assert result.interpretation.responsible_party == case["responsible"]
    assert result.interpretation.expected_outcome == case["outcome"]
    assert result.interpretation.completion_criteria == (case["done_when"],)
    assert result.interpretation.follow_up_checkpoint == case["follow_up"]
    assert result.command.verify_digest()
    assert result.command.idempotency_identity.endswith(result.command.command_digest)


def test_03_person_name_mention_alone_is_not_delegation() -> None:
    result = _prepare("Bill reviewed the request.")
    assert result.command.command_type == AtlasCommandType.UPDATE
    assert result.lifecycle_plan is None
    assert "No actionable lifecycle transition" in result.interpretation.blockers


def test_04_waiting_for_bill_becomes_waiting_on() -> None:
    result = _prepare("Waiting for Bill to respond.")
    assert result.command.command_type == AtlasCommandType.WAITING_ON
    assert result.lifecycle_plan is not None
    assert (
        result.lifecycle_plan.next_action_projection.action_title
        == "Follow up on Bill to respond"
    )


def test_05_missing_responsible_party_blocks() -> None:
    result = _prepare(
        "Assigned to someone.\nExpected outcome: Access is approved.\n"
        "Done when: Approval is recorded.\nFollow up Monday."
    )
    assert result.command.command_type == AtlasCommandType.DELEGATE
    assert "Responsible party required" in result.interpretation.blockers
    assert result.lifecycle_plan is None


def test_06_missing_expected_outcome_blocks() -> None:
    result = _prepare(
        "Delegated to Bill.\nDone when: Bill confirms completion.\nFollow up Monday."
    )
    assert "Expected outcome required" in result.interpretation.blockers
    assert result.lifecycle_plan is None


def test_07_missing_completion_criteria_blocks() -> None:
    result = _prepare(
        "Bill is handling the request.\nExpected outcome: Access is approved.\n"
        "Follow up Monday."
    )
    assert "Completion criteria required" in result.interpretation.blockers
    assert result.lifecycle_plan is None


def test_08_delegate_due_and_follow_up_remain_separate() -> None:
    case = _positive("separate-dates")
    result = _prepare(str(case["text"]))
    assert result.interpretation.delegate_due == "Friday"
    assert result.interpretation.follow_up_checkpoint == "Thursday"
    assert result.lifecycle_plan is not None
    checkpoint = result.lifecycle_plan.todoist_operations[-1]
    assert checkpoint.payload["due"] == "Thursday"
    assert result.lifecycle_plan.notion_operations[0].payload["delegate_due"] == "Friday"


def test_09_ambiguous_date_meaning_blocks() -> None:
    result = _prepare(
        "Bill is handling the request Friday.\nExpected outcome: Access is approved.\n"
        "Done when: Bill confirms completion."
    )
    assert "Clarify whether the date is delegate due or Ryan follow-up" in (
        result.interpretation.blockers
    )
    assert result.lifecycle_plan is None


def test_10_explicit_follow_up_is_todoist_due_date() -> None:
    result = _prepare(str(_positive("natural-detailed")["text"]))
    assert result.lifecycle_plan is not None
    checkpoint = result.lifecycle_plan.todoist_operations[-1]
    assert checkpoint.action == "upsert_current_checkpoint"
    assert checkpoint.payload["due"] == "Monday"


def test_11_missing_follow_up_uses_compiled_undated_policy() -> None:
    result = _prepare(
        "Bill owns the request and should finish Friday.\n"
        "Expected outcome: Access is approved."
    )
    assert result.interpretation.delegate_due == "Friday"
    assert result.interpretation.follow_up_checkpoint is None
    assert result.lifecycle_plan is not None
    assert result.lifecycle_plan.todoist_operations[-1].payload["due"] is None


def test_12_existing_checkpoint_is_replaced_not_duplicated() -> None:
    result = _prepare(
        str(_positive("natural-detailed")["text"]),
        active_checkpoints=("OLD-CHECKPOINT",),
    )
    assert result.lifecycle_plan is not None
    actions = [item.action for item in result.lifecycle_plan.todoist_operations]
    assert actions == ["complete_obsolete_checkpoint", "upsert_current_checkpoint"]
    assert result.lifecycle_plan.next_action_projection.active_checkpoint_count_after == 1


def test_13_replay_creates_zero_duplicate_provider_writes() -> None:
    text = str(_positive("natural-detailed")["text"])
    first = _prepare(text, active_checkpoints=("OLD-CHECKPOINT",))
    second = _prepare(text, active_checkpoints=("OLD-CHECKPOINT",))
    assert first == second
    assert first.receipt.provider_write_count == 0
    assert first.canonical_plan == second.canonical_plan


def test_14_parent_task_remains_open_after_delegation() -> None:
    result = _prepare(str(_positive("natural-detailed")["text"]))
    assert result.lifecycle_plan is not None
    assert not any(
        item.action == "complete_parent_after_definition_of_done"
        for item in result.lifecycle_plan.todoist_operations
    )
    assert result.lifecycle_plan.next_action_projection.preserves_parent


def test_15_delegated_child_completion_does_not_complete_parent() -> None:
    result = _prepare("The delegated child is complete.")
    assert result.lifecycle_plan is not None
    assert not any(
        item.action == "complete_parent_after_definition_of_done"
        for item in result.lifecycle_plan.todoist_operations
    )


def test_16_provider_planning_has_zero_writes_before_authorization() -> None:
    result = _prepare(str(_positive("natural-detailed")["text"]))
    assert result.canonical_plan is not None
    assert result.receipt.authorization_id is None
    assert result.receipt.provider_write_count == 0


def test_17_provider_readback_verifies_notion_and_todoist_identities() -> None:
    result = _prepare(str(_positive("natural-detailed")["text"]))
    assert result.lifecycle_plan is not None
    notion = result.lifecycle_plan.notion_operations[0]
    checkpoint = result.lifecycle_plan.todoist_operations[-1]
    assessment = DelegatedLifecycleReconciler().assess(
        result.lifecycle_plan,
        notion_readback=dict(notion.expected_readback),
        todoist_readback=dict(checkpoint.expected_readback),
    )
    assert assessment.consistent
    assert len(assessment.verified_identities) == 2


def test_18_reconciliation_recovers_after_partial_failure() -> None:
    result = _prepare(str(_positive("natural-detailed")["text"]))
    assert result.lifecycle_plan is not None
    notion = result.lifecycle_plan.notion_operations[0]
    partial = DelegatedLifecycleReconciler().assess(
        result.lifecycle_plan,
        notion_readback=dict(notion.expected_readback),
        todoist_readback=None,
    )
    assert not partial.consistent
    assert partial.recovery_actions == (
        "read back checkpoint by projection identity before any retry",
    )
    assert "todoist checkpoint readback missing" in partial.missing_or_mismatched


def test_19_cookbook_examples_match_normalizer_behavior() -> None:
    cookbook = Path("docs/operations/ATLAS_ROS_V800_DELEGATION_COOKBOOK.md").read_text()
    for case in FIXTURES["positive_delegation"]:
        assert str(case["text"]) in cookbook
        assert _prepare(str(case["text"])).command.command_type == AtlasCommandType.DELEGATE
    for case in FIXTURES["negative_delegation"][:4]:
        assert str(case["text"]) in cookbook
        assert _prepare(str(case["text"])).command.command_type != AtlasCommandType.DELEGATE


@pytest.mark.parametrize("case", FIXTURES["negative_delegation"], ids=lambda item: item["id"])
def test_20_false_positive_delegation_rate_is_zero(case: dict[str, str]) -> None:
    result = _prepare(case["text"])
    assert result.command.command_type != AtlasCommandType.DELEGATE
    assert result.lifecycle_plan is None


def test_21_notion_mapping_keeps_dates_and_governance_fields_distinct() -> None:
    result = _prepare(str(_positive("separate-dates")["text"]))
    assert result.lifecycle_plan is not None
    properties = DelegatedLifecycleProviderMapper.notion_properties(
        result.lifecycle_plan.notion_operations[0]
    )
    assert properties["date:Delivery Due Date:start"] == "Friday"
    assert properties["date:Next Checkpoint:start"] == "Thursday"
    assert properties["Command Digest"] == result.command.command_digest
    assert properties["Latest Reconciliation State"] == "planned_not_executed"


def test_22_todoist_checkpoint_names_parent_outcome_and_links_notion() -> None:
    result = _prepare(str(_positive("natural-detailed")["text"]))
    assert result.lifecycle_plan is not None
    mapped = DelegatedLifecycleProviderMapper.todoist_checkpoint(
        result.lifecycle_plan.todoist_operations[-1]
    )
    assert mapped["content"] == (
        "Follow up with Bill J on Workday access request 276412207"
    )
    assert mapped["due"] == "Monday"
    assert mapped["authoritative_record_identity"] in mapped["description"]


def test_23_natural_interpretation_does_not_expand_execution_scope() -> None:
    result = _prepare(str(_positive("natural-detailed")["text"]))
    assert result.normalization is not None
    assert result.normalization.provenance
    assert result.canonical_plan is not None
    assert not hasattr(result.normalization, "authorization_id")
    assert result.receipt.completion_state == "planned_not_executed"
