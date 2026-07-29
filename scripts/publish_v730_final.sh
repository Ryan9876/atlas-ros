#!/usr/bin/env bash
set -euo pipefail

: "${GH_TOKEN:?GH_TOKEN is required}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
: "${SOURCE_COMMIT:?SOURCE_COMMIT is required}"
: "${FINAL_MANIFEST_COMMIT:?FINAL_MANIFEST_COMMIT is required}"
: "${PACKAGE_SOURCE_COMMIT:?PACKAGE_SOURCE_COMMIT is required}"
: "${FINAL_ARTIFACT_ID:?FINAL_ARTIFACT_ID is required}"
: "${FINAL_ARTIFACT_DIGEST:?FINAL_ARTIFACT_DIGEST is required}"
: "${EXPECTED_SOURCE_SHA256:?EXPECTED_SOURCE_SHA256 is required}"
: "${EXPECTED_WHEEL_SHA256:?EXPECTED_WHEEL_SHA256 is required}"
: "${EXPECTED_SBOM_SHA256:?EXPECTED_SBOM_SHA256 is required}"
: "${EXPECTED_SOURCE_MANIFEST_SHA256:?EXPECTED_SOURCE_MANIFEST_SHA256 is required}"
: "${EXPECTED_PACKAGE_MANIFEST_DIGEST:?EXPECTED_PACKAGE_MANIFEST_DIGEST is required}"
: "${DECISION_URL:?DECISION_URL is required}"
: "${PACKAGE_REVIEW_URL:?PACKAGE_REVIEW_URL is required}"
: "${PREPUBLICATION_REVIEW_URL:?PREPUBLICATION_REVIEW_URL is required}"
: "${RELEASE_TAG:?RELEASE_TAG is required}"
: "${ROLLBACK_TAG:?ROLLBACK_TAG is required}"
PUBLISH="${PUBLISH:-false}"

version="$(python - <<'PY'
import tomllib
from pathlib import Path
print(tomllib.loads(Path('pyproject.toml').read_text(encoding='utf-8'))['project']['version'])
PY
)"
test "$version" = "7.3.0"
test "$(git rev-parse HEAD)" = "$SOURCE_COMMIT"
git cat-file -e "${FINAL_MANIFEST_COMMIT}^{commit}"
git cat-file -e "${PACKAGE_SOURCE_COMMIT}^{commit}"

auth_manifest_path="release/RELEASE_MANIFEST_V730.md"
git cat-file -e "${FINAL_MANIFEST_COMMIT}:${auth_manifest_path}"

rm -rf artifact-root final-publication final-evidence release-readback verify-v730 rollback-v711 rollback-clean artifact.zip
mkdir -p artifact-root final-publication final-evidence
stage() { printf '%s\n' "$1" > final-evidence/STAGE.txt; }
stage initialized

gh api "repos/${GITHUB_REPOSITORY}/actions/artifacts/${FINAL_ARTIFACT_ID}/zip" > artifact.zip
echo "${FINAL_ARTIFACT_DIGEST#sha256:}  artifact.zip" | sha256sum -c -
stage artifact-digest-verified
unzip -q artifact.zip -d artifact-root
test -d artifact-root/final-package
test -f artifact-root/exact-validation/EXACT_CANDIDATE_VALIDATION.json
(cd artifact-root/final-package && sha256sum -c SHA256SUMS)
stage nested-checksums-verified

export PACKAGE_SOURCE_COMMIT EXPECTED_SOURCE_SHA256 EXPECTED_WHEEL_SHA256 \
  EXPECTED_SBOM_SHA256 EXPECTED_SOURCE_MANIFEST_SHA256 \
  EXPECTED_PACKAGE_MANIFEST_DIGEST
python - <<'PY'
import json
import os
from pathlib import Path

root = Path('artifact-root/final-package')
identity = json.loads((root / 'FINAL_PACKAGE_IDENTITY.json').read_text(encoding='utf-8'))
validation = json.loads(Path('artifact-root/exact-validation/EXACT_CANDIDATE_VALIDATION.json').read_text(encoding='utf-8'))
assert identity['release_version'] == '7.3.0'
assert identity['status'] == 'implementation_ready_for_ryan_promotion_review'
assert identity['candidate_commit'] == os.environ['PACKAGE_SOURCE_COMMIT']
assert identity['source_sha256'] == os.environ['EXPECTED_SOURCE_SHA256']
assert identity['wheel_sha256'] == os.environ['EXPECTED_WHEEL_SHA256']
assert identity['sbom_sha256'] == os.environ['EXPECTED_SBOM_SHA256']
assert identity['source_manifest_sha256'] == os.environ['EXPECTED_SOURCE_MANIFEST_SHA256']
assert identity['manifest_digest'] == os.environ['EXPECTED_PACKAGE_MANIFEST_DIGEST']
assert identity['build_count'] == 1
assert identity['provider_writes'] == 0
assert identity['production_promotion_authorized'] is False
assert identity['final_tag_created'] is False
assert identity['final_release_published'] is False
assert identity['authority_activated'] is False
assert identity['production_notion_schema_changed'] is False
assert identity['todoist_tasks_created'] == 0
assert identity['messages_sent'] == 0
assert identity['scheduled_operations'] == 0
assert identity['records_deleted'] == 0
assert identity['credentials_changed'] is False
assert identity['integration_scope_expanded'] is False
assert validation['status'] == 'passed'
assert validation['candidate_commit'] == os.environ['PACKAGE_SOURCE_COMMIT']
assert validation['provider_writes'] == 0
PY
stage exact-package-identity-verified

