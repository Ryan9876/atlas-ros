from __future__ import annotations

from typing import Any

from atlas_ros.contracts import EvidenceSignal
from atlas_ros.domain.models import ManagementWorkstream, ResponsibilityDomain


class ClassificationExplainability:
    """Builds concise evidence-aligned explanations without exposing hidden reasoning."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config

    def explain(
        self,
        *,
        responsibility_domain: ResponsibilityDomain,
        workstream: ManagementWorkstream,
        rationale_basis: str,
        evidence: tuple[EvidenceSignal, ...],
        ambiguities: tuple[str, ...],
        confidence: float,
    ) -> str:
        if responsibility_domain is ResponsibilityDomain.UNRESOLVED:
            explanation = (
                "Needs clarification because the primary management responsibility "
                "could not be determined from governed evidence."
            )
        else:
            decisive = evidence[0].signal if evidence else "the available context"
            explanation = (
                f"Routed to {workstream.value} because the primary responsibility is "
                f"{rationale_basis}; the decisive signal was '{decisive}'."
            )
        if ambiguities and bool(self._config["explanations"]["include_ambiguity"]):
            explanation += f" Confidence is {confidence:.2f}; material ambiguity remains."
        maximum = int(self._config["explanations"]["max_characters"])
        if len(explanation) > maximum:
            explanation = explanation[: maximum - 1].rstrip() + "…"
        return explanation
