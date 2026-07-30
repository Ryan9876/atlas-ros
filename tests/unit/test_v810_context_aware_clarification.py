from __future__ import annotations

import pytest

from atlas_ros.capabilities.operational_awareness import ContextAwareClarificationAnalyzer
from atlas_ros.contracts.operational_awareness import (
    AmbiguityCategory,
    ClarificationQuestionMode,
)


def test_lew_connector_typo_preserves_possible_entity_and_asks_confirmatory_question() -> None:
    analyzer = ContextAwareClarificationAnalyzer()

    result = analyzer.analyze(
        "build phase 1 or lew",
        context_sources_checked=("notion:portfolio-projects", "notion:action-records"),
    )

    assert result.stable_intent == ("Build Phase 1",)
    assert result.ambiguity_category is AmbiguityCategory.CONNECTOR_ERROR
    assert result.ambiguous_span == "or"
    assert result.leading_interpretation == "Build Phase 1 of LEW"
    assert result.question_mode is ClarificationQuestionMode.CONFIRMATORY
    assert result.clarification_question == (
        "I understand that you want to build Phase 1, and LEW may be the application name. "
        "Did you mean: “Build Phase 1 of LEW”?"
    )
    assert result.clarification_required is True
    assert result.continue_unrelated_work is True
    assert result.downstream_execution_blocked is True
    assert result.provider_write_count == 0
    assert result.verify_digest()


def test_lew_resolution_binds_the_answer_to_one_capture_without_authorizing_writes() -> None:
    analyzer = ContextAwareClarificationAnalyzer()
    analysis = analyzer.analyze("build phase 1 or lew")

    resolution = analyzer.resolve(
        analysis,
        capture_id="cap-raycast-20260730T222946Z-32107",
        correlation_id="ros-raycast-20260730T222946Z-28150",
        user_response=(
            "Oops, it was supposed to say build phase 1 of lew. "
            "lew is a new application I'm working on building."
        ),
        normalized_instruction="Build Phase 1 of LEW.",
    )

    assert resolution.analysis_digest == analysis.analysis_digest
    assert resolution.original_instruction == "build phase 1 or lew"
    assert resolution.normalized_instruction == "Build Phase 1 of LEW."
    assert resolution.ambiguity_category is AmbiguityCategory.CONNECTOR_ERROR
    assert resolution.provider_write_count == 0
    assert resolution.verify_digest()


def test_two_material_interpretations_produce_a_bounded_choice() -> None:
    result = ContextAwareClarificationAnalyzer().analyze("Move Phase 2 to Orion")

    assert result.ambiguity_category is AmbiguityCategory.MULTIPLE_TARGETS
    assert result.question_mode is ClarificationQuestionMode.BOUNDED_CHOICE
    assert result.leading_interpretation is None
    assert len(result.candidates) == 2
    assert "Orion project" in result.clarification_question
    assert "take ownership" in result.clarification_question
    assert result.downstream_execution_blocked is True


def test_missing_owner_preserves_outcome_and_date() -> None:
    result = ContextAwareClarificationAnalyzer().analyze(
        "Have the network migration completed by Friday"
    )

    assert result.ambiguity_category is AmbiguityCategory.MISSING_OWNER
    assert result.stable_intent == ("Complete the network migration by Friday",)
    assert result.question_mode is ClarificationQuestionMode.INFORMATION_SEEKING
    assert result.clarification_question == (
        "I understand that the network migration should be completed by Friday. "
        "Who should own the work?"
    )


def test_familiar_word_can_be_the_typo_instead_of_the_entity() -> None:
    result = ContextAwareClarificationAnalyzer().analyze(
        "Prepare the review for Acme form Friday"
    )

    assert result.ambiguity_category is AmbiguityCategory.TRANSCRIPTION_ERROR
    assert result.ambiguous_span == "form"
    assert result.leading_interpretation == "Prepare the review for Acme for Friday"


def test_voice_homophone_uses_bounded_context() -> None:
    result = ContextAwareClarificationAnalyzer().analyze(
        "Schedule a review of the new cite design",
        context_sources_checked=("notion:website-project",),
        context_terms=("website",),
    )

    assert result.ambiguity_category is AmbiguityCategory.TRANSCRIPTION_ERROR
    assert result.ambiguous_span == "cite"
    assert result.leading_interpretation == "Schedule a review of the new site design"


def test_clear_task_does_not_trigger_needless_clarification() -> None:
    result = ContextAwareClarificationAnalyzer().analyze(
        'Add “Review Rivian response” to my Work tasks.'
    )

    assert result.ambiguity_category is AmbiguityCategory.NONE
    assert result.clarification_required is False
    assert result.downstream_execution_blocked is False
    assert result.clarification_question is None
    assert result.provider_write_count == 0


def test_resolution_rejects_non_ambiguous_analysis() -> None:
    analyzer = ContextAwareClarificationAnalyzer()
    analysis = analyzer.analyze("Review the Rivian response")

    with pytest.raises(ValueError, match="only clarification-required analyses"):
        analyzer.resolve(
            analysis,
            capture_id="capture-1",
            correlation_id="correlation-1",
            user_response="yes",
            normalized_instruction="Review the Rivian response",
        )
