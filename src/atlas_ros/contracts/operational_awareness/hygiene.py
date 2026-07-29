"""Work-graph hygiene and governed repair-proposal contracts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from atlas_ros.contracts.advisory_v1 import ConfidenceAssessment
from atlas_ros.contracts.digests import sha256_digest

from .base import DigestBoundModel, HygieneSeverity, RepairClass
from .records import OperationalRecordRefV1


class WorkGraphNodeV1(DigestBoundModel):
    digest_field = "node_digest"

    contract_id: Literal["atlas.work-graph-node"] = "atlas.work-graph-node"
    schema_version: Literal["1.0"] = "1.0"
    record_reference: OperationalRecordRefV1
    effective_state: str
    protected_history: bool = False
    node_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> WorkGraphNodeV1:
        return cls(node_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_digest(self) -> WorkGraphNodeV1:
        if not self.verify_digest():
            raise ValueError("work graph node digest mismatch")
        return self


class WorkGraphEdgeV1(DigestBoundModel):
    digest_field = "edge_digest"

    contract_id: Literal["atlas.work-graph-edge"] = "atlas.work-graph-edge"
    schema_version: Literal["1.0"] = "1.0"
    source_record_id: str
    target_record_id: str
    edge_type: str
    edge_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> WorkGraphEdgeV1:
        return cls(edge_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_digest(self) -> WorkGraphEdgeV1:
        if self.source_record_id == self.target_record_id:
            raise ValueError("work graph edge cannot be self-referential")
        if not self.verify_digest():
            raise ValueError("work graph edge digest mismatch")
        return self


class WorkGraphSnapshotV1(DigestBoundModel):
    digest_field = "graph_digest"

    contract_id: Literal["atlas.work-graph-snapshot"] = "atlas.work-graph-snapshot"
    schema_version: Literal["1.0"] = "1.0"
    snapshot_id: str
    nodes: tuple[WorkGraphNodeV1, ...]
    edges: tuple[WorkGraphEdgeV1, ...]
    graph_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> WorkGraphSnapshotV1:
        return cls(graph_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_graph(self) -> WorkGraphSnapshotV1:
        identities = tuple(node.record_reference.canonical_record_id for node in self.nodes)
        if len(set(identities)) != len(identities):
            raise ValueError("work graph contains duplicate node identities")
        if not self.verify_digest():
            raise ValueError("work graph digest mismatch")
        return self


class HygieneFindingV1(DigestBoundModel):
    digest_field = "finding_digest"

    contract_id: Literal["atlas.hygiene-finding"] = "atlas.hygiene-finding"
    schema_version: Literal["1.0"] = "1.0"
    finding_id: str
    rule_id: str
    affected_records: tuple[OperationalRecordRefV1, ...]
    evidence: tuple[str, ...]
    severity: HygieneSeverity
    confidence: ConfidenceAssessment
    downstream_impact: str
    proposed_disposition: str
    repair_eligibility: RepairClass
    protected_record_status: bool
    finding_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> HygieneFindingV1:
        return cls(finding_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_finding(self) -> HygieneFindingV1:
        if not self.affected_records or not self.evidence:
            raise ValueError("hygiene finding requires affected records and evidence")
        if self.protected_record_status and self.repair_eligibility != RepairClass.PROTECTED:
            raise ValueError("protected record findings must be repair-prohibited")
        if not self.verify_digest():
            raise ValueError("hygiene finding digest mismatch")
        return self


class RepairProposalV1(DigestBoundModel):
    digest_field = "proposal_digest"

    contract_id: Literal["atlas.repair-proposal"] = "atlas.repair-proposal"
    schema_version: Literal["1.0"] = "1.0"
    finding_id: str
    exact_affected_records: tuple[OperationalRecordRefV1, ...]
    intended_final_state: str
    reason: str
    preconditions: tuple[str, ...]
    expected_provider_operations: tuple[dict[str, Any], ...]
    reversibility: str
    risk_classification: str
    readback_requirements: tuple[str, ...]
    idempotency_identity: str
    proposal_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> RepairProposalV1:
        return cls(proposal_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_proposal(self) -> RepairProposalV1:
        if not self.preconditions or not self.readback_requirements:
            raise ValueError("repair proposal requires preconditions and readback")
        if not self.verify_digest():
            raise ValueError("repair proposal digest mismatch")
        return self
