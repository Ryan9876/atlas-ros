from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from atlas_ros import clarification_baseline_v752 as baseline
from atlas_ros import clarification_evaluation_v752 as evaluation
from atlas_ros import intent_learning_v750 as intent
from atlas_ros.contracts.digests import sha256_digest

FIXTURE_PATH = Path("tests/fixtures/v752_clarification_cases.json")


def familiarity() -> intent.ContextFamiliarityV1:
    return intent.ContextFamiliarityV1(
        user=0.8,
        domain=0.7,
        project=0.7,
        terminology=0.8,
        evidence_recency=0.8,
        interpretation_consistency=0.7,
    )


def predecessor() -> intent.ClarificationDecisionV1:
    return intent.decide_relationship(
        capture="Centrally manage ANX customer devices",
        proposed_completion=None,
        related_records=(),
        familiarity=familiarity(),
        consequence=intent.ConsequenceAssessmentV1(
            production=True,
            architecture=True,
            reversible=False,
        ),
    )


def event_for(
    decision: intent.ClarificationDecisionV1,
) -> evaluation.ClarificationEventV1:
    decision_digest = sha256_digest(decision.model_dump(mode="json"))
    return evaluation.ClarificationEventV1(
        operation_id="op-v752-1",
        correlation_id="workspace-redacted:1",
        snapshot_digest="a" * 64,
        original_capture=decision.original_capture,
        related_record_ids=decision.related_record_ids,
        candidate_interpretations=decision.candidate_interpretations,
        initial_decision_digest=decision_digest,
        evidence_level=decision.evidence_level.value,
        familiarity_digest=sha256_digest(
            decision.familiarity.model_dump(mode="json")
        ),
        consequence_digest=sha256_digest(
            decision.consequence.model_dump(mode="json")
        ),
        reversible=False,
        question=(
            "Should this be treated as a separate centralized configuration outcome?"
        ),
        question_basis="The completion boundary differs from related naming work.",
        user_response="This is a separate centralized configuration outcome.",
        final_confirmed_interpretation=(
            "separate centralized configuration outcome"
        ),
        final_classification=intent.RelationshipClassification.DISTINCT_OUTCOME.value,
        final_destination="retained-evaluation-only",
        execution_path_effect="suppression_prevented",
    )


def quality() -> evaluation.QuestionQualityAssessmentV1:
    return evaluation.QuestionQualityAssessmentV1(
        demonstrates_understanding=True,
        identifies_material_ambiguity=True,
        one_focused_question=True,
        avoids_generic_language=True,
        avoids_known_information_request=True,
        minimizes_interaction_burden=True,
        materially_changes_or_confirms_decision=True,
        preserves_consequence_controls=True,
        preserves_reversibility_controls=True,
    )


def shadow_case(case_id: str = "anx-central-management") -> evaluation.ClarificationEvaluationCaseV1:
    decision = predecessor()
    case = evaluation.ClarificationEvaluationPolicyV752(mode="shadow").evaluate(
        event=event_for(decision),
        predecessor_decision=decision,
        counterfactual=evaluation.CounterfactualDecisionV1(
            likely_classification=(
                intent.RelationshipClassification.PARAPHRASED_DUPLICATE.value
            ),
            differs_from_confirmed=True,
            confidence_basis=(
                "related wording",
                "missing completion equivalence",
            ),
        ),
        question_quality=quality(),
        outcome=evaluation.ClarificationOutcomeV1(
            corrected_by_user=True,
            resolved_with_one_question=True,
            material_change=True,
            false_duplicate_prevented=True,
            task_suppression_prevented=True,
        ),
        case_id=case_id,
    )
    assert case is not None
    return case


def test_disabled_policy_is_equivalent_to_predecessor() -> None:
    decision = predecessor()
    before = decision.model_dump(mode="json")
    result = evaluation.ClarificationEvaluationPolicyV752().evaluate(
        event=event_for(decision),
        predecessor_decision=decision,
        counterfactual=evaluation.CounterfactualDecisionV1(
            likely_classification=(
                intent.RelationshipClassification.PARAPHRASED_DUPLICATE.value
            ),
            differs_from_confirmed=True,
        ),
        question_quality=quality(),
        outcome=evaluation.ClarificationOutcomeV1(),
        case_id="disabled",
    )
    assert result is None
    assert decision.model_dump(mode="json") == before
    assert decision.provider_writes == 0
    assert decision.todoist_write_allowed is False


