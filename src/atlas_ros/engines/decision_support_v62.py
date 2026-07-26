from __future__ import annotations

from typing import Any

from atlas_ros.contracts.models import deterministic_digest
from atlas_ros.contracts.v62 import (
    ArchetypeSelection,
    CanonicalIntent,
    ClarificationDecision,
    ClarificationStatus,
    ConfidenceDimensionV2,
    ConstraintPropagationResult,
    DependencyRecord,
    DependencyState,
    EvidenceReference,
    FindingSeverity,
    IntentConfidenceProfile,
    IntentGraph,
    IntentNodeType,
    MemoryApprovalState,
    OutcomeSet,
    PlanningMemoryEntry,
    PlanningStyle,
    ProjectionBand,
    ProjectionDecisionV62,
    ProjectionPolicy,
    ReflectionFinding,
    ReflectionResult,
    RiskDimension,
    RiskLevel,
    RiskProfile,
    stable_fingerprint,
)


class ConfidenceProfileEngineV62:
    """Produce explicit execution-affecting confidence dimensions."""

    _TECHNICAL_ARCHETYPES = {
        "controlled-technology-pilot",
        "automation-proof-of-concept",
        "infrastructure-modernization",
        "migration",
        "decommission",
    }

    def evaluate(
        self,
        canonical: CanonicalIntent,
        outcomes: OutcomeSet,
        selection: ArchetypeSelection,
        graph: IntentGraph,
        dependencies: tuple[DependencyRecord, ...],
        constraint_result: ConstraintPropagationResult,
    ) -> IntentConfidenceProfile:
        unresolved_material = tuple(
            item
            for item in dependencies
            if item.material and item.state == DependencyState.UNRESOLVED
        )
        competing = bool(outcomes.competing or outcomes.ranking_requires_clarification)
        ambiguity = max(
            1 - selection.confidence,
            0.45 if competing else 0,
            0.40 if unresolved_material else 0,
        )
        contradiction = 1.0 if graph.blocked or constraint_result.hard_conflicts else 0.0
        technical_domain_required = selection.archetype_id in self._TECHNICAL_ARCHETYPES
        domain_score = (
            0.98
            if canonical.domain != "general"
            else 0.65
            if technical_domain_required
            else 0.86
        )
        dependency_score = 0.55 if unresolved_material else 0.93
        checkpoint_count = sum(
            node.node_type == IntentNodeType.CURRENT_CHECKPOINT for node in graph.nodes
        )
        delegation_present = any(
            node.node_type == IntentNodeType.DELEGATED_OUTCOME for node in graph.nodes
        )
        material_evidence = (
            EvidenceReference(
                source="canonical_intent",
                detail=f"Canonical fingerprint {canonical.semantic_fingerprint}",
            ),
            EvidenceReference(
                source="archetype_selection",
                detail=(
                    f"{selection.archetype_id}@{selection.archetype_version} "
                    f"confidence={selection.confidence:.2f}"
                ),
            ),
        )
        values = (
            ("primary_business_objective", 0.99 if outcomes.primary.text else 0.0, True),
            ("intent_type", selection.confidence, True),
            ("responsibility_domain", 0.96 if selection.confidence >= 0.85 else 0.65, True),
            ("workstream_routing", 0.96 if selection.confidence >= 0.85 else 0.65, True),
            ("current_horizon", 0.97 if checkpoint_count else 0.55, True),
            ("delegation", 0.97 if delegation_present else 0.80, True),
            ("dependency_completeness", dependency_score, True),
            (
                "constraint_completeness",
                0.98 if constraint_result.execution_eligible else 0.10,
                True,
            ),
            ("temporal_scope", 0.90 if not competing else 0.65, True),
            ("domain_knowledge_sufficiency", domain_score, technical_domain_required),
            ("ambiguity_resolution", 1 - ambiguity, True),
            ("contradiction_resolution", 1 - contradiction, True),
            (
                "execution_eligibility",
                min(selection.confidence, dependency_score, 1 - contradiction),
                True,
            ),
        )
        dimensions = tuple(
            ConfidenceDimensionV2(
                dimension=name,
                score=max(0.0, min(1.0, score)),
                threshold=0.75,
                material=material,
                evidence=material_evidence,
                affects_execution_eligibility=material,
            )
            for name, score, material in values
        )
        material_floor = min(
            (item.score for item in dimensions if item.material), default=1.0
        )
        failed_material = any(
            item.material and item.affects_execution_eligibility and not item.passes
            for item in dimensions
        )
        eligible = not failed_material and ambiguity < 0.30 and contradiction < 0.20
        warnings = tuple(
            f"low_nonmaterial_confidence:{item.dimension}"
            for item in dimensions
            if not item.material and not item.passes
        )
        payload: dict[str, Any] = {
            "contract_version": 1,
            "dimensions": [item.model_dump(mode="json") for item in dimensions],
            "ambiguity_score": ambiguity,
            "contradiction_score": contradiction,
            "material_confidence_floor": material_floor,
            "execution_eligible": eligible,
            "supporting_evidence": [item.model_dump(mode="json") for item in material_evidence],
            "warnings": warnings,
        }
        return IntentConfidenceProfile(
            dimensions=dimensions,
            ambiguity_score=ambiguity,
            contradiction_score=contradiction,
            material_confidence_floor=material_floor,
            execution_eligible=eligible,
            supporting_evidence=material_evidence,
            warnings=warnings,
            profile_digest=deterministic_digest(payload),
        )


