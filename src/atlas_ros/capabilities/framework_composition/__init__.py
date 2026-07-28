"""Governed provider-free framework composition for Atlas ROS v7."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from atlas_ros.capabilities.interfaces import FrameworkCompositionResult
from atlas_ros.contracts.digests import sha256_digest

CAPABILITY_ID = "atlas.framework-composition"


class FrameworkCompositionPort(Protocol):
    def compose(self, rules: tuple[str, ...]) -> FrameworkCompositionResult: ...


@dataclass(frozen=True, slots=True)
class GovernedFrameworkCompositionService:
    """Compose unique ordered rules and make provenance explicit."""

    capability_id: str = CAPABILITY_ID

    def compose(self, rules: tuple[str, ...]) -> FrameworkCompositionResult:
        normalized = tuple(rule.strip() for rule in rules if rule.strip())
        ordered = tuple(dict.fromkeys(normalized))
        warnings: list[str] = []
        if len(ordered) != len(normalized):
            warnings.append("duplicate_rules_removed")
        provenance = tuple(f"policy:{index + 1}:{rule}" for index, rule in enumerate(ordered))
        digest = sha256_digest(
            {"ordered_rules": ordered, "provenance": provenance, "warnings": warnings}
        )
        return FrameworkCompositionResult(
            ordered_rules=ordered,
            provenance=provenance,
            warnings=tuple(warnings),
            digest=digest,
        )


__all__ = [
    "CAPABILITY_ID",
    "FrameworkCompositionPort",
    "FrameworkCompositionResult",
    "GovernedFrameworkCompositionService",
]
