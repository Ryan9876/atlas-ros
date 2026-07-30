from __future__ import annotations

from typing import Any, Literal

from atlas_ros.contracts.models import deterministic_digest
from atlas_ros.contracts.v62 import (
    ArchetypeSelection,
    CanonicalIntent,
    ConstraintCategory,
    ConstraintPropagationResult,
    ConstraintRecord,
    ConstraintStrength,
    DependencyRecord,
    DependencyState,
    EvidenceReference,
    IntentEdge,
    IntentEdgeType,
    IntentGraph,
    IntentNode,
    IntentNodeType,
    OutcomeSet,
    PlanningArchetype,
    stable_fingerprint,
)

from .archetypes_v62 import ArchetypeRegistryV62


_DEPENDENCY_DESCRIPTIONS = {
    "required_information": "Required source information and current-state evidence",
    "existing_documentation": "Existing architecture, process, and operational documentation",
    "technical_ownership": "Named technical owner with capacity to perform delegated work",
    "stakeholder_approval": "Required stakeholder and governance approval",
    "budget_procurement": "Budget, licensing, or procurement readiness",
    "vendor_dependency": "Vendor capability, support, or delivery dependency",
    "platform": "Required platform, infrastructure, and access readiness",
    "lab_test_environment": "Bounded lab or test environment",
    "pilot_targets": "Approved low-risk targets for the controlled pilot",
    "monitoring": "Monitoring, observability, and evidence capture",
    "backup_restoration": "Backup and restoration readiness",
    "rollback": "Tested rollback capability",
    "security_compliance": "Security and compliance requirements",
    "change_management": "Change-management controls and approval path",
    "success_measures": "Measurable success criteria",
    "evidence_requirements": "Completion and decision evidence requirements",
    "domain_knowledge": "Sufficient authoritative domain knowledge",
}


class DependencyDiscoveryEngineV62:
    """Discover prerequisites without converting them into current tasks."""

    def discover(
        self,
        canonical: CanonicalIntent,
        archetype: PlanningArchetype,
        primary_node_id: str,
    ) -> tuple[DependencyRecord, ...]:
        raw = canonical.raw_input.casefold()
        result: list[DependencyRecord] = []
        for category in archetype.required_dependency_categories:
            state = DependencyState.INFERRED
            confidence = 0.90
            material = category in {
                "technical_ownership",
                "change_management",
                "rollback",
                "security_compliance",
            }
            if category in raw or category.replace("_", " ") in raw:
                state = DependencyState.CONFIRMED
                confidence = 0.98
            if category == "technical_ownership" and any(
                term in raw for term in ("owner unknown", "no owner", "unassigned owner")
            ):
                state = DependencyState.UNRESOLVED
                confidence = 0.99
                material = True
            dependency_id = f"dependency-{category}-{canonical.semantic_fingerprint[:12]}"
            result.append(
                DependencyRecord(
                    dependency_id=dependency_id,
                    category=category,
                    description=_DEPENDENCY_DESCRIPTIONS.get(
                        category, category.replace("_", " ").title()
                    ),
                    state=state,
                    material=material,
                    confidence=confidence,
                    evidence=(
                        EvidenceReference(
                            source="planning_archetype_registry",
                            detail=f"Required by {archetype.archetype_id}@{archetype.version}",
                        ),
                    ),
                    affected_node_ids=(primary_node_id,),
                )
            )
        technical_archetypes = {
            "controlled-technology-pilot",
            "automation-proof-of-concept",
            "infrastructure-modernization",
            "migration",
            "decommission",
        }
        if canonical.domain == "general" and archetype.archetype_id in technical_archetypes:
            result.append(
                DependencyRecord(
                    dependency_id=f"dependency-domain-{canonical.semantic_fingerprint[:12]}",
                    category="domain_knowledge",
                    description=_DEPENDENCY_DESCRIPTIONS["domain_knowledge"],
                    state=DependencyState.UNRESOLVED,
                    material=True,
                    confidence=0.65,
                    evidence=(
                        EvidenceReference(
                            source="canonical_intent",
                            detail="Technical archetype selected without a resolved domain pack.",
                        ),
                    ),
                    affected_node_ids=(primary_node_id,),
                )
            )
        return tuple(result)


