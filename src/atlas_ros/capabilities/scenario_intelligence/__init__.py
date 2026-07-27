"""Advisory scenario intelligence capability boundary for Atlas ROS v7."""

from typing import Protocol

from atlas_ros.capabilities.interfaces import ScenarioAnalysisResult

CAPABILITY_ID = "atlas.scenario-intelligence"


class ScenarioIntelligencePort(Protocol):
    def compare(self, scenario_ids: tuple[str, ...]) -> ScenarioAnalysisResult: ...


__all__ = ["CAPABILITY_ID", "ScenarioAnalysisResult", "ScenarioIntelligencePort"]
