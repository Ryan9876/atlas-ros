#!/usr/bin/env bash
set -euo pipefail

: "${GH_TOKEN:?GH_TOKEN is required}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
: "${SOURCE_COMMIT:?SOURCE_COMMIT is required}"
: "${FINAL_SOURCE_COMMIT:?FINAL_SOURCE_COMMIT is required}"
: "${FINAL_PACKAGE_MERGE_COMMIT:?FINAL_PACKAGE_MERGE_COMMIT is required}"
: "${FINAL_ARTIFACT_ID:?FINAL_ARTIFACT_ID is required}"
: "${FINAL_ARTIFACT_DIGEST:?FINAL_ARTIFACT_DIGEST is required}"
: "${EXPECTED_SOURCE_SHA256:?EXPECTED_SOURCE_SHA256 is required}"
: "${EXPECTED_WHEEL_SHA256:?EXPECTED_WHEEL_SHA256 is required}"
: "${DECISION_URL:?DECISION_URL is required}"
: "${REVIEW_URL:?REVIEW_URL is required}"
: "${RELEASE_TAG:?RELEASE_TAG is required}"
: "${ROLLBACK_TAG:?ROLLBACK_TAG is required}"
: "${HISTORICAL_ROLLBACK_TAG:?HISTORICAL_ROLLBACK_TAG is required}"
PUBLISH="${PUBLISH:-false}"

version="$(python - <<'PY'
import tomllib
from pathlib import Path
print(tomllib.loads(Path('pyproject.toml').read_text(encoding='utf-8'))['project']['version'])
PY
)"
test "$version" = "7.0.0"
test "$(python -c 'import atlas_ros; print(atlas_ros.__version__)')" = "$version"
test "$(git rev-parse HEAD)" = "$SOURCE_COMMIT"
git merge-base --is-ancestor "$FINAL_PACKAGE_MERGE_COMMIT" HEAD

rm -rf final-artifact final-publication final-evidence release-readback rollback-v650 rollback-v620 verify-v700 verify-v650 verify-v620
mkdir -p final-artifact final-publication final-evidence

artifact_zip="final-artifact.zip"
gh api "repos/${GITHUB_REPOSITORY}/actions/artifacts/${FINAL_ARTIFACT_ID}/zip" > "$artifact_zip"
echo "${FINAL_ARTIFACT_DIGEST#sha256:}  ${artifact_zip}" | sha256sum -c -
unzip -q "$artifact_zip" -d final-artifact

publication_dir="$(find final-artifact -type d -name v700-final-publication -print -quit)"
evidence_dir="$(find final-artifact -type d -name v700-final-evidence -print -quit)"
test -n "$publication_dir"
test -n "$evidence_dir"
(cd "$publication_dir" && sha256sum -c CHECKSUMS.sha256)
(cd "$evidence_dir" && sha256sum -c FINAL_EVIDENCE_CHECKSUMS.sha256)

python - "$publication_dir/FINAL_IDENTITY.json" <<'PY'
import json, os, sys
from pathlib import Path
identity = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
assert identity['release_version'] == '7.0.0'
assert identity['final_source_commit'] == os.environ['FINAL_SOURCE_COMMIT']
assert identity['source']['sha256'] == os.environ['EXPECTED_SOURCE_SHA256']
assert identity['wheel']['sha256'] == os.environ['EXPECTED_WHEEL_SHA256']
assert identity['immediate_rollback']['version'] == '6.5.0'
assert identity['immediate_rollback']['commit'] == 'bb6d6fea70d6824c9bc6a42e63ba36cc88029260'
assert identity['historical_rollback']['version'] == '6.2.0'
assert identity['provider_writes'] == 0
PY