class ConstraintPropagationEngineV62:
    """Apply typed hard constraints and preferences across affected graph nodes."""

    def propagate(
        self,
        canonical: CanonicalIntent,
        affected_node_ids: tuple[str, ...],
    ) -> ConstraintPropagationResult:
        raw = canonical.raw_input.casefold()
        constraints: list[ConstraintRecord] = [
            ConstraintRecord(
                constraint_id=f"constraint-provider-{canonical.semantic_fingerprint[:12]}",
                category=ConstraintCategory.PROVIDER_RESTRICTION,
                statement=(
                    "Reasoning and planning remain provider-free; provider application requires "
                    "separate attended authorization."
                ),
                strength=ConstraintStrength.HARD,
                source="atlas_operating_boundary",
                affected_node_ids=affected_node_ids,
                derived_effects=(
                    "Prevent provider writes during reasoning and planning.",
                    "Keep execution_authorized false.",
                ),
            )
        ]
        hard_conflicts: list[str] = []

        if any(term in raw for term in ("no downtime", "zero downtime", "without downtime")):
            constraints.append(
                ConstraintRecord(
                    constraint_id=f"constraint-availability-{canonical.semantic_fingerprint[:12]}",
                    category=ConstraintCategory.AVAILABILITY,
                    statement="No service downtime is permitted.",
                    strength=ConstraintStrength.HARD,
                    source="user_input",
                    affected_node_ids=affected_node_ids,
                    derived_effects=(
                        "Require bounded targets and staged sequencing.",
                        "Require validated rollback and availability evidence.",
                    ),
                )
            )
        if any(term in raw for term in ("lab only", "non-production only", "test environment only")):
            constraints.append(
                ConstraintRecord(
                    constraint_id=f"constraint-lab-{canonical.semantic_fingerprint[:12]}",
                    category=ConstraintCategory.ENVIRONMENT,
                    statement="Work is restricted to a non-production environment.",
                    strength=ConstraintStrength.HARD,
                    source="user_input",
                    affected_node_ids=affected_node_ids,
                    derived_effects=("Exclude production targets and production execution.",),
                )
            )
        if "budget" in raw or "under $" in raw or "not exceed $" in raw:
            constraints.append(
                ConstraintRecord(
                    constraint_id=f"constraint-budget-{canonical.semantic_fingerprint[:12]}",
                    category=ConstraintCategory.BUDGET,
                    statement="Delivery must remain within the stated budget boundary.",
                    strength=ConstraintStrength.HARD,
                    source="user_input",
                    affected_node_ids=affected_node_ids,
                    derived_effects=("Require cost evidence before approval.",),
                )
            )
        if any(term in raw for term in ("must be approved", "requires approval", "after approval")):
            constraints.append(
                ConstraintRecord(
                    constraint_id=f"constraint-approval-{canonical.semantic_fingerprint[:12]}",
                    category=ConstraintCategory.APPROVAL,
                    statement="Execution requires explicit approval.",
                    strength=ConstraintStrength.HARD,
                    source="user_input",
                    affected_node_ids=affected_node_ids,
                    derived_effects=("Withhold provider execution until approval is verified.",),
                )
            )
        if any(term in raw for term in ("preserve previous", "preserve prior", "retain prior")):
            constraints.append(
                ConstraintRecord(
                    constraint_id=f"constraint-preserve-{canonical.semantic_fingerprint[:12]}",
                    category=ConstraintCategory.USER_PROHIBITION,
                    statement="Existing historical records must remain unchanged.",
                    strength=ConstraintStrength.HARD,
                    source="user_input",
                    affected_node_ids=affected_node_ids,
                    derived_effects=("Use additive version-specific records only.",),
                )
            )

        no_downtime = any(
            term in raw for term in ("no downtime", "zero downtime", "without downtime")
        )
        downtime_allowed = any(
            term in raw for term in ("downtime is allowed", "allow downtime", "outage permitted")
        )
        if no_downtime and downtime_allowed:
            hard_conflicts.append("availability_constraint_conflict")
        lab_only = any(
            term in raw for term in ("lab only", "non-production only", "test environment only")
        )
        production_required = any(
            term in raw for term in ("production only", "must run in production")
        )
        if lab_only and production_required:
            hard_conflicts.append("environment_constraint_conflict")
        provider_execution_requested = any(
            term in raw for term in ("execute now", "apply live", "run the upgrade now")
        )
        if provider_execution_requested:
            hard_conflicts.append("provider_execution_requires_separate_authorization")

        affected_nodes: dict[str, tuple[str, ...]] = {}
        for node_id in affected_node_ids:
            affected_nodes[node_id] = tuple(item.constraint_id for item in constraints)
        values: dict[str, Any] = {
            "constraints": [item.model_dump(mode="json") for item in constraints],
            "hard_conflicts": tuple(hard_conflicts),
            "affected_nodes": affected_nodes,
            "execution_eligible": not hard_conflicts,
        }
        return ConstraintPropagationResult(
            constraints=tuple(constraints),
            hard_conflicts=tuple(hard_conflicts),
            affected_nodes=affected_nodes,
            execution_eligible=not hard_conflicts,
            result_digest=deterministic_digest(values),
        )