def test_shadow_evaluation_is_inert_and_digest_bound() -> None:
    case = shadow_case()
    assert case.counterfactual.non_authoritative is True
    assert case.counterfactual.routing_allowed is False
    assert case.counterfactual.execution_authorized is False
    assert case.event.provider_write_count == 0
    assert case.event.todoist_write_count == 0
    assert case.outcome.provider_write_count == 0
    assert case.outcome.todoist_write_count == 0
    assert case.predecessor_decision_digest == case.event.initial_decision_digest


def test_identical_inputs_produce_identical_report_digest() -> None:
    first_case = shadow_case("deterministic")
    second_case = shadow_case("deterministic")
    first = evaluation.build_report(
        feature_mode="shadow",
        snapshot_digest="a" * 64,
        cases=(first_case,),
    )
    second = evaluation.build_report(
        feature_mode="shadow",
        snapshot_digest="a" * 64,
        cases=(second_case,),
    )
    assert first == second
    assert first.deterministic_digest == second.deterministic_digest
    assert first.provider_write_count == first.todoist_write_count == 0


@pytest.mark.parametrize(
    ("field", "value"),
    (("provider_write_count", 1), ("todoist_write_count", 1)),
)
def test_evaluation_event_rejects_all_write_counts(field: str, value: int) -> None:
    decision = predecessor()
    payload = {
        "operation_id": "op",
        "correlation_id": "redacted",
        "snapshot_digest": "a" * 64,
        "original_capture": decision.original_capture,
        "initial_decision_digest": sha256_digest(
            decision.model_dump(mode="json")
        ),
        "evidence_level": intent.EvidenceLevel.MINIMAL.value,
        "familiarity_digest": "b" * 64,
        "consequence_digest": "c" * 64,
        field: value,
    }
    with pytest.raises(ValidationError, match="provider-write free"):
        evaluation.ClarificationEventV1.model_validate(payload)


def test_literal_contracts_reject_todoist_and_provider_writes() -> None:
    with pytest.raises(ValidationError):
        evaluation.ClarificationOutcomeV1(todoist_write_count=1)
    with pytest.raises(ValidationError):
        evaluation.CounterfactualDecisionV1(
            likely_classification="distinct_outcome",
            differs_from_confirmed=True,
            provider_write_count=1,
        )


def test_shadow_policy_rejects_wrong_predecessor_digest() -> None:
    decision = predecessor()
    bad_event = event_for(decision).model_copy(
        update={"initial_decision_digest": "f" * 64}
    )
    with pytest.raises(ValueError, match="authoritative predecessor"):
        evaluation.ClarificationEvaluationPolicyV752(mode="shadow").evaluate(
            event=bad_event,
            predecessor_decision=decision,
            counterfactual=evaluation.CounterfactualDecisionV1(
                likely_classification="distinct_outcome",
                differs_from_confirmed=False,
            ),
            question_quality=quality(),
            outcome=evaluation.ClarificationOutcomeV1(),
            case_id="bad-binding",
        )


def test_question_quality_counts_all_governed_checks() -> None:
    assert quality().passed_checks == 9


def test_metrics_include_deterministic_counts_and_rates() -> None:
    report = evaluation.build_report(
        feature_mode="shadow",
        snapshot_digest="a" * 64,
        cases=(shadow_case(),),
    )
    metrics = report.metrics
    assert metrics.total_cases == 1
    assert metrics.false_duplicates == 1
    assert metrics.false_duplicate_rate == 1.0
    assert metrics.user_correction_rate == 1.0
    assert metrics.clarification_frequency == 1.0
    assert metrics.one_question_resolution_rate == 1.0
    assert metrics.task_suppression_prevented_rate == 1.0
    assert metrics.repeated_question_rate == 0.0


def test_empty_metrics_use_zero_rates_without_thresholds() -> None:
    report = evaluation.build_report(
        feature_mode="shadow",
        snapshot_digest="a" * 64,
        cases=(),
    )
    assert report.metrics.total_cases == 0
    for name, value in report.metrics.model_dump().items():
        if name.endswith("_rate") or name == "clarification_frequency":
            assert value == 0.0


