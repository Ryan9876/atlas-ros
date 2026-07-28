from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.validate_v700_pre_v6_deletion_plan import (
    PreV6DeletionPlanError,
    canonical_sha256,
    validate_pre_v6_deletion_plan,
)


ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> dict[str, object]:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def resign(value: dict[str, object]) -> None:
    value.pop("plan_sha256", None)
    value["plan_sha256"] = canonical_sha256(value)


def test_pre_v6_deletion_plan_is_non_blocking_and_unauthorized() -> None:
    result = validate_pre_v6_deletion_plan(
        read("release/v700-pre-v6-deletion-plan.json"),
        folder_payload=read("release/v700-drive-folder-traversal.json"),
    )

    assert result["status"] == "pre_v6_deletion_planned_not_authorized"
    assert result["target_folder_count"] == 92
    assert result["preserved_release_family"] == "6.x_and_newer"
    assert result["promotion_blocking"] is False
    assert result["deletion_ready"] is False
    assert result["deletion_authorized"] is False
    assert result["provider_writes"] == 0


def test_pre_v6_deletion_plan_rejects_early_authorization() -> None:
    plan = deepcopy(read("release/v700-pre-v6-deletion-plan.json"))
    plan["deletion_authorized"] = True
    plan["explicit_deletion_authorization_id"] = "V4D-TEST"
    resign(plan)

    with pytest.raises(PreV6DeletionPlanError, match="unsafe state"):
        validate_pre_v6_deletion_plan(
            plan,
            folder_payload=read("release/v700-drive-folder-traversal.json"),
        )


def test_pre_v6_deletion_plan_rejects_v6_folder_in_scope() -> None:
    tree = deepcopy(read("release/v700-drive-folder-traversal.json"))
    compact = tree["tree"]
    assert isinstance(compact, list)
    children = compact[2]
    assert isinstance(children, list)
    historical = children[0]
    assert isinstance(historical, list)
    historical_children = historical[2]
    assert isinstance(historical_children, list)
    historical_children.append(["unsafe-v6", "Atlas ROS v6.0.0", []])

    with pytest.raises(PreV6DeletionPlanError, match="folder|v6"):
        validate_pre_v6_deletion_plan(
            read("release/v700-pre-v6-deletion-plan.json"),
            folder_payload=tree,
        )
