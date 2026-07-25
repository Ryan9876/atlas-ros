import pytest

from atlas_ros.adapters.llm import FixtureLLMAdapter
from atlas_ros.domain.models import Action, Capture, Classification, RoutingRecommendation
from atlas_ros.services.routing import RoutingService
from atlas_ros.services.todoist_execution import TodoistService


def test_routing_low_confidence_needs_clarification() -> None:
    service = RoutingService(
        FixtureLLMAdapter(
            RoutingRecommendation(
                classification=Classification.ACTION,
                destination="action_records",
                confidence=0.2,
                desired_outcome="Do it",
            )
        )
    )
    assert (
        service.plan(Capture(content="Something")).classification
        == Classification.NEEDS_CLARIFICATION
    )


def test_invalid_destination_is_rejected() -> None:
    service = RoutingService(
        FixtureLLMAdapter(
            RoutingRecommendation(
                classification=Classification.ACTION,
                destination="todoist",
                confidence=0.9,
                desired_outcome="Do it",
            )
        )
    )
    with pytest.raises(ValueError, match="invalid destination"):
        service.plan(Capture(content="Something"))


def test_prohibited_classification_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "atlas_ros.services.routing.load_config",
        lambda _: {
            "allowed": ["project"],
            "destinations": {"action": "action_records"},
            "confidence_threshold": 0.75,
        },
    )
    service = RoutingService(
        FixtureLLMAdapter(
            RoutingRecommendation(
                classification=Classification.ACTION,
                destination="action_records",
                confidence=0.9,
                desired_outcome="Act on it",
            )
        )
    )
    with pytest.raises(ValueError, match="prohibited classification"):
        service.plan(Capture(content="Something"))


def test_todoist_dry_run() -> None:
    action = Action(
        id="a",
        title="Investigate circuit",
        owner="Ryan",
        definition_of_done="Finding recorded",
        execution_ready=True,
        delegated_work_present=True,
    )
    assert TodoistService().plan(action).dry_run


def test_todoist_rejects_prohibited_label() -> None:
    action = Action(
        id="a",
        title="Investigate",
        owner="Ryan",
        definition_of_done="Done",
        execution_ready=True,
        delegated_work_present=True,
        labels=["ROS"],
    )
    with pytest.raises(ValueError, match="prohibited"):
        TodoistService().plan(action)


def test_todoist_requires_readiness_and_never_applies() -> None:
    incomplete = Action(id="a", title="Investigate", execution_ready=True)
    with pytest.raises(ValueError, match="execution-planning gate"):
        TodoistService().plan(incomplete)
    complete = Action(
        id="a",
        title="Investigate",
        owner="Ryan",
        definition_of_done="Done",
        execution_ready=True,
        delegated_work_present=True,
    )
    with pytest.raises(PermissionError, match="explicit confirmation"):
        TodoistService().apply(complete)
    with pytest.raises(PermissionError, match="no production"):
        TodoistService().apply(complete, confirmed=True)
