from atlas_ros.domain.models import Action
from atlas_ros.planning.decomposition import DecompositionService
from atlas_ros.rules import RulesEngine, action_rules


def test_execution_ready_requires_all_gates() -> None:
    action = Action(id="a1", title="Migrate network", execution_ready=True)
    findings = RulesEngine(action_rules()).evaluate(action, action.id)
    assert {item.rule_id for item in findings} == {
        "ACTION_EXECUTION_READY_REQUIRES_DOD",
        "ACTION_EXECUTION_READY_REQUIRES_RYAN_OWNER",
        "ACTION_DELEGATION_REVIEWED",
    }


def test_ready_action_passes() -> None:
    action = Action(
        id="a1",
        title="Investigation",
        owner="Ryan",
        definition_of_done="Decision recorded",
        execution_ready=True,
        delegated_work_present=True,
    )
    report = DecompositionService().readiness(action)
    assert report.status.value == "ready"
    assert report.proposed_subtasks


def test_personal_action_does_not_require_delegated_work() -> None:
    action = Action(
        id="a2",
        title="Review budget",
        owner="Ryan",
        definition_of_done="Budget approved",
        execution_ready=True,
        delegation_reviewed=True,
        delegated_work_required=False,
    )
    report = DecompositionService().readiness(action)
    assert report.status.value == "ready"


def test_required_delegation_must_be_separated() -> None:
    action = Action(
        id="a3",
        title="Coordinate implementation",
        owner="Ryan",
        definition_of_done="Implementation validated",
        execution_ready=True,
        delegation_reviewed=True,
        delegated_work_required=True,
    )
    findings = RulesEngine(action_rules()).evaluate(action, action.id)
    assert "ACTION_REQUIRED_DELEGATION_SEPARATED" in {item.rule_id for item in findings}
