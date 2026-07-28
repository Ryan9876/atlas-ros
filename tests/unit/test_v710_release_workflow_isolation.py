from __future__ import annotations

from pathlib import Path

import yaml


def test_release_workflow_compatibility_registry_names_canonical_compiler() -> None:
    registry = yaml.safe_load(
        Path("governance/release-workflow-compatibility.yaml").read_text()
    )
    assert registry["canonical_compiler"] == "tools/release/release_compiler.py"
    assert registry["canonical_candidate_workflow"] == (
        ".github/workflows/v710-consolidation-candidate.yml"
    )
    assert registry["historical_release_workflows"]["production_runtime_reachable"] is False
    assert registry["historical_release_workflows"]["may_define_new_policy"] is False
