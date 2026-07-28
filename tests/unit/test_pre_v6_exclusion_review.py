from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.validate_v700_pre_v6_exclusion_review import (
    PreV6ExclusionReviewError,
    canonical_sha256,
    validate_pre_v6_exclusion_review,
)


ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> dict[str, object]:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def resign(value: dict[str, object]) -> None:
    value.pop("review_sha256", None)
    value["review_sha256"] = canonical_sha256(value)


def validate(review: dict[str, object]) -> dict[str, object]:
    return validate_pre_v6_exclusion_review(
        review,
        deletion_plan=read("release/v700-pre-v6-deletion-plan.json"),
        folder_payload=read("release/v700-drive-folder-traversal.json"),
    )


def test_pre_v6_exclusion_review_emits_deterministic_candidates() -> None:
    result = validate(read("release/v700-pre-v6-exclusion-review.json"))

    assert result["status"] == "pre_v6_exclusion_review_open_not_authorized"
    assert result["candidate_folder_count"] == 92
    assert result["reviewed_folder_count"] == 0
    assert result["pending_folder_review_count"] == 92
    assert result["excluded_item_count"] == 0
    digest = result["candidate_folder_set_sha256"]
    assert isinstance(digest, str) and len(digest) == 64
    candidates = result["candidate_folders"]
    assert isinstance(candidates, list) and len(candidates) == 92
    assert result["file_candidates_complete"] is False
    assert result["exclusion_review_complete"] is False
    assert result["promotion_blocking"] is False
    assert result["deletion_authorized"] is False
    assert result["provider_writes"] == 0
    assert result["destructive_actions_performed"] == 0


def test_pre_v6_exclusion_review_rejects_out_of_scope_review() -> None:
    review = deepcopy(read("release/v700-pre-v6-exclusion-review.json"))
    review["reviewed_folder_ids"] = ["outside-historical-root"]
    resign(review)

    with pytest.raises(PreV6ExclusionReviewError, match="out-of-scope"):
        validate(review)


def test_pre_v6_exclusion_review_rejects_file_exclusion_before_inventory() -> None:
    review = deepcopy(read("release/v700-pre-v6-exclusion-review.json"))
    review["excluded_items"] = [
        {
            "item_id": "unverified-file",
            "item_type": "file",
            "exclusion_class": "legal_hold",
            "rationale": "Test-only exclusion",
            "evidence_url": "https://example.invalid/review",
            "reviewed_by": "test-reviewer",
            "reviewed_on": "2026-07-27",
        }
    ]
    resign(review)

    with pytest.raises(PreV6ExclusionReviewError, match="file candidate inventory"):
        validate(review)


def test_pre_v6_exclusion_review_rejects_early_authorization() -> None:
    review = deepcopy(read("release/v700-pre-v6-exclusion-review.json"))
    review["explicit_deletion_authorization_id"] = "V4D-TEST"
    review["deletion_authorized"] = True
    resign(review)

    with pytest.raises(PreV6ExclusionReviewError, match="unsafe state"):
        validate(review)


def test_pre_v6_exclusion_review_rejects_digest_tampering() -> None:
    review = deepcopy(read("release/v700-pre-v6-exclusion-review.json"))
    review["candidate_folder_count"] = 91

    with pytest.raises(PreV6ExclusionReviewError, match="folder count|digest"):
        validate(review)
