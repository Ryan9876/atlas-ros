from __future__ import annotations

import pytest

from atlas_ros.capabilities.operational_awareness import ContextAwareClarificationAnalyzer
from atlas_ros.contracts.operational_awareness import (
    AmbiguityCategory,
    ClarificationContextV1,
    ClarificationQuestionMode,
)


def analyzer() -> ContextAwareClarificationAnalyzer:
    return ContextAwareClarificationAnalyzer()


def test_lew_connector_typo_preserves_possible_entity_and_asks_confirmatory_question() -> None:
    result = analyzer().analyze(
        "build phase 1 or lew",
        context=ClarificationContextV1(
            source_refs=("notion:portfolio-projects", "notion:action-records"),
        ),
    )

    assert result.stable_intent == ("Build Phase 1",)
    assert result.ambiguity_category is AmbiguityCategory.CONNECTOR_ERROR
    assert result.ambiguous_span == "or"
    assert result.preserved_entities == ("LEW",)
    assert result.leading_interpretation == "Build Phase 1 of LEW"
    assert result.question_mode is ClarificationQuestionMode.CONFIRMATORY
    assert result.clarification_question == (
        "I understand that you want to build Phase 1, and LEW may be the application name. "
        "Did you mean: “Build Phase 1 of LEW”?"
    )
    assert result.clarification_required is True
    assert result.continue_unrelated_work is True
    assert result.downstream_execution_blocked is True
    assert result.routing_allowed is False
    assert result.execution_authorized is False
    assert result.provider_write_count == 0
    assert result.todoist_write_count == 0
    assert result.verify_digest()


def test_lew_resolution_preserves_original_and_requires_second_stage_scope_question() -> None:
    engine = analyzer()
    analysis = engine.analyze("build phase 1 or lew")

    resolution = engine.resolve(
        analysis,
        capture_id="cap-raycast-20260730T222946Z-32107",
        correlation_id="ros-raycast-20260730T222946Z-28150",
        user_response=(
            "Oops, it was supposed to say build phase 1 of lew. "
            "lew is a new application I'm working on building."
        ),
        normalized_instruction="Build Phase 1 of LEW.",
    )
    follow_up = engine.analyze(resolution.normalized_instruction)

    assert resolution.analysis_digest == analysis.analysis_digest
    assert resolution.original_instruction == "build phase 1 or lew"
    assert resolution.normalized_instruction == "Build Phase 1 of LEW."
    assert resolution.ambiguity_category is AmbiguityCategory.CONNECTOR_ERROR
    assert resolution.provider_write_count == 0
    assert resolution.todoist_write_count == 0
    assert resolution.verify_digest()
    assert follow_up.ambiguity_category is AmbiguityCategory.ACTION_VERSUS_PROJECT
    assert follow_up.clarification_question == (
        "I understand that Phase 1 belongs to LEW. "
        "What outcome should mark Phase 1 complete?"
    )


def test_unknown_term_in_entity_position_is_preserved_without_typo_assumption() -> None:
    result = analyzer().analyze("Review the Novaryn migration plan.")

    assert result.ambiguity_category is AmbiguityCategory.POSSIBLE_PROPER_NOUN
    assert result.preserved_entities == ("Novaryn",)
    assert result.clarification_required is False
    assert result.downstream_execution_blocked is False
    assert "does not prove a typo" in " ".join(result.evidence)


def test_familiar_connector_word_is_identified_as_typo() -> None:
    result = analyzer().analyze("Prepare the review for Acme form Friday")

    assert result.ambiguity_category is AmbiguityCategory.TRANSCRIPTION_ERROR
    assert result.ambiguous_span == "form"
    assert result.leading_interpretation == "Prepare the review for Acme for Friday"
    assert result.clarification_question == (
        "I understand that you want to prepare the review for the named target. "
        "Did you mean: “Prepare the review for Acme for Friday”?"
    )


def test_two_material_interpretations_produce_bounded_choice() -> None:
    result = analyzer().analyze("Move Phase 2 to Orion")

    assert result.ambiguity_category is AmbiguityCategory.MULTIPLE_TARGETS
    assert result.question_mode is ClarificationQuestionMode.BOUNDED_CHOICE
    assert result.leading_interpretation is None
    assert len(result.candidates) == 2
    assert "Orion project" in result.clarification_question
    assert "take ownership" in result.clarification_question


