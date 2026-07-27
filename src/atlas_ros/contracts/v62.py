from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import ContractKind, deterministic_digest


def stable_fingerprint(payload: Any) -> str:
    """Return a stable SHA-256 fingerprint for a JSON-compatible payload."""
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class OutcomeRole(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    SUPPORTING = "supporting"
    CONSTRAINT = "constraint"
    EVIDENCE = "evidence"
    COMPETING = "competing"


class IntentNodeType(StrEnum):
    PRIMARY_OUTCOME = "primary_outcome"
    SECONDARY_OUTCOME = "secondary_outcome"
    CURRENT_CHECKPOINT = "current_checkpoint"
    DELEGATED_OUTCOME = "delegated_outcome"
    CONDITIONAL_OUTCOME = "conditional_outcome"
    FUTURE_OUTCOME = "future_outcome"
    DEPENDENCY = "dependency"
    CONSTRAINT = "constraint"
    ASSUMPTION = "assumption"
    RISK = "risk"
    APPROVAL = "approval"
    EVIDENCE_REQUIREMENT = "evidence_requirement"
    DOMAIN_KNOWLEDGE_REFERENCE = "domain_knowledge_reference"


class IntentEdgeType(StrEnum):
    REQUIRES = "requires"
    ENABLES = "enables"
    BLOCKS = "blocks"
    DEPENDS_ON = "depends_on"
    DELEGATED_TO = "delegated_to"
    CONDITIONAL_ON = "conditional_on"
    CONSTRAINED_BY = "constrained_by"
    EVIDENCED_BY = "evidenced_by"
    PRECEDES = "precedes"
    REFINES = "refines"
    CONFLICTS_WITH = "conflicts_with"
    DERIVED_FROM = "derived_from"


class DependencyState(StrEnum):
    CONFIRMED = "confirmed"
    INFERRED = "inferred"
    OPTIONAL = "optional"
    UNRESOLVED = "unresolved"


class ConstraintStrength(StrEnum):
    HARD = "hard"
    PREFERENCE = "preference"


class ConstraintCategory(StrEnum):
    AVAILABILITY = "availability"
    SAFETY = "safety"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    BUDGET = "budget"
    TIMELINE = "timeline"
    RESOURCE_CAPACITY = "resource_capacity"
    SCOPE = "scope"
    ENVIRONMENT = "environment"
    APPROVAL = "approval"
    ROLLBACK = "rollback"
    EVIDENCE = "evidence"
    CHANGE_MANAGEMENT = "change_management"
    PROVIDER_RESTRICTION = "provider_restriction"
    USER_PROHIBITION = "user_prohibition"


class PlanningStyle(StrEnum):
    EXECUTIVE = "executive"
    STRATEGIC = "strategic"
    PROJECT_MANAGEMENT = "project_management"
    ENGINEERING = "engineering"
    OPERATIONAL = "operational"
    RESEARCH = "research"
    CONCISE = "concise"


class ClarificationStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    REQUIRED = "required"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    OPTIONAL_ENRICHMENT = "optional_enrichment"
    NONBLOCKING_WARNING = "nonblocking_warning"


class FindingSeverity(StrEnum):
    BLOCKING = "blocking"
    REVIEW_REQUIRED = "review_required"
    WARNING = "warning"
    INFORMATIONAL = "informational"


class RiskLevel(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class PlanningMemoryScope(StrEnum):
    GLOBAL = "global"
    USER_PREFERENCE = "user_preference"
    DOMAIN = "domain"
    RELEASE = "release"


class MemoryApprovalState(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    RETIRED = "retired"


class ProjectionBand(StrEnum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    PROGRAM = "program"


class EvidenceReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source: str = Field(min_length=1, max_length=500)
    detail: str = Field(min_length=1, max_length=2_000)


class ConfidenceDimensionV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    dimension: str = Field(min_length=1, max_length=100)
    score: float = Field(ge=0, le=1)
    threshold: float = Field(default=0.75, ge=0, le=1)
    material: bool = True
    evidence: tuple[EvidenceReference, ...] = ()
    affects_execution_eligibility: bool = True

    @property
    def passes(self) -> bool:
        return self.score >= self.threshold


class IntentConfidenceProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal[1] = 1
    dimensions: tuple[ConfidenceDimensionV2, ...]
    ambiguity_score: float = Field(ge=0, le=1)
    contradiction_score: float = Field(ge=0, le=1)
    material_confidence_floor: float = Field(ge=0, le=1)
    execution_eligible: bool
    supporting_evidence: tuple[EvidenceReference, ...] = ()
    warnings: tuple[str, ...] = ()
    profile_digest: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_profile(self) -> IntentConfidenceProfile:
        names = [item.dimension for item in self.dimensions]
        if len(names) != len(set(names)):
            raise ValueError("confidence dimensions must be unique")
        material = [item.score for item in self.dimensions if item.material]
        expected_floor = min(material, default=1.0)
        if abs(self.material_confidence_floor - expected_floor) > 1e-9:
            raise ValueError("material confidence floor does not match material dimensions")
        failed_material = [
            item.dimension
            for item in self.dimensions
            if item.material and item.affects_execution_eligibility and not item.passes
        ]
        should_be_eligible = (
            not failed_material
            and self.ambiguity_score < 0.30
            and self.contradiction_score < 0.20
        )
        if self.execution_eligible != should_be_eligible:
            raise ValueError("execution eligibility contradicts material confidence")
        if not self.verify_digest():
            raise ValueError("confidence-profile digest verification failed")
        return self

    def digest_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"profile_digest"})

    def verify_digest(self) -> bool:
        return self.profile_digest == deterministic_digest(self.digest_payload())


class CanonicalIntent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal[1] = 1
    raw_input: str = Field(min_length=1, max_length=100_000)
    canonical_text: str = Field(min_length=1, max_length=10_000)
    intent_type: str = Field(min_length=1, max_length=200)
    domain: str = Field(default="general", min_length=1, max_length=200)
    normalization_steps: tuple[str, ...] = ()
    material_qualifiers: tuple[str, ...] = ()
    semantic_fingerprint: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_fingerprint(self) -> CanonicalIntent:
        expected = stable_fingerprint(
            {
                "canonical_text": self.canonical_text,
                "intent_type": self.intent_type,
                "domain": self.domain,
                "material_qualifiers": self.material_qualifiers,
            }
        )
        if self.semantic_fingerprint != expected:
            raise ValueError("canonical intent fingerprint verification failed")
        return self


class OutcomeV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    outcome_id: str = Field(min_length=1, max_length=256)
    text: str = Field(min_length=1, max_length=10_000)
    role: OutcomeRole
    priority: int = Field(default=1, ge=1, le=100)
    explicit: bool = True
    provenance: tuple[str, ...] = ()


class OutcomeSet(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal[1] = 1
    primary: OutcomeV2
    secondary: tuple[OutcomeV2, ...] = ()
    supporting: tuple[OutcomeV2, ...] = ()
    competing: tuple[OutcomeV2, ...] = ()
    ranking_requires_clarification: bool = False
    outcome_digest: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_outcomes(self) -> OutcomeSet:
        all_items = (self.primary, *self.secondary, *self.supporting, *self.competing)
        ids = [item.outcome_id for item in all_items]
        if len(ids) != len(set(ids)):
            raise ValueError("outcome IDs must be unique")
        if self.primary.role != OutcomeRole.PRIMARY:
            raise ValueError("primary outcome must use the primary role")
        expected = deterministic_digest(
            self.model_dump(mode="json", exclude={"outcome_digest"})
        )
        if self.outcome_digest != expected:
            raise ValueError("outcome-set digest verification failed")
        return self


class IntentNode(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    node_id: str = Field(min_length=1, max_length=256)
    node_type: IntentNodeType
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=10_000)
    owner: str = Field(default="", max_length=200)
    horizon: Literal["current", "next", "conditional", "future", "reference", "blocked"]
    material: bool = True
    projection_eligible: bool = False
    provenance: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_projection_eligibility(self) -> IntentNode:
        allowed = {
            IntentNodeType.PRIMARY_OUTCOME,
            IntentNodeType.SECONDARY_OUTCOME,
            IntentNodeType.CURRENT_CHECKPOINT,
        }
        if self.projection_eligible and (
            self.node_type not in allowed or self.horizon != "current"
        ):
            raise ValueError("only current business nodes may be projection eligible")
        return self


class IntentEdge(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    edge_id: str = Field(min_length=1, max_length=256)
    source_node_id: str = Field(min_length=1, max_length=256)
    target_node_id: str = Field(min_length=1, max_length=256)
    edge_type: IntentEdgeType
    rationale: str = Field(default="", max_length=2_000)


class IntentGraph(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal[1] = 1
    nodes: tuple[IntentNode, ...]
    edges: tuple[IntentEdge, ...] = ()
    blocked: bool = False
    findings: tuple[str, ...] = ()
    graph_digest: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_graph(self) -> IntentGraph:
        node_ids = [node.node_id for node in self.nodes]
        edge_ids = [edge.edge_id for edge in self.edges]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("intent graph node IDs must be unique")
        if len(edge_ids) != len(set(edge_ids)):
            raise ValueError("intent graph edge IDs must be unique")
        known = set(node_ids)
        for edge in self.edges:
            if edge.source_node_id not in known or edge.target_node_id not in known:
                raise ValueError("intent graph edges must reference declared nodes")
            if edge.source_node_id == edge.target_node_id:
                raise ValueError("intent graph self-cycles are prohibited")
        if self._has_dependency_cycle():
            raise ValueError("intent graph contains a material dependency cycle")
        primary = [
            node for node in self.nodes if node.node_type == IntentNodeType.PRIMARY_OUTCOME
        ]
        if len(primary) != 1:
            raise ValueError("intent graph requires exactly one primary outcome")
        if not self.verify_digest():
            raise ValueError("intent-graph digest verification failed")
        return self

    def _has_dependency_cycle(self) -> bool:
        dependency_types = {
            IntentEdgeType.REQUIRES,
            IntentEdgeType.DEPENDS_ON,
            IntentEdgeType.PRECEDES,
        }
        adjacency: dict[str, set[str]] = {}
        for edge in self.edges:
            if edge.edge_type in dependency_types:
                adjacency.setdefault(edge.source_node_id, set()).add(edge.target_node_id)
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str) -> bool:
            if node_id in visiting:
                return True
            if node_id in visited:
                return False
            visiting.add(node_id)
            for target in adjacency.get(node_id, set()):
                if visit(target):
                    return True
            visiting.remove(node_id)
            visited.add(node_id)
            return False

        return any(visit(node.node_id) for node in self.nodes)

    def digest_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"graph_digest"})

    def verify_digest(self) -> bool:
        return self.graph_digest == deterministic_digest(self.digest_payload())


class DependencyRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    dependency_id: str = Field(min_length=1, max_length=256)
    category: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2_000)
    state: DependencyState
    material: bool
    confidence: float = Field(ge=0, le=1)
    evidence: tuple[EvidenceReference, ...] = ()
    affected_node_ids: tuple[str, ...] = ()


class ConstraintRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    constraint_id: str = Field(min_length=1, max_length=256)
    category: ConstraintCategory
    statement: str = Field(min_length=1, max_length=2_000)
    strength: ConstraintStrength
    source: str = Field(min_length=1, max_length=500)
    affected_node_ids: tuple[str, ...] = ()
    derived_effects: tuple[str, ...] = ()
    conflicts_with: tuple[str, ...] = ()


class ConstraintPropagationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    constraints: tuple[ConstraintRecord, ...]
    hard_conflicts: tuple[str, ...] = ()
    affected_nodes: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    execution_eligible: bool
    result_digest: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_result(self) -> ConstraintPropagationResult:
        if self.execution_eligible == bool(self.hard_conflicts):
            raise ValueError("constraint execution eligibility contradicts hard conflicts")
        expected = deterministic_digest(
            self.model_dump(mode="json", exclude={"result_digest"})
        )
        if self.result_digest != expected:
            raise ValueError("constraint-propagation digest verification failed")
        return self


class PlanningArchetype(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    archetype_id: str = Field(min_length=1, max_length=200)
    version: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1, max_length=2_000)
    trigger_terms: tuple[str, ...]
    current_checkpoint_templates: tuple[str, ...]
    delegated_template: str = Field(default="", max_length=1_000)
    conditional_template: str = Field(default="", max_length=1_000)
    future_template: str = Field(default="", max_length=1_000)
    required_dependency_categories: tuple[str, ...] = ()
    approval_state: MemoryApprovalState = MemoryApprovalState.APPROVED
    registry_digest: str = Field(min_length=64, max_length=64)


class ArchetypeSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    archetype_id: str = Field(min_length=1, max_length=200)
    archetype_version: str = Field(min_length=1, max_length=100)
    confidence: float = Field(ge=0, le=1)
    evidence: tuple[EvidenceReference, ...]
    alternatives: tuple[str, ...] = ()
    selection_digest: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_selection(self) -> ArchetypeSelection:
        expected = deterministic_digest(
            self.model_dump(mode="json", exclude={"selection_digest"})
        )
        if self.selection_digest != expected:
            raise ValueError("archetype-selection digest verification failed")
        return self


class ClarificationDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: ClarificationStatus
    question: str = Field(default="", max_length=2_000)
    expected_information_value: float = Field(default=0, ge=0, le=1)
    material_issue: str = Field(default="", max_length=2_000)
    alternatives: tuple[str, ...] = ()
    decision_digest: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_decision(self) -> ClarificationDecision:
        requires_question = self.status == ClarificationStatus.REQUIRED
        if requires_question != bool(self.question):
            raise ValueError("clarification question must match clarification status")
        expected = deterministic_digest(
            self.model_dump(mode="json", exclude={"decision_digest"})
        )
        if self.decision_digest != expected:
            raise ValueError("clarification-decision digest verification failed")
        return self


class ReflectionFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    finding_id: str = Field(min_length=1, max_length=256)
    severity: FindingSeverity
    check: str = Field(min_length=1, max_length=500)
    passed: bool
    detail: str = Field(min_length=1, max_length=2_000)
    affected_node_ids: tuple[str, ...] = ()


class ReflectionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    findings: tuple[ReflectionFinding, ...]
    revision_count: int = Field(default=0, ge=0, le=2)
    passed: bool
    review_required: bool
    result_digest: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_reflection(self) -> ReflectionResult:
        blocking = any(
            item.severity == FindingSeverity.BLOCKING and not item.passed
            for item in self.findings
        )
        review = any(
            item.severity == FindingSeverity.REVIEW_REQUIRED and not item.passed
            for item in self.findings
        )
        if self.passed == blocking:
            raise ValueError("reflection pass state contradicts blocking findings")
        if self.review_required != (blocking or review):
            raise ValueError("reflection review state contradicts findings")
        expected = deterministic_digest(
            self.model_dump(mode="json", exclude={"result_digest"})
        )
        if self.result_digest != expected:
            raise ValueError("reflection-result digest verification failed")
        return self


class RiskDimension(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    dimension: str = Field(min_length=1, max_length=100)
    inherent_score: float = Field(ge=0, le=1)
    residual_score: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    contributing_node_ids: tuple[str, ...] = ()
    evidence: tuple[EvidenceReference, ...] = ()


class RiskProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    dimensions: tuple[RiskDimension, ...]
    overall_level: RiskLevel
    review_required: bool
    low_confidence_dimensions: tuple[str, ...] = ()
    profile_digest: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_risk(self) -> RiskProfile:
        names = [item.dimension for item in self.dimensions]
        if len(names) != len(set(names)):
            raise ValueError("risk dimensions must be unique")
        maximum = max((item.residual_score for item in self.dimensions), default=0)
        expected_level = (
            RiskLevel.CRITICAL
            if maximum >= 0.85
            else RiskLevel.HIGH
            if maximum >= 0.65
            else RiskLevel.MODERATE
            if maximum >= 0.35
            else RiskLevel.LOW
        )
        if self.overall_level != expected_level:
            raise ValueError("risk level contradicts residual dimensions")
        if self.review_required != (maximum >= 0.65):
            raise ValueError("risk review state contradicts threshold")
        expected = deterministic_digest(
            self.model_dump(mode="json", exclude={"profile_digest"})
        )
        if self.profile_digest != expected:
            raise ValueError("risk-profile digest verification failed")
        return self


class PlanningMemoryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    memory_id: str = Field(min_length=1, max_length=256)
    version: str = Field(min_length=1, max_length=100)
    scope: PlanningMemoryScope
    approval_state: MemoryApprovalState
    topology: dict[str, Any]
    provenance: tuple[EvidenceReference, ...]
    review_policy: str = Field(min_length=1, max_length=1_000)
    expires_on: str = Field(default="", max_length=100)
    content_fingerprint: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_memory(self) -> PlanningMemoryEntry:
        expected = stable_fingerprint(
            {
                "version": self.version,
                "scope": self.scope,
                "topology": self.topology,
                "provenance": self.provenance,
                "review_policy": self.review_policy,
                "expires_on": self.expires_on,
            }
        )
        if self.content_fingerprint != expected:
            raise ValueError("planning-memory fingerprint verification failed")
        return self


class ProjectionPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_version: Literal[1] = 1
    small_max: int = Field(default=2, ge=1, le=5)
    medium_max: int = Field(default=5, ge=2, le=10)
    large_max: int = Field(default=8, ge=3, le=15)
    program_max: int = Field(default=12, ge=4, le=25)
    exclude_delegated: bool = True
    exclude_conditional: bool = True
    exclude_future: bool = True
    exclude_control_plane: bool = True


class ProjectionDecisionV62(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    band: ProjectionBand
    projected_node_ids: tuple[str, ...]
    withheld_node_ids: tuple[str, ...]
    explanation: str = Field(min_length=1, max_length=3_000)
    review_required: bool
    decision_digest: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_projection(self) -> ProjectionDecisionV62:
        if set(self.projected_node_ids) & set(self.withheld_node_ids):
            raise ValueError("projected and withheld node sets must be disjoint")
        expected = deterministic_digest(
            self.model_dump(mode="json", exclude={"decision_digest"})
        )
        if self.decision_digest != expected:
            raise ValueError("projection-decision digest verification failed")
        return self


class EnhancedReasoningPackage(BaseModel):
    """Provider-free Atlas ROS v6.2 reasoning result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal[5] = 5
    contract_kind: ContractKind = ContractKind.REASONING
    source_component: str = "engines.input_pipeline_v62"
    canonical_intent: CanonicalIntent
    outcomes: OutcomeSet
    archetype_selection: ArchetypeSelection
    intent_graph: IntentGraph
    dependencies: tuple[DependencyRecord, ...]
    constraint_result: ConstraintPropagationResult
    confidence_profile: IntentConfidenceProfile
    risk_profile: RiskProfile
    clarification: ClarificationDecision
    reflection: ReflectionResult
    planning_style: PlanningStyle
    memory_entry_ids: tuple[str, ...] = ()
    projection: ProjectionDecisionV62
    user_facing_summary: str = Field(min_length=1, max_length=5_000)
    provider_writes: Literal[0] = 0
    execution_authorized: Literal[False] = False
    package_digest: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_package(self) -> EnhancedReasoningPackage:
        blocked = (
            not self.confidence_profile.execution_eligible
            or not self.constraint_result.execution_eligible
            or not self.reflection.passed
            or self.reflection.review_required
            or self.risk_profile.review_required
            or self.clarification.status
            in {ClarificationStatus.REQUIRED, ClarificationStatus.HUMAN_REVIEW_REQUIRED}
        )
        if blocked and self.projection.projected_node_ids:
            raise ValueError("blocked reasoning cannot project current execution work")
        if not self.verify_digest():
            raise ValueError("enhanced reasoning-package digest verification failed")
        return self

    def digest_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"package_digest"})

    def verify_digest(self) -> bool:
        return self.package_digest == deterministic_digest(self.digest_payload())