class IntentGraphEngineV62:
    """Build a deterministic, typed intent graph with explicit withheld horizons."""

    def __init__(self, registry: ArchetypeRegistryV62 | None = None) -> None:
        self.registry = registry or ArchetypeRegistryV62()

    @staticmethod
    def primary_node_id(outcomes: OutcomeSet) -> str:
        return f"node-primary-{outcomes.primary.outcome_id[-16:]}"

    def build(
        self,
        canonical: CanonicalIntent,
        outcomes: OutcomeSet,
        selection: ArchetypeSelection,
        dependencies: tuple[DependencyRecord, ...],
        constraint_result: ConstraintPropagationResult,
    ) -> IntentGraph:
        archetype = self.registry.get(selection.archetype_id)
        primary_id = self.primary_node_id(outcomes)
        nodes: list[IntentNode] = [
            IntentNode(
                node_id=primary_id,
                node_type=IntentNodeType.PRIMARY_OUTCOME,
                title=outcomes.primary.text,
                description="Canonical primary business outcome.",
                horizon="current",
                material=True,
                projection_eligible=True,
                provenance=("canonical_intent", "outcome_set"),
            )
        ]
        edges: list[IntentEdge] = []

        checkpoint_ids: list[str] = []
        for index, title in enumerate(archetype.current_checkpoint_templates, start=1):
            node_id = f"node-current-{index}-{canonical.semantic_fingerprint[:10]}"
            checkpoint_ids.append(node_id)
            nodes.append(
                IntentNode(
                    node_id=node_id,
                    node_type=IntentNodeType.CURRENT_CHECKPOINT,
                    title=title,
                    description="Minimum coherent current management checkpoint.",
                    horizon="current",
                    material=True,
                    projection_eligible=True,
                    provenance=(f"archetype:{archetype.archetype_id}@{archetype.version}",),
                )
            )
            edges.append(
                self._edge(
                    primary_id,
                    node_id,
                    IntentEdgeType.REQUIRES,
                    f"Primary outcome requires current checkpoint {index}.",
                )
            )
        for source, target in zip(checkpoint_ids, checkpoint_ids[1:], strict=False):
            edges.append(
                self._edge(
                    source,
                    target,
                    IntentEdgeType.PRECEDES,
                    "Current checkpoints retain governed sequence.",
                )
            )

        for outcome in (*outcomes.secondary, *outcomes.supporting, *outcomes.competing):
            node_id = f"node-secondary-{outcome.outcome_id[-16:]}"
            node_type = IntentNodeType.SECONDARY_OUTCOME
            horizon: Literal["blocked", "current"] = (
                "blocked" if outcome.role.value == "competing" else "current"
            )
            nodes.append(
                IntentNode(
                    node_id=node_id,
                    node_type=node_type,
                    title=outcome.text,
                    description=f"{outcome.role.value} outcome.",
                    horizon=horizon,
                    material=True,
                    projection_eligible=horizon == "current",
                    provenance=outcome.provenance,
                )
            )
            edge_type = (
                IntentEdgeType.CONFLICTS_WITH
                if horizon == "blocked"
                else IntentEdgeType.REFINES
            )
            edges.append(self._edge(primary_id, node_id, edge_type, outcome.role.value))

        delegated_id = f"node-delegated-{canonical.semantic_fingerprint[:12]}"
        conditional_id = f"node-conditional-{canonical.semantic_fingerprint[:12]}"
        future_id = f"node-future-{canonical.semantic_fingerprint[:12]}"
        if archetype.delegated_template:
            delegated_title = archetype.delegated_template
            if canonical.domain == "network_automation":
                delegated_title = "Build and execute the Arista CloudVision technical pilot"
            nodes.append(
                IntentNode(
                    node_id=delegated_id,
                    node_type=IntentNodeType.DELEGATED_OUTCOME,
                    title=delegated_title,
                    description="Technical implementation is delegated and not user-owned current work.",
                    horizon="next",
                    material=True,
                    projection_eligible=False,
                    provenance=("archetype_delegation_boundary",),
                )
            )
            edges.append(
                self._edge(delegated_id, primary_id, IntentEdgeType.DERIVED_FROM, "Delegated work supports the primary outcome.")
            )
        if archetype.conditional_template:
            nodes.append(
                IntentNode(
                    node_id=conditional_id,
                    node_type=IntentNodeType.CONDITIONAL_OUTCOME,
                    title=archetype.conditional_template,
                    description="Decision work is withheld until evidence exists.",
                    horizon="conditional",
                    material=True,
                    projection_eligible=False,
                    provenance=("archetype_conditional_horizon",),
                )
            )
            edges.append(
                self._edge(
                    conditional_id,
                    delegated_id if archetype.delegated_template else primary_id,
                    IntentEdgeType.CONDITIONAL_ON,
                    "Conditional review requires completed technical evidence.",
                )
            )
        if archetype.future_template:
            nodes.append(
                IntentNode(
                    node_id=future_id,
                    node_type=IntentNodeType.FUTURE_OUTCOME,
                    title=archetype.future_template,
                    description="Future expansion requires a separate decision and scope.",
                    horizon="future",
                    material=False,
                    projection_eligible=False,
                    provenance=("archetype_future_horizon",),
                )
            )
            edges.append(
                self._edge(
                    future_id,
                    conditional_id if archetype.conditional_template else primary_id,
                    IntentEdgeType.CONDITIONAL_ON,
                    "Future work follows an affirmative governed decision.",
                )
            )

        for dependency in dependencies:
            node_id = f"node-{dependency.dependency_id}"
            nodes.append(
                IntentNode(
                    node_id=node_id,
                    node_type=IntentNodeType.DEPENDENCY,
                    title=dependency.description,
                    description=f"Dependency state: {dependency.state.value}.",
                    horizon="reference" if dependency.state != DependencyState.UNRESOLVED else "blocked",
                    material=dependency.material,
                    projection_eligible=False,
                    provenance=tuple(item.source for item in dependency.evidence),
                )
            )
            edges.append(
                self._edge(primary_id, node_id, IntentEdgeType.DEPENDS_ON, dependency.category)
            )

        for constraint in constraint_result.constraints:
            node_id = f"node-{constraint.constraint_id}"
            nodes.append(
                IntentNode(
                    node_id=node_id,
                    node_type=IntentNodeType.CONSTRAINT,
                    title=constraint.statement,
                    description="; ".join(constraint.derived_effects),
                    horizon="reference",
                    material=constraint.strength == ConstraintStrength.HARD,
                    projection_eligible=False,
                    provenance=(constraint.source,),
                )
            )
            edges.append(
                self._edge(primary_id, node_id, IntentEdgeType.CONSTRAINED_BY, constraint.category.value)
            )

        domain_node_id = f"node-domain-{canonical.semantic_fingerprint[:12]}"
        nodes.append(
            IntentNode(
                node_id=domain_node_id,
                node_type=IntentNodeType.DOMAIN_KNOWLEDGE_REFERENCE,
                title=f"Domain pack: {canonical.domain}",
                description="Domain knowledge enriches planning but cannot authorize execution.",
                horizon="reference",
                material=False,
                projection_eligible=False,
                provenance=("canonical_domain_resolution",),
            )
        )
        edges.append(
            self._edge(primary_id, domain_node_id, IntentEdgeType.DERIVED_FROM, "Domain knowledge reference")
        )

        risk_node_id = f"node-risk-{canonical.semantic_fingerprint[:12]}"
        nodes.append(
            IntentNode(
                node_id=risk_node_id,
                node_type=IntentNodeType.RISK,
                title="Evaluate planning, operational, dependency, and rollback risk",
                description="Risk is evaluated separately and cannot authorize execution.",
                horizon="reference",
                material=True,
                projection_eligible=False,
                provenance=("v62_dynamic_risk_policy",),
            )
        )
        edges.append(self._edge(primary_id, risk_node_id, IntentEdgeType.REQUIRES, "Risk gate"))

        incident_counts: dict[str, int] = {node.node_id: 0 for node in nodes}
        for edge in edges:
            incident_counts[edge.source_node_id] += 1
            incident_counts[edge.target_node_id] += 1
        orphaned = tuple(
            node_id
            for node_id, count in incident_counts.items()
            if count == 0 and node_id != primary_id
        )
        findings = tuple(f"orphaned_material_node:{node_id}" for node_id in orphaned)
        blocked = bool(findings or constraint_result.hard_conflicts)
        values: dict[str, Any] = {
            "contract_version": 1,
            "nodes": [node.model_dump(mode="json") for node in nodes],
            "edges": [edge.model_dump(mode="json") for edge in edges],
            "blocked": blocked,
            "findings": findings,
        }
        return IntentGraph(
            nodes=tuple(nodes),
            edges=tuple(edges),
            blocked=blocked,
            findings=findings,
            graph_digest=deterministic_digest(values),
        )

    @staticmethod
    def _edge(
        source: str,
        target: str,
        edge_type: IntentEdgeType,
        rationale: str,
    ) -> IntentEdge:
        identity = stable_fingerprint((source, target, edge_type.value, rationale))[:20]
        return IntentEdge(
            edge_id=f"edge-{identity}",
            source_node_id=source,
            target_node_id=target,
            edge_type=edge_type,
            rationale=rationale,
        )
