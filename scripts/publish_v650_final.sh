#!/usr/bin/env bash
set -euo pipefail
: "${GH_TOKEN:?}"
: "${GITHUB_REPOSITORY:?}"
: "${SOURCE_COMMIT:?}"
: "${CANDIDATE_COMMIT:?}"
: "${CANDIDATE_MERGE_COMMIT:?}"
: "${CANDIDATE_ARTIFACT_ID:?}"
: "${CANDIDATE_ARTIFACT_DIGEST:?}"
: "${RELEASE_TAG:?}"
: "${ROLLBACK_TAG:?}"
PUBLISH="${PUBLISH:-false}"
version="$(python - <<'PY'
import tomllib
from pathlib import Path
print(tomllib.loads(Path("pyproject.toml").read_text())["project"]["version"])
PY
)"
test "$version" = "6.5.0"
test "$(python -c 'import atlas_ros; print(atlas_ros.__version__)')" = "$version"
test "$(git rev-parse HEAD)" = "$SOURCE_COMMIT"
git merge-base --is-ancestor "$CANDIDATE_COMMIT" HEAD
git merge-base --is-ancestor "$CANDIDATE_MERGE_COMMIT" HEAD
rm -rf final-publication final-evidence dist build restore-active restore-rollback
mkdir -p final-publication final-evidence/test-results
ruff check .
python scripts/validate_architecture.py
mypy src
pytest --junitxml=final-evidence/test-results/pytest.xml --cov-report=json:final-evidence/test-results/coverage.json
python scripts/scan_candidate_secrets.py --root . --output final-evidence/secret-scan.json
python scripts/validate_dependency_lock.py requirements.runtime.lock
python scripts/validate_vulnerability_exceptions.py
pip-audit --disable-pip --require-hashes --no-deps --requirement requirements.runtime.lock --format json --output final-evidence/pip-audit.json
python scripts/evaluate_dependency_audit.py final-evidence/pip-audit.json
rm -f release/CHECKSUMS.sha256
atlas release checksums --root . --checksum-file release/CHECKSUMS.sha256
atlas release verify --root . --checksum-file release/CHECKSUMS.sha256
python -m build
test -f dist/atlas_ros-6.5.0.tar.gz
test -f dist/atlas_ros-6.5.0-py3-none-any.whl
python -m venv final-wheel
final-wheel/bin/python -m pip install --disable-pip-version-check dist/atlas_ros-6.5.0-py3-none-any.whl
final-wheel/bin/python - <<'PY'
from importlib.metadata import version
import atlas_ros
from atlas_ros.contracts import AdvisoryRecommendation
from atlas_ros.engines import ExecutionPresenterV65, GovernedFrameworkComposerV65, MinimumEffectivePathPlannerV65, ScenarioIntelligenceV65
assert version("atlas-ros") == "6.5.0"
assert atlas_ros.__version__ == "6.5.0"
assert all((AdvisoryRecommendation, ExecutionPresenterV65, GovernedFrameworkComposerV65, MinimumEffectivePathPlannerV65, ScenarioIntelligenceV65))
PY
gh release download "$ROLLBACK_TAG" --repo "$GITHUB_REPOSITORY" --pattern 'atlas_ros-6.2.0*.whl' --dir restore-active
gh release download v6.1.1 --repo "$GITHUB_REPOSITORY" --pattern 'atlas_ros-6.1.1*.whl' --dir restore-rollback
python -m venv active-wheel
active-wheel/bin/python -m pip install --disable-pip-version-check "$(find restore-active -name '*.whl' -print -quit)"
active-wheel/bin/python -c "import atlas_ros; assert atlas_ros.__version__ == '6.2.0'"
python -m venv rollback-wheel
rollback-wheel/bin/python -m pip install --disable-pip-version-check "$(find restore-rollback -name '*.whl' -print -quit)"
rollback-wheel/bin/python -c "import atlas_ros; assert atlas_ros.__version__ == '6.1.1'"
cp dist/atlas_ros-6.5.0.tar.gz final-publication/
cp dist/atlas_ros-6.5.0-py3-none-any.whl final-publication/
cp release/RELEASE_NOTES_V650.md final-publication/
cp release/RELEASE_SCOPE_V650.md final-publication/
cp release/SBOM_V650_CANDIDATE.cdx.json final-publication/SBOM.cdx.json
cp release/CHECKSUMS.sha256 final-publication/SOURCE_CHECKSUMS.sha256
candidate_digest="${CANDIDATE_ARTIFACT_DIGEST#sha256:}"
wheel_sha="$(sha256sum final-publication/atlas_ros-6.5.0-py3-none-any.whl | awk '{print $1}')"
source_sha="$(sha256sum final-publication/atlas_ros-6.5.0.tar.gz | awk '{print $1}')"
export SOURCE_COMMIT CANDIDATE_COMMIT CANDIDATE_MERGE_COMMIT CANDIDATE_ARTIFACT_ID candidate_digest wheel_sha source_sha
python - <<'PY'
import json, os
from pathlib import Path
p=Path("final-publication")
identity={"release":"v6.5.0","source_commit":os.environ["SOURCE_COMMIT"],"candidate_commit":os.environ["CANDIDATE_COMMIT"],"candidate_merge_commit":os.environ["CANDIDATE_MERGE_COMMIT"],"candidate_artifact_id":os.environ["CANDIDATE_ARTIFACT_ID"],"candidate_artifact_digest":os.environ["candidate_digest"],"final_wheel_sha256":os.environ["wheel_sha"],"final_source_sha256":os.environ["source_sha"],"immediate_rollback":"v6.2.0","historical_rollback":"v6.1.1","provider_writes":0}
(p/"FINAL_IDENTITY.json").write_text(json.dumps(identity,indent=2,sort_keys=True))
(p/"RELEASE_MANIFEST.md").write_text("# Atlas ROS v6.5.0 Release Manifest\n\nStatus: final production package pending live authority activation.\n\n"+ "\n".join(f"- {k}: `{v}`" for k,v in identity.items())+"\n")
PY
tar -czf final-publication/Atlas_ROS_v6.5.0_final_evidence.tar.gz -C final-evidence .
(cd final-publication && find . -maxdepth 1 -type f ! -name CHECKSUMS.sha256 -print0 | sort -z | xargs -0 sha256sum > CHECKSUMS.sha256 && sha256sum -c CHECKSUMS.sha256)
if [[ "$PUBLISH" == "true" ]]; then
  ! gh release view "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" >/dev/null 2>&1
  gh release create "$RELEASE_TAG" final-publication/* --repo "$GITHUB_REPOSITORY" --target "$SOURCE_COMMIT" --title "Atlas ROS v6.5.0" --notes-file release/RELEASE_NOTES_V650.md
  git fetch --tags --force
  test "$(git rev-list -n 1 "$RELEASE_TAG")" = "$SOURCE_COMMIT"
  mkdir -p release-readback
  gh release download "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" --dir release-readback
  (cd release-readback && sha256sum -c CHECKSUMS.sha256)
fi

# Controller validation trigger.