def test_report_orders_cases_and_rejects_duplicate_or_mixed_snapshots() -> None:
    first = shadow_case("b")
    second = shadow_case("a")
    report = evaluation.build_report(
        feature_mode="shadow",
        snapshot_digest="a" * 64,
        cases=(first, second),
    )
    assert tuple(case.case_id for case in report.cases) == ("a", "b")
    with pytest.raises(ValueError, match="unique"):
        evaluation.build_report(
            feature_mode="shadow",
            snapshot_digest="a" * 64,
            cases=(first, first),
        )
    mixed = second.model_copy(
        update={
            "event": second.event.model_copy(
                update={"snapshot_digest": "b" * 64}
            )
        }
    )
    with pytest.raises(ValueError, match="report snapshot"):
        evaluation.build_report(
            feature_mode="shadow",
            snapshot_digest="a" * 64,
            cases=(first, mixed),
        )


def test_minimized_fixture_corpus_is_complete_and_attributable() -> None:
    document = baseline.load_fixture_document(FIXTURE_PATH)
    assert len(document.cases) == 12
    assert baseline.validate_fixture_minimization(document) == ()
    case_ids = {case.case_id for case in document.cases}
    assert {
        "anx-central-management",
        "jira-customization-vs-integration",
        "true-completion-equivalent",
        "paraphrased-duplicate",
        "high-consequence-ambiguity",
        "strong-evidence-avoids-question",
        "context-change-reintroduces-question",
        "stale-evidence",
        "contradictory-evidence",
        "user-correction",
        "no-material-change",
        "prevents-duplicate-task",
    } == case_ids


def test_fixture_privacy_check_rejects_sensitive_content() -> None:
    document = baseline.load_fixture_document(FIXTURE_PATH)
    first = document.cases[0].model_copy(
        update={"capture": "Contact private@example.com for the token"}
    )
    modified = document.model_copy(update={"cases": (first, *document.cases[1:])})
    errors = baseline.validate_fixture_minimization(modified)
    assert any("sensitive content" in error for error in errors)


def test_fixture_baseline_is_deterministic_and_provider_write_free() -> None:
    document = baseline.load_fixture_document(FIXTURE_PATH)
    first = baseline.build_fixture_baseline_report(document)
    second = baseline.build_fixture_baseline_report(document)
    assert first == second
    assert first.deterministic_digest == second.deterministic_digest
    assert len(first.cases) == 12
    assert first.provider_write_count == first.todoist_write_count == 0
    assert first.metrics.clarification_frequency > 0.0
    assert first.metrics.duplicate_task_creation_prevented == 1
    assert first.metrics.task_suppression_prevented == 1
    assert first.metrics.clarification_avoided_strong_evidence == 1
    assert first.metrics.clarification_reintroduced_context_change == 1
    assert first.recommended_thresholds
    assert not any(re.search(r"\b\d+(?:\.\d+)?%", item) for item in first.recommended_thresholds)


def test_contract_schema_bundle_contains_exact_required_contracts() -> None:
    assert set(baseline.contract_schemas()) == {
        "ClarificationEventV1",
        "ClarificationEvaluationCaseV1",
        "CounterfactualDecisionV1",
        "QuestionQualityAssessmentV1",
        "ClarificationOutcomeV1",
        "ClarificationMetricsV1",
        "ClarificationEvaluationReportV1",
    }


def test_evidence_builder_is_deterministic(tmp_path: Path) -> None:
    first_directory = tmp_path / "first"
    second_directory = tmp_path / "second"
    first_paths = baseline.write_evaluation_evidence(
        fixture_path=FIXTURE_PATH,
        output_directory=first_directory,
    )
    second_paths = baseline.write_evaluation_evidence(
        fixture_path=FIXTURE_PATH,
        output_directory=second_directory,
    )
    assert [path.name for path in first_paths] == [path.name for path in second_paths]
    for first, second in zip(first_paths, second_paths, strict=True):
        assert first.read_bytes() == second.read_bytes()
    report = json.loads((first_directory / "V752_BASELINE_REPORT.json").read_text())
    receipt = json.loads(
        (first_directory / "V752_DATA_MINIMIZATION_RECEIPT.json").read_text()
    )
    assert report["deterministic_digest"]
    assert report["provider_write_count"] == report["todoist_write_count"] == 0
    assert receipt["status"] == "passed"
    assert receipt["fixture_count"] == 12
