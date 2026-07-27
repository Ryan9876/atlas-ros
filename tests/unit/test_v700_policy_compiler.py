from __future__ import annotations

from pathlib import Path

import pytest

from atlas_ros.policy.compiler import PolicyCompilationError, compile_policy_registry


def write_policy(path: Path, policy_id: str = "atlas.test") -> Path:
    path.write_text(
        "schema_version: '1.0'\npolicy_id: " + policy_id + "\nlifecycle: active\nrules:\n  - do_the_thing\n",
        encoding="utf-8",
    )
    return path


def test_compiler_is_deterministic_and_immutable(tmp_path: Path) -> None:
    policy = write_policy(tmp_path / "one.yaml")
    first = compile_policy_registry([policy])
    second = compile_policy_registry([policy])
    assert first.digest == second.digest
    assert first.require("atlas.test").rules == ("do_the_thing",)
    with pytest.raises(TypeError):
        first.policies["atlas.other"] = first.require("atlas.test")  # type: ignore[index]


def test_compiler_fails_closed_for_duplicate_policy_ids(tmp_path: Path) -> None:
    with pytest.raises(PolicyCompilationError, match="duplicate"):
        compile_policy_registry([write_policy(tmp_path / "one.yaml"), write_policy(tmp_path / "two.yaml")])
