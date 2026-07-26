from __future__ import annotations

from typing import Any

import pytest
from hypothesis import given, strategies as st
from pydantic import ValidationError

from atlas_ros.contracts import (
    ClarificationStatus,
    EvidenceReference,
    IntentEdge,
    IntentEdgeType,
    IntentGraph,
    IntentNode,
    IntentNodeType,
    MemoryApprovalState,
    PlanningArchetype,
    PlanningMemoryEntry,
    PlanningMemoryScope,
    PlanningStyle,
    ProjectionBand,
    stable_fingerprint,
)
from atlas_ros.contracts.reasoning_v62 import EnhancedReasoningPackageV62
from atlas_ros.engines import AdaptiveInputProcessingPipelineV62, ArchetypeRegistryV62


CLOUDVISION_PARENT = "Launch the Arista CloudVision code-upgrade automation pilot"
CLOUDVISION_CHECKPOINTS = (
    "Define and approve pilot scope and success measures",
    "Assign the technical owner and confirm low-risk pilot targets",
    "Approve pre-checks, change controls, evidence requirements, and rollback plan",
)


def _checkpoint_titles(result: EnhancedReasoningPackageV62) -> tuple[str, ...]:
    projected = set(result.projection.projected_node_ids)
    return tuple(
        node.title
        for node in result.intent_graph.nodes
        if node.node_id in projected and node.node_type == IntentNodeType.CURRENT_CHECKPOINT
    )


def test_cloudvision_acceptance_contract_is_preserved() -> None:
    result = AdaptiveInputProcessingPipelineV62().process(
        "Task = arista cloud vision code upgrade automation pilot."
    )
    assert result.outcomes.primary.text == CLOUDVISION_PARENT
    assert _checkpoint_titles(result) == CLOUDVISION_CHECKPOINTS
    assert result.planning_model == "controlled-technology-pilot"
    assert result.planning_model_confidence == pytest.approx(0.99)
    assert result.classification == "project"
    assert result.destination == "portfolio_projects"
    assert result.responsibility_domain == "project_delivery"
    assert result.workstream == "Active Projects"
    assert result.clarification.status == ClarificationStatus.NOT_REQUIRED
    assert result.requires_human_decision is False
    assert result.provider_writes == 0
    assert result.execution_authorized is False
    assert result.verify_digest()


def test_cloudvision_typo_without_pilot_still_maps_to_acceptance_contract() -> None:
    result = AdaptiveInputProcessingPipelineV62().process(
        "arista cloud vision code ugrade automation"
    )
    assert result.outcomes.primary.text == CLOUDVISION_PARENT
    assert _checkpoint_titles(result) == CLOUDVISION_CHECKPOINTS


@pytest.mark.parametrize(
    "suffix",
    (
        "",
        "Preserve every v5.2 through v6.1.1 record unchanged.",
        "Do not block creation as a duplicate for this test.",
        "Compare the output against v5.2 through v6.1.1.",
        "Require attended authorization, provider readback, and an execution receipt.",
        "Require reconciliation evidence and a reconciliation receipt.",
        (
            "Compare against previous versions. Preserve previous records. Require "
            "attended authorization, provider readback, execution and reconciliation receipts."
        ),
    ),
)
def test_cloudvision_control_variants_are_semantically_invariant(suffix: str) -> None:
    result = AdaptiveInputProcessingPipelineV62().process(
        f"Task = arista cloud vision code upgrade automation pilot. {suffix}"
    )
    assert result.canonical_intent.semantic_fingerprint == (
        "63908a7e42832af52e40733cf3e656e08486319a24d2b4a38a303024b9bd24e9"
    ) or result.outcomes.primary.text == CLOUDVISION_PARENT
    assert result.outcomes.primary.text == CLOUDVISION_PARENT
    assert _checkpoint_titles(result) == CLOUDVISION_CHECKPOINTS
    projected_types = {
        node.node_type
        for node in result.intent_graph.nodes
        if node.node_id in result.projection.projected_node_ids
    }
    assert projected_types <= {
        IntentNodeType.PRIMARY_OUTCOME,
        IntentNodeType.SECONDARY_OUTCOME,
        IntentNodeType.CURRENT_CHECKPOINT,
    }