test "$(sha256sum "$publication_dir/atlas_ros-7.0.0.tar.gz" | awk '{print $1}')" = "$EXPECTED_SOURCE_SHA256"
test "$(sha256sum "$publication_dir/atlas_ros-7.0.0-py3-none-any.whl" | awk '{print $1}')" = "$EXPECTED_WHEEL_SHA256"
cp "$publication_dir"/* final-publication/
cp "$evidence_dir"/* final-evidence/

export SOURCE_COMMIT FINAL_SOURCE_COMMIT FINAL_PACKAGE_MERGE_COMMIT FINAL_ARTIFACT_ID FINAL_ARTIFACT_DIGEST EXPECTED_SOURCE_SHA256 EXPECTED_WHEEL_SHA256 DECISION_URL REVIEW_URL RELEASE_TAG ROLLBACK_TAG HISTORICAL_ROLLBACK_TAG PUBLISH
python - <<'PY'
import json, os
from pathlib import Path
p = Path('final-publication')
authorization = {
    'schema_version': '1.0',
    'decision': 'V4D-39',
    'decision_url': os.environ['DECISION_URL'],
    'review': 'V4V-55',
    'review_url': os.environ['REVIEW_URL'],
    'authorized_final_source_commit': os.environ['FINAL_SOURCE_COMMIT'],
    'final_package_merge_commit': os.environ['FINAL_PACKAGE_MERGE_COMMIT'],
    'publication_controller_commit': os.environ['SOURCE_COMMIT'],
    'final_artifact_id': os.environ['FINAL_ARTIFACT_ID'],
    'final_artifact_digest': os.environ['FINAL_ARTIFACT_DIGEST'].removeprefix('sha256:'),
    'final_source_sha256': os.environ['EXPECTED_SOURCE_SHA256'],
    'final_wheel_sha256': os.environ['EXPECTED_WHEEL_SHA256'],
    'release_tag': os.environ['RELEASE_TAG'],
    'immediate_rollback': os.environ['ROLLBACK_TAG'],
    'historical_rollback': os.environ['HISTORICAL_ROLLBACK_TAG'],
    'drive_retirement_authorized': False,
    'historical_deletion_authorized': False,
    'credential_actions_authorized': False,
    'integration_scope_change_authorized': False,
}
(p / 'AUTHORIZATION.json').write_text(json.dumps(authorization, indent=2, sort_keys=True) + '\n', encoding='utf-8')
identity = json.loads((p / 'FINAL_IDENTITY.json').read_text(encoding='utf-8'))
identity.update({
    'production_authorized': True,
    'publication_controller_commit': os.environ['SOURCE_COMMIT'],
    'final_package_merge_commit': os.environ['FINAL_PACKAGE_MERGE_COMMIT'],
    'promotion_decision_url': os.environ['DECISION_URL'],
    'review_record_url': os.environ['REVIEW_URL'],
    'release_tag': os.environ['RELEASE_TAG'],
    'published': False,
    'authority_activated': False,
})
(p / 'FINAL_IDENTITY.json').write_text(json.dumps(identity, indent=2, sort_keys=True) + '\n', encoding='utf-8')
manifest = f'''# Atlas ROS v7.0.0 Release Manifest\n\nStatus: exact production package authorized; immutable publication and live-authority activation pending.\n\n- Authorized final source commit: `{os.environ['FINAL_SOURCE_COMMIT']}`\n- Final package merge commit: `{os.environ['FINAL_PACKAGE_MERGE_COMMIT']}`\n- Publication controller commit: `{os.environ['SOURCE_COMMIT']}`\n- Final artifact ID: `{os.environ['FINAL_ARTIFACT_ID']}`\n- Final artifact digest: `{os.environ['FINAL_ARTIFACT_DIGEST'].removeprefix('sha256:')}`\n- Final source SHA-256: `{os.environ['EXPECTED_SOURCE_SHA256']}`\n- Final wheel SHA-256: `{os.environ['EXPECTED_WHEEL_SHA256']}`\n- Promotion decision: `V4D-39`\n- Governed validation: `V4V-55`\n- Intended immutable tag: `{os.environ['RELEASE_TAG']}`\n- Immediate immutable rollback after promotion: `{os.environ['ROLLBACK_TAG']}`\n- Historical rollback retained: `{os.environ['HISTORICAL_ROLLBACK_TAG']}`\n- Provider writes outside GitHub release publication: `0`\n- Drive retirement or deletion: `not authorized`\n\nThe final release remains inactive until immutable publication readback and live authority activation pass.\n'''
(p / 'RELEASE_MANIFEST.md').write_text(manifest, encoding='utf-8')
PY

python -m venv verify-v700
verify-v700/bin/python -m pip install --disable-pip-version-check final-publication/atlas_ros-7.0.0-py3-none-any.whl
verify-v700/bin/python -c "import atlas_ros; assert atlas_ros.__version__ == '7.0.0'"

gh release download "$ROLLBACK_TAG" --repo "$GITHUB_REPOSITORY" --pattern 'atlas_ros-6.5.0*.whl' --dir rollback-v650
gh release download "$HISTORICAL_ROLLBACK_TAG" --repo "$GITHUB_REPOSITORY" --pattern 'atlas_ros-6.2.0*.whl' --dir rollback-v620
python -m venv verify-v650
verify-v650/bin/python -m pip install --disable-pip-version-check "$(find rollback-v650 -name '*.whl' -print -quit)"
verify-v650/bin/python -c "import atlas_ros; assert atlas_ros.__version__ == '6.5.0'"
python -m venv verify-v620
verify-v620/bin/python -m pip install --disable-pip-version-check "$(find rollback-v620 -name '*.whl' -print -quit)"
verify-v620/bin/python -c "import atlas_ros; assert atlas_ros.__version__ == '6.2.0'"

(cd final-publication && find . -maxdepth 1 -type f ! -name CHECKSUMS.sha256 -print0 | sort -z | xargs -0 sha256sum > CHECKSUMS.sha256 && sha256sum -c CHECKSUMS.sha256)

python - <<'PY'
import json, os
from pathlib import Path
status = {
    'schema_version': '1.0',
    'status': 'validated_authorized' if os.environ.get('PUBLISH', 'false') != 'true' else 'published_readback_passed',
    'publication_controller_commit': os.environ['SOURCE_COMMIT'],
    'authorized_final_source_commit': os.environ['FINAL_SOURCE_COMMIT'],
    'final_artifact_id': os.environ['FINAL_ARTIFACT_ID'],
    'final_artifact_digest': os.environ['FINAL_ARTIFACT_DIGEST'].removeprefix('sha256:'),
    'release_tag': os.environ['RELEASE_TAG'],
    'immediate_rollback': os.environ['ROLLBACK_TAG'],
    'provider_writes_outside_github_release': 0,
}
Path('final-evidence/PUBLICATION_CONTROLLER_STATUS.json').write_text(json.dumps(status, indent=2, sort_keys=True) + '\n', encoding='utf-8')
PY
(cd final-evidence && find . -maxdepth 1 -type f ! -name PUBLICATION_EVIDENCE_CHECKSUMS.sha256 -print0 | sort -z | xargs -0 sha256sum > PUBLICATION_EVIDENCE_CHECKSUMS.sha256 && sha256sum -c PUBLICATION_EVIDENCE_CHECKSUMS.sha256)

if [[ "$PUBLISH" == "true" ]]; then
  ! gh release view "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" >/dev/null 2>&1
  gh release create "$RELEASE_TAG" final-publication/* \
    --repo "$GITHUB_REPOSITORY" \
    --target "$SOURCE_COMMIT" \
    --title "Atlas ROS v7.0.0" \
    --notes-file final-publication/RELEASE_NOTES.md
  git fetch --tags --force
  test "$(git rev-list -n 1 "$RELEASE_TAG")" = "$SOURCE_COMMIT"
  mkdir -p release-readback
  gh release download "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" --dir release-readback
  (cd release-readback && sha256sum -c CHECKSUMS.sha256)
  python -m venv release-readback/clean-install
  release-readback/clean-install/bin/python -m pip install --disable-pip-version-check release-readback/atlas_ros-7.0.0-py3-none-any.whl
  release-readback/clean-install/bin/python -c "import atlas_ros; assert atlas_ros.__version__ == '7.0.0'"
fi
