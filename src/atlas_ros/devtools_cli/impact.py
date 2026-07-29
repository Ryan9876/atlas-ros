"""Conservative shadow-mode change impact analysis."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable

from atlas_ros.devtools_cli.contracts import ChangeImpactAssessmentV1

BROAD_PREFIXES = (
    "governance/",
    ".github/workflows/",
    "pyproject.toml",
    "requirements",
    "src/atlas_ros/contracts/",
    "src/atlas_ros/capabilities/",
    "src/atlas_ros/adapters/",
    "src/atlas_ros/release",
    "scripts/",
)


def assess_changes(paths: Iterable[str]) -> ChangeImpactAssessmentV1:
    changed = tuple(sorted(set(paths)))
    broad = not changed or any(path.startswith(BROAD_PREFIXES) for path in changed)
    known = all(path.startswith(("src/", "tests/", "docs/", "governance/", ".github/", "release/")) or path in {"pyproject.toml"} for path in changed)
    if not known:
        broad = True
    selected = ("ruff", "mypy", "architecture", "pytest") if broad else ("ruff", "targeted-pytest")
    broadened = ("complete-candidate-gates",) if broad else ()
    rationale = []
    if broad:
        rationale.append("shared, release-sensitive, workflow, dependency, or unknown change")
    if not known:
        rationale.append("unknown path broadened validation")
    payload = {"changed": changed, "selected": selected, "broadened": broadened, "mode": "shadow"}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return ChangeImpactAssessmentV1(
        changed_paths=changed,
        affected_nodes=("development-tooling",),
        transitive_effects=("validation", "packaging") if broad else (),
        risk_classification="broad" if broad else "bounded",
        selected_validation=selected,
        broadened_validation=broadened,
        workflow_selection=("lean-ci", "full-candidate-ci") if broad else ("lean-ci",),
        full_history_required=broad,
        clean_build_required=broad,
        rationale=tuple(rationale) or ("bounded known-path change",),
        impact_digest=digest,
    )
