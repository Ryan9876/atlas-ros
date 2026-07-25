from __future__ import annotations

import pytest

from atlas_ros.adapters.llm import FixtureLLMAdapter
from atlas_ros.contracts import ReasoningPackageV2
from atlas_ros.domain.models import Capture, Classification, RoutingRecommendation
from atlas_ros.engines import ManagementReasoningEngine
from atlas_ros.services import RecordRoutingService
from atlas_ros.services.routing import RoutingMode, RoutingService


@pytest.mark.parametrize(
    ("content", "domain", "workstream", "context"),
    [
        (
            "Restore access for a direct report so the employee can work",
            "people_leadership",
            "Leadership & Team",
            "people_leader",
        ),
        (
            "Restore the production service after a service outage",
            "operational_stewardship",
            "Operations",
            "operations_manager",
        ),
        (
            "Coordinate the network migration project milestone",
            "project_delivery",
            "Active Projects",
            "project_manager",
        ),
        (
            "Follow up with vendor because we are waiting on a pending response",
            "external_dependency",
            "Waiting on Others",
            "",
        ),
        (
            "Complete the cloud certification course and training",
            "capability_building",
            "Development & Learning",
            "",
        ),
    ],
)
def test_responsibility_first_classification(
    content: str,
    domain: str,
    workstream: str,
    context: str,
) -> None:
    reasoning = ManagementReasoningEngine().reason_v2(Capture(content=content))
    assert reasoning.contract_version == 2
    assert reasoning.responsibility_domain == domain
    assert reasoning.workstream == workstream
    assert reasoning.operating_context == context
    assert reasoning.confidence >= 0.75
    assert reasoning.requires_human_decision is False
    assert reasoning.rationale
    assert workstream in reasoning.rationale[0]
    assert reasoning.decisive_evidence


def test_technical_activity_does_not_override_people_responsibility() -> None:
    reasoning = ManagementReasoningEngine().reason_v2(
        Capture(
            content=("Troubleshoot the VPN access for a direct report and enable the team member")
        )
    )
    assert reasoning.responsibility_domain == "people_leadership"
    assert reasoning.workstream == "Leadership & Team"
    assert "direct report" in {item.signal for item in reasoning.decisive_evidence}


@pytest.mark.parametrize(
    ("content", "classification", "destination"),
    [
        ("Record a risk about the production migration", "risk", "risks_and_blockers"),
        ("Make a decision about the vendor strategy", "decision", "decision_log"),
        ("Create a project for the multi-phase network migration", "project", "portfolio_projects"),
        ("Delegate to the engineer the implementation work", "delegated_work", "delegated_work"),
        ("For reference save this note about the operating model", "reference", "universal_inbox"),
    ],
)
def test_record_classification_is_separate_from_workstream(
    content: str,
    classification: str,
    destination: str,
) -> None:
    reasoning = ManagementReasoningEngine().reason_v2(Capture(content=content))
    assert reasoning.classification == classification
    assert reasoning.destination == destination


def test_sparse_context_fails_closed() -> None:
    engine = ManagementReasoningEngine()
    reasoning = engine.reason_v2(Capture(content="Look into this later"))
    recommendation = engine.recommendation_from_v2(reasoning)
    routed = RecordRoutingService().apply(recommendation, reasoning)
    assert reasoning.responsibility_domain == "unresolved"
    assert reasoning.requires_human_decision is True
    assert reasoning.fallback_reason
    assert routed.classification is Classification.NEEDS_CLARIFICATION
    assert routed.destination == "universal_inbox"


def test_v2_contract_projects_to_v1_without_losing_routing_fields() -> None:
    reasoning = ManagementReasoningEngine().reason_v2(
        Capture(content="Coordinate the datacenter migration project milestone")
    )
    projected = reasoning.project_v1()
    assert projected.contract_version == 1
    assert projected.classification == reasoning.classification
    assert projected.destination == reasoning.destination
    assert projected.confidence == reasoning.confidence
    assert projected.rationale == reasoning.rationale


