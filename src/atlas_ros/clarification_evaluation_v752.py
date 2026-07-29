"""Provider-write-free clarification calibration and evaluation for Atlas ROS v7.5.2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.intent_learning_v750 import ClarificationDecisionV1

EvaluationMode = Literal["disabled", "shadow"]


class StrictContract(BaseModel):
    """Shared immutable contract configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class ClarificationEventV1(StrictContract):
    """Minimized evidence for one authoritative predecessor clarification decision."""

    operation_id: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)
    snapshot_digest: str = Field(min_length=64, max_length=64)
    original_capture: str = Field(min_length=1)
    related_record_ids: tuple[str, ...] = ()
    candidate_interpretations: tuple[str, ...] = ()
    initial_decision_digest: str = Field(min_length=64, max_length=64)
    evidence_level: str
    familiarity_digest: str = Field(min_length=64, max_length=64)
    consequence_digest: str = Field(min_length=64, max_length=64)
    question: str | None = None
    question_basis: str | None = None
    user_response: str | None = None
    final_confirmed_interpretation: str | None = None
    final_classification: str | None = None
    final_destination: str | None = None
    execution_path_effect: Literal[
        "none",
        "suppression_prevented",
        "duplicate_prevented",
    ] = "none"
    provider_write_count: int = 0
    todoist_write_count: int = 0

    @model_validator(mode="after")
    def _write_free(self) -> ClarificationEventV1:
        if self.provider_write_count != 0 or self.todoist_write_count != 0:
            raise ValueError("v7.5.2 evaluation events must remain provider-write free")
        return self

    @property
    def deterministic_digest(self) -> str:
        return sha256_digest(self.model_dump(mode="json"))


class CounterfactualDecisionV1(StrictContract):
    """Non-authoritative estimate of likely behavior without clarification."""

    likely_classification: str
    likely_destination: str | None = None
    confidence_basis: tuple[str, ...] = ()
    differs_from_confirmed: bool
    non_authoritative: Literal[True] = True
    routing_allowed: Literal[False] = False
    execution_authorized: Literal[False] = False
    provider_write_count: Literal[0] = 0
    todoist_write_count: Literal[0] = 0


class QuestionQualityAssessmentV1(StrictContract):
    """Deterministic assessment of whether one clarification question was useful."""

    demonstrates_understanding: bool
    identifies_material_ambiguity: bool
    one_focused_question: bool
    avoids_generic_language: bool
    avoids_known_information_request: bool
    minimizes_interaction_burden: bool
    materially_changes_or_confirms_decision: bool
    preserves_consequence_controls: bool
    preserves_reversibility_controls: bool

    @property
    def passed_checks(self) -> int:
        return sum(bool(value) for value in self.model_dump().values())


class ClarificationOutcomeV1(StrictContract):
    """Confirmed evaluation outcome without execution authority."""

    corrected_by_user: bool = False
    resolved_with_one_question: bool = False
    repeated_question: bool = False
    material_change: bool = False
    false_duplicate_prevented: bool = False
    false_separate_prevented: bool = False
    task_suppression_prevented: bool = False
    duplicate_task_creation_prevented: bool = False
    confirmed_pattern_reused: bool = False
    clarification_avoided_strong_evidence: bool = False
    clarification_reintroduced_context_change: bool = False
    provider_write_count: Literal[0] = 0
    todoist_write_count: Literal[0] = 0


class ClarificationEvaluationCaseV1(StrictContract):
    """One deterministic case joining predecessor authority and shadow evaluation."""

    case_id: str = Field(min_length=1)
    event: ClarificationEventV1
    predecessor_decision_digest: str = Field(min_length=64, max_length=64)
    counterfactual: CounterfactualDecisionV1
    question_quality: QuestionQualityAssessmentV1 | None = None
    outcome: ClarificationOutcomeV1

    @property
    def deterministic_digest(self) -> str:
        return sha256_digest(self.model_dump(mode="json"))


class ClarificationMetricsV1(StrictContract):
    """Aggregate metrics derived only from retained evaluation cases."""

    total_cases: int = Field(ge=0)
    false_duplicates: int = Field(ge=0)
    false_separate_classifications: int = Field(ge=0)
    user_corrections: int = Field(ge=0)
    clarifications: int = Field(ge=0)
    one_question_resolutions: int = Field(ge=0)
    repeated_questions: int = Field(ge=0)
    no_material_change_questions: int = Field(ge=0)
    task_suppression_prevented: int = Field(ge=0)
    duplicate_task_creation_prevented: int = Field(ge=0)
    confirmed_pattern_reuse: int = Field(ge=0)
    clarification_avoided_strong_evidence: int = Field(ge=0)
    clarification_reintroduced_context_change: int = Field(ge=0)


