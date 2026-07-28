#!/usr/bin/env bash
set -euo pipefail

: "${GH_TOKEN:?GH_TOKEN is required}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
: "${SOURCE_COMMIT:?SOURCE_COMMIT is required}"
: "${FINAL_SOURCE_COMMIT:?FINAL_SOURCE_COMMIT is required}"
: "${FINAL_ARTIFACT_ID:?FINAL_ARTIFACT_ID is required}"
: "${FINAL_ARTIFACT_DIGEST:?FINAL_ARTIFACT_DIGEST is required}"
: "${EXPECTED_SOURCE_SHA256:?EXPECTED_SOURCE_SHA256 is required}"
: "${EXPECTED_WHEEL_SHA256:?EXPECTED_WHEEL_SHA256 is required}"
: "${EXPECTED_MANIFEST_CANONICAL_SHA256:?EXPECTED_MANIFEST_CANONICAL_SHA256 is required}"
: "${EXPECTED_MANIFEST_RAW_SHA256:?EXPECTED_MANIFEST_RAW_SHA256 is required}"
: "${EXPECTED_SBOM_SHA256:?EXPECTED_SBOM_SHA256 is required}"
: "${EXPECTED_SOURCE_MANIFEST_SHA256:?EXPECTED_SOURCE_MANIFEST_SHA256 is required}"
: "${EXPECTED_STAGED_AUTHORITY_SHA256:?EXPECTED_STAGED_AUTHORITY_SHA256 is required}"
: "${EXPECTED_STAGED_INDEX_SHA256:?EXPECTED_STAGED_INDEX_SHA256 is required}"
: "${DECISION_URL:?DECISION_URL is required}"
: "${PACKAGE_REVIEW_URL:?PACKAGE_REVIEW_URL is required}"
: "${PREPUBLICATION_REVIEW_URL:?PREPUBLICATION_REVIEW_URL is required}"
: "${RELEASE_TAG:?RELEASE_TAG is required}"
: "${ROLLBACK_TAG:?ROLLBACK_TAG is required}"
: "${HISTORICAL_ROLLBACK_TAG_1:?HISTORICAL_ROLLBACK_TAG_1 is required}"
: "${HISTORICAL_ROLLBACK_TAG_2:?HISTORICAL_ROLLBACK_TAG_2 is required}"
PUBLISH="${PUBLISH:-false}"

version="$(python - <<'PY'
import tomllib
from pathlib import Path
print(tomllib.loads(Path('pyproject.toml').read_text(encoding='utf-8'))['project']['version'])
PY
)"
test "$version" = "7.1.0"
test "$(git rev-parse HEAD)" = "$SOURCE_COMMIT"
git cat-file -e "${FINAL_SOURCE_COMMIT}^{commit}"

rm -rf final-artifact final-publication final-evidence release-readback \
  rollback-v701 rollback-v650 rollback-v620 verify-v710 verify-v701 verify-v650 verify-v620
mkdir -p final-artifact final-publication final-evidence
stage() { printf '%s\n' "$1" > final-evidence/STAGE.txt; }
stage initialized

artifact_zip="final-artifact.zip"
gh api "repos/${GITHUB_REPOSITORY}/actions/artifacts/${FINAL_ARTIFACT_ID}/zip" > "$artifact_zip"
echo "${FINAL_ARTIFACT_DIGEST#sha256:}  ${artifact_zip}" | sha256sum -c -
stage artifact-digest-verified
unzip -q "$artifact_zip" -d final-artifact
(cd final-artifact && sha256sum -c SHA256SUMS)
stage nested-checksums-verified

export FINAL_SOURCE_COMMIT EXPECTED_SOURCE_SHA256 EXPECTED_WHEEL_SHA256 \
  EXPECTED_MANIFEST_CANONICAL_SHA256 EXPECTED_MANIFEST_RAW_SHA256 \
  EXPECTED_SBOM_SHA256 EXPECTED_SOURCE_MANIFEST_SHA256 \
  EXPECTED_STAGED_AUTHORITY_SHA256 EXPECTED_STAGED_INDEX_SHA256
