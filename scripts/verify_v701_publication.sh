#!/usr/bin/env bash
set -euo pipefail

: "${GH_TOKEN:?GH_TOKEN is required}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
: "${RELEASE_TAG:?RELEASE_TAG is required}"
: "${EXPECTED_SOURCE_COMMIT:?EXPECTED_SOURCE_COMMIT is required}"
: "${EXPECTED_SOURCE_SHA256:?EXPECTED_SOURCE_SHA256 is required}"
: "${EXPECTED_WHEEL_SHA256:?EXPECTED_WHEEL_SHA256 is required}"
: "${EXPECTED_MANIFEST_SHA256:?EXPECTED_MANIFEST_SHA256 is required}"

rm -rf post-publication-evidence release-readback verify-v701 verify-v700 verify-v650 rollback-v700 rollback-v650
mkdir -p post-publication-evidence release-readback

release_json="$(gh release view "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" --json tagName,isDraft,isPrerelease,targetCommitish)"
python - "$release_json" <<'PY'
import json, os, sys
payload = json.loads(sys.argv[1])
assert payload['tagName'] == os.environ['RELEASE_TAG']
assert payload['isDraft'] is False
assert payload['isPrerelease'] is False
PY

git fetch --tags --force
test "$(git rev-list -n 1 "$RELEASE_TAG")" = "$EXPECTED_SOURCE_COMMIT"
gh release download "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" --dir release-readback
(cd release-readback && sha256sum -c CHECKSUMS.sha256)
test "$(sha256sum release-readback/atlas_ros-7.0.1.tar.gz | awk '{print $1}')" = "$EXPECTED_SOURCE_SHA256"
test "$(sha256sum release-readback/atlas_ros-7.0.1-py3-none-any.whl | awk '{print $1}')" = "$EXPECTED_WHEEL_SHA256"
test "$(sha256sum release-readback/RELEASE_MANIFEST_V701.md | awk '{print $1}')" = "$EXPECTED_MANIFEST_SHA256"

python - <<'PY'
import json, os
from pathlib import Path
identity = json.loads(Path('release-readback/FINAL_IDENTITY.json').read_text(encoding='utf-8'))
authorization = json.loads(Path('release-readback/AUTHORIZATION.json').read_text(encoding='utf-8'))
assert identity['release_version'] == '7.0.1'
assert identity['candidate_commit'] == os.environ['EXPECTED_SOURCE_COMMIT']
assert identity['source']['sha256'] == os.environ['EXPECTED_SOURCE_SHA256']
assert identity['wheel']['sha256'] == os.environ['EXPECTED_WHEEL_SHA256']
assert identity['immutable_manifest']['sha256'] == os.environ['EXPECTED_MANIFEST_SHA256']
assert identity['production_authorized'] is True
assert identity['published'] is True
assert identity['authority_activated'] is False
assert identity['required_integrations'] == ['GitHub', 'Notion', 'Todoist']
assert identity['google_drive_required'] is False
assert identity['google_drive_read_during_initialization'] is False
assert authorization['decision'] == 'V4D-41'
assert authorization['review'] == 'V4V-58'
assert authorization['authorized_final_source_commit'] == os.environ['EXPECTED_SOURCE_COMMIT']
assert authorization['required_integrations'] == ['GitHub', 'Notion', 'Todoist']
assert authorization['google_drive_initialization_role'] == 'forbidden'
PY

python -m venv verify-v701
verify-v701/bin/python -m pip install --disable-pip-version-check release-readback/atlas_ros-7.0.1-py3-none-any.whl
verify-v701/bin/python -c "import atlas_ros; assert atlas_ros.__version__ == '7.0.1'"

gh release download v7.0.0 --repo "$GITHUB_REPOSITORY" --pattern 'atlas_ros-7.0.0*.whl' --dir rollback-v700
gh release download v6.5.0 --repo "$GITHUB_REPOSITORY" --pattern 'atlas_ros-6.5.0*.whl' --dir rollback-v650
python -m venv verify-v700
verify-v700/bin/python -m pip install --disable-pip-version-check "$(find rollback-v700 -name '*.whl' -print -quit)"
verify-v700/bin/python -c "import atlas_ros; assert atlas_ros.__version__ == '7.0.0'"
python -m venv verify-v650
verify-v650/bin/python -m pip install --disable-pip-version-check "$(find rollback-v650 -name '*.whl' -print -quit)"
verify-v650/bin/python -c "import atlas_ros; assert atlas_ros.__version__ == '6.5.0'"

export RELEASE_TAG EXPECTED_SOURCE_COMMIT EXPECTED_SOURCE_SHA256 EXPECTED_WHEEL_SHA256 EXPECTED_MANIFEST_SHA256
python - <<'PY'
import hashlib, json, os
from datetime import UTC, datetime
from pathlib import Path
root = Path('release-readback')
checksums = hashlib.sha256((root / 'CHECKSUMS.sha256').read_bytes()).hexdigest()
result = {
    'schema_version': '1.0',
    'status': 'passed',
    'release_tag': os.environ['RELEASE_TAG'],
    'tag_target': os.environ['EXPECTED_SOURCE_COMMIT'],
    'source_sha256': os.environ['EXPECTED_SOURCE_SHA256'],
    'wheel_sha256': os.environ['EXPECTED_WHEEL_SHA256'],
    'immutable_manifest_sha256': os.environ['EXPECTED_MANIFEST_SHA256'],
    'release_checksums_file_sha256': checksums,
    'clean_install_version': '7.0.1',
    'v700_restoration_passed': True,
    'v650_restoration_passed': True,
    'required_integrations': ['GitHub', 'Notion', 'Todoist'],
    'google_drive_initialization_role': 'forbidden',
    'provider_writes': 0,
    'verified_at': datetime.now(UTC).isoformat(),
}
Path('post-publication-evidence/V701_PUBLICATION_READBACK.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
PY
(cd post-publication-evidence && sha256sum V701_PUBLICATION_READBACK.json > SHA256SUMS && sha256sum -c SHA256SUMS)
