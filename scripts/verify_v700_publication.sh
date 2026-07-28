#!/usr/bin/env bash
set -euo pipefail
: "${GH_TOKEN:?GH_TOKEN is required}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
: "${RELEASE_TAG:?RELEASE_TAG is required}"
: "${EXPECTED_SOURCE_COMMIT:?EXPECTED_SOURCE_COMMIT is required}"
: "${EXPECTED_FINAL_SOURCE_SHA256:?EXPECTED_FINAL_SOURCE_SHA256 is required}"
: "${EXPECTED_FINAL_WHEEL_SHA256:?EXPECTED_FINAL_WHEEL_SHA256 is required}"
rm -rf post-publication-evidence published-assets verify-published verify-v650 verify-v620 rollback-v650 rollback-v620
mkdir -p post-publication-evidence published-assets
release_json="$(gh api "repos/${GITHUB_REPOSITORY}/releases/tags/${RELEASE_TAG}")"
python - "$release_json" <<'PY'
import json, sys
r = json.loads(sys.argv[1])
assert r['draft'] is False
assert r['prerelease'] is False
PY
git fetch --tags --force
test "$(git rev-list -n 1 "$RELEASE_TAG")" = "$EXPECTED_SOURCE_COMMIT"
gh release download "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" --dir published-assets
(cd published-assets && sha256sum -c CHECKSUMS.sha256)
python - <<'PY'
import json, os
from pathlib import Path
p = Path('published-assets')
identity = json.loads((p/'FINAL_IDENTITY.json').read_text(encoding='utf-8'))
auth = json.loads((p/'AUTHORIZATION.json').read_text(encoding='utf-8'))
assert identity['release_version'] == '7.0.0'
assert identity['production_authorized'] is True
assert identity['publication_controller_commit'] == os.environ['EXPECTED_SOURCE_COMMIT']
assert identity['source']['sha256'] == os.environ['EXPECTED_FINAL_SOURCE_SHA256']
assert identity['wheel']['sha256'] == os.environ['EXPECTED_FINAL_WHEEL_SHA256']
assert auth['decision'] == 'V4D-39'
assert auth['review'] == 'V4V-55'
assert auth['immediate_rollback'] == 'v6.5.0'
assert auth['drive_retirement_authorized'] is False
PY
test "$(sha256sum published-assets/atlas_ros-7.0.0.tar.gz | awk '{print $1}')" = "$EXPECTED_FINAL_SOURCE_SHA256"
test "$(sha256sum published-assets/atlas_ros-7.0.0-py3-none-any.whl | awk '{print $1}')" = "$EXPECTED_FINAL_WHEEL_SHA256"
python -m venv verify-published
verify-published/bin/python -m pip install --disable-pip-version-check published-assets/atlas_ros-7.0.0-py3-none-any.whl
verify-published/bin/python -c "import atlas_ros; assert atlas_ros.__version__ == '7.0.0'"
gh release download v6.5.0 --repo "$GITHUB_REPOSITORY" --pattern 'atlas_ros-6.5.0*.whl' --dir rollback-v650
gh release download v6.2.0 --repo "$GITHUB_REPOSITORY" --pattern 'atlas_ros-6.2.0*.whl' --dir rollback-v620
python -m venv verify-v650
verify-v650/bin/python -m pip install --disable-pip-version-check "$(find rollback-v650 -name '*.whl' -print -quit)"
verify-v650/bin/python -c "import atlas_ros; assert atlas_ros.__version__ == '6.5.0'"
python -m venv verify-v620
verify-v620/bin/python -m pip install --disable-pip-version-check "$(find rollback-v620 -name '*.whl' -print -quit)"
verify-v620/bin/python -c "import atlas_ros; assert atlas_ros.__version__ == '6.2.0'"
cp published-assets/FINAL_IDENTITY.json post-publication-evidence/
cp published-assets/AUTHORIZATION.json post-publication-evidence/
cp published-assets/CHECKSUMS.sha256 post-publication-evidence/PUBLISHED_CHECKSUMS.sha256
python - <<'PY'
import json, os
from pathlib import Path
record = {
  'schema_version': '1.0',
  'status': 'passed',
  'release_tag': os.environ['RELEASE_TAG'],
  'production_source_commit': os.environ['EXPECTED_SOURCE_COMMIT'],
  'final_source_sha256': os.environ['EXPECTED_FINAL_SOURCE_SHA256'],
  'final_wheel_sha256': os.environ['EXPECTED_FINAL_WHEEL_SHA256'],
  'clean_install': True,
  'v650_immediate_rollback_restored': True,
  'v620_historical_rollback_restored': True,
  'provider_writes': 0,
}
Path('post-publication-evidence/POST_PUBLICATION_VERIFICATION.json').write_text(json.dumps(record, indent=2, sort_keys=True)+'\n', encoding='utf-8')
PY
(cd post-publication-evidence && find . -type f ! -name POST_PUBLICATION_CHECKSUMS.sha256 -print0 | sort -z | xargs -0 sha256sum > POST_PUBLICATION_CHECKSUMS.sha256 && sha256sum -c POST_PUBLICATION_CHECKSUMS.sha256)