python - <<'PY'
import hashlib
import json
import os
from pathlib import Path
from atlas_ros.contracts.digests import sha256_digest

root = Path('final-artifact')
identity = json.loads((root / 'FINAL_PACKAGE_IDENTITY.json').read_text(encoding='utf-8'))
assert identity['status'] == 'final_package_validated_not_authorized'
assert identity['release_version'] == '7.1.0'
assert identity['source_commit'] == os.environ['FINAL_SOURCE_COMMIT']
assert identity['source_sha256'] == os.environ['EXPECTED_SOURCE_SHA256']
assert identity['wheel_sha256'] == os.environ['EXPECTED_WHEEL_SHA256']
assert identity['manifest_canonical_sha256'] == os.environ['EXPECTED_MANIFEST_CANONICAL_SHA256']
assert identity['manifest_raw_sha256'] == os.environ['EXPECTED_MANIFEST_RAW_SHA256']
assert identity['sbom_sha256'] == os.environ['EXPECTED_SBOM_SHA256']
assert identity['source_manifest_sha256'] == os.environ['EXPECTED_SOURCE_MANIFEST_SHA256']
assert identity['staged_authority_sha256'] == os.environ['EXPECTED_STAGED_AUTHORITY_SHA256']
assert identity['staged_release_index_sha256'] == os.environ['EXPECTED_STAGED_INDEX_SHA256']
assert identity['active_production_release'] == '7.0.1'
assert identity['immediate_rollback_after_promotion'] == '7.0.1'
assert identity['historical_rollbacks'] == ['6.5.0', '6.2.0']
assert identity['required_integrations'] == ['GitHub', 'Notion', 'Todoist']
assert identity['optional_integrations'] == ['Google Drive']
assert identity['provider_writes'] == 0
assert identity['destructive_actions'] == 0
assert identity['production_authorized'] is False
assert identity['published'] is False
assert identity['authority_activated'] is False
checks = {
    'atlas_ros-7.1.0.tar.gz': os.environ['EXPECTED_SOURCE_SHA256'],
    'atlas_ros-7.1.0-py3-none-any.whl': os.environ['EXPECTED_WHEEL_SHA256'],
    'SBOM.spdx.json': os.environ['EXPECTED_SBOM_SHA256'],
    'SOURCE_MANIFEST_FINAL.json': os.environ['EXPECTED_SOURCE_MANIFEST_SHA256'],
}
for name, expected in checks.items():
    actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
    assert actual == expected, (name, actual, expected)
assert sha256_digest((root / 'staged-authority/AUTHORITY.json').read_text(encoding='utf-8')) == os.environ['EXPECTED_STAGED_AUTHORITY_SHA256']
assert sha256_digest((root / 'staged-authority/RELEASE_INDEX.md').read_text(encoding='utf-8')) == os.environ['EXPECTED_STAGED_INDEX_SHA256']
PY
stage exact-identity-verified

cp "$artifact_zip" final-publication/atlas-ros-v7.1.0-final-package.zip
cp final-artifact/atlas_ros-7.1.0.tar.gz final-publication/
cp final-artifact/atlas_ros-7.1.0-py3-none-any.whl final-publication/
cp final-artifact/SOURCE_MANIFEST_FINAL.json final-publication/
cp final-artifact/SBOM.spdx.json final-publication/
cp final-artifact/PRODUCTION_MANIFEST_VALIDATION.json final-publication/
cp final-artifact/runtime-status.json final-publication/
cp final-artifact/runtime-verify.json final-publication/
cp final-artifact/startup-comparison.json final-publication/
cp final-artifact/FINAL_PACKAGE_IDENTITY.json final-publication/FINAL_PACKAGE_IDENTITY_PREAUTH.json
cp final-artifact/PROMOTION_INPUTS.json final-publication/
git show "${FINAL_SOURCE_COMMIT}:release/RELEASE_MANIFEST_V710.md" > final-publication/RELEASE_MANIFEST_V710.md

