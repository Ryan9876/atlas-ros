#!/usr/bin/env python3
"""Validate the fail-closed pre-v6 Drive exclusion review."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from scripts.validate_v700_pre_v6_deletion_plan import (
    validate_pre_v6_deletion_plan,
)


class PreV6ExclusionReviewError(ValueError):
    """Raised when the exclusion review is incomplete or unsafe."""


def canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _fail(message: str) -> None:
    raise PreV6ExclusionReviewError(message)


def _sha(value: Any, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail(f"{field} must be a lowercase SHA-256")
    return value


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PreV6ExclusionReviewError(
            f"invalid JSON evidence: {path}"
        ) from error
    if not isinstance(value, dict):
        _fail(f"JSON evidence must be an object: {path}")
    return value


def _node(value: Any) -> tuple[str, str, list[Any]]:
    if (
        not isinstance(value, list)
        or len(value) != 3
        or not isinstance(value[0], str)
        or not isinstance(value[1], str)
        or not isinstance(value[2], list)
    ):
        _fail("folder tree contains an invalid compact node")
    return value[0], value[1], value[2]


def _find(node: Any, folder_id: str) -> Any | None:
    current_id, _, children = _node(node)
    if current_id == folder_id:
        return node
    for child in children:
        found = _find(child, folder_id)
        if found is not None:
            return found
    return None


def _flatten(node: Any) -> list[tuple[str, str]]:
    folder_id, title, children = _node(node)
    records = [(folder_id, title)]
    for child in children:
        records.extend(_flatten(child))
    return records


def _detected_major(title: str) -> int | None:
    match = re.search(r"(?:^|[ _-])v(\d+)(?:[._-]|$)", title, re.IGNORECASE)
    return int(match.group(1)) if match else None


def _string_list(value: Any, field: str) -> list[str]:
    if (
        not isinstance(value, list)
        or not all(isinstance(item, str) and item for item in value)
        or len(value) != len(set(value))
    ):
        _fail(f"{field} must contain unique non-empty strings")
    return value


def _validate_excluded_items(
    raw_items: Any,
    *,
    target_folder_ids: set[str],
    reviewed_folder_ids: set[str],
    exclusion_classes: set[str],
    file_candidates_complete: bool,
) -> list[dict[str, Any]]:
    if not isinstance(raw_items, list):
        _fail("excluded_items must be a list")
    validated: list[dict[str, Any]] = []
    seen_item_ids: set[str] = set()
    for raw in raw_items:
        if not isinstance(raw, dict):
            _fail("excluded item must be an object")
        item_id = raw.get("item_id")
        item_type = raw.get("item_type")
        exclusion_class = raw.get("exclusion_class")
        rationale = raw.get("rationale")
        evidence_url = raw.get("evidence_url")
        reviewed_by = raw.get("reviewed_by")
        reviewed_on = raw.get("reviewed_on")
        if not isinstance(item_id, str) or not item_id:
            _fail("excluded item ID must be a non-empty string")
        if item_id in seen_item_ids:
            _fail(f"duplicate excluded item ID: {item_id}")
        if item_type not in {"folder", "file"}:
            _fail(f"invalid excluded item type: {item_id}")
        if exclusion_class not in exclusion_classes:
            _fail(f"invalid exclusion class: {item_id}")
        if not isinstance(rationale, str) or not rationale.strip():
            _fail(f"excluded item rationale is required: {item_id}")
        if not isinstance(evidence_url, str) or not evidence_url.startswith("https://"):
            _fail(f"excluded item evidence URL is invalid: {item_id}")
        if not isinstance(reviewed_by, str) or not reviewed_by.strip():
            _fail(f"excluded item reviewer is required: {item_id}")
        if (
            not isinstance(reviewed_on, str)
            or re.fullmatch(r"\d{4}-\d{2}-\d{2}", reviewed_on) is None
        ):
            _fail(f"excluded item review date is invalid: {item_id}")
        if item_type == "folder":
            if item_id not in target_folder_ids:
                _fail(f"excluded folder is outside the target subtree: {item_id}")
            if item_id not in reviewed_folder_ids:
                _fail(f"excluded folder has not been reviewed: {item_id}")
        elif not file_candidates_complete:
            _fail("file exclusions require a complete file candidate inventory")
        seen_item_ids.add(item_id)
        validated.append(dict(raw))
    return validated


def validate_pre_v6_exclusion_review(
    review: dict[str, Any],
    *,
    deletion_plan: dict[str, Any],
    folder_payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate review scope and emit the deterministic folder candidate set."""
    plan_result = validate_pre_v6_deletion_plan(
        deletion_plan,
        folder_payload=folder_payload,
    )
    if plan_result["status"] != "pre_v6_deletion_planned_not_authorized":
        _fail("pre-v6 deletion plan is not in the required fail-closed state")

    if review.get("schema_version") != "1.0":
        _fail("pre-v6 exclusion review schema_version must be 1.0")
    if review.get("generated_for_release") != "7.0.0rc1":
        _fail("pre-v6 exclusion review must target 7.0.0rc1")
    if review.get("source_root_id") != folder_payload.get("source_root_id"):
        _fail("pre-v6 exclusion review source root mismatch")
    tree_sha = _sha(review.get("folder_tree_sha256"), "folder_tree_sha256")
    if tree_sha != folder_payload.get("folder_tree_sha256"):
        _fail("pre-v6 exclusion review is not bound to the folder tree")
    if review.get("deletion_plan_sha256") != deletion_plan.get("plan_sha256"):
        _fail("pre-v6 exclusion review is not bound to the deletion plan")

    target_id = review.get("target_root_id")
    target_title = review.get("target_root_title")
    if target_id != deletion_plan.get("target_root_id"):
        _fail("pre-v6 exclusion review target root mismatch")
    if target_title != deletion_plan.get("target_root_title"):
        _fail("pre-v6 exclusion review target title mismatch")
    target = _find(folder_payload.get("tree"), target_id)
    if target is None:
        _fail("pre-v6 exclusion review target root is missing")
    _, actual_title, _ = _node(target)
    if actual_title != target_title:
        _fail("pre-v6 exclusion review target title does not reconcile")

    folder_records = _flatten(target)
    target_folder_ids = {folder_id for folder_id, _ in folder_records}
    if len(folder_records) != 92:
        _fail("pre-v6 exclusion review must contain exactly 92 folders")
    if review.get("candidate_folder_count") != len(folder_records):
        _fail("pre-v6 exclusion review folder count mismatch")
    if review.get("folder_candidates_complete") is not True:
        _fail("pre-v6 folder candidate enumeration must be complete")
    if review.get("candidate_file_count") is not None:
        _fail("pre-v6 file candidate count must remain unknown")
    if review.get("file_candidates_complete") is not False:
        _fail("pre-v6 file candidate inventory must remain incomplete")
    if review.get("review_scope") != "folder_and_file_item_level":
        _fail("pre-v6 exclusion review scope is invalid")

    reviewed = set(
        _string_list(review.get("reviewed_folder_ids"), "reviewed_folder_ids")
    )
    if not reviewed.issubset(target_folder_ids):
        _fail("reviewed folder IDs contain an out-of-scope folder")

    required_exclusions = {
        "legal_hold",
        "security_record_required_for_v6_or_v7",
        "decision_record_required_for_v6_or_v7",
        "audit_record_required_for_v6_or_v7",
    }
    exclusions = set(
        _string_list(review.get("exclusion_classes"), "exclusion_classes")
    )
    if exclusions != required_exclusions:
        _fail("pre-v6 exclusion classes are incomplete")
    excluded_items = _validate_excluded_items(
        review.get("excluded_items"),
        target_folder_ids=target_folder_ids,
        reviewed_folder_ids=reviewed,
        exclusion_classes=exclusions,
        file_candidates_complete=False,
    )

    expected = {
        "exclusion_review_complete": False,
        "review_decision_record_url": None,
        "explicit_deletion_authorization_id": None,
        "deletion_authorized": False,
        "promotion_blocking": False,
        "provider_writes": 0,
        "destructive_actions_performed": 0,
    }
    for field, value in expected.items():
        if review.get(field) != value:
            _fail(f"pre-v6 exclusion review has unsafe state: {field}")

    review_sha = _sha(review.get("review_sha256"), "review_sha256")
    unsigned = dict(review)
    unsigned.pop("review_sha256", None)
    if review_sha != canonical_sha256(unsigned):
        _fail("pre-v6 exclusion review digest mismatch")

    candidates = [
        {
            "folder_id": folder_id,
            "title": title,
            "detected_major": _detected_major(title),
            "review_state": "reviewed" if folder_id in reviewed else "unreviewed",
        }
        for folder_id, title in sorted(folder_records)
    ]
    return {
        "schema_version": "1.0",
        "status": "pre_v6_exclusion_review_open_not_authorized",
        "review_sha256": review_sha,
        "deletion_plan_sha256": deletion_plan["plan_sha256"],
        "candidate_folder_count": len(candidates),
        "candidate_folder_set_sha256": canonical_sha256(candidates),
        "candidate_folders": candidates,
        "reviewed_folder_count": len(reviewed),
        "pending_folder_review_count": len(candidates) - len(reviewed),
        "excluded_item_count": len(excluded_items),
        "file_candidates_complete": False,
        "exclusion_review_complete": False,
        "promotion_blocking": False,
        "deletion_ready": False,
        "deletion_authorized": False,
        "provider_writes": 0,
        "destructive_actions_performed": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--folder-tree", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = validate_pre_v6_exclusion_review(
        _read_json(args.review),
        deletion_plan=_read_json(args.plan),
        folder_payload=_read_json(args.folder_tree),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