cp artifact.zip final-publication/atlas-ros-v7.3.0-exact-promotion-package.zip
cp artifact-root/final-package/atlas_ros-7.3.0.tar.gz final-publication/
cp artifact-root/final-package/atlas_ros-7.3.0-py3-none-any.whl final-publication/
cp artifact-root/final-package/SBOM.spdx.json final-publication/
cp artifact-root/final-package/SOURCE_MANIFEST_FINAL.json final-publication/
cp artifact-root/final-package/FINAL_PACKAGE_IDENTITY.json final-publication/FINAL_PACKAGE_IDENTITY_PREAUTH.json
cp artifact-root/final-package/PROMOTION_INPUTS.json final-publication/
cp artifact-root/final-package/performance.json final-publication/
cp artifact-root/final-package/migration-validation.json final-publication/
cp artifact-root/final-package/validation-summary.json final-publication/
cp artifact-root/exact-validation/EXACT_CANDIDATE_VALIDATION.json final-publication/
git show "${FINAL_MANIFEST_COMMIT}:${auth_manifest_path}" > final-publication/RELEASE_MANIFEST_V730.md

export FINAL_MANIFEST_COMMIT PACKAGE_SOURCE_COMMIT FINAL_ARTIFACT_ID FINAL_ARTIFACT_DIGEST \
  DECISION_URL PACKAGE_REVIEW_URL PREPUBLICATION_REVIEW_URL RELEASE_TAG ROLLBACK_TAG PUBLISH
python - <<'PY'
import hashlib
import json
import os
from pathlib import Path
from atlas_ros.kernel.digests import sha256_digest

root = Path('final-publication')
manifest_text = (root / 'RELEASE_MANIFEST_V730.md').read_text(encoding='utf-8')
manifest_raw = hashlib.sha256(manifest_text.encode('utf-8')).hexdigest()
manifest_canonical = sha256_digest(manifest_text)
(root / 'MANIFEST_DIGESTS.json').write_text(json.dumps({
    'schema_version': '1.0',
    'manifest_path': 'release/RELEASE_MANIFEST_V730.md',
    'immutable_commit': os.environ['FINAL_MANIFEST_COMMIT'],
    'raw_sha256': manifest_raw,
    'canonical_sha256': manifest_canonical,
}, indent=2, sort_keys=True) + '\n', encoding='utf-8')

authorization = {
    'schema_version': '1.0',
    'release_version': '7.3.0',
    'authorized_package_source_commit': os.environ['PACKAGE_SOURCE_COMMIT'],
    'authorized_manifest_commit': os.environ['FINAL_MANIFEST_COMMIT'],
    'artifact_id': int(os.environ['FINAL_ARTIFACT_ID']),
    'artifact_digest': os.environ['FINAL_ARTIFACT_DIGEST'].removeprefix('sha256:'),
    'decision_url': os.environ['DECISION_URL'],
    'package_review_url': os.environ['PACKAGE_REVIEW_URL'],
    'prepublication_review_url': os.environ['PREPUBLICATION_REVIEW_URL'],
    'release_tag': os.environ['RELEASE_TAG'],
    'immediate_rollback_tag': os.environ['ROLLBACK_TAG'],
    'required_integrations': ['GitHub', 'Notion', 'Todoist'],
    'google_drive_required': False,
    'notion_additive_migration_authorized': True,
    'credential_actions_authorized': False,
    'integration_scope_change_authorized': False,
    'autonomous_execution_authorized': False,
}
(root / 'AUTHORIZATION.json').write_text(json.dumps(authorization, indent=2, sort_keys=True) + '\n', encoding='utf-8')

preauth = json.loads((root / 'FINAL_PACKAGE_IDENTITY_PREAUTH.json').read_text(encoding='utf-8'))
preauth.update({
    'status': 'published_authority_activation_pending' if os.environ.get('PUBLISH') == 'true' else 'authorized_publication_rehearsed',
    'production_promotion_authorized': True,
    'final_tag_created': os.environ.get('PUBLISH') == 'true',
    'final_release_published': os.environ.get('PUBLISH') == 'true',
    'authority_activated': False,
    'production_notion_schema_changed': False,
    'manifest_commit': os.environ['FINAL_MANIFEST_COMMIT'],
    'manifest_raw_sha256': manifest_raw,
    'manifest_canonical_sha256': manifest_canonical,
    'publication_controller_commit': os.environ['SOURCE_COMMIT'],
    'promotion_decision_url': os.environ['DECISION_URL'],
})
(root / 'FINAL_IDENTITY.json').write_text(json.dumps(preauth, indent=2, sort_keys=True) + '\n', encoding='utf-8')