class PlanningMemoryEngineV62:
    """Consult approved topology memory without changing or overriding live intent."""

    def consult(
        self,
        entries: tuple[PlanningMemoryEntry, ...],
        archetype_id: str,
    ) -> tuple[str, ...]:
        selected = [
            item.memory_id
            for item in entries
            if item.approval_state == MemoryApprovalState.APPROVED
            and item.topology.get("archetype_id") == archetype_id
        ]
        return tuple(sorted(selected))


class RiskProfileEngineV62:
    """Score inherent and residual risk with contributing evidence."""

    def evaluate(
        self,
        canonical: CanonicalIntent,
        graph: IntentGraph,
        dependencies: tuple[DependencyRecord, ...],
        constraint_result: ConstraintPropagationResult,
    ) -> RiskProfile:
        primary_ids = tuple(
            node.node_id
            for node in graph.nodes
            if node.node_type == IntentNodeType.PRIMARY_OUTCOME
        )
        unresolved = sum(
            item.material and item.state == DependencyState.UNRESOLVED
            for item in dependencies
        )
        technical = canonical.domain in {
            "network_automation",
            "networking",
            "cloud_infrastructure",
            "security_compliance",
        }
        hard_conflict = bool(constraint_result.hard_conflicts)
        provider_request = any(
            item == "provider_execution_requires_separate_authorization"
            for item in constraint_result.hard_conflicts
        )
        evidence = (
            EvidenceReference(
                source="intent_graph",
                detail=f"Graph {graph.graph_digest} with {len(graph.nodes)} nodes.",
            ),
        )
        scores = {
            "business_risk": (0.45 if technical else 0.30, 0.30),
            "operational_risk": (0.75 if technical else 0.35, 0.45 if technical else 0.25),
            "planning_risk": (0.40, 0.25 if not graph.blocked else 0.80),
            "execution_risk": (0.70 if technical else 0.35, 0.45 if technical else 0.25),
            "dependency_risk": (0.60 if dependencies else 0.25, 0.70 if unresolved else 0.30),
            "constraint_risk": (0.45, 0.90 if hard_conflict else 0.20),
            "change_risk": (0.70 if technical else 0.30, 0.40 if technical else 0.20),
            "security_compliance_risk": (
                0.60 if canonical.domain == "security_compliance" else 0.35,
                0.45 if canonical.domain == "security_compliance" else 0.20,
            ),
            "rollback_risk": (0.65 if technical else 0.30, 0.35 if technical else 0.20),
            "evidence_risk": (0.45, 0.25),
            "ambiguity_risk": (0.35, 0.65 if unresolved else 0.15),
            "provider_write_risk": (0.70 if provider_request else 0.20, 0.90 if provider_request else 0.0),
        }
        dimensions = tuple(
            RiskDimension(
                dimension=name,
                inherent_score=inherent,
                residual_score=residual,
                confidence=0.92 if name != "ambiguity_risk" or not unresolved else 0.75,
                contributing_node_ids=primary_ids,
                evidence=evidence,
            )
            for name, (inherent, residual) in scores.items()
        )
        maximum = max(item.residual_score for item in dimensions)
        level = (
            RiskLevel.CRITICAL
            if maximum >= 0.85
            else RiskLevel.HIGH
            if maximum >= 0.65
            else RiskLevel.MODERATE
            if maximum >= 0.35
            else RiskLevel.LOW
        )
        low_confidence = tuple(
            item.dimension for item in dimensions if item.confidence < 0.75
        )
        payload: dict[str, Any] = {
            "dimensions": [item.model_dump(mode="json") for item in dimensions],
            "overall_level": level.value,
            "review_required": maximum >= 0.65,
            "low_confidence_dimensions": low_confidence,
        }
        return RiskProfile(
            dimensions=dimensions,
            overall_level=level,
            review_required=maximum >= 0.65,
            low_confidence_dimensions=low_confidence,
            profile_digest=deterministic_digest(payload),
        )


