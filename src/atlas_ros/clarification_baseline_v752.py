"""Deterministic provider-write-free baseline reporting for Atlas ROS v7.5.2."""

from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import Field

from atlas_ros.clarification_evaluation_v752 import (
    ClarificationEventV1,
    ClarificationEvaluationCaseV1,
    ClarificationEvaluationReportV1,
    ClarificationMetricsV1,
    ClarificationOutcomeV1,
    CounterfactualDecisionV1,
    ExecutionPathEffect,
    QuestionQualityAssessmentV1,
    StrictContract,
    build_report,
)
from atlas_ros.contracts.digests import sha256_digest


class ClarificationFixtureV1(StrictContract):
    """One minimized attributable observation in the accepted evaluation corpus."""

    case_id: str = Field(min_length=1)
    capture: str = Field(min_length=1, max_length=240)
    provenance: str = Field(min_length=1, max_length=240)
    predecessor_reference: str = Field(min_length=1, max_length=300)
    expected: str = Field(min_length=1, max_length=240)
    evidence_level: str = Field(min_length=1)
    related_record_ids: tuple[str, ...] = ()
    candidate_interpretations: tuple[str, ...] = ()
    high_consequence: bool = False
    reversible: bool | None = None
    question: str | None = Field(default=None, max_length=300)
    question_basis: str | None = Field(default=None, max_length=300)
    user_response: str | None = Field(default=None, max_length=300)
    confirmed_classification: str = Field(min_length=1)
    confirmed_destination: str | None = None
    counterfactual_classification: str = Field(min_length=1)
    counterfactual_destination: str | None = None
    counterfactual_differs: bool
    execution_path_effect: ExecutionPathEffect = "none"
    question_quality: QuestionQualityAssessmentV1 | None = None
    outcome: ClarificationOutcomeV1 = ClarificationOutcomeV1()


class ClarificationFixtureDocumentV1(StrictContract):
    """Versioned minimized fixture corpus used for deterministic baseline generation."""

    schema_version: str = Field(pattern=r"^1\.0$")
    cases: tuple[ClarificationFixtureV1, ...] = Field(min_length=12)


_FORBIDDEN_FIXTURE_PATTERNS = (
    re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE),
    re.compile(r"\b(?:api[_-]?key|access[_-]?token|bearer)\b", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----"),
    re.compile(r"https?://(?:www\.)?notion\.(?:so|site)/", re.IGNORECASE),
)


def load_fixture_document(path: Path) -> ClarificationFixtureDocumentV1:
    """Load and validate the minimized fixture corpus."""

    return ClarificationFixtureDocumentV1.model_validate_json(path.read_text())


def validate_fixture_minimization(
    document: ClarificationFixtureDocumentV1,
) -> tuple[str, ...]:
    """Return deterministic privacy and attribution errors for fixture content."""

    errors: list[str] = []
    case_ids = tuple(case.case_id for case in document.cases)
    if len(case_ids) != len(set(case_ids)):
        errors.append("fixture case identifiers must be unique")
    for case in document.cases:
        values = (
            case.capture,
            case.provenance,
            case.predecessor_reference,
            case.expected,
            case.question or "",
            case.question_basis or "",
            case.user_response or "",
        )
        combined = "\n".join(values)
        if any(pattern.search(combined) for pattern in _FORBIDDEN_FIXTURE_PATTERNS):
            errors.append(f"{case.case_id}: fixture contains prohibited sensitive content")
        if "accepted v7.5" not in case.provenance and "minimized synthetic" not in case.provenance:
            errors.append(f"{case.case_id}: fixture provenance is not attributable")
        if case.question is None and case.question_quality is not None:
            errors.append(f"{case.case_id}: question quality requires a question")
        if case.question is not None and case.question_quality is None:
            errors.append(f"{case.case_id}: question requires a quality assessment")
    return tuple(sorted(errors))


def _fixture_case(
    fixture: ClarificationFixtureV1,
    *,
    snapshot_digest: str,
) -> ClarificationEvaluationCaseV1:
    decision_digest = sha256_digest(
        {
            "case_id": fixture.case_id,
            "predecessor_reference": fixture.predecessor_reference,
            "provenance": fixture.provenance,
        }
    )
    familiarity_digest = sha256_digest(
        {
            "evidence_level": fixture.evidence_level,
            "provenance": fixture.provenance,
        }
    )
    consequence_digest = sha256_digest(
        {
            "high_consequence": fixture.high_consequence,
            "reversible": fixture.reversible,
        }
    )
    event = ClarificationEventV1(
        operation_id=f"fixture:{fixture.case_id}",
        correlation_id="fixture:v752:minimized",
        snapshot_digest=snapshot_digest,
        original_capture=fixture.capture,
        related_record_ids=fixture.related_record_ids,
        candidate_interpretations=fixture.candidate_interpretations,
        initial_decision_digest=decision_digest,
        evidence_level=fixture.evidence_level,
        familiarity_digest=familiarity_digest,
        consequence_digest=consequence_digest,
        reversible=fixture.reversible,
        question=fixture.question,
        question_basis=fixture.question_basis,
        user_response=fixture.user_response,
        final_confirmed_interpretation=fixture.expected,
        final_classification=fixture.confirmed_classification,
        final_destination=fixture.confirmed_destination,
        execution_path_effect=fixture.execution_path_effect,
    )
    return ClarificationEvaluationCaseV1(
        case_id=fixture.case_id,
        event=event,
        predecessor_decision_digest=decision_digest,
        counterfactual=CounterfactualDecisionV1(
            likely_classification=fixture.counterfactual_classification,
            likely_destination=fixture.counterfactual_destination,
            confidence_basis=(fixture.predecessor_reference, fixture.provenance),
            differs_from_confirmed=fixture.counterfactual_differs,
        ),
        question_quality=fixture.question_quality,
        outcome=fixture.outcome,
    )


