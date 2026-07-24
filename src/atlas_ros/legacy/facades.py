from __future__ import annotations

from atlas_ros.adapters.llm import LLMAdapter
from atlas_ros.domain.models import Action, Capture, ReadinessReport, RoutingRecommendation
from atlas_ros.runtime.database import RuntimeDatabase
from atlas_ros.workflows.w01_capture import CaptureService
from atlas_ros.workflows.w02_routing import RoutingService
from atlas_ros.workflows.w03_todoist import TodoistPlan, TodoistService
from atlas_ros.workflows.w03a_decomposition import DecompositionService


class W01CaptureFacade:
    """Compatibility facade for the legacy W01 capture interface."""

    def __init__(self, database: RuntimeDatabase) -> None:
        self._service = CaptureService(database)

    def capture(
        self,
        content: str,
        source: str = "cli",
        *,
        due_date_input: str = "",
        delegation_input: str = "",
        additional_context: str = "",
    ) -> Capture:
        return self._service.capture(
            content,
            source,
            due_date_input=due_date_input,
            delegation_input=delegation_input,
            additional_context=additional_context,
        )


class W02RoutingFacade:
    """Compatibility facade preserving the current W02 routing contract."""

    def __init__(self, adapter: LLMAdapter) -> None:
        self._service = RoutingService(adapter)

    def plan(self, capture: Capture) -> RoutingRecommendation:
        return self._service.plan(capture)


class W03ADecompositionFacade:
    """Compatibility facade preserving W03A readiness behavior."""

    def __init__(self) -> None:
        self._service = DecompositionService()

    def readiness(self, action: Action) -> ReadinessReport:
        return self._service.readiness(action)


class W03TodoistFacade:
    """Compatibility facade preserving the current attended W03 plan interface."""

    def __init__(self) -> None:
        self._service = TodoistService()

    def plan(self, action: Action) -> TodoistPlan:
        return self._service.plan(action)
