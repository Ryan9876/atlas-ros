"""Advisory immutable scenario intelligence for Atlas ROS v7."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from atlas_ros.capabilities.interfaces import ScenarioAnalysisResult
from atlas_ros.contracts.digests import sha256_digest

CAPABILITY_ID = "atlas.scenario-intelligence"


class ScenarioIntelligencePort(Protocol):
    def compare(self, scenario_ids: tuple[str, ...]) -> ScenarioAnalysisResult: ...


@dataclass(frozen=True, slots=True)
class ImmutableScenarioIntelligenceService:
    """Compare named scenarios without changing assumptions, plans, or records."""

    capability_id: str = CAPABILITY_ID

    def compare(self, scenario_ids: tuple[str, ...]) -> ScenarioAnalysisResult:
        scenarios = tuple(dict.fromkeys(item.strip() for item in scenario_ids if item.strip()))
        if not scenarios:
            raise ValueError("at least one scenario ID is required")
        baseline = scenarios[0]
        changed_assumptions = tuple(
            f"compare_assumptions:{baseline}:{scenario}" for scenario in scenarios[1:]
        )
        changed_outcomes = tuple(
            f"compare_outcomes:{baseline}:{scenario}" for scenario in scenarios[1:]
        )
        triggers = tuple(f"decision_trigger:{scenario}" for scenario in scenarios[1:])
        digest = sha256_digest(
            {
                "scenario_ids": scenarios,
                "changed_assumptions": changed_assumptions,
                "changed_outcomes": changed_outcomes,
                "decision_triggers": triggers,
            }
        )
        return ScenarioAnalysisResult(
            scenario_ids=scenarios,
            changed_assumptions=changed_assumptions,
            changed_outcomes=changed_outcomes,
            decision_triggers=triggers,
            digest=digest,
        )


__all__ = [
    "CAPABILITY_ID",
    "ImmutableScenarioIntelligenceService",
    "ScenarioAnalysisResult",
    "ScenarioIntelligencePort",
]
