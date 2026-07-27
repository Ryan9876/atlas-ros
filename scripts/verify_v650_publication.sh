#!/usr/bin/env bash
set -euo pipefail

: "${GH_TOKEN:?}"
: "${GITHUB_REPOSITORY:?}"
: "${RELEASE_TAG:?}"
: "${EXPECTED_SOURCE_COMMIT:?}"

rm -rf release-readback post-publication-evidence verify-v650-wheel verify-v620-wheel verify-v611-wheel restore-v620 restore-v611
mkdir -p release-readback post-publication-evidence restore-v620 restore-v611

gh release view "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" --json tagName,targetCommitish,isDraft,isPrerelease,publishedAt,url > post-publication-evidence/release.json
python - <<'PY'
import json
from pathlib import Path
data=json.loads(Path("post-publication-evidence/release.json").read_text())
assert data["tagName"] == "v6.5.0"
assert data["isDraft"] is False
assert data["isPrerelease"] is False
assert data["publishedAt"]
assert data["url"]
PY

test "$(git rev-list -n 1 "$RELEASE_TAG")" = "$EXPECTED_SOURCE_COMMIT"

gh release download "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" --dir release-readback
test -f release-readback/CHECKSUMS.sha256
test -f release-readback/FINAL_IDENTITY.json
test -f release-readback/RELEASE_MANIFEST.md
test -f release-readback/atlas_ros-6.5.0-py3-none-any.whl
test -f release-readback/atlas_ros-6.5.0.tar.gz
(cd release-readback && sha256sum -c CHECKSUMS.sha256)

python - <<'PY'
import json
import os
from pathlib import Path
identity=json.loads(Path("release-readback/FINAL_IDENTITY.json").read_text())
assert identity["release"] == "v6.5.0"
assert identity["source_commit"] == os.environ["EXPECTED_SOURCE_COMMIT"]
assert identity["candidate_commit"] == "1412e615726e27fd1880222598c1271d4e466058"
assert identity["candidate_merge_commit"] == "4247baf812eae3635408af2fb61761685ea1115f"
assert identity["candidate_artifact_id"] == "8654164435"
assert identity["candidate_artifact_digest"] == "cc46bd3725717a620c9872ac0da81667e31298b444bab8a125ae94506c9ac040"
assert identity["immediate_rollback"] == "v6.2.0"
assert identity["historical_rollback"] == "v6.1.1"
assert identity["provider_writes"] == 0
Path("post-publication-evidence/FINAL_IDENTITY.json").write_text(json.dumps(identity, indent=2, sort_keys=True) + "\n")
PY

python -m venv verify-v650-wheel
verify-v650-wheel/bin/python -m pip install --disable-pip-version-check release-readback/atlas_ros-6.5.0-py3-none-any.whl
verify-v650-wheel/bin/python - <<'PY'
from importlib.metadata import version
import atlas_ros
from atlas_ros.contracts import AdvisoryRecommendation
from atlas_ros.engines import ExecutionPresenterV65, GovernedFrameworkComposerV65, MinimumEffectivePathPlannerV65, ScenarioIntelligenceV65
assert version("atlas-ros") == "6.5.0"
assert atlas_ros.__version__ == "6.5.0"
assert all((AdvisoryRecommendation, ExecutionPresenterV65, GovernedFrameworkComposerV65, MinimumEffectivePathPlannerV65, ScenarioIntelligenceV65))
PY

gh release download v6.2.0 --repo "$GITHUB_REPOSITORY" --pattern 'atlas_ros-6.2.0*.whl' --dir restore-v620
gh release download v6.1.1 --repo "$GITHUB_REPOSITORY" --pattern 'atlas_ros-6.1.1*.whl' --dir restore-v611
python -m venv verify-v620-wheel
verify-v620-wheel/bin/python -m pip install --disable-pip-version-check "$(find restore-v620 -name '*.whl' -print -quit)"
verify-v620-wheel/bin/python -c "import atlas_ros; assert atlas_ros.__version__ == '6.2.0'"
python -m venv verify-v611-wheel
verify-v611-wheel/bin/python -m pip install --disable-pip-version-check "$(find restore-v611 -name '*.whl' -print -quit)"
verify-v611-wheel/bin/python -c "import atlas_ros; assert atlas_ros.__version__ == '6.1.1'"

cp release-readback/CHECKSUMS.sha256 post-publication-evidence/PUBLISHED_CHECKSUMS.sha256
cp release-readback/RELEASE_MANIFEST.md post-publication-evidence/RELEASE_MANIFEST.md
(
  cd post-publication-evidence
  find . -maxdepth 1 -type f ! -name EVIDENCE_CHECKSUMS.sha256 -print0 | sort -z | xargs -0 sha256sum > EVIDENCE_CHECKSUMS.sha256
  sha256sum -c EVIDENCE_CHECKSUMS.sha256
)
