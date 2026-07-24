import pytest

from atlas_ros.adapters.llm import FixtureLLMAdapter
from atlas_ros.domain.models import Capture, Classification, RoutingRecommendation
from atlas_ros.engines import ManagementReasoningEngine
from atlas_ros.services import RecordRoutingService, RoutingShadowComparator
from atlas_ros.workflows.w02_routing import RoutingService


def recommendation(
    *,
    classification: Classification = Classification.ACTION,
    destination: str = "action_records",
    confidence: float = 1.0,
    ambiguities: list[str] | None = None,
    clarification_required: bool = False,
) -> RoutingRecommendation:
    return RoutingRecommendation(
        classification=classification,
        destination=destination,
        confidence=confidence,
        desired_outcome="A governed result exists",
        ambiguities=ambiguities or [],
        clarification_required=clarification_required,
    )


def test_management_reasoning_is_provider_independent() -> None:
    capture = Capture(content="Prepare the operating review")
    engine = ManagementReasoningEngine(FixtureLLMAdapter(recommendation()))
    package = engine.reason(capture)
    assert package.classification == "action"
    assert package.destination == "action_records"
    assert package.correlation_id == capture.correlation_id
    assert package.source_component == "engines.management_reasoning"


def test_record_routing_fails_closed_for_low_confidence() -> None:
    capture = Capture(content="Maybe follow up on this")
    proposed = recommendation(confidence=0.5)
    reasoning = ManagementReasoningEngine.from_recommendation(capture, proposed)
    routed = RecordRoutingService().apply(proposed, reasoning)
    assert routed.classification == Classification.NEEDS_CLARIFICATION
    assert routed.destination == "universal_inbox"
    assert routed.clarification_required is True


def test_record_routing_rejects_invalid_destination() -> None:
    capture = Capture(content="Prepare the operating review")
    proposed = recommendation(destination="portfolio_projects")
    reasoning = ManagementReasoningEngine.from_recommendation(capture, proposed)
    with pytest.raises(ValueError, match="invalid destination"):
        RecordRoutingService().apply(proposed, reasoning)


def test_legacy_w02_matches_semantic_path() -> None:
    capture = Capture(content="Prepare the operating review")
    proposed = recommendation()
    legacy = RoutingService(FixtureLLMAdapter(proposed)).plan(capture)
    reasoning = ManagementReasoningEngine.from_recommendation(capture, proposed)
    semantic = RecordRoutingService().apply(proposed, reasoning)
    differential = RoutingShadowComparator().compare(legacy, semantic)
    assert differential.equivalent is True
    assert differential.fields == ()


def test_shadow_comparator_identifies_material_drift() -> None:
    legacy = recommendation()
    semantic = recommendation(
        classification=Classification.PROJECT,
        destination="portfolio_projects",
    )
    differential = RoutingShadowComparator().compare(legacy, semantic)
    assert differential.equivalent is False
    assert differential.fields == ("classification", "destination")