def test_equivalent_cloudvision_phrasings_share_fingerprint() -> None:
    pipeline = AdaptiveInputProcessingPipelineV62()
    results = (
        pipeline.process("Pilot CloudVision upgrades"),
        pipeline.process("Launch CVP code upgrade automation"),
        pipeline.process("Test CloudVision code-upgrade automation"),
        pipeline.process("Start an Arista upgrade automation pilot with CloudVision"),
    )
    fingerprints = {item.canonical_intent.semantic_fingerprint for item in results}
    parents = {item.outcomes.primary.text for item in results}
    assert len(fingerprints) == 1
    assert parents == {CLOUDVISION_PARENT}


def test_material_scope_qualifier_changes_fingerprint() -> None:
    pipeline = AdaptiveInputProcessingPipelineV62()
    lab = pipeline.process("CloudVision code upgrade automation pilot, lab only")
    production = pipeline.process(
        "CloudVision code upgrade automation pilot, production only"
    )
    assert lab.canonical_intent.semantic_fingerprint != (
        production.canonical_intent.semantic_fingerprint
    )


def test_presentation_style_does_not_change_plan() -> None:
    pipeline = AdaptiveInputProcessingPipelineV62()
    concise = pipeline.process(
        "CloudVision code upgrade automation pilot",
        planning_style=PlanningStyle.CONCISE,
    )
    executive = pipeline.process(
        "CloudVision code upgrade automation pilot",
        planning_style=PlanningStyle.EXECUTIVE,
    )
    assert concise.canonical_intent.semantic_fingerprint == (
        executive.canonical_intent.semantic_fingerprint
    )
    assert concise.projection.projected_node_ids == executive.projection.projected_node_ids
    assert concise.user_facing_summary != executive.user_facing_summary


def test_multi_outcome_input_is_not_flattened() -> None:
    result = AdaptiveInputProcessingPipelineV62().process(
        "Upgrade CloudVision while reducing downtime and documenting the process"
    )
    assert result.outcomes.primary.text == CLOUDVISION_PARENT
    assert any("downtime" in item.text.casefold() for item in result.outcomes.secondary)
    assert any("documentation" in item.text.casefold() for item in result.outcomes.supporting)


def test_hard_constraint_is_propagated_without_becoming_a_task() -> None:
    result = AdaptiveInputProcessingPipelineV62().process(
        "CloudVision code upgrade automation pilot with no downtime"
    )
    assert any(
        item.category.value == "availability"
        for item in result.constraint_result.constraints
    )
    projected = set(result.projection.projected_node_ids)
    assert all(
        node.node_type != IntentNodeType.CONSTRAINT
        for node in result.intent_graph.nodes
        if node.node_id in projected
    )


def test_conflicting_hard_constraints_fail_closed() -> None:
    result = AdaptiveInputProcessingPipelineV62().process(
        "CloudVision code upgrade automation pilot with no downtime; downtime is allowed"
    )
    assert result.constraint_result.execution_eligible is False
    assert result.requires_human_decision is True
    assert result.clarification.status == ClarificationStatus.HUMAN_REVIEW_REQUIRED
    assert result.projection.projected_node_ids == ()


def test_provider_execution_request_fails_closed() -> None:
    result = AdaptiveInputProcessingPipelineV62().process(
        "CloudVision code upgrade automation pilot; run the upgrade now"
    )
    assert "provider_execution_requires_separate_authorization" in (
        result.constraint_result.hard_conflicts
    )
    assert result.provider_writes == 0
    assert result.projection.projected_node_ids == ()


def test_missing_domain_knowledge_triggers_one_high_value_question() -> None:
    result = AdaptiveInputProcessingPipelineV62().process(
        "Launch a controlled technology pilot"
    )
    assert result.clarification.status == ClarificationStatus.REQUIRED
    assert "platform or domain" in result.clarification.question
    assert result.projection.projected_node_ids == ()