class ClarificationEngineV62:
    """Ask only the highest-value material question."""

    def decide(
        self,
        outcomes: OutcomeSet,
        dependencies: tuple[DependencyRecord, ...],
        constraint_result: ConstraintPropagationResult,
        confidence: IntentConfidenceProfile,
        risk: RiskProfile,
    ) -> ClarificationDecision:
        status = ClarificationStatus.NOT_REQUIRED
        question = ""
        issue = ""
        value = 0.0
        alternatives: tuple[str, ...] = ()
        if constraint_result.hard_conflicts:
            status = ClarificationStatus.HUMAN_REVIEW_REQUIRED
            issue = constraint_result.hard_conflicts[0]
            value = 1.0
        elif outcomes.ranking_requires_clarification:
            status = ClarificationStatus.REQUIRED
            issue = "competing_outcome_priority"
            question = "Which outcome should take priority if both cannot be satisfied?"
            alternatives = tuple(item.text for item in outcomes.competing) or (
                outcomes.primary.text,
                "The competing alternative",
            )
            value = 0.95
        else:
            unresolved = next(
                (
                    item
                    for item in dependencies
                    if item.material and item.state == DependencyState.UNRESOLVED
                ),
                None,
            )
            if unresolved is not None:
                status = ClarificationStatus.REQUIRED
                issue = f"unresolved_dependency:{unresolved.category}"
                question = self._dependency_question(unresolved.category)
                alternatives = self._dependency_alternatives(unresolved.category)
                value = 0.90
            elif not confidence.execution_eligible:
                status = ClarificationStatus.REQUIRED
                issue = "material_confidence_below_threshold"
                question = "Is this intended as a bounded pilot, a production rollout, or planning only?"
                alternatives = ("Bounded pilot", "Production rollout", "Planning only")
                value = 0.85
            elif risk.review_required:
                status = ClarificationStatus.HUMAN_REVIEW_REQUIRED
                issue = f"risk_threshold:{risk.overall_level.value}"
                value = 0.80
            elif confidence.warnings:
                status = ClarificationStatus.NONBLOCKING_WARNING
                issue = confidence.warnings[0]
                value = 0.20
        payload: dict[str, Any] = {
            "status": status.value,
            "question": question,
            "expected_information_value": value,
            "material_issue": issue,
            "alternatives": alternatives,
        }
        return ClarificationDecision(
            status=status,
            question=question,
            expected_information_value=value,
            material_issue=issue,
            alternatives=alternatives,
            decision_digest=deterministic_digest(payload),
        )

    @staticmethod
    def _dependency_question(category: str) -> str:
        return {
            "technical_ownership": "Who is accountable for the technical implementation?",
            "domain_knowledge": "Which platform or domain is this initiative intended to address?",
            "stakeholder_approval": "Which approval is required before the initiative can proceed?",
            "rollback": "What rollback capability must be available before execution?",
        }.get(category, f"What is the authoritative status of the {category.replace('_', ' ')} dependency?")

    @staticmethod
    def _dependency_alternatives(category: str) -> tuple[str, ...]:
        return {
            "technical_ownership": ("Named owner", "Owner to be assigned", "External owner"),
            "domain_knowledge": ("Networking", "Cloud infrastructure", "Security", "Other"),
            "stakeholder_approval": ("Manager approval", "Change approval", "No approval required"),
            "rollback": ("Automated rollback", "Manual rollback", "Rollback not yet defined"),
        }.get(category, ("Confirmed", "Not yet confirmed", "Not applicable"))


