from __future__ import annotations

from math import inf

import pytest

from atlas_ros.contracts.advisory_v1 import (
    AdvisoryAlternative,
    AdvisoryReceipt,
    AdvisoryRecommendation,
    AdvisoryValueState,
    ConfidenceAssessment,
    MissingDataIndicator,
    ProvenanceRecord,
    UncertaintyRange,
    ValueOrigin,
    stable_advisory_digest,
)


def test_digest_is_deterministic_key_order_independent_and_recursively_canonical() -> None:
    left = stable_advisory_digest({"b": {"z": 2, "a": 1}, "a": {3, 2, 1}})
    right = stable_advisory_digest({"a": {1, 2, 3}, "b": {"a": 1, "z": 2}})
    assert left == right


def test_digest_can_exclude_nonsemantic_fields_explicitly() -> None:
    left = stable_advisory_digest({"value": "same", "observed_at": "first"})
    right = stable_advisory_digest({"value": "same", "observed_at": "second"})
    assert left != right
    assert stable_advisory_digest(
        {"value": "same", "observed_at": "first"}, excluded_keys=("observed_at",)
    ) == stable_advisory_digest(
        {"value": "same", "observed_at": "second"}, excluded_keys=("observed_at",)
    )


def test_digest_rejects_ambiguous_or_unsafe_values() -> None:
    with pytest.raises(ValueError, match="non-finite"):
        stable_advisory_digest({"value": inf})
    with pytest.raises(TypeError, match="unsupported"):
        stable_advisory_digest({"value": object()})


def test_confidence_rejects_fabricated_precision_and_unknown_is_explicit() -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        ConfidenceAssessment(score=1.01, rationale="unsupported")
    missing = MissingDataIndicator("startup_effort", "No estimate supplied", material=True)
    assessment = ConfidenceAssessment(score=None, rationale="Unknown", missing_data=(missing,))
    assert assessment.score is None
    assert assessment.missing_data == (missing,)


def test_uncertainty_range_rejects_reversed_or_nonfinite_bounds() -> None:
    with pytest.raises(ValueError, match="low must not exceed high"):
        UncertaintyRange(low=4.0, high=3.0, unit="hours")
    with pytest.raises(ValueError, match="finite"):
        UncertaintyRange(low=inf, high=None, unit="hours")
    estimate = UncertaintyRange(
        low=1.0, high=2.0, unit="hours", origin=ValueOrigin.CONFIGURED
    )
    assert estimate.origin is ValueOrigin.CONFIGURED


def test_receipt_verifies_exact_recommendation_and_input_without_tampering() -> None:
    recommendation = AdvisoryRecommendation(
        identifier="recommendation-1",
        summary="Use a review gate",
        rationale="Risk is unknown",
        confidence=ConfidenceAssessment(None, "Incomplete evidence"),
        alternatives=(AdvisoryAlternative("alternative-1", "Defer", ("slower",)),),
        provenance=(ProvenanceRecord("policy-v1", ValueOrigin.CONFIGURED),),
        value_state=AdvisoryValueState.PROPOSAL,
    )
    payload = {"record": "R-1", "risk": "unknown"}
    receipt = AdvisoryReceipt(
        recommendation_id=recommendation.identifier,
        input_digest=stable_advisory_digest(payload),
        recommendation_digest=stable_advisory_digest({"recommendation": recommendation}),
    )
    assert receipt.verify(recommendation, payload)
    assert not receipt.verify(recommendation, {"record": "R-1", "risk": "low"})