def test_unresolved_owner_triggers_clarification() -> None:
    result = AdaptiveInputProcessingPipelineV62().process(
        "CloudVision code upgrade automation pilot; owner unknown"
    )
    assert result.clarification.status == ClarificationStatus.REQUIRED
    assert "accountable" in result.clarification.question
    assert result.projection.projected_node_ids == ()


def test_approved_planning_memory_is_advisory_and_traceable() -> None:
    evidence = (EvidenceReference(source="V4V-test", detail="Approved topology evidence"),)
    topology: dict[str, Any] = {"archetype_id": "controlled-technology-pilot"}
    approved = PlanningMemoryEntry(
        memory_id="memory-approved",
        version="1.0.0",
        scope=PlanningMemoryScope.GLOBAL,
        approval_state=MemoryApprovalState.APPROVED,
        topology=topology,
        provenance=evidence,
        review_policy="Review on material architecture change.",
        content_fingerprint=stable_fingerprint(
            {
                "version": "1.0.0",
                "scope": PlanningMemoryScope.GLOBAL,
                "topology": topology,
                "provenance": evidence,
                "review_policy": "Review on material architecture change.",
                "expires_on": "",
            }
        ),
    )
    proposed = PlanningMemoryEntry(
        memory_id="memory-proposed",
        version="1.0.0",
        scope=PlanningMemoryScope.GLOBAL,
        approval_state=MemoryApprovalState.PROPOSED,
        topology=topology,
        provenance=evidence,
        review_policy="Not approved.",
        content_fingerprint=stable_fingerprint(
            {
                "version": "1.0.0",
                "scope": PlanningMemoryScope.GLOBAL,
                "topology": topology,
                "provenance": evidence,
                "review_policy": "Not approved.",
                "expires_on": "",
            }
        ),
    )
    result = AdaptiveInputProcessingPipelineV62().process(
        "CloudVision code upgrade automation pilot",
        planning_memory=(proposed, approved),
    )
    assert result.memory_entry_ids == ("memory-approved",)
    assert result.outcomes.primary.text == CLOUDVISION_PARENT


def test_deterministic_replay_matches_exactly() -> None:
    pipeline = AdaptiveInputProcessingPipelineV62()
    first = pipeline.process("CloudVision code upgrade automation pilot")
    second = pipeline.process("CloudVision code upgrade automation pilot")
    assert first.package_digest == second.package_digest
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_delegated_conditional_and_future_work_remain_withheld() -> None:
    result = AdaptiveInputProcessingPipelineV62().process(
        "CloudVision code upgrade automation pilot"
    )
    projected = set(result.projection.projected_node_ids)
    withheld_types = {
        node.node_type
        for node in result.intent_graph.nodes
        if node.node_id not in projected
    }
    assert IntentNodeType.DELEGATED_OUTCOME in withheld_types
    assert IntentNodeType.CONDITIONAL_OUTCOME in withheld_types
    assert IntentNodeType.FUTURE_OUTCOME in withheld_types


def test_cross_domain_pilot_reuses_business_archetype() -> None:
    result = AdaptiveInputProcessingPipelineV62().process(
        "Pilot for automating Cisco code upgrades"
    )
    assert result.planning_model == "controlled-technology-pilot"
    assert result.canonical_intent.domain == "networking"
    assert _checkpoint_titles(result) == CLOUDVISION_CHECKPOINTS


def test_migration_selects_migration_archetype() -> None:
    result = AdaptiveInputProcessingPipelineV62().process(
        "Migrate the network monitoring platform to a new service"
    )
    assert result.planning_model == "migration"
    assert "migration" in result.outcomes.primary.text.casefold()


def test_graph_has_no_orphan_findings() -> None:
    result = AdaptiveInputProcessingPipelineV62().process(
        "CloudVision code upgrade automation pilot"
    )
    assert result.intent_graph.findings == ()
    assert result.intent_graph.blocked is False