notes = '''# Atlas ROS v7.3.0

Atlas ROS v7.3.0 adds evidence-backed Operational Awareness and explicit command-driven work lifecycle planning. It provides continuous work-state intelligence, delegation and commitment tracking, exception-based operating briefs, execution context and resumption memory, work-graph hygiene, and exact idempotent lifecycle plans for attended authorization.

Production activation is separate from immutable publication. Until canonical GitHub and Notion authority activation and final readback complete, Atlas ROS v7.1.1 remains Active.

Immediate rollback after activation: Atlas ROS v7.1.1. Required production integrations remain exactly GitHub, Notion, and Todoist. Google Drive remains optional and non-authoritative.
'''
(root / 'RELEASE_NOTES.md').write_text(notes, encoding='utf-8')
PY
stage publication-assets-assembled

python -m venv verify-v730
verify-v730/bin/python -m pip install --disable-pip-version-check final-publication/atlas_ros-7.3.0-py3-none-any.whl
verify-v730/bin/python -c "import atlas_ros; assert atlas_ros.__version__ == '7.3.0'"
verify-v730/bin/atlas status --json > final-evidence/v730-status.json
verify-v730/bin/atlas verify --json > final-evidence/v730-verify.json
stage candidate-clean-install-passed

mkdir -p rollback-v711
gh release download "$ROLLBACK_TAG" --repo "$GITHUB_REPOSITORY" --dir rollback-v711
(cd rollback-v711 && sha256sum -c CHECKSUMS.sha256)
rollback_wheel="$(find rollback-v711 -name 'atlas_ros-7.1.1*.whl' -print -quit)"
test -n "$rollback_wheel"
python -m venv rollback-clean
rollback-clean/bin/python -m pip install --disable-pip-version-check "$rollback_wheel"
rollback-clean/bin/python -c "import atlas_ros; assert atlas_ros.__version__ == '7.1.1'"
rollback-clean/bin/atlas status --json > final-evidence/rollback-v711-status.json
stage rollback-restoration-passed

(cd final-publication && find . -maxdepth 1 -type f ! -name CHECKSUMS.sha256 -print0 | sort -z | xargs -0 sha256sum > CHECKSUMS.sha256)
(cd final-publication && sha256sum -c CHECKSUMS.sha256)
stage publication-checksums-passed

if [[ "$PUBLISH" == "true" ]]; then
  ! gh release view "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" >/dev/null 2>&1
  test -z "$(git ls-remote --tags origin "refs/tags/${RELEASE_TAG}")"
  gh release create "$RELEASE_TAG" final-publication/* \
    --repo "$GITHUB_REPOSITORY" \
    --target "$FINAL_MANIFEST_COMMIT" \
    --title "Atlas ROS v7.3.0" \
    --notes-file final-publication/RELEASE_NOTES.md
  git fetch --tags --force
  test "$(git rev-list -n 1 "$RELEASE_TAG")" = "$FINAL_MANIFEST_COMMIT"
  mkdir -p release-readback
  gh release view "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" \
    --json tagName,targetCommitish,isDraft,isPrerelease,url > release-readback/release.json
  gh release download "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" --dir release-readback/assets
  (cd release-readback/assets && sha256sum -c CHECKSUMS.sha256)
  release_wheel="$(find release-readback/assets -name 'atlas_ros-7.3.0*.whl' -print -quit)"
  test -n "$release_wheel"
  python -m venv release-readback-clean
  release-readback-clean/bin/python -m pip install --disable-pip-version-check "$release_wheel"
  release-readback-clean/bin/python -c "import atlas_ros; assert atlas_ros.__version__ == '7.3.0'"
  release-readback-clean/bin/atlas status --json > release-readback/status.json
  release-readback-clean/bin/atlas verify --json > release-readback/verify.json
  python - <<'PY'
import json
import os
from pathlib import Path
release = json.loads(Path('release-readback/release.json').read_text(encoding='utf-8'))
assert release['tagName'] == os.environ['RELEASE_TAG']
assert release['targetCommitish'] == os.environ['FINAL_MANIFEST_COMMIT']
assert release['isDraft'] is False
assert release['isPrerelease'] is False
Path('release-readback/PUBLICATION_READBACK.json').write_text(json.dumps({
    'schema_version': '1.0',
    'status': 'passed',
    'release_version': '7.3.0',
    'tag': os.environ['RELEASE_TAG'],
    'tag_target': os.environ['FINAL_MANIFEST_COMMIT'],
    'package_source_commit': os.environ['PACKAGE_SOURCE_COMMIT'],
    'artifact_id': int(os.environ['FINAL_ARTIFACT_ID']),
    'provider_writes_outside_github_release': 0,
    'authority_activated': False,
    'notion_schema_changed': False,
}, indent=2, sort_keys=True) + '\n', encoding='utf-8')
PY
  stage immutable-publication-readback-passed
else
  ! gh release view "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" >/dev/null 2>&1
  test -z "$(git ls-remote --tags origin "refs/tags/${RELEASE_TAG}")"
  stage authorized-publication-rehearsal-passed
fi
