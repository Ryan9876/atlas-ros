from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from hypothesis import given
from hypothesis import strategies as st

from atlas_ros.contracts import (
    PlanningModelCandidate,
    ReasoningPackageV3,
)
from atlas_ros.engines import KnowledgeCompositionEngine, ManagementStructureEngine
from atlas_ros.models import (
    DependencyResolutionError,
    KnowledgeDependencyResolver,
    KnowledgeModule,
    KnowledgeModuleRegistry,
    ModuleDependency,
    PlanningModel,
    SectionDefinition,
    assert_source_package_equivalence,
    load_default_registries,
    version_satisfies,
)


def selected_reasoning(**known_inputs: object) -> ReasoningPackageV3:
    return ReasoningPackageV3(
        correlation_id=uuid4(),
        source_component="engines.management_reasoning",
        classification="action",
        destination="action_records",
        normalized_intent=(
            "Create a team operating framework that clarifies responsibility standards"
        ),
        management_pattern="Operational Excellence",
        candidate_planning_models=(
            PlanningModelCandidate(
                model_id="team-operating-model",
                version_constraint="^2.0.0",
                confidence=0.96,
                rationale="The request concerns team-level operating responsibilities.",
            ),
            PlanningModelCandidate(
                model_id="roles-and-responsibilities",
                confidence=0.72,
                rationale="The request also mentions responsibility standards.",
            ),
        ),
        selected_planning_model_id="team-operating-model",
        selected_planning_model_version_constraint="^2.0.0",
        selection_method="user_selected",
        selection_confidence=1.0,
        selection_rationale="Ryan selected the complete Team Operating Model framework.",
        alternatives_considered=("roles-and-responsibilities",),
        planning_assumptions=("The request concerns a team-level operating model.",),
        known_inputs=dict(known_inputs),
    )


def complete_context() -> dict[str, object]:
    return {
        "owner": "Ryan",
        "responsibility": "Lead the network services team operating model",
        "desired_outcome": "A reviewed, accountable, measurable team operating model exists",
        "services": ["network operations", "network engineering"],
        "service_owner": "Ryan",
        "review_cadence": "quarterly",
        "metric_owner": "service owners",
        "metric_source": "service health dashboard",
        "effective_date": "2026-08-01",
        "next_review_date": "2026-11-01",
    }


def test_team_operating_model_v2_is_deterministic_and_stops_before_execution() -> None:
    models, modules = load_default_registries()
    reasoned = selected_reasoning(**complete_context())
    events: list[tuple[str, dict[str, str]]] = []
    knowledge_engine = KnowledgeCompositionEngine(
        modules,
        models,
        lambda event, fields: events.append((event, fields)),
    )
    first = knowledge_engine.compose_v2(reasoned)
    second = knowledge_engine.compose_v2(reasoned)
    assert first.package_digest == second.package_digest
    assert first.resolution_digest == second.resolution_digest
    assert first.verify_digest()
    assert len(first.composition_order) == 14
    assert first.missing_context_requirements == ()
    assert all(first.value_provenance.values())

    management = ManagementStructureEngine(
        models,
        lambda event, fields: events.append((event, fields)),
    ).structure_v2(reasoned, first)
    assert management.verify_digest()
    assert management.lifecycle_status == "structurally_complete"
    assert len(management.sections) == 14
    assert all(state == "complete" for state in management.section_completeness.values())
    assert all(management.section_provenance.values())
    assert not hasattr(management, "steps")
    assert not hasattr(management, "provider")
    assert [event for event, _ in events] == [
        "knowledge_package_composed",
        "knowledge_package_composed",
        "management_package_constructed",
    ]


def test_incomplete_context_is_explicitly_decision_required() -> None:
    models, modules = load_default_registries()
    reasoned = selected_reasoning()
    knowledge = KnowledgeCompositionEngine(modules, models).compose_v2(reasoned)
    assert set(knowledge.missing_context_requirements) >= {
        "owner",
        "services",
        "service_owner",
        "metric_owner",
        "metric_source",
        "review_cadence",
    }
    management = ManagementStructureEngine(models).structure_v2(reasoned, knowledge)
    assert management.lifecycle_status == "decision_required"
    assert "missing_accountable_owner" in management.decision_points
    with pytest.raises(ValueError, match="unsafe lossy"):
        knowledge.project_v1()
    with pytest.raises(ValueError, match="unsafe lossy"):
        management.project_v1()


