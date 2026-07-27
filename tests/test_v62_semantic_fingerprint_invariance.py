from __future__ import annotations

from atlas_ros.engines import AdaptiveInputProcessingPipelineV62


BASE_INPUT = "Task = arista cloud vision code upgrade automation pilot."
CONTROL_SUFFIXES = (
    "Preserve every v5.2 through v6.1.1 record unchanged.",
    "Compare the output against v5.2 through v6.1.1.",
    "Require attended authorization, provider readback, and an execution receipt.",
    (
        "Compare against previous versions. Preserve previous records. Require "
        "attended authorization, provider readback, execution and reconciliation receipts."
    ),
)


def test_control_plane_qualifiers_do_not_change_business_semantic_fingerprint() -> None:
    pipeline = AdaptiveInputProcessingPipelineV62()
    baseline = pipeline.process(BASE_INPUT)

    for suffix in CONTROL_SUFFIXES:
        result = pipeline.process(f"{BASE_INPUT} {suffix}")
        assert result.canonical_intent.semantic_fingerprint == (
            baseline.canonical_intent.semantic_fingerprint
        )
        assert result.outcomes.primary.text == baseline.outcomes.primary.text
        assert result.projection.projected_node_ids == baseline.projection.projected_node_ids


def test_business_scope_qualifier_still_changes_semantic_fingerprint() -> None:
    pipeline = AdaptiveInputProcessingPipelineV62()
    lab = pipeline.process(f"{BASE_INPUT} Lab only.")
    production = pipeline.process(f"{BASE_INPUT} Production only.")

    assert lab.canonical_intent.semantic_fingerprint != (
        production.canonical_intent.semantic_fingerprint
    )
