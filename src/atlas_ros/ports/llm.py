"""Provider-neutral LLM input views and gateway boundary."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol


class ProjectReasoningView(Protocol):
    """Read-only project fields required by an LLM reasoning adapter."""

    project_id: object
    title: str
    description: str
    status: object
    intended_outcomes: Sequence[str]


class ProjectReasoningPort(Protocol):
    """Provider-neutral project reasoning operation."""

    def reason(self, project: ProjectReasoningView) -> dict[str, object]: ...


__all__ = ["ProjectReasoningPort", "ProjectReasoningView"]