class AdaptiveProjectionEngineV62:
    """Project the minimum coherent current path using complexity bands."""

    def __init__(self, policy: ProjectionPolicy | None = None) -> None:
        self.policy = policy or ProjectionPolicy()

    def project(
        self,
        graph: IntentGraph,
        confidence: IntentConfidenceProfile,
        constraint_result: ConstraintPropagationResult,
        risk: RiskProfile,
        clarification: ClarificationDecision,
        *,
        reflection_blocked: bool = False,
    ) -> ProjectionDecisionV62:
        current = tuple(
            node.node_id
            for node in graph.nodes
            if node.projection_eligible and node.horizon == "current"
        )
        current_checkpoints = sum(
            node.node_type == IntentNodeType.CURRENT_CHECKPOINT
            for node in graph.nodes
            if node.node_id in current
        )
        band = (
            ProjectionBand.SMALL
            if current_checkpoints <= self.policy.small_max
            else ProjectionBand.MEDIUM
            if current_checkpoints <= self.policy.medium_max
            else ProjectionBand.LARGE
            if current_checkpoints <= self.policy.large_max
            else ProjectionBand.PROGRAM
        )
        limit = {
            ProjectionBand.SMALL: self.policy.small_max,
            ProjectionBand.MEDIUM: self.policy.medium_max,
            ProjectionBand.LARGE: self.policy.large_max,
            ProjectionBand.PROGRAM: self.policy.program_max,
        }[band]
        blocked = (
            not confidence.execution_eligible
            or not constraint_result.execution_eligible
            or risk.review_required
            or clarification.status
            in {ClarificationStatus.REQUIRED, ClarificationStatus.HUMAN_REVIEW_REQUIRED}
            or reflection_blocked
        )
        projected = () if blocked else current[: limit + 1]
        withheld = tuple(node.node_id for node in graph.nodes if node.node_id not in projected)
        explanation = (
            "Projection is withheld because a material confidence, constraint, risk, "
            "clarification, or reflection gate requires review."
            if blocked
            else (
                f"{band.value.title()} complexity projects one primary outcome and "
                f"{current_checkpoints} current checkpoint(s); delegated, conditional, "
                "future, dependency, risk, reference, and control-plane nodes remain withheld."
            )
        )
        payload: dict[str, Any] = {
            "band": band.value,
            "projected_node_ids": projected,
            "withheld_node_ids": withheld,
            "explanation": explanation,
            "review_required": blocked,
        }
        return ProjectionDecisionV62(
            band=band,
            projected_node_ids=projected,
            withheld_node_ids=withheld,
            explanation=explanation,
            review_required=blocked,
            decision_digest=deterministic_digest(payload),
        )