class ClarificationEvaluationReportV1(StrictContract):
    """Snapshot-bound, deterministic, provider-write-free evaluation report."""

    schema_version: Literal["1.0"] = "1.0"
    evaluation_version: Literal["7.5.2"] = "7.5.2"
    feature_mode: EvaluationMode
    snapshot_digest: str = Field(min_length=64, max_length=64)
    cases: tuple[ClarificationEvaluationCaseV1, ...]
    metrics: ClarificationMetricsV1
    recommended_thresholds: tuple[str, ...] = ()
    authoritative: Literal[False] = False
    routing_allowed: Literal[False] = False
    execution_authorized: Literal[False] = False
    provider_write_count: Literal[0] = 0
    todoist_write_count: Literal[0] = 0

    @property
    def deterministic_digest(self) -> str:
        return sha256_digest(self.model_dump(mode="json"))


@dataclass(frozen=True)
class ClarificationEvaluationPolicyV752:
    """Disabled-by-default feature policy for provider-write-free shadow evaluation."""

    mode: EvaluationMode = "disabled"

    def evaluate(
        self,
        *,
        event: ClarificationEventV1,
        predecessor_decision: ClarificationDecisionV1,
        counterfactual: CounterfactualDecisionV1,
        question_quality: QuestionQualityAssessmentV1 | None,
        outcome: ClarificationOutcomeV1,
        case_id: str,
    ) -> ClarificationEvaluationCaseV1 | None:
        if self.mode == "disabled":
            return None
        predecessor_digest = sha256_digest(
            predecessor_decision.model_dump(mode="json")
        )
        if predecessor_digest != event.initial_decision_digest:
            raise ValueError(
                "evaluation event does not reference the authoritative predecessor decision"
            )
        return ClarificationEvaluationCaseV1(
            case_id=case_id,
            event=event,
            predecessor_decision_digest=predecessor_digest,
            counterfactual=counterfactual,
            question_quality=question_quality,
            outcome=outcome,
        )


def aggregate_metrics(
    cases: tuple[ClarificationEvaluationCaseV1, ...],
) -> ClarificationMetricsV1:
    """Derive deterministic metrics without thresholds or external writes."""

    return ClarificationMetricsV1(
        total_cases=len(cases),
        false_duplicates=sum(
            case.outcome.false_duplicate_prevented for case in cases
        ),
        false_separate_classifications=sum(
            case.outcome.false_separate_prevented for case in cases
        ),
        user_corrections=sum(case.outcome.corrected_by_user for case in cases),
        clarifications=sum(case.event.question is not None for case in cases),
        one_question_resolutions=sum(
            case.outcome.resolved_with_one_question for case in cases
        ),
        repeated_questions=sum(case.outcome.repeated_question for case in cases),
        no_material_change_questions=sum(
            case.event.question is not None and not case.outcome.material_change
            for case in cases
        ),
        task_suppression_prevented=sum(
            case.outcome.task_suppression_prevented for case in cases
        ),
        duplicate_task_creation_prevented=sum(
            case.outcome.duplicate_task_creation_prevented for case in cases
        ),
        confirmed_pattern_reuse=sum(
            case.outcome.confirmed_pattern_reused for case in cases
        ),
        clarification_avoided_strong_evidence=sum(
            case.outcome.clarification_avoided_strong_evidence for case in cases
        ),
        clarification_reintroduced_context_change=sum(
            case.outcome.clarification_reintroduced_context_change for case in cases
        ),
    )


def build_report(
    *,
    feature_mode: EvaluationMode,
    snapshot_digest: str,
    cases: tuple[ClarificationEvaluationCaseV1, ...],
    recommended_thresholds: tuple[str, ...] = (),
) -> ClarificationEvaluationReportV1:
    """Build one deterministic report from retained cases and observed evidence."""

    return ClarificationEvaluationReportV1(
        feature_mode=feature_mode,
        snapshot_digest=snapshot_digest,
        cases=cases,
        metrics=aggregate_metrics(cases),
        recommended_thresholds=recommended_thresholds,
    )
