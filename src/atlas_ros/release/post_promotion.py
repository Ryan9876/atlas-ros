from __future__ import annotations

REQUIRED_POST_PROMOTION_CHECKS = (
    "final_release_verified",
    "production_source_verified",
    "release_index_v6_active",
    "system_state_v6_active",
    "manifest_v6_active",
    "integrations_current",
    "registry_matches_notion",
    "notion_matches_registry",
    "promotion_decision_active",
    "full_validation_passed",
    "rollback_v5_6_immutable",
)


def evaluate_post_promotion(
    snapshot: dict[str, bool], *, production: bool = False
) -> dict[str, object]:
    checks = {
        name: bool(snapshot.get(name, False))
        for name in REQUIRED_POST_PROMOTION_CHECKS
    }
    settled = all(checks.values())
    if not production and settled:
        raise ValueError("dry-run mode cannot report post-promotion success")
    return {
        "mode": "production" if production else "dry-run",
        "checks": checks,
        "settled": settled,
        "fail_closed": not settled,
    }