test "$(sha256sum final-publication/RELEASE_MANIFEST_V710.md | awk '{print $1}')" = "$EXPECTED_MANIFEST_RAW_SHA256"
manifest_canonical="$(python - <<'PY'
from pathlib import Path
from atlas_ros.contracts.digests import sha256_digest
print(sha256_digest(Path('final-publication/RELEASE_MANIFEST_V710.md').read_text(encoding='utf-8')))
PY
)"
test "$manifest_canonical" = "$EXPECTED_MANIFEST_CANONICAL_SHA256"
stage exact-files-verified

export SOURCE_COMMIT FINAL_ARTIFACT_ID FINAL_ARTIFACT_DIGEST DECISION_URL \
  PACKAGE_REVIEW_URL PREPUBLICATION_REVIEW_URL RELEASE_TAG ROLLBACK_TAG \
  HISTORICAL_ROLLBACK_TAG_1 HISTORICAL_ROLLBACK_TAG_2 PUBLISH
python - <<'PY'
import json
import os
from pathlib import Path

root = Path('final-publication')
publish = os.environ.get('PUBLISH', 'false') == 'true'
identity = json.loads((root / 'FINAL_PACKAGE_IDENTITY_PREAUTH.json').read_text(encoding='utf-8'))
authorization = {
    'schema_version': '1.0',
    'decision': 'V4D-46',
    'decision_url': os.environ['DECISION_URL'],
    'package_review': 'V4V-66',
    'package_review_url': os.environ['PACKAGE_REVIEW_URL'],
    'prepublication_review': 'V4V-67',
    'prepublication_review_url': os.environ['PREPUBLICATION_REVIEW_URL'],
    'authorized_final_source_commit': os.environ['FINAL_SOURCE_COMMIT'],
    'publication_controller_commit': os.environ['SOURCE_COMMIT'],
    'final_artifact_id': os.environ['FINAL_ARTIFACT_ID'],
    'final_artifact_digest': os.environ['FINAL_ARTIFACT_DIGEST'].removeprefix('sha256:'),
    'release_tag': os.environ['RELEASE_TAG'],
    'immediate_rollback': os.environ['ROLLBACK_TAG'],
    'historical_rollbacks': [os.environ['HISTORICAL_ROLLBACK_TAG_1'], os.environ['HISTORICAL_ROLLBACK_TAG_2']],
    'required_integrations': ['GitHub', 'Notion', 'Todoist'],
    'google_drive_required': False,
    'google_drive_read_during_initialization': False,
    'google_drive_deletion_authorized': False,
    'google_drive_retirement_authorized': False,
    'historical_deletion_authorized': False,
    'credential_actions_authorized': False,
    'integration_scope_change_authorized': False,
    'autonomous_execution_authorized': False,
}
(root / 'AUTHORIZATION.json').write_text(json.dumps(authorization, indent=2, sort_keys=True) + '\n', encoding='utf-8')
identity.update({
    'status': 'published_authority_activation_pending' if publish else 'authorized_publication_rehearsed',
    'production_authorized': True,
    'published': publish,
    'authority_activated': False,
    'publication_controller_commit': os.environ['SOURCE_COMMIT'],
    'promotion_decision': 'V4D-46',
    'promotion_decision_url': os.environ['DECISION_URL'],
    'package_review': 'V4V-66',
    'prepublication_review': 'V4V-67',
    'release_tag': os.environ['RELEASE_TAG'],
})
(root / 'FINAL_IDENTITY.json').write_text(json.dumps(identity, indent=2, sort_keys=True) + '\n', encoding='utf-8')
notes = '''# Atlas ROS v7.1.0\n\nAtlas ROS v7.1.0 is the authorized immutable release package for the v7 consolidation work. It preserves the GitHub-first authority model, attended execution boundaries, and exact required integration set of GitHub, Notion, and Todoist.\n\nPublication does not itself activate production authority. Atlas ROS v7.0.1 remains Active until independent publication readback succeeds and matching GitHub and Notion authority activation is completed.\n\nImmediate rollback after activation: Atlas ROS v7.0.1. Historical rollbacks retained: v6.5.0 and v6.2.0. Google Drive remains optional, non-authoritative, and outside initialization.\n'''
(root / 'RELEASE_NOTES.md').write_text(notes, encoding='utf-8')
manifest = f'''# Atlas ROS v7.1.0 Production Publication Manifest\n\nStatus: {'immutable publication completed; live authority activation pending' if publish else 'exact package authorized; immutable publication pending'}.\n\n- Authorized source commit: `{os.environ['FINAL_SOURCE_COMMIT']}`\n- Publication controller commit: `{os.environ['SOURCE_COMMIT']}`\n- Final artifact ID: `{os.environ['FINAL_ARTIFACT_ID']}`\n- Final artifact SHA-256: `{os.environ['FINAL_ARTIFACT_DIGEST'].removeprefix('sha256:')}`\n- Source SHA-256: `{os.environ['EXPECTED_SOURCE_SHA256']}`\n- Wheel SHA-256: `{os.environ['EXPECTED_WHEEL_SHA256']}`\n- Immutable manifest path: `release/RELEASE_MANIFEST_V710.md`\n- Immutable manifest canonical SHA-256: `{os.environ['EXPECTED_MANIFEST_CANONICAL_SHA256']}`\n- Promotion decision: `V4D-46`\n- Governed package validation: `V4V-66`\n- Prepublication validation: `V4V-67`\n- Immutable tag: `{os.environ['RELEASE_TAG']}`\n- Immediate rollback after activation: `{os.environ['ROLLBACK_TAG']}`\n- Historical rollbacks: `{os.environ['HISTORICAL_ROLLBACK_TAG_1']}`, `{os.environ['HISTORICAL_ROLLBACK_TAG_2']}`\n- Required integrations: `GitHub`, `Notion`, `Todoist`\n- Google Drive: optional, non-authoritative, not read during initialization\n\nThe release is not Active until independent publication readback and matching GitHub and Notion authority activation pass.\n'''
(root / 'RELEASE_MANIFEST.md').write_text(manifest, encoding='utf-8')
PY

