from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Classification(StrEnum):
    ACTION = "action"
    PROJECT = "project"
    DELEGATED_WORK = "delegated_work"
    RISK = "risk"
    DECISION = "decision"
    REFERENCE = "reference"
    NEEDS_CLARIFICATION = "needs_clarification"


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ReadinessStatus(StrEnum):
    READY = "ready"
    NOT_READY = "not_ready"
    NEEDS_DECISION = "needs_decision"


class Capture(BaseModel):
    model_config = ConfigDict(frozen=True)
    capture_id: UUID = Field(default_factory=uuid4)
    correlation_id: UUID = Field(default_factory=uuid4)
    content: str = Field(min_length=1, max_length=100_000)
    source: str = "cli"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RoutingRecommendation(BaseModel):
    classification: Classification
    destination: str
    confidence: float = Field(ge=0, le=1)
    desired_outcome: str
    ryan_next_action: str = ""
    delegated_outcome: str = ""
    owner: str = ""
    definition_of_done: str = Field(default="", max_length=10_000)
    risk_flags: list[str] = Field(default_factory=list)
    security_flags: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    clarification_required: bool = False


class Action(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=256)
    title: str = Field(min_length=1, max_length=500)
    owner: str = ""
    definition_of_done: str = Field(default="", max_length=10_000)
    execution_ready: bool = False
    classification: Classification = Classification.ACTION
    delegated_work_present: bool = False
    todoist_project: str = "Work"
    todoist_section: str = ""
    labels: list[str] = Field(default_factory=list, max_length=20)
    todoist_task_id: str = ""


class Finding(BaseModel):
    id: str
    rule_id: str
    severity: Severity
    authority: str
    affected_object: str
    message: str
    evidence: dict[str, str] = Field(default_factory=dict)
    recommended_action: str


class ReadinessReport(BaseModel):
    status: ReadinessStatus
    passed_rules: list[str] = Field(default_factory=list)
    failed_rules: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    required_human_decisions: list[str] = Field(default_factory=list)
    proposed_subtasks: list[str] = Field(default_factory=list)


class ObservabilityEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    event_id: UUID = Field(default_factory=uuid4)
    correlation_id: UUID
    event_type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    workflow: str
    status: str
    error_class: str = ""
    duration_ms: int = Field(default=0, ge=0)
    attempt: int = Field(default=1, ge=1)

    @field_validator("event_type", "workflow", "status")
    @classmethod
    def nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must be non-empty")
        return value
