from atlas_ros.domain.models import Action
from atlas_ros.rules import RulesEngine, action_rules
from atlas_ros.workflows.w03a_decomposition import DecompositionService


def test_execution_ready_requires_all_gates() -> None:
    action = Action(id="a1", title="Migrate network", execution_ready=True)
    findings = RulesEngine(action_rules()).evaluate(action, action.id)
    assert {item.rule_id for item in findings} == {
        "ACTION_EXECUTION_READY_REQUIRES_DOD",
        "ACTION_EXECUTION_READY_REQUIRES_RYAN_OWNER",
        "ACTION_DELEGATION_SEPARATION",
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
