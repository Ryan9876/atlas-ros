from __future__ import annotations

from enum import StrEnum
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.intent_learning_v750 import (
    ClarificationDecisionV1,
    ClarificationStatus,
    ConsequenceAssessmentV1,
    ContextFamiliarityV1,
    EvidenceLevel,
    RelationshipClassification,
)


class EvaluationMode(StrEnum):
    DISABLED = "disabled"
    SHADOW = "shadow"


class CounterfactualDecisionV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    likely_relationship_without_clarification: RelationshipClassification
    confirmed_relationship: RelationshipClassification
    likely_destination_without_clarification: str | None = None
    confirmed_destination: str | None = None
    likely_execution_path_effect: str
    confirmed_execution_path_effect: str
    authoritative: bool = False
    provider_writes: int = 0
    todoist_writes: int = 0

    @model_validator(mode="after")
    def enforce_shadow_boundary(self) -> CounterfactualDecisionV1:
        if self.authoritative:
            raise ValueError("counterfactual evaluation cannot be authoritative")
        if self.provider_writes or self.todoist_writes:
            raise ValueError("counterfactual evaluation must remain write-free")
        return self


class QuestionQualityAssessmentV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    demonstrates_understanding: bool
    identifies_material_ambiguity: bool
    asks_one_focused_question: bool
    avoids_generic_language: bool
    avoids_known_information: bool
    minimizes_interaction_burden: bool
    changes_or_confirms_decision: bool
    preserves_consequence_controls: bool
    material_change: bool
    findings: tuple[str, ...] = ()


class ClarificationEventV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "1.0"
    evaluation_version: str = "7.5.2"
    operation_id: str
    correlation_id: str
    snapshot_id: str
    original_capture: str
    related_record_ids: tuple[str, ...]
    candidate_interpretations: tuple[str, ...]
    initial_decision: ClarificationDecisionV1
    evidence_level: EvidenceLevel
    familiarity: ContextFamiliarityV1
    consequence: ConsequenceAssessmentV1
    question: str | None = None
    question_basis: str | None = None
    user_response: str | None = None
    final_confirmed_interpretation: str | None = None
    final_classification: RelationshipClassification
    final_destination: str | None = None
    execution_path_effect: str = "none"
    provider_write_count: int = 0
    todoist_write_count: int = 0
    deterministic_digest: str

    @model_validator(mode="after")
    def enforce_event_boundary(self) -> ClarificationEventV1:
        if self.provider_write_count or self.todoist_write_count:
            raise ValueError("clarification evaluation events must remain write-free")
        if self.deterministic_digest != self.compute_digest():
            raise ValueError("deterministic digest does not match event payload")
        return self

    def digest_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"deterministic_digest"})

    def compute_digest(self) -> str:
        return sha256_digest(self.digest_payload())


class ClarificationEvaluationCaseV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    case_id: str
    provenance: str
    event: ClarificationEventV1
    counterfactual: CounterfactualDecisionV1
    question_quality: QuestionQualityAssessmentV1


class ClarificationOutcomeV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    case_id: str
    clarification_required: bool
    resolved_with_one_question: bool
    user_corrected_interpretation: bool
    material_change: bool
    prevented_false_duplicate: bool = False
    prevented_false_separate: bool = False
    prevented_task_suppression: bool = False
    prevented_duplicate_task: bool = False
    confirmed_pattern_reused: bool = False
    clarification_avoided_strong_evidence: bool = False
    clarification_reintroduced_changed_context: bool = False


class ClarificationMetricsV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    total_cases: int = Field(ge=0)
    false_duplicates: int = Field(ge=0)
    false_separate_classifications: int = Field(ge=0)
    user_corrections: int = Field(ge=0)
    clarification_cases: int = Field(ge=0)
    one_question_resolutions: int = Field(ge=0)
    repeated_questions: int = Field(ge=0)
    no_material_change_questions: int = Field(ge=0)
    task_suppression_prevented: int = Field(ge=0)
    duplicate_task_creation_prevented: int = Field(ge=0)
    confirmed_pattern_reuse: int = Field(ge=0)
    clarification_avoided_strong_evidence: int = Field(ge=0)
    clarification_reintroduced_changed_context: int = Field(ge=0)


class ClarificationEvaluationReportV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "1.0"
    evaluation_version: str = "7.5.2"
    snapshot_id: str
    mode: EvaluationMode
    cases: tuple[ClarificationEvaluationCaseV1, ...]
    outcomes: tuple[ClarificationOutcomeV1, ...]
    metrics: ClarificationMetricsV1
    recommended_thresholds: tuple[str, ...] = ()
    authoritative: bool = False
    provider_writes: int = 0
    todoist_writes: int = 0
    deterministic_digest: str

    @model_validator(mode="after")
    def enforce_report_boundary(self) -> ClarificationEvaluationReportV1:
        if self.authoritative:
            raise ValueError("evaluation reports cannot be authoritative")
        if self.provider_writes or self.todoist_writes:
            raise ValueError("evaluation reports must remain write-free")
        if self.deterministic_digest != self.compute_digest():
            raise ValueError("deterministic digest does not match report payload")
        return self

    def digest_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"deterministic_digest"})

    def compute_digest(self) -> str:
        return sha256_digest(self.digest_payload())


