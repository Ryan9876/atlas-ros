#!/usr/bin/env bash
set -euo pipefail

: "${GH_TOKEN:?GH_TOKEN is required}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
: "${GITHUB_RUN_ID:?GITHUB_RUN_ID is required}"
CANDIDATE_SHA="${CANDIDATE_SHA:-$(git rev-parse HEAD)}"
ATLAS_VERSION="$(python - <<'PY'
import tomllib
from pathlib import Path
print(tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]["version"])
PY
)"
test "$ATLAS_VERSION" = "6.5.0"
test "$(python -c 'import atlas_ros; print(atlas_ros.__version__)')" = "$ATLAS_VERSION"

rm -rf candidate-evidence publication dist build clean-candidate active-assets rollback-assets
mkdir -p candidate-evidence/test-results candidate-evidence/benchmarks publication

ruff check .
python scripts/validate_architecture.py
mypy src
pytest --junitxml=candidate-evidence/test-results/pytest.xml \
  --cov-report=json:candidate-evidence/test-results/coverage.json
python scripts/evaluate_execution_planning.py \
  --dataset benchmarks/execution-planning-v1.json \
  --output candidate-evidence/benchmarks/execution-planning.json
python scripts/scan_candidate_secrets.py --root . --output candidate-evidence/secret-scan.json

rm -f release/CHECKSUMS.sha256
atlas release checksums --root . --checksum-file release/CHECKSUMS.sha256
atlas release verify --root . --checksum-file release/CHECKSUMS.sha256
python -m build
SDIST="atlas_ros-${ATLAS_VERSION}.tar.gz"
WHEEL="atlas_ros-${ATLAS_VERSION}-py3-none-any.whl"
test -f "dist/$SDIST"
test -f "dist/$WHEEL"
sha256sum "dist/$SDIST" "dist/$WHEEL" > candidate-evidence/candidate-artifacts.sha256

python -m venv clean-candidate
clean-candidate/bin/python -m pip install --disable-pip-version-check "dist/$WHEEL"
clean-candidate/bin/python - <<'PY'
import atlas_ros
from atlas_ros.contracts import AdvisoryRecommendation
from atlas_ros.engines import (
    ExecutionPresenterV65,
    GovernedFrameworkComposerV65,
    MinimumEffectivePathPlannerV65,
    ScenarioIntelligenceV65,
)
assert atlas_ros.__version__ == "6.5.0"
assert all((AdvisoryRecommendation, ExecutionPresenterV65, GovernedFrameworkComposerV65,
            MinimumEffectivePathPlannerV65, ScenarioIntelligenceV65))
PY

gh release download v6.2.0 --repo "$GITHUB_REPOSITORY" \
  --pattern 'atlas_ros-6.2.0*.whl' --dir active-assets
gh release download v6.1.1 --repo "$GITHUB_REPOSITORY" \
  --pattern 'atlas_ros-6.1.1*.whl' --dir rollback-assets
ACTIVE_WHEEL="$(find active-assets -name 'atlas_ros-6.2.0*.whl' -print -quit)"
ROLLBACK_WHEEL="$(find rollback-assets -name 'atlas_ros-6.1.1*.whl' -print -quit)"
test -n "$ACTIVE_WHEEL"
test -n "$ROLLBACK_WHEEL"
python -m venv restore-active
restore-active/bin/python -m pip install --disable-pip-version-check "$ACTIVE_WHEEL"
restore-active/bin/python -c "import atlas_ros; assert atlas_ros.__version__ == '6.2.0'"
python -m venv restore-rollback
restore-rollback/bin/python -m pip install --disable-pip-version-check "$ROLLBACK_WHEEL"
restore-rollback/bin/python -c "import atlas_ros; assert atlas_ros.__version__ == '6.1.1'"

cp release/RELEASE_SCOPE_V650.md candidate-evidence/
cp release/RELEASE_NOTES_V650.md candidate-evidence/
cp release/SBOM_V650_CANDIDATE.cdx.json candidate-evidence/SBOM.cdx.json
cp release/CHECKSUMS.sha256 candidate-evidence/SOURCE_CHECKSUMS.sha256
export CANDIDATE_SHA GITHUB_RUN_ID ATLAS_VERSION SDIST WHEEL
python - <<'PY'
import hashlib
import json
import os
from pathlib import Path

evidence = Path("candidate-evidence")
status = {
    "release": "Atlas ROS v6.5.0",
    "status": "candidate_validated_not_promoted",
    "candidate_sha": os.environ["CANDIDATE_SHA"],
    "workflow_run_id": os.environ["GITHUB_RUN_ID"],
    "source_distribution": os.environ["SDIST"],
    "wheel": os.environ["WHEEL"],
    "active_production_baseline_restored": "v6.2.0",
    "historical_rollback_restored": "v6.1.1",
    "provider_writes": 0,
    "production_promotion_authorized": False,
}
path = evidence / "V650_CANDIDATE_STATUS.json"
path.write_text(json.dumps(status, indent=2, sort_keys=True), encoding="utf-8")
digest = hashlib.sha256(path.read_bytes()).hexdigest()
(evidence / "V650_CANDIDATE_STATUS.sha256").write_text(
    f"{digest}  {path.name}\n", encoding="utf-8"
)
(evidence / "RELEASE_MANIFEST_V650_CANDIDATE.md").write_text(
    f"""# Atlas ROS v6.5.0 Candidate Manifest

Status: Validated release candidate; not promoted.

- Candidate commit: \`{status["candidate_sha"]}\`
- Validation workflow run: \`{status["workflow_run_id"]}\`
- Active production baseline restored: \`v6.2.0\`
- Historical rollback restored: \`v6.1.1\`
- Provider writes during validation: \`0\`
- Final production promotion: not authorized

This candidate cannot alter the active Release Index, Notion System State, immutable production tag, GitHub Release, or integration authority without a separate explicit production-promotion decision.
""",
    encoding="utf-8",
)
PY

(
  cd candidate-evidence
  find . -type f ! -name EVIDENCE_CHECKSUMS.sha256 -print0 | sort -z |
    xargs -0 sha256sum > EVIDENCE_CHECKSUMS.sha256
  sha256sum -c EVIDENCE_CHECKSUMS.sha256
)
cp "dist/$SDIST" "dist/$WHEEL" publication/
cp -R candidate-evidence publication/evidence
tar -czf publication/Atlas_ROS_v6.5.0_candidate_evidence.tar.gz -C publication evidence
(
  cd publication
  find . -maxdepth 1 -type f ! -name PUBLICATION_CHECKSUMS.sha256 -print0 | sort -z |
    xargs -0 sha256sum > PUBLICATION_CHECKSUMS.sha256
  sha256sum -c PUBLICATION_CHECKSUMS.sha256
)