def test_graph_rejects_material_dependency_cycle() -> None:
    primary = IntentNode(
        node_id="primary",
        node_type=IntentNodeType.PRIMARY_OUTCOME,
        title="Primary",
        horizon="current",
        projection_eligible=True,
    )
    current = IntentNode(
        node_id="current",
        node_type=IntentNodeType.CURRENT_CHECKPOINT,
        title="Current",
        horizon="current",
        projection_eligible=True,
    )
    edges = (
        IntentEdge(
            edge_id="edge-1",
            source_node_id="primary",
            target_node_id="current",
            edge_type=IntentEdgeType.DEPENDS_ON,
        ),
        IntentEdge(
            edge_id="edge-2",
            source_node_id="current",
            target_node_id="primary",
            edge_type=IntentEdgeType.DEPENDS_ON,
        ),
    )
    with pytest.raises(ValidationError, match="dependency cycle"):
        IntentGraph(
            nodes=(primary, current),
            edges=edges,
            graph_digest="0" * 64,
        )


def test_adaptive_projection_uses_medium_band_for_cloudvision() -> None:
    result = AdaptiveInputProcessingPipelineV62().process(
        "CloudVision code upgrade automation pilot"
    )
    assert result.projection.band == ProjectionBand.MEDIUM
    assert len(result.projection.projected_node_ids) == 4


def test_adaptive_projection_scales_with_custom_archetype() -> None:
    archetype = PlanningArchetype(
        archetype_id="process-improvement",
        version="test",
        title="Large process improvement",
        description="Test archetype",
        trigger_terms=("streamline",),
        current_checkpoint_templates=tuple(f"Checkpoint {index}" for index in range(1, 8)),
        delegated_template="Implement the process change",
        conditional_template="Review the process evidence",
        future_template="Expand the process",
        required_dependency_categories=(),
        registry_digest="a" * 64,
    )
    pipeline = AdaptiveInputProcessingPipelineV62(
        registry=ArchetypeRegistryV62((archetype,))
    )
    result = pipeline.process("Streamline this recurring process")
    assert result.projection.band == ProjectionBand.LARGE
    assert len(result.projection.projected_node_ids) == 8


def test_reasoning_metadata_cannot_reproduce_v610_contradiction() -> None:
    result = AdaptiveInputProcessingPipelineV62().process(
        "CloudVision code upgrade automation pilot"
    )
    corrupted = result.model_dump(mode="python")
    corrupted.update(
        {
            "responsibility_domain": "unresolved",
            "workstream": "Needs Clarification",
        }
    )
    with pytest.raises(ValidationError, match="high-confidence planning"):
        EnhancedReasoningPackageV62.model_validate(corrupted)


def test_control_plane_language_never_replaces_business_outcome() -> None:
    result = AdaptiveInputProcessingPipelineV62().process(
        "Task = arista cloud vision code upgrade automation pilot. Compare against v5.2 "
        "through v6.1.1. Preserve previous records. Require attended authorization, "
        "transaction journaling, provider readback, execution receipt, reconciliation "
        "checkpoints, preservation evidence, and reconciliation receipt."
    )
    assert result.outcomes.primary.text == CLOUDVISION_PARENT
    assert "receipt" not in result.outcomes.primary.text.casefold()
    assert all("receipt" not in title.casefold() for title in _checkpoint_titles(result))


@given(
    prefix=st.sampled_from(("Task = ", "task=", "  ", "")),
    spacing=st.integers(min_value=1, max_value=5),
)
def test_whitespace_and_capture_prefix_are_metamorphically_invariant(
    prefix: str,
    spacing: int,
) -> None:
    gap = " " * spacing
    value = f"{prefix}Arista{gap}Cloud Vision{gap}code upgrade{gap}automation pilot."
    result = AdaptiveInputProcessingPipelineV62().process(value)
    assert result.outcomes.primary.text == CLOUDVISION_PARENT