def test_intent_is_supporting_evidence_not_sole_authority() -> None:
    reasoning = ManagementReasoningEngine().reason_v2(
        Capture(
            content=("As project manager, restore the production service after a service outage")
        )
    )
    assert reasoning.responsibility_domain == "operational_stewardship"
    assert reasoning.workstream == "Operations"
    assert reasoning.operating_context == "operations_manager"


def test_shadow_mode_preserves_legacy_authority_and_records_semantic_evidence() -> None:
    legacy = RoutingRecommendation(
        classification=Classification.ACTION,
        destination="action_records",
        confidence=1.0,
        desired_outcome="Access is restored",
    )
    service = RoutingService(FixtureLLMAdapter(legacy), mode=RoutingMode.SHADOW)
    result = service.plan(
        Capture(content="Restore access for a direct report so the employee can work")
    )
    assert result == legacy
    assert service.last_semantic_evidence is not None
    assert service.last_semantic_evidence.reasoning.responsibility_domain == "people_leadership"
    assert service.last_semantic_evidence.differential.semantic_workstream == "Leadership & Team"


def test_semantic_mode_returns_governed_semantic_route() -> None:
    legacy = RoutingRecommendation(
        classification=Classification.REFERENCE,
        destination="universal_inbox",
        confidence=1.0,
        desired_outcome="Legacy placeholder",
    )
    service = RoutingService(FixtureLLMAdapter(legacy), mode=RoutingMode.SEMANTIC)
    result = service.plan(Capture(content="Resolve the production incident and restore service"))
    assert result.classification is Classification.ACTION
    assert result.destination == "action_records"
    assert result.clarification_required is False


def test_reasoning_v2_rejects_context_confidence_without_context() -> None:
    with pytest.raises(ValueError, match="confidence requires an operating context"):
        ReasoningPackageV2(
            source_component="test",
            classification="action",
            destination="action_records",
            responsibility_domain="people_leadership",
            desired_outcome="A result exists",
            workstream="Leadership & Team",
            activity_summary="Support a team member",
            operating_context="",
            operating_context_confidence=0.8,
            confidence=0.9,
        )


def test_classification_challenge_is_traceable_and_idempotent() -> None:
    from atlas_ros.contracts import ClassificationChallenge
    from atlas_ros.services import ClassificationChallengeService

    reasoning = ManagementReasoningEngine().reason_v2(
        Capture(content="Restore access for a direct report")
    )
    challenge = ClassificationChallenge(
        challenge_id="challenge-1",
        correlation_id=reasoning.correlation_id,
        status="corrected",
        reason="This work is part of a governed migration project.",
        corrected_responsibility_domain="project_delivery",
        corrected_workstream="Active Projects",
    )
    service = ClassificationChallengeService()
    corrected, receipt = service.apply(reasoning, challenge)
    replayed, replay_receipt = service.apply(reasoning, challenge)
    assert corrected.responsibility_domain == "project_delivery"
    assert corrected.workstream == "Active Projects"
    assert corrected.challenge_status == "corrected"
    assert receipt.applied is True
    assert replayed == corrected
    assert replay_receipt.idempotent_replay is True


def test_challenge_id_cannot_be_reused_with_different_content() -> None:
    from atlas_ros.contracts import ClassificationChallenge
    from atlas_ros.services import ClassificationChallengeService

    reasoning = ManagementReasoningEngine().reason_v2(
        Capture(content="Restore access for a direct report")
    )
    service = ClassificationChallengeService()
    first = ClassificationChallenge(
        challenge_id="challenge-1",
        correlation_id=reasoning.correlation_id,
        status="accepted",
        reason="Classification is correct.",
    )
    second = ClassificationChallenge(
        challenge_id="challenge-1",
        correlation_id=reasoning.correlation_id,
        status="challenged",
        reason="Classification is not correct.",
    )
    service.apply(reasoning, first)
    with pytest.raises(ValueError, match="different content"):
        service.apply(reasoning, second)
