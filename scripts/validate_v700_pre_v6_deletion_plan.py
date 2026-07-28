#!/usr/bin/env python3
"""Validate a fail-closed post-cutover deletion plan for pre-v6 Drive history."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


class PreV6DeletionPlanError(ValueError):
    """Raised when the historical deletion plan is incomplete or unsafe."""


def canonical_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _fail(message: str) -> None:
    raise PreV6DeletionPlanError(message)


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
        raise PreV6DeletionPlanError(f"invalid JSON evidence: {path}") from error
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
    match = re.search(r"(?:^|[ _-])v?(\d+)(?:[._-]|$)", title, re.IGNORECASE)
    if match is None:
        return None
    return int(match.group(1))


def validate_pre_v6_deletion_plan(
    plan: dict[str, Any],
    *,
    folder_payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate scope and confirm that deletion remains unauthorized."""
    if plan.get("schema_version") != "1.0":
        _fail("pre-v6 deletion plan schema_version must be 1.0")
    if plan.get("generated_for_release") != "7.0.0rc1":
        _fail("pre-v6 deletion plan must target 7.0.0rc1")
    if folder_payload.get("folder_traversal_complete") is not True:
        _fail("Drive folder traversal must be complete")
    if plan.get("source_root_id") != folder_payload.get("source_root_id"):
        _fail("pre-v6 deletion plan source root mismatch")
    tree_sha = _sha(plan.get("folder_tree_sha256"), "folder_tree_sha256")
    if tree_sha != folder_payload.get("folder_tree_sha256"):
        _fail("pre-v6 deletion plan is not bound to the folder tree")

    target_id = plan.get("target_root_id")
    target_title = plan.get("target_root_title")
    if not isinstance(target_id, str) or not isinstance(target_title, str):
        _fail("pre-v6 target root identity is invalid")
    target = _find(folder_payload.get("tree"), target_id)
    if target is None:
        _fail("pre-v6 target root is not present in the folder tree")
    _, actual_title, _ = _node(target)
    if actual_title != target_title:
        _fail("pre-v6 target root title mismatch")
    if actual_title != "Historical Documentation — Not Current Authority":
        _fail("pre-v6 deletion must target the governed historical root")

    records = _flatten(target)
    if plan.get("target_folder_count") != len(records):
        _fail("pre-v6 target folder count mismatch")
    if len(records) != 92:
        _fail("pre-v6 historical subtree must contain 92 folders")
    detected = [
        (title, major)
        for _, title in records
        if (major := _detected_major(title)) is not None
    ]
    invalid_versions = sorted(title for title, major in detected if major >= 6)
    if invalid_versions:
        _fail("pre-v6 deletion scope contains v6-or-newer folders")

    if plan.get("scope_rule") != "delete_versions_below_6_after_v7_cutover":
        _fail("unexpected pre-v6 deletion scope rule")
    if plan.get("preserved_release_family") != "6.x_and_newer":
        _fail("v6 and newer releases must be preserved")
    if plan.get("target_file_count") is not None:
        _fail("unknown pre-v6 file count cannot be asserted")
    if plan.get("item_inventory_complete") is not False:
        _fail("pre-v6 item inventory must remain explicitly incomplete")

    required_exclusions = {
        "legal_hold",
        "security_record_required_for_v6_or_v7",
        "decision_record_required_for_v6_or_v7",
        "audit_record_required_for_v6_or_v7",
    }
    exclusions = plan.get("exclusion_classes")
    if not isinstance(exclusions, list) or set(exclusions) != required_exclusions:
        _fail("pre-v6 deletion exclusion classes are incomplete")
    if plan.get("exclusion_review_required") is not True:
        _fail("pre-v6 deletion requires an exclusion review")
    if plan.get("exclusion_review_complete") is not False:
        _fail("pre-v6 exclusion review cannot be complete before item review")

    blocked_state = {
        "v7_active": False,
        "v7_post_promotion_readback_complete": False,
        "v650_rollback_restored": False,
        "explicit_deletion_authorization_id": None,
        "deletion_authorized": False,
        "promotion_blocking": False,
        "provider_writes": 0,
        "destructive_actions_performed": 0,
    }
    for field, expected in blocked_state.items():
        if plan.get(field) != expected:
            _fail(f"pre-v6 deletion plan has unsafe pre-cutover state: {field}")

    plan_sha = _sha(plan.get("plan_sha256"), "plan_sha256")
    unsigned = dict(plan)
    unsigned.pop("plan_sha256", None)
    if plan_sha != canonical_sha256(unsigned):
        _fail("pre-v6 deletion plan digest mismatch")

    return {
        "schema_version": "1.0",
        "status": "pre_v6_deletion_planned_not_authorized",
        "plan_sha256": plan_sha,
        "target_root_id": target_id,
        "target_folder_count": len(records),
        "detected_versioned_folder_count": len(detected),
        "preserved_release_family": "6.x_and_newer",
        "promotion_blocking": False,
        "deletion_ready": False,
        "deletion_authorized": False,
        "provider_writes": 0,
        "destructive_actions_performed": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--folder-tree", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = validate_pre_v6_deletion_plan(
        _read_json(args.plan),
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
