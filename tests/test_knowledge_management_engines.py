from uuid import uuid4

import pytest

from atlas_ros.contracts import ReasoningPackage
from atlas_ros.engines import KnowledgeCompositionEngine, ManagementStructureEngine
from atlas_ros.models import (
    KnowledgeModule,
    KnowledgeModuleRegistry,
    PlanningModel,
    PlanningModelRegistry,
)


def reasoning() -> ReasoningPackage:
    return ReasoningPackage(
        correlation_id=uuid4(),
        source_component="engines.management_reasoning",
        classification="action",
        destination="action_records",
        confidence=0.98,
    )


def test_team_operating_model_fixture_composes_without_execution() -> None:
    reasoned = reasoning()
    knowledge_registry = KnowledgeModuleRegistry(
        (
            KnowledgeModule(
                module_id="team-operating-model",
                facts={"cadence": "weekly", "audience": "network engineering team"},
                required_context=("priority",),
            ),
        )
    )
    planning_registry = PlanningModelRegistry(
        (
            PlanningModel(
                model_id="team-operating-model",
                responsibility_template=(
                    "Lead the {cadence} operating review for the {audience}"
                ),
                outcome_template=(
                    "The team aligns on {priority} priorities and accountable next actions"
                ),
                default_owner="Ryan",
                default_workstream="Leadership & Team",
            ),
        )
    )
    knowledge = KnowledgeCompositionEngine(knowledge_registry).compose(
        reasoned,
        ("team-operating-model",),
        {"priority": "current"},
    )
    management = ManagementStructureEngine(planning_registry).structure(
        reasoned,
        knowledge,
        "team-operating-model",
    )
    assert knowledge.unresolved_questions == []
    assert management.owner == "Ryan"
    assert management.workstream == "Leadership & Team"
    assert management.responsibility == (
        "Lead the weekly operating review for the network engineering team"
    )
    assert management.desired_outcome == (
        "The team aligns on current priorities and accountable next actions"
    )
    assert not hasattr(management, "steps")


def test_missing_context_becomes_decision_point() -> None:
    reasoned = reasoning()
    module_registry = KnowledgeModuleRegistry(
        (KnowledgeModule(module_id="leadership", required_context=("audience",)),)
    )
    model_registry = PlanningModelRegistry(
        (
            PlanningModel(
                model_id="leadership",
                responsibility_template="Lead the review",
                outcome_template="A decision-ready review exists",
            ),
        )
    )
    knowledge = KnowledgeCompositionEngine(module_registry).compose(
        reasoned, ("leadership",)
    )
    management = ManagementStructureEngine(model_registry).structure(
        reasoned, knowledge, "leadership"
    )
    assert knowledge.unresolved_questions == ["audience"]
    assert management.decision_points == ["audience"]


def test_registry_rejects_duplicates_and_unknown_ids() -> None:
    module = KnowledgeModule(module_id="core")
    with pytest.raises(ValueError, match="duplicate knowledge module"):
        KnowledgeModuleRegistry((module, module))
    with pytest.raises(KeyError, match="unknown planning model"):
        PlanningModelRegistry().get("missing")


def test_management_structure_requires_correlated_packages() -> None:
    reasoned = reasoning()
    other = reasoning()
    knowledge = KnowledgeCompositionEngine(
        KnowledgeModuleRegistry((KnowledgeModule(module_id="core"),))
    ).compose(other, ("core",))
    registry = PlanningModelRegistry(
        (
            PlanningModel(
                model_id="core",
                responsibility_template="Lead the work",
                outcome_template="The work is complete",
            ),
        )
    )
    with pytest.raises(ValueError, match="correlation ids must match"):
        ManagementStructureEngine(registry).structure(reasoned, knowledge, "core")