python -m venv verify-v710
verify-v710/bin/python -m pip install --disable-pip-version-check final-publication/atlas_ros-7.1.0-py3-none-any.whl
verify-v710/bin/python -c "import atlas_ros; assert atlas_ros.__version__ == '7.1.0'"
stage v710-clean-install-passed

for pair in "v7.0.1 7.0.1 rollback-v701 verify-v701" "v6.5.0 6.5.0 rollback-v650 verify-v650" "v6.2.0 6.2.0 rollback-v620 verify-v620"; do
  set -- $pair
  tag="$1"; expected_version="$2"; download_dir="$3"; env_dir="$4"
  mkdir -p "$download_dir"
  gh release download "$tag" --repo "$GITHUB_REPOSITORY" --pattern "atlas_ros-${expected_version}*.whl" --dir "$download_dir"
  wheel="$(find "$download_dir" -name '*.whl' -print -quit)"
  test -n "$wheel"
  python -m venv "$env_dir"
  "$env_dir/bin/python" -m pip install --disable-pip-version-check "$wheel"
  "$env_dir/bin/python" -c "import atlas_ros; assert atlas_ros.__version__ == '${expected_version}'"
done
stage rollback-restoration-passed

(cd final-publication && find . -maxdepth 1 -type f ! -name CHECKSUMS.sha256 -print0 | sort -z | xargs -0 sha256sum > CHECKSUMS.sha256 && sha256sum -c CHECKSUMS.sha256)
stage publication-checksums-passed

