"""Canonical planning submission boundary for typed lifecycle proposals."""
from __future__ import annotations

from typing import Protocol

from atlas_ros.contracts.execution.transaction import ProposedExecutionPlan
from atlas_ros.contracts.operational_awareness import TodoistLifecyclePlanV1


class LifecyclePlanCompilerPort(Protocol):
    """Compile one typed lifecycle proposal into an exact unexecuted plan."""

    def compile(self, lifecycle: TodoistLifecyclePlanV1) -> ProposedExecutionPlan: ...
