from atlas_ros.contracts import BenchmarkMode, ConfidenceDimensionV1
from atlas_ros.domain.models import Capture
from atlas_ros.engines import ManagementReasoningEngine, ReasoningCoherenceGate
from atlas_ros.planning import HorizonPromotionEngine


def test_cloudvision_reasoning_is_coherent_without_review() -> None:
    reasoning = ManagementReasoningEngine().reason_v4(
        Capture(content="Launch the Arista CloudVision code-upgrade automation pilot")
    )
    result = ReasoningCoherenceGate().evaluate(reasoning)
    assert result.passed
    assert not result.review_required
    assert reasoning.responsibility_domain == "project_delivery"
    assert reasoning.workstream == "Active Projects"
    assert reasoning.requires_human_decision is False
    summary = reasoning.user_facing_summary.casefold()
    assert "clarification is required" not in summary
    assert "needs clarification" not in summary
    dimensions = {item.dimension: item for item in reasoning.confidence_dimensions}
    assert isinstance(dimensions["planning_model"], ConfidenceDimensionV1)
    assert dimensions["planning_model"].score >= 0.95
    assert dimensions["responsibility_resolution"].score >= 0.85


def test_material_unresolved_responsibility_fails_closed() -> None:
    reasoning = ManagementReasoningEngine().reason_v4(
        Capture(content="Launch a controlled technology pilot")
    ).model_copy(
        update={
            "responsibility_domain": "unresolved",
            "workstream": "Needs Clarification",
            "requires_human_decision": False,
            "rationale": ("Needs clarification before routing.",),
        }
    )
    result = ReasoningCoherenceGate().evaluate(reasoning)
    assert not result.passed
    assert result.review_required
    assert "responsibility_consistency" in {
        condition.condition for condition in result.conditions if not condition.passed
    }


def test_benchmark_modes_default_to_provider_free() -> None:
    assert BenchmarkMode.PROVIDER_FREE.value == "provider_free"


def test_horizon_re_evaluation_never_writes_providers() -> None:
    proposal = HorizonPromotionEngine().evaluate(
        scope_approved=True,
        owner_targets_confirmed=True,
        controls_rollback_approved=True,
        execution_evidence_complete=False,
        go_decision=False,
    )
    assert proposal.provider_writes == 0
    assert proposal.attended_authorization_required