def fixture_cases(
    document: ClarificationFixtureDocumentV1,
) -> tuple[str, tuple[ClarificationEvaluationCaseV1, ...]]:
    """Convert minimized observations into deterministic non-authoritative cases."""

    errors = validate_fixture_minimization(document)
    if errors:
        raise ValueError("; ".join(errors))
    snapshot_digest = sha256_digest(document.model_dump(mode="json"))
    cases = tuple(
        _fixture_case(fixture, snapshot_digest=snapshot_digest)
        for fixture in document.cases
    )
    return snapshot_digest, cases


def recommend_thresholds(
    cases: tuple[ClarificationEvaluationCaseV1, ...],
) -> tuple[str, ...]:
    """Recommend review thresholds from observed evidence without creating policy."""

    if not cases:
        return ("Collect a non-empty retained corpus before proposing acceptance thresholds.",)
    report = build_report(
        feature_mode="shadow",
        snapshot_digest=cases[0].event.snapshot_digest,
        cases=cases,
    )
    metrics = report.metrics
    recommendations: list[str] = []
    if metrics.repeated_questions:
        recommendations.append(
            "Review the observed repeated-question rate before setting a target."
        )
    if metrics.no_material_change_questions:
        recommendations.append(
            "Review questions that confirmed but did not change a decision before "
            "setting a clarification-frequency target."
        )
    if metrics.task_suppression_prevented or metrics.duplicate_task_creation_prevented:
        recommendations.append(
            "Preserve consequence controls because observed questions prevented "
            "incorrect execution-path effects."
        )
    if not recommendations:
        recommendations.append(
            "Retain the observed baseline and gather additional representative cases "
            "before setting thresholds."
        )
    return tuple(recommendations)


def build_baseline_report(
    *,
    snapshot_digest: str,
    cases: tuple[ClarificationEvaluationCaseV1, ...],
) -> ClarificationEvaluationReportV1:
    """Create a deterministic retained-artifact report with evidence-based recommendations."""

    return build_report(
        feature_mode="shadow",
        snapshot_digest=snapshot_digest,
        cases=cases,
        recommended_thresholds=recommend_thresholds(cases),
    )


def build_fixture_baseline_report(
    document: ClarificationFixtureDocumentV1,
) -> ClarificationEvaluationReportV1:
    """Build the deterministic baseline from the accepted minimized corpus."""

    snapshot_digest, cases = fixture_cases(document)
    return build_baseline_report(snapshot_digest=snapshot_digest, cases=cases)


def contract_schemas() -> dict[str, dict[str, object]]:
    """Export the required versioned contract schemas for retained validation."""

    from atlas_ros.clarification_evaluation_v752 import (
        ClarificationEvaluationReportV1,
        ClarificationEventV1,
        ClarificationEvaluationCaseV1,
        ClarificationMetricsV1,
        ClarificationOutcomeV1,
        CounterfactualDecisionV1,
        QuestionQualityAssessmentV1,
    )

    contracts = (
        ClarificationEventV1,
        ClarificationEvaluationCaseV1,
        CounterfactualDecisionV1,
        QuestionQualityAssessmentV1,
        ClarificationOutcomeV1,
        ClarificationMetricsV1,
        ClarificationEvaluationReportV1,
    )
    return {contract.__name__: contract.model_json_schema() for contract in contracts}


def write_evaluation_evidence(
    *,
    fixture_path: Path,
    output_directory: Path,
) -> tuple[Path, Path, Path]:
    """Write deterministic baseline, schema, and minimization evidence artifacts."""

    document = load_fixture_document(fixture_path)
    errors = validate_fixture_minimization(document)
    if errors:
        raise ValueError("; ".join(errors))
    report = build_fixture_baseline_report(document)
    output_directory.mkdir(parents=True, exist_ok=True)
    baseline_path = output_directory / "V752_BASELINE_REPORT.json"
    schema_path = output_directory / "V752_CONTRACT_SCHEMAS.json"
    minimization_path = output_directory / "V752_DATA_MINIMIZATION_RECEIPT.json"
    baseline_payload = report.model_dump(mode="json") | {
        "deterministic_digest": report.deterministic_digest
    }
    baseline_path.write_text(
        json.dumps(baseline_payload, indent=2, sort_keys=True) + "\n"
    )
    schema_path.write_text(
        json.dumps(contract_schemas(), indent=2, sort_keys=True) + "\n"
    )
    minimization_path.write_text(
        json.dumps(
            {
                "schema_version": "v752-data-minimization-receipt-v1",
                "status": "passed",
                "fixture_count": len(document.cases),
                "fixture_snapshot_digest": report.snapshot_digest,
                "provider_writes": 0,
                "todoist_writes": 0,
                "errors": [],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    return baseline_path, schema_path, minimization_path
