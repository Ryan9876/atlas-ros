"""Provider-write-free clarification calibration and evaluation for Atlas ROS v7.5.2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.intent_learning_v750 import ClarificationDecisionV1

EvaluationMode = Literal["disabled", "shadow"]
ExecutionPathEffect = Literal[
    "none",
    "suppression_prevented",
    "duplicate_prevented",
]


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
    evidence_level: str = Field(min_length=1)
    familiarity_digest: str = Field(min_length=64, max_length=64)
    consequence_digest: str = Field(min_length=64, max_length=64)
    reversible: bool | None = None
    question: str | None = None
    question_basis: str | None = None
    user_response: str | None = None
    final_confirmed_interpretation: str | None = None
    final_classification: str | None = None
    final_destination: str | None = None
    execution_path_effect: ExecutionPathEffect = "none"
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

    likely_classification: str = Field(min_length=1)
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

    @model_validator(mode="after")
    def _decision_binding(self) -> ClarificationEvaluationCaseV1:
        if self.predecessor_decision_digest != self.event.initial_decision_digest:
            raise ValueError("evaluation case must bind to the event predecessor decision")
        return self

    @property
    def deterministic_digest(self) -> str:
        return sha256_digest(self.model_dump(mode="json"))


class ClarificationMetricsV1(StrictContract):
    """Aggregate counts and rates derived only from retained evaluation cases."""

    total_cases: int = Field(ge=0)
    false_duplicates: int = Field(ge=0)
    false_duplicate_rate: float = Field(ge=0.0, le=1.0)
    false_separate_classifications: int = Field(ge=0)
    false_separate_classification_rate: float = Field(ge=0.0, le=1.0)
    user_corrections: int = Field(ge=0)
    user_correction_rate: float = Field(ge=0.0, le=1.0)
    clarifications: int = Field(ge=0)
    clarification_frequency: float = Field(ge=0.0, le=1.0)
    one_question_resolutions: int = Field(ge=0)
    one_question_resolution_rate: float = Field(ge=0.0, le=1.0)
    repeated_questions: int = Field(ge=0)
    repeated_question_rate: float = Field(ge=0.0, le=1.0)
    no_material_change_questions: int = Field(ge=0)
    no_material_change_rate: float = Field(ge=0.0, le=1.0)
    task_suppression_prevented: int = Field(ge=0)
    task_suppression_prevented_rate: float = Field(ge=0.0, le=1.0)
    duplicate_task_creation_prevented: int = Field(ge=0)
    duplicate_task_creation_prevented_rate: float = Field(ge=0.0, le=1.0)
    confirmed_pattern_reuse: int = Field(ge=0)
    confirmed_pattern_reuse_rate: float = Field(ge=0.0, le=1.0)
    clarification_avoided_strong_evidence: int = Field(ge=0)
    clarification_avoided_strong_evidence_rate: float = Field(ge=0.0, le=1.0)
    clarification_reintroduced_context_change: int = Field(ge=0)
    clarification_reintroduced_context_change_rate: float = Field(ge=0.0, le=1.0)


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


def _rate(numerator: int, denominator: int) -> float:
    """Return a stable bounded rate without creating an acceptance threshold."""

    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 12)


def aggregate_metrics(
    cases: tuple[ClarificationEvaluationCaseV1, ...],
) -> ClarificationMetricsV1:
    """Derive deterministic counts and rates without thresholds or external writes."""

    total = len(cases)
    false_duplicates = sum(
        case.outcome.false_duplicate_prevented for case in cases
    )
    false_separate = sum(case.outcome.false_separate_prevented for case in cases)
    corrections = sum(case.outcome.corrected_by_user for case in cases)
    clarifications = sum(case.event.question is not None for case in cases)
    one_question = sum(case.outcome.resolved_with_one_question for case in cases)
    repeated = sum(case.outcome.repeated_question for case in cases)
    no_change = sum(
        case.event.question is not None and not case.outcome.material_change
        for case in cases
    )
    suppression_prevented = sum(
        case.outcome.task_suppression_prevented for case in cases
    )
    duplicate_prevented = sum(
        case.outcome.duplicate_task_creation_prevented for case in cases
    )
    pattern_reuse = sum(case.outcome.confirmed_pattern_reused for case in cases)
    avoided_strong = sum(
        case.outcome.clarification_avoided_strong_evidence for case in cases
    )
    reintroduced = sum(
        case.outcome.clarification_reintroduced_context_change for case in cases
    )
    return ClarificationMetricsV1(
        total_cases=total,
        false_duplicates=false_duplicates,
        false_duplicate_rate=_rate(false_duplicates, total),
        false_separate_classifications=false_separate,
        false_separate_classification_rate=_rate(false_separate, total),
        user_corrections=corrections,
        user_correction_rate=_rate(corrections, total),
        clarifications=clarifications,
        clarification_frequency=_rate(clarifications, total),
        one_question_resolutions=one_question,
        one_question_resolution_rate=_rate(one_question, clarifications),
        repeated_questions=repeated,
        repeated_question_rate=_rate(repeated, clarifications),
        no_material_change_questions=no_change,
        no_material_change_rate=_rate(no_change, clarifications),
        task_suppression_prevented=suppression_prevented,
        task_suppression_prevented_rate=_rate(suppression_prevented, total),
        duplicate_task_creation_prevented=duplicate_prevented,
        duplicate_task_creation_prevented_rate=_rate(duplicate_prevented, total),
        confirmed_pattern_reuse=pattern_reuse,
        confirmed_pattern_reuse_rate=_rate(pattern_reuse, total),
        clarification_avoided_strong_evidence=avoided_strong,
        clarification_avoided_strong_evidence_rate=_rate(avoided_strong, total),
        clarification_reintroduced_context_change=reintroduced,
        clarification_reintroduced_context_change_rate=_rate(reintroduced, total),
    )


def build_report(
    *,
    feature_mode: EvaluationMode,
    snapshot_digest: str,
    cases: tuple[ClarificationEvaluationCaseV1, ...],
    recommended_thresholds: tuple[str, ...] = (),
) -> ClarificationEvaluationReportV1:
    """Build one deterministic report from retained cases and observed evidence."""

    ordered_cases = tuple(sorted(cases, key=lambda case: case.case_id))
    case_ids = tuple(case.case_id for case in ordered_cases)
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("evaluation report case identifiers must be unique")
    if any(case.event.snapshot_digest != snapshot_digest for case in ordered_cases):
        raise ValueError("evaluation report cases must reference the report snapshot")
    return ClarificationEvaluationReportV1(
        feature_mode=feature_mode,
        snapshot_digest=snapshot_digest,
        cases=ordered_cases,
        metrics=aggregate_metrics(ordered_cases),
        recommended_thresholds=recommended_thresholds,
    )
