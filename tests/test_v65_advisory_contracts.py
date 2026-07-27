from __future__ import annotations

import pytest

from atlas_ros.contracts.advisory_v1 import (
    ConfidenceAssessment,
    MissingDataIndicator,
    UncertaintyRange,
    ValueOrigin,
    stable_advisory_digest,
)


def test_digest_is_deterministic_and_key_order_independent() -> None:
    left = stable_advisory_digest({"b": 2, "a": 1})
    right = stable_advisory_digest({"a": 1, "b": 2})
    assert left == right


def test_digest_can_exclude_nonsemantic_fields_explicitly() -> None:
    left = stable_advisory_digest({"value": "same", "observed_at": "first"})
    right = stable_advisory_digest({"value": "same", "observed_at": "second"})
    assert left != right
    assert stable_advisory_digest(
        {"value": "same", "observed_at": "first"},
        excluded_keys=("observed_at",),
    ) == stable_advisory_digest(
        {"value": "same", "observed_at": "second"},
        excluded_keys=("observed_at",),
    )


def test_confidence_rejects_fabricated_precision() -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        ConfidenceAssessment(score=1.01, rationale="unsupported")


def test_unknown_confidence_retains_missing_data() -> None:
    missing = MissingDataIndicator("startup_effort", "No estimate supplied", material=True)
    assessment = ConfidenceAssessment(score=None, rationale="Unknown", missing_data=(missing,))
    assert assessment.score is None
    assert assessment.missing_data == (missing,)


def test_uncertainty_range_rejects_reversed_bounds() -> None:
    with pytest.raises(ValueError, match="low must not exceed high"):
        UncertaintyRange(low=4.0, high=3.0, unit="hours")


def test_uncertainty_preserves_origin() -> None:
    estimate = UncertaintyRange(
        low=1.0,
        high=2.0,
        unit="hours",
        origin=ValueOrigin.CONFIGURED,
    )
    assert estimate.origin is ValueOrigin.CONFIGURED