def test_v2_safe_projection_retains_v1_readers() -> None:
    models, modules = load_default_registries()
    reasoned = selected_reasoning(**complete_context())
    knowledge = KnowledgeCompositionEngine(modules, models).compose_v2(reasoned)
    management = ManagementStructureEngine(models).structure_v2(reasoned, knowledge)
    assert knowledge.project_v1().module_ids == list(knowledge.composition_order)
    assert management.project_v1().owner == "Ryan"


def test_registry_versioning_manifest_digest_and_registration_order() -> None:
    one = KnowledgeModule(module_id="core", version="1.0.0")
    two = KnowledgeModule(module_id="core", version="2.0.0")
    forward = KnowledgeModuleRegistry((one, two))
    reverse = KnowledgeModuleRegistry((two, one))
    assert forward.resolve("core", "^1.0.0") == one
    assert forward.resolve("core", ">=1.0.0,<3.0.0") == two
    assert forward.list() == reverse.list()
    assert forward.digest() == reverse.digest()
    with pytest.raises(ValueError, match="duplicate knowledge module"):
        forward.register(two)
    with pytest.raises(KeyError, match="unsupported knowledge module version"):
        forward.resolve("core", "^3.0.0")


@given(
    major=st.integers(min_value=0, max_value=10),
    minor=st.integers(min_value=0, max_value=20),
    patch=st.integers(min_value=0, max_value=20),
)
def test_exact_semver_constraint_property(major: int, minor: int, patch: int) -> None:
    version = f"{major}.{minor}.{patch}"
    assert version_satisfies(version, version)
    assert version_satisfies(version, f"=={version}")


def test_dependency_cycle_missing_conflict_and_ambiguous_provider_fail_closed() -> None:
    model = PlanningModel(
        model_id="test",
        version="2.0.0",
        sections=(SectionDefinition(section_id="one", title="One"),),
        required_modules=(ModuleDependency("a"),),
    )
    cycle = KnowledgeModuleRegistry(
        (
            KnowledgeModule(
                module_id="a",
                version="2.0.0",
                required_dependencies=(ModuleDependency("b"),),
            ),
            KnowledgeModule(
                module_id="b",
                version="2.0.0",
                required_dependencies=(ModuleDependency("a"),),
            ),
        )
    )
    with pytest.raises(DependencyResolutionError, match="dependency cycle"):
        KnowledgeDependencyResolver(cycle).resolve(model)

    with pytest.raises(DependencyResolutionError, match="unknown knowledge module"):
        KnowledgeDependencyResolver(KnowledgeModuleRegistry()).resolve(model)

    conflict = KnowledgeModuleRegistry(
        (
            KnowledgeModule(module_id="a", version="2.0.0", declared_conflicts=("b",)),
            KnowledgeModule(module_id="b", version="2.0.0"),
        )
    )
    conflict_model = PlanningModel(
        model_id="conflict",
        version="2.0.0",
        sections=(SectionDefinition(section_id="one", title="One"),),
        required_modules=(ModuleDependency("a"), ModuleDependency("b")),
    )
    with pytest.raises(DependencyResolutionError, match="declared module conflict"):
        KnowledgeDependencyResolver(conflict).resolve(conflict_model)

    ambiguous = KnowledgeModuleRegistry(
        (
            KnowledgeModule(
                module_id="a",
                version="2.0.0",
                facts={"owner": "one"},
                provided_knowledge_keys=("owner",),
            ),
            KnowledgeModule(
                module_id="b",
                version="2.0.0",
                facts={"owner": "two"},
                provided_knowledge_keys=("owner",),
            ),
        )
    )
    with pytest.raises(DependencyResolutionError, match="ambiguous providers"):
        KnowledgeDependencyResolver(ambiguous).resolve(conflict_model)


def test_optional_degraded_and_deprecated_module_warnings() -> None:
    registry = KnowledgeModuleRegistry(
        (
            KnowledgeModule(
                module_id="core",
                version="2.0.0",
                lifecycle_status="deprecated",
                replacement_module="replacement",
            ),
        )
    )
    model = PlanningModel(
        model_id="test",
        version="2.0.0",
        sections=(SectionDefinition(section_id="one", title="One"),),
        required_modules=(ModuleDependency("core"),),
        optional_modules=(ModuleDependency("missing"),),
        allow_degraded_composition=True,
    )
    result = KnowledgeDependencyResolver(registry).resolve(model)
    assert result.warnings == (
        "deprecated_module:core@2.0.0:replacement=replacement",
        "optional_dependency_omitted:missing",
    )


def test_source_and_packaged_configuration_are_checksum_equivalent() -> None:
    root = Path(__file__).resolve().parents[1]
    assert_source_package_equivalence(
        root / "config",
        root / "src" / "atlas_ros" / "data",
    )
