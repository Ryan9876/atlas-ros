import pytest

from atlas_ros.release.post_promotion import (
    REQUIRED_POST_PROMOTION_CHECKS,
    evaluate_post_promotion,
)


def test_pre_promotion_dry_run_fails_closed() -> None:
    report = evaluate_post_promotion(
        {name: False for name in REQUIRED_POST_PROMOTION_CHECKS}
    )
    assert report["mode"] == "dry-run"
    assert report["settled"] is False
    assert report["fail_closed"] is True


def test_dry_run_cannot_claim_post_promotion_success() -> None:
    with pytest.raises(ValueError, match="cannot report"):
        evaluate_post_promotion(
            {name: True for name in REQUIRED_POST_PROMOTION_CHECKS}
        )


def test_production_mode_requires_every_authoritative_check() -> None:
    snapshot = {name: True for name in REQUIRED_POST_PROMOTION_CHECKS}
    snapshot["system_state_v6_active"] = False
    assert evaluate_post_promotion(snapshot, production=True)["settled"] is False
    assert (
        evaluate_post_promotion(
            {name: True for name in REQUIRED_POST_PROMOTION_CHECKS},
            production=True,
        )["settled"]
        is True
    )
