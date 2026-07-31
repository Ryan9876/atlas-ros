from __future__ import annotations

import pytest

from atlas_ros.application.clarification_workflow import (
    AttendedClarificationWorkflow,
    AttendedInboxItem,
    ClarificationReplayConflict,
)
from atlas_ros.capabilities.operational_awareness import (
    ClarificationCompatibilityAdapter,
    ContextAwareClarificationAnalyzer,
)
from atlas_ros.contracts.clarification_compatibility import (
    ClarificationStatusV752,
    RelationshipClassificationV752,
)
from atlas_ros.contracts.operational_awareness import (
    AmbiguityCategory,
    ClarificationBatchDisposition,
    ClarificationContextV1,
    ClarificationReplayDisposition,
)
from atlas_ros.intent_learning_v750 import ClarificationDecisionV1


def workflow() -> AttendedClarificationWorkflow:
    return AttendedClarificationWorkflow(ContextAwareClarificationAnalyzer())


def test_batch_interrupts_at_first_ambiguous_item_and_preserves_later_independent_work() -> None:
    items = (
        AttendedInboxItem(
            capture_id="cap-1",
            correlation_id="corr-1",
            instruction='Add “Review Rivian response” to my Work tasks.',
        ),
        AttendedInboxItem(
            capture_id="cap-2",
            correlation_id="corr-2",
            instruction="build phase 1 or lew",
        ),
        AttendedInboxItem(
            capture_id="cap-3",
            correlation_id="corr-3",
            instruction="Review the Novaryn migration plan.",
        ),
        AttendedInboxItem(
            capture_id="cap-4",
            correlation_id="corr-4",
            instruction="Prepare the Acme review",
        ),
    )

    plan = workflow().plan_batch(items)

    assert plan.clarification_capture_id == "cap-2"
    assert plan.interruption_position == 2
    assert plan.interrupt_before_next_item is True
    assert plan.processed_before_interruption == ("cap-1",)
    assert plan.paused_capture_ids == ("cap-2",)
    assert plan.eligible_after_interruption == ("cap-3", "cap-4")
    assert plan.provider_write_count == 0
    assert plan.todoist_write_count == 0
    assert plan.execution_authorized is False
    assert tuple(item.disposition for item in plan.item_results) == (
        ClarificationBatchDisposition.COMPLETED_BEFORE_INTERRUPTION,
        ClarificationBatchDisposition.PAUSED_FOR_CLARIFICATION,
        ClarificationBatchDisposition.ELIGIBLE_AFTER_INTERRUPTION,
        ClarificationBatchDisposition.ELIGIBLE_AFTER_INTERRUPTION,
    )
    assert plan.verify_digest()


def test_clear_batch_has_no_interruption() -> None:
    items = (
        AttendedInboxItem("cap-1", "corr-1", "Review the Novaryn migration plan."),
        AttendedInboxItem(
            "cap-2",
            "corr-2",
            'Add “Review Rivian response” to my Work tasks.',
        ),
    )

    plan = workflow().plan_batch(items)

    assert plan.clarification_capture_id is None
    assert plan.interruption_position is None
    assert plan.paused_capture_ids == ()
    assert plan.processed_before_interruption == ("cap-1", "cap-2")
    assert all(
        item.disposition is ClarificationBatchDisposition.CLEAR_NO_INTERRUPTION
        for item in plan.item_results
    )


def test_analysis_binds_to_accepted_v752_clarification_decision() -> None:
    engine = ContextAwareClarificationAnalyzer()
    context = ClarificationContextV1(
        authoritative_snapshot_digest="b" * 64,
        source_refs=("notion:universal-inbox", "notion:portfolio-projects"),
        related_record_ids=("inbox:cap-2",),
    )
    analysis = engine.analyze("build phase 1 or lew", context=context)

    decision, binding = ClarificationCompatibilityAdapter().bind(
        analysis,
        context=context,
    )
    accepted_v752 = ClarificationDecisionV1.model_validate(
        decision.model_dump(mode="json")
    )

    assert decision.original_capture == "build phase 1 or lew"
    assert decision.relationship is RelationshipClassificationV752.NEEDS_CLARIFICATION
    assert decision.clarification_status is ClarificationStatusV752.REQUIRED
    assert decision.clarification_question == analysis.clarification_question
    assert decision.preserve_capture is True
    assert decision.todoist_write_allowed is False
    assert decision.provider_writes == 0
    assert accepted_v752.model_dump(mode="json") == decision.model_dump(mode="json")
    assert binding.analysis_digest == analysis.analysis_digest
    assert binding.predecessor_status == ClarificationStatusV752.REQUIRED.value
    assert binding.provider_write_count == 0
    assert binding.todoist_write_count == 0
    assert binding.verify_digest()


def test_resolution_reanalysis_and_duplicate_replay_are_exact_once() -> None:
    engine = ContextAwareClarificationAnalyzer()
    flow = AttendedClarificationWorkflow(engine)
    item = AttendedInboxItem(
        capture_id="cap-raycast-20260730T222946Z-32107",
        correlation_id="ros-raycast-20260730T222946Z-28150",
        instruction="build phase 1 or lew",
    )
    analysis = engine.analyze(item.instruction)
    response = (
        "Oops, it was supposed to say build phase 1 of lew. "
        "lew is a new application I'm working on building."
    )

    first = flow.resume(
        item=item,
        analysis=analysis,
        user_response=response,
        normalized_instruction="Build Phase 1 of LEW.",
    )
    duplicate = flow.resume(
        item=item,
        analysis=analysis,
        user_response=response,
        normalized_instruction="Build Phase 1 of LEW.",
        existing_resolution=first.resolution,
    )

    assert first.receipt.replay_disposition is ClarificationReplayDisposition.APPLIED
    assert first.receipt.reclassification_required is True
    assert first.follow_up_analysis.ambiguity_category is AmbiguityCategory.ACTION_VERSUS_PROJECT
    assert first.receipt.remaining_clarification_required is True
    assert duplicate.receipt.replay_disposition is (
        ClarificationReplayDisposition.DUPLICATE_IGNORED
    )
    assert duplicate.receipt.reclassification_required is False
    assert duplicate.resolution == first.resolution
    assert duplicate.receipt.provider_write_count == 0
    assert duplicate.receipt.todoist_write_count == 0


def test_conflicting_second_resolution_fails_closed() -> None:
    engine = ContextAwareClarificationAnalyzer()
    flow = AttendedClarificationWorkflow(engine)
    item = AttendedInboxItem("cap-1", "corr-1", "build phase 1 or lew")
    analysis = engine.analyze(item.instruction)
    first = flow.resume(
        item=item,
        analysis=analysis,
        user_response="Yes, of LEW.",
        normalized_instruction="Build Phase 1 of LEW.",
    )

    with pytest.raises(ClarificationReplayConflict, match="conflicting resolution"):
        flow.resume(
            item=item,
            analysis=analysis,
            user_response="No, for LEW.",
            normalized_instruction="Build Phase 1 for LEW.",
            existing_resolution=first.resolution,
        )


def test_answer_cannot_bind_to_wrong_capture() -> None:
    engine = ContextAwareClarificationAnalyzer()
    flow = AttendedClarificationWorkflow(engine)
    analysis = engine.analyze("build phase 1 or lew")
    wrong_item = AttendedInboxItem("cap-other", "corr-other", "Move Phase 2 to Orion")

    with pytest.raises(ValueError, match="does not bind"):
        flow.resume(
            item=wrong_item,
            analysis=analysis,
            user_response="Yes",
            normalized_instruction="Build Phase 1 of LEW.",
        )
