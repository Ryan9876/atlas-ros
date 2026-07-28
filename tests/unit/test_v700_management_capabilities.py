from __future__ import annotations

from atlas_ros.capabilities.framework_composition import (
    GovernedFrameworkCompositionService,
)
from atlas_ros.capabilities.input_processing import DeterministicInputProcessor
from atlas_ros.capabilities.management_reasoning import (
    DeterministicManagementReasoningService,
)
from atlas_ros.contracts.execution.pipeline import CaptureEnvelope


def test_management_reasoning_separates_actions_decisions_and_constraints() -> None:
    graph = DeterministicInputProcessor().process(
        CaptureEnvelope(
            source="test",
            content=(
                "Complete the v7 implementation. "
                "Create the candidate evidence. "
                "Decide whether promotion is appropriate. "
                "Never promote without explicit authorization."
            ),
        )
    )

    result = DeterministicManagementReasoningService().reason(graph)

    assert result.primary_outcome == "Complete the v7 implementation"
    assert result.current_actions == ("Create the candidate evidence",)
    assert result.conditional_actions == ("Decide whether promotion is appropriate",)
    assert result.blockers == ("Never promote without explicit authorization",)


def test_framework_composition_is_ordered_deduplicated_and_digest_bound() -> None:
    service = GovernedFrameworkCompositionService()
    first = service.compose(("fail_closed", "read_before_write", "fail_closed"))
    replay = service.compose(("fail_closed", "read_before_write", "fail_closed"))

    assert first.ordered_rules == ("fail_closed", "read_before_write")
    assert first.warnings == ("duplicate_rules_removed",)
    assert first.provenance == (
        "policy:1:fail_closed",
        "policy:2:read_before_write",
    )
    assert first.digest == replay.digest