class ReflectionGateV62:
    """Evaluate structured conclusions without recording hidden chain-of-thought."""

    def evaluate(
        self,
        graph: IntentGraph,
        projection: ProjectionDecisionV62,
        constraint_result: ConstraintPropagationResult,
        *,
        classification: str,
        destination: str,
        responsibility_domain: str,
        workstream: str,
    ) -> ReflectionResult:
        nodes = {node.node_id: node for node in graph.nodes}
        projected_nodes = tuple(nodes[node_id] for node_id in projection.projected_node_ids)
        expected_destination = {
            "action": "action_records",
            "project": "portfolio_projects",
            "delegated_work": "delegated_work",
            "risk": "risks_and_blockers",
            "decision": "decision_log",
            "reference": "reference",
            "needs_clarification": "universal_inbox",
        }.get(classification)
        checks = (
            (
                "primary_outcome_visible",
                sum(node.node_type == IntentNodeType.PRIMARY_OUTCOME for node in graph.nodes) == 1,
                "Exactly one primary business outcome remains visible.",
            ),
            (
                "control_plane_excluded",
                all(
                    node.node_type
                    in {
                        IntentNodeType.PRIMARY_OUTCOME,
                        IntentNodeType.SECONDARY_OUTCOME,
                        IntentNodeType.CURRENT_CHECKPOINT,
                    }
                    for node in projected_nodes
                ),
                "Only current business nodes may be projected.",
            ),
            (
                "delegated_work_withheld",
                all(node.node_type != IntentNodeType.DELEGATED_OUTCOME for node in projected_nodes),
                "Delegated technical work remains outside user-owned current work.",
            ),
            (
                "conditional_future_withheld",
                all(
                    node.node_type
                    not in {IntentNodeType.CONDITIONAL_OUTCOME, IntentNodeType.FUTURE_OUTCOME}
                    for node in projected_nodes
                ),
                "Conditional and future outcomes remain withheld until their triggers.",
            ),
            (
                "routing_coherent",
                expected_destination is None
                or (
                    destination == expected_destination
                    and responsibility_domain != "unresolved"
                    and workstream != "Needs Clarification"
                ),
                "Classification, destination, responsibility, and workstream describe one conclusion.",
            ),
            (
                "hard_constraints_satisfied",
                constraint_result.execution_eligible,
                "No hard-constraint conflict remains unresolved.",
            ),
            (
                "graph_integrity",
                not graph.blocked and not graph.findings,
                "The graph has no unresolved conflict or orphan finding.",
            ),
            (
                "minimum_coherent_path",
                len(projection.projected_node_ids)
                <= sum(node.projection_eligible for node in graph.nodes),
                "Projection does not exceed the eligible current business path.",
            ),
        )
        findings = tuple(
            ReflectionFinding(
                finding_id=f"reflection-{stable_fingerprint(name)[:16]}",
                severity=FindingSeverity.BLOCKING if not passed else FindingSeverity.INFORMATIONAL,
                check=name,
                passed=passed,
                detail=detail,
                affected_node_ids=(),
            )
            for name, passed, detail in checks
        )
        blocking = any(not item.passed and item.severity == FindingSeverity.BLOCKING for item in findings)
        payload: dict[str, Any] = {
            "findings": [item.model_dump(mode="json") for item in findings],
            "revision_count": 0,
            "passed": not blocking,
            "review_required": blocking,
        }
        return ReflectionResult(
            findings=findings,
            revision_count=0,
            passed=not blocking,
            review_required=blocking,
            result_digest=deterministic_digest(payload),
        )


class PlanningStyleEngineV62:
    """Render presentation style without altering canonical semantics."""

    def summarize(
        self,
        style: PlanningStyle,
        primary_outcome: str,
        checkpoint_titles: tuple[str, ...],
        risk: RiskProfile,
        clarification: ClarificationDecision,
    ) -> str:
        status = (
            "Review required"
            if clarification.status
            in {ClarificationStatus.REQUIRED, ClarificationStatus.HUMAN_REVIEW_REQUIRED}
            else "No clarification required"
        )
        path = "; ".join(checkpoint_titles)
        if style == PlanningStyle.EXECUTIVE:
            return (
                f"Outcome: {primary_outcome}. Current management path: {path}. "
                f"Residual risk: {risk.overall_level.value}. {status}."
            )
        if style == PlanningStyle.ENGINEERING:
            return (
                f"Canonical outcome: {primary_outcome}. Ordered control checkpoints: {path}. "
                f"Provider writes remain disabled. Risk={risk.overall_level.value}; {status.lower()}."
            )
        if style == PlanningStyle.PROJECT_MANAGEMENT:
            return (
                f"Project outcome: {primary_outcome}. Governed checkpoints: {path}. "
                f"Risk status: {risk.overall_level.value}; {status.lower()}."
            )
        if style == PlanningStyle.OPERATIONAL:
            return (
                f"Operational objective: {primary_outcome}. Execute only after: {path}. "
                f"Risk is {risk.overall_level.value}; {status.lower()}."
            )
        if style == PlanningStyle.STRATEGIC:
            return (
                f"Strategic outcome: {primary_outcome}. The current horizon establishes {path}. "
                f"Residual risk is {risk.overall_level.value}; {status.lower()}."
            )
        if style == PlanningStyle.RESEARCH:
            return (
                f"Evaluated outcome: {primary_outcome}. Current hypotheses and controls are tested through: "
                f"{path}. Residual risk is {risk.overall_level.value}; {status.lower()}."
            )
        return f"{primary_outcome}. Current path: {path}. {status}."