def test_missing_owner_preserves_outcome_and_date() -> None:
    result = analyzer().analyze("Have the network migration completed by Friday")

    assert result.ambiguity_category is AmbiguityCategory.MISSING_OWNER
    assert result.stable_intent == ("Complete the network migration by Friday",)
    assert result.question_mode is ClarificationQuestionMode.INFORMATION_SEEKING
    assert result.clarification_question == (
        "I understand that the network migration should be completed by Friday. "
        "Who should own the work?"
    )


def test_clear_todoist_request_does_not_trigger_clarification() -> None:
    result = analyzer().analyze('Add “Review Rivian response” to my Work tasks.')

    assert result.ambiguity_category is AmbiguityCategory.NONE
    assert result.clarification_required is False
    assert result.stable_intent == ("Add Review Rivian response to Work tasks",)


def test_voice_homophone_uses_bounded_website_context() -> None:
    result = analyzer().analyze(
        "Schedule a review of the new cite design",
        context=ClarificationContextV1(
            source_refs=("notion:portfolio-projects",),
            context_terms=("website",),
        ),
    )

    assert result.ambiguity_category is AmbiguityCategory.TRANSCRIPTION_ERROR
    assert result.leading_interpretation == "Schedule a review of the new site design"
    assert "available context points to a website" in result.clarification_question


def test_phase_wording_is_not_collapsed_into_one_physical_action() -> None:
    result = analyzer().analyze("Build Phase 1 of LEW.")

    assert result.ambiguity_category is AmbiguityCategory.ACTION_VERSUS_PROJECT
    assert result.stable_intent == ("Build Phase 1 of LEW",)
    assert result.clarification_question == (
        "I understand that Phase 1 belongs to LEW. "
        "What outcome should mark Phase 1 complete?"
    )


@pytest.mark.parametrize(
    ("instruction", "expected_category"),
    [
        ("Review", AmbiguityCategory.MISSING_TARGET),
        ("Build Phase 1 of", AmbiguityCategory.MISSING_ENTITY),
        ("Kweku owns this", AmbiguityCategory.MISSING_OUTCOME),
        (
            "Delegate the Rivian response review to Kweku",
            AmbiguityCategory.MISSING_COMPLETION_CRITERIA,
        ),
        ("Kweku can handle the Rivian response", AmbiguityCategory.AMBIGUOUS_DELEGATION),
        (
            "Complete the migration by Friday and due Monday",
            AmbiguityCategory.CONFLICTING_DATES,
        ),
        (
            "Complete the migration as P1 and P3 priority",
            AmbiguityCategory.CONFLICTING_PRIORITIES,
        ),
        ("Update it", AmbiguityCategory.AMBIGUOUS_PRONOUN),
        ("Rivian response is delayed", AmbiguityCategory.REQUEST_VERSUS_NOTE),
    ],
)
def test_required_ambiguity_categories_fail_closed(
    instruction: str,
    expected_category: AmbiguityCategory,
) -> None:
    result = analyzer().analyze(instruction)

    assert result.ambiguity_category is expected_category
    assert result.clarification_required is True
    assert result.downstream_execution_blocked is True
    assert result.routing_allowed is False
    assert result.execution_authorized is False
    assert result.provider_write_count == 0
    assert result.todoist_write_count == 0
    assert result.clarification_question is not None
    assert result.clarification_question.startswith("I understand")


def test_pronoun_can_resolve_without_interruption_when_context_is_unique() -> None:
    result = analyzer().analyze(
        "Update it",
        context=ClarificationContextV1(
            source_refs=("notion:action-records",),
            candidate_targets=("Rivian response action",),
        ),
    )

    assert result.clarification_required is False
    assert result.stable_intent == ("Update Rivian response action",)


def test_conflicting_resolution_content_is_not_silently_normalized() -> None:
    analysis = analyzer().analyze("build phase 1 or lew")

    with pytest.raises(ValueError, match="answer and normalized instruction"):
        analyzer().resolve(
            analysis,
            capture_id="cap-1",
            correlation_id="corr-1",
            user_response="",
            normalized_instruction="",
        )


def test_same_inputs_replay_to_same_analysis_digest() -> None:
    context = ClarificationContextV1(
        authoritative_snapshot_digest="a" * 64,
        source_refs=("notion:action-records", "notion:portfolio-projects"),
    )

    first = analyzer().analyze("build phase 1 or lew", context=context)
    second = analyzer().analyze("build phase 1 or lew", context=context)

    assert first == second
    assert first.analysis_digest == second.analysis_digest
