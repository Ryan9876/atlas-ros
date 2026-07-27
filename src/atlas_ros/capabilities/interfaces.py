"""Provider-neutral interfaces and immutable result types for v7 capabilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from atlas_ros.contracts.execution.pipeline import CaptureEnvelope
from atlas_ros.contracts.execution.transaction import (
    ExecutionTransactionReceipt,
    PlannedProviderOperation,
    ProposedExecutionPlan,
)
from atlas_ros.contracts.reasoning import IntentGraph


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    classification: str
    destination: str
    responsibility_domain: str
    workstream: str
    confidence: float
    findings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class KnowledgeCompositionResult:
    references: tuple[str, ...]
    facts: tuple[str, ...]
    assumptions: tuple[str, ...]
    conflicts: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ManagementReasoningResult:
    primary_outcome: str
    current_actions: tuple[str, ...]
    delegated_actions: tuple[str, ...]
    conditional_actions: tuple[str, ...]
    blockers: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ManagementStructureResult:
    parent_title: str
    sections: tuple[str, ...]
    relationships: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    destination: str
    rationale: str
    review_required: bool


@dataclass(frozen=True, slots=True)
class FrameworkCompositionResult:
    ordered_rules: tuple[str, ...]
    provenance: tuple[str, ...]
    warnings: tuple[str, ...]
    digest: str


@dataclass(frozen=True, slots=True)
class MinimumEffectivePathResult:
    step_ids: tuple[str, ...]
    required_evidence: tuple[str, ...]
    blockers: tuple[str, ...]
    digest: str


@dataclass(frozen=True, slots=True)
class ExecutionIntelligenceResult:
    state: str
    next_valid_actions: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExecutionPresentationResult:
    executive_summary: str
    technical_summary: str
    audit_digest: str


@dataclass(frozen=True, slots=True)
class ScenarioAnalysisResult:
    scenario_ids: tuple[str, ...]
    changed_assumptions: tuple[str, ...]
    changed_outcomes: tuple[str, ...]
    decision_triggers: tuple[str, ...]
    digest: str


@dataclass(frozen=True, slots=True)
class DecisionSupportResult:
    decision_required: bool
    options: tuple[str, ...]
    recommendation: str | None
    uncertainty: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    transaction_id: str
    matched_operation_ids: tuple[str, ...]
    missing_operation_ids: tuple[str, ...]
    unexpected_operation_ids: tuple[str, ...]
    conflicts: tuple[str, ...]
    complete: bool


class InputProcessingPort(Protocol):
    def process(self, envelope: CaptureEnvelope) -> IntentGraph: ...


class ClassificationPort(Protocol):
    def classify(self, graph: IntentGraph) -> ClassificationResult: ...


class KnowledgeCompositionPort(Protocol):
    def compose(self, graph: IntentGraph) -> KnowledgeCompositionResult: ...


class ManagementReasoningPort(Protocol):
    def reason(self, graph: IntentGraph) -> ManagementReasoningResult: ...


class ManagementStructurePort(Protocol):
    def structure(
        self,
        reasoning: ManagementReasoningResult,
    ) -> ManagementStructureResult: ...


class RecordRoutingPort(Protocol):
    def route(
        self,
        classification: ClassificationResult,
        structure: ManagementStructureResult,
    ) -> RoutingDecision: ...


class ExecutionPlanningPort(Protocol):
    def plan(
        self,
        graph: IntentGraph,
        requests: tuple[PlannedProviderOperation, ...],
    ) -> ProposedExecutionPlan: ...


class ReconciliationPort(Protocol):
    def reconcile(
        self,
        plan: ProposedExecutionPlan,
        receipt: ExecutionTransactionReceipt,
    ) -> ReconciliationResult: ...
