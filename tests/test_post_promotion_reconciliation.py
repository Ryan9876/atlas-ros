import pytest

from scripts.post_promotion_reconciliation import REQUIRED, evaluate


def test_pre_promotion_dry_run_fails_closed() -> None:
    report = evaluate({name: False for name in REQUIRED})
    assert report["mode"] == "dry-run"
    assert report["settled"] is False
    assert report["fail_closed"] is True


def test_dry_run_cannot_claim_post_promotion_success() -> None:
    with pytest.raises(ValueError, match="cannot report"):
        evaluate({name: True for name in REQUIRED})


def test_production_mode_requires_every_authoritative_check() -> None:
    snapshot = {name: True for name in REQUIRED}
    snapshot["system_state_v6_active"] = False
    assert evaluate(snapshot, production=True)["settled"] is False
    assert evaluate({name: True for name in REQUIRED}, production=True)["settled"] is True