if [[ "$PUBLISH" == "true" ]]; then
  ! gh release view "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" >/dev/null 2>&1
  test -z "$(git ls-remote --tags origin "refs/tags/${RELEASE_TAG}")"
  gh release create "$RELEASE_TAG" final-publication/* \
    --repo "$GITHUB_REPOSITORY" \
    --target "$FINAL_SOURCE_COMMIT" \
    --title "Atlas ROS v7.1.0" \
    --notes-file final-publication/RELEASE_NOTES.md
  git fetch --tags --force
  test "$(git rev-list -n 1 "$RELEASE_TAG")" = "$FINAL_SOURCE_COMMIT"
  gh release view "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" \
    --json tagName,targetCommitish,isDraft,isPrerelease,url > final-evidence/RELEASE_METADATA.json
  python - <<'PY'
import json
from pathlib import Path
meta = json.loads(Path('final-evidence/RELEASE_METADATA.json').read_text(encoding='utf-8'))
assert meta['tagName'] == 'v7.1.0'
assert meta['isDraft'] is False
assert meta['isPrerelease'] is False
PY
  mkdir -p release-readback
  gh release download "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" --dir release-readback
  (cd release-readback && sha256sum -c CHECKSUMS.sha256)
  test "$(sha256sum release-readback/atlas-ros-v7.1.0-final-package.zip | awk '{print $1}')" = "${FINAL_ARTIFACT_DIGEST#sha256:}"
  test "$(sha256sum release-readback/atlas_ros-7.1.0.tar.gz | awk '{print $1}')" = "$EXPECTED_SOURCE_SHA256"
  test "$(sha256sum release-readback/atlas_ros-7.1.0-py3-none-any.whl | awk '{print $1}')" = "$EXPECTED_WHEEL_SHA256"
  test "$(sha256sum release-readback/RELEASE_MANIFEST_V710.md | awk '{print $1}')" = "$EXPECTED_MANIFEST_RAW_SHA256"
  python -m venv release-readback/clean-install
  release-readback/clean-install/bin/python -m pip install --disable-pip-version-check release-readback/atlas_ros-7.1.0-py3-none-any.whl
  release-readback/clean-install/bin/python -c "import atlas_ros; assert atlas_ros.__version__ == '7.1.0'"
  stage publication-readback-passed
fi

python - <<'PY'
import json
import os
from pathlib import Path
status = {
    'schema_version': '1.0',
    'status': 'published_initial_readback_passed' if os.environ.get('PUBLISH') == 'true' else 'authorized_rehearsal_passed',
    'publication_controller_commit': os.environ['SOURCE_COMMIT'],
    'authorized_source_commit': os.environ['FINAL_SOURCE_COMMIT'],
    'final_artifact_id': os.environ['FINAL_ARTIFACT_ID'],
    'final_artifact_digest': os.environ['FINAL_ARTIFACT_DIGEST'].removeprefix('sha256:'),
    'release_tag': os.environ['RELEASE_TAG'],
    'immediate_rollback': os.environ['ROLLBACK_TAG'],
    'historical_rollbacks': [os.environ['HISTORICAL_ROLLBACK_TAG_1'], os.environ['HISTORICAL_ROLLBACK_TAG_2']],
    'required_integrations': ['GitHub', 'Notion', 'Todoist'],
    'google_drive_required': False,
    'authority_activated': False,
    'provider_writes_outside_github_release': 0,
}
Path('final-evidence/PUBLICATION_CONTROLLER_STATUS.json').write_text(json.dumps(status, indent=2, sort_keys=True) + '\n', encoding='utf-8')
PY
(cd final-evidence && find . -type f ! -name PUBLICATION_EVIDENCE_CHECKSUMS.sha256 -print0 | sort -z | xargs -0 sha256sum > PUBLICATION_EVIDENCE_CHECKSUMS.sha256 && sha256sum -c PUBLICATION_EVIDENCE_CHECKSUMS.sha256)
stage complete
