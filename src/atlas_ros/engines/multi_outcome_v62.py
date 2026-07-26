from __future__ import annotations

from typing import Any

from atlas_ros.contracts.models import deterministic_digest
from atlas_ros.contracts.v62 import CanonicalIntent, OutcomeRole, OutcomeSet, OutcomeV2, stable_fingerprint

from .archetypes_v62 import MultiOutcomeEngineV62 as _BaseMultiOutcomeEngineV62


class MultiOutcomeEngineV62(_BaseMultiOutcomeEngineV62):
    """Extended outcome recognition for gerund and evidence-oriented phrasing."""

    def recognize(self, canonical: CanonicalIntent) -> OutcomeSet:
        result = super().recognize(canonical)
        raw = canonical.raw_input.casefold()
        documentation_requested = any(
            term in raw
            for term in (
                "document the process",
                "documenting the process",
                "create documentation",
                "produce documentation",
            )
        )
        if not documentation_requested or any(
            "documentation" in item.text.casefold() for item in result.supporting
        ):
            return result
        text = "Create reusable process documentation"
        supporting = (
            *result.supporting,
            OutcomeV2(
                outcome_id=f"outcome-supporting-{stable_fingerprint(text)[:16]}",
                text=text,
                role=OutcomeRole.SUPPORTING,
                priority=3,
                explicit=True,
                provenance=("explicit_supporting_outcome",),
            ),
        )
        values: dict[str, Any] = {
            "contract_version": 1,
            "primary": result.primary.model_dump(mode="json"),
            "secondary": [item.model_dump(mode="json") for item in result.secondary],
            "supporting": [item.model_dump(mode="json") for item in supporting],
            "competing": [item.model_dump(mode="json") for item in result.competing],
            "ranking_requires_clarification": result.ranking_requires_clarification,
        }
        return OutcomeSet(
            primary=result.primary,
            secondary=result.secondary,
            supporting=supporting,
            competing=result.competing,
            ranking_requires_clarification=result.ranking_requires_clarification,
            outcome_digest=deterministic_digest(values),
        )