class ClarificationEvaluationEngineV752:
    def __init__(self, *, mode: EvaluationMode = EvaluationMode.DISABLED) -> None:
        self.mode = mode

    def evaluate(
        self,
        *,
        snapshot_id: str,
        cases: Iterable[ClarificationEvaluationCaseV1],
        outcomes: Iterable[ClarificationOutcomeV1],
    ) -> ClarificationEvaluationReportV1 | None:
        if self.mode is EvaluationMode.DISABLED:
            return None
        case_items = tuple(cases)
        outcome_items = tuple(outcomes)
        metrics = _metrics(case_items, outcome_items)
        payload = {
            "schema_version": "1.0",
            "evaluation_version": "7.5.2",
            "snapshot_id": snapshot_id,
            "mode": self.mode,
            "cases": case_items,
            "outcomes": outcome_items,
            "metrics": metrics,
            "recommended_thresholds": (),
            "authoritative": False,
            "provider_writes": 0,
            "todoist_writes": 0,
        }
        digest = sha256_digest(
            ClarificationEvaluationReportV1.model_construct(
                **payload,
                deterministic_digest="",
            ).model_dump(mode="json", exclude={"deterministic_digest"})
        )
        return ClarificationEvaluationReportV1(**payload, deterministic_digest=digest)


def build_event(**values: object) -> ClarificationEventV1:
    provisional = ClarificationEventV1.model_construct(**values, deterministic_digest="")
    digest = sha256_digest(provisional.model_dump(mode="json", exclude={"deterministic_digest"}))
    return ClarificationEventV1(**values, deterministic_digest=digest)


def assess_question(
    *,
    decision: ClarificationDecisionV1,
    user_response: str | None,
    final_relationship: RelationshipClassification,
) -> QuestionQualityAssessmentV1:
    question = decision.clarification_question or ""
    normalized = question.casefold().strip()
    one_question = question.count("?") == 1
    generic = normalized in {"what do you mean?", "can you clarify?", "please clarify?"}
    material_change = decision.relationship != final_relationship
    findings: list[str] = []
    if generic:
        findings.append("Question uses generic clarification language.")
    if not one_question and question:
        findings.append("Question is not limited to one focused question.")
    if user_response is None and decision.clarification_status is ClarificationStatus.REQUIRED:
        findings.append("Required clarification has no recorded user response.")
    return QuestionQualityAssessmentV1(
        demonstrates_understanding=bool(decision.related_record_ids or decision.material_distinction),
        identifies_material_ambiguity=bool(decision.material_distinction),
        asks_one_focused_question=one_question,
        avoids_generic_language=not generic,
        avoids_known_information=True,
        minimizes_interaction_burden=one_question,
        changes_or_confirms_decision=user_response is not None,
        preserves_consequence_controls=(
            not decision.consequence.consequential
            or decision.clarification_status is ClarificationStatus.REQUIRED
        ),
        material_change=material_change,
        findings=tuple(findings),
    )


def _metrics(
    cases: tuple[ClarificationEvaluationCaseV1, ...],
    outcomes: tuple[ClarificationOutcomeV1, ...],
) -> ClarificationMetricsV1:
    return ClarificationMetricsV1(
        total_cases=len(cases),
        false_duplicates=sum(item.prevented_false_duplicate for item in outcomes),
        false_separate_classifications=sum(item.prevented_false_separate for item in outcomes),
        user_corrections=sum(item.user_corrected_interpretation for item in outcomes),
        clarification_cases=sum(item.clarification_required for item in outcomes),
        one_question_resolutions=sum(item.resolved_with_one_question for item in outcomes),
        repeated_questions=0,
        no_material_change_questions=sum(
            item.clarification_required and not item.material_change for item in outcomes
        ),
        task_suppression_prevented=sum(item.prevented_task_suppression for item in outcomes),
        duplicate_task_creation_prevented=sum(item.prevented_duplicate_task for item in outcomes),
        confirmed_pattern_reuse=sum(item.confirmed_pattern_reused for item in outcomes),
        clarification_avoided_strong_evidence=sum(
            item.clarification_avoided_strong_evidence for item in outcomes
        ),
        clarification_reintroduced_changed_context=sum(
            item.clarification_reintroduced_changed_context for item in outcomes
        ),
    )
