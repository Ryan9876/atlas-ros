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
: "${EXPECTED_EVIDENCE_PACKAGE_SHA256:?EXPECTED_EVIDENCE_PACKAGE_SHA256 is required}"
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
test "$version" = "7.4.0"
test "$(git rev-parse HEAD)" = "$SOURCE_COMMIT"
git cat-file -e "${FINAL_MANIFEST_COMMIT}^{commit}"
git cat-file -e "${PACKAGE_SOURCE_COMMIT}^{commit}"

manifest_path="release/RELEASE_MANIFEST_V740.md"
git cat-file -e "${FINAL_MANIFEST_COMMIT}:${manifest_path}"

rm -rf artifact-root final-publication final-evidence release-readback verify-v740 rollback-v730 rollback-clean artifact.zip
mkdir -p artifact-root final-publication final-evidence
stage() { printf '%s\n' "$1" > final-evidence/STAGE.txt; }
stage initialized

gh api "repos/${GITHUB_REPOSITORY}/actions/artifacts/${FINAL_ARTIFACT_ID}/zip" > artifact.zip
echo "${FINAL_ARTIFACT_DIGEST#sha256:}  artifact.zip" | sha256sum -c -
stage artifact-digest-verified
unzip -q artifact.zip -d artifact-root
(cd artifact-root && sha256sum -c build/NESTED_CHECKSUMS.sha256)
stage nested-checksums-verified

export PACKAGE_SOURCE_COMMIT EXPECTED_SOURCE_SHA256 EXPECTED_WHEEL_SHA256 \
  EXPECTED_SBOM_SHA256 EXPECTED_SOURCE_MANIFEST_SHA256 \
  EXPECTED_EVIDENCE_PACKAGE_SHA256
python - <<'PY'
import json
import os
from pathlib import Path
root = Path('artifact-root')
assert (root / 'build/SOURCE_COMMIT.txt').read_text().strip() == os.environ['PACKAGE_SOURCE_COMMIT']
assert (root / 'build/BUILD_COUNT.txt').read_text().strip() == '1'
controller = json.loads((root / 'build/FINAL_CONTROLLER.json').read_text())
receipt = json.loads((root / 'build/v740-validation-receipt.json').read_text())
assert controller['status'] == 'passed'
assert controller['candidate_version'] == '7.4.0'
assert controller['candidate_commit'] == os.environ['PACKAGE_SOURCE_COMMIT']
assert controller['package_build_count'] == 1
assert controller['provider_writes'] == 0
assert controller['release_publications'] == 0
assert controller['authority_changes'] == 0
assert controller['production_schema_migrations'] == 0
assert receipt['candidate_freeze_permitted'] is True
assert receipt['checks_failed'] == []
assert receipt['provider_writes'] == 0
checks = (root / 'build/CHECKSUMS.sha256').read_text()
assert os.environ['EXPECTED_SOURCE_SHA256'] in checks
assert os.environ['EXPECTED_WHEEL_SHA256'] in checks
evidence = (root / 'build/EVIDENCE_CHECKSUMS.sha256').read_text()
assert os.environ['EXPECTED_SBOM_SHA256'] in evidence
assert os.environ['EXPECTED_SOURCE_MANIFEST_SHA256'] in evidence
line = (root / 'build/EVIDENCE_PACKAGE.sha256').read_text().split()[0]
assert line == os.environ['EXPECTED_EVIDENCE_PACKAGE_SHA256']
PY
stage exact-package-identity-verified

cp artifact.zip final-publication/atlas-ros-v7.4.0-exact-promotion-package.zip
cp artifact-root/dist/atlas_ros-7.4.0.tar.gz final-publication/
cp artifact-root/dist/atlas_ros-7.4.0-py3-none-any.whl final-publication/
cp artifact-root/build/SBOM.spdx.json final-publication/
cp artifact-root/build/SOURCE_MANIFEST.sha256 final-publication/
cp artifact-root/build/v740-evidence.tar.gz final-publication/
cp artifact-root/build/FINAL_CONTROLLER.json final-publication/FINAL_CONTROLLER_PREAUTH.json
cp artifact-root/build/v740-validation-receipt.json final-publication/
cp artifact-root/build/PERFORMANCE.json final-publication/
cp artifact-root/build/MANUAL_FALLBACK.json final-publication/
cp artifact-root/build/v740-secret-scan.json final-publication/
cp artifact-root/build/pip-audit-pypi.json final-publication/
cp artifact-root/build/pip-audit-osv.json final-publication/
git show "${FINAL_MANIFEST_COMMIT}:${manifest_path}" > final-publication/RELEASE_MANIFEST_V740.md

export FINAL_MANIFEST_COMMIT PACKAGE_SOURCE_COMMIT FINAL_ARTIFACT_ID FINAL_ARTIFACT_DIGEST \
  DECISION_URL PACKAGE_REVIEW_URL PREPUBLICATION_REVIEW_URL RELEASE_TAG ROLLBACK_TAG PUBLISH SOURCE_COMMIT
python - <<'PY'
import hashlib
import json
import os
from pathlib import Path
from atlas_ros.kernel.digests import sha256_digest
root = Path('final-publication')
manifest_text = (root / 'RELEASE_MANIFEST_V740.md').read_text(encoding='utf-8')
manifest_raw = hashlib.sha256(manifest_text.encode('utf-8')).hexdigest()
manifest_canonical = sha256_digest(manifest_text)
(root / 'MANIFEST_DIGESTS.json').write_text(json.dumps({
    'schema_version': '1.0',
    'manifest_path': 'release/RELEASE_MANIFEST_V740.md',
    'immutable_commit': os.environ['FINAL_MANIFEST_COMMIT'],
    'raw_sha256': manifest_raw,
    'canonical_sha256': manifest_canonical,
}, indent=2, sort_keys=True) + '\n')
(root / 'AUTHORIZATION.json').write_text(json.dumps({
    'schema_version': '1.0',
    'release_version': '7.4.0',
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
    'notion_schema_migration_authorized': False,
    'credential_actions_authorized': False,
    'integration_scope_change_authorized': False,
    'autonomous_execution_authorized': False,
}, indent=2, sort_keys=True) + '\n')
preauth = json.loads((root / 'FINAL_CONTROLLER_PREAUTH.json').read_text())
identity = {
    **preauth,
    'schema_version': 'v740-final-identity-v1',
    'status': 'published_authority_activation_pending' if os.environ['PUBLISH'] == 'true' else 'authorized_publication_rehearsed',
    'production_promotion_authorized': True,
    'final_tag_created': os.environ['PUBLISH'] == 'true',
    'final_release_published': os.environ['PUBLISH'] == 'true',
    'authority_activated': False,
    'manifest_commit': os.environ['FINAL_MANIFEST_COMMIT'],
    'manifest_raw_sha256': manifest_raw,
    'manifest_canonical_sha256': manifest_canonical,
    'publication_controller_commit': os.environ['SOURCE_COMMIT'],
    'promotion_decision_url': os.environ['DECISION_URL'],
}
(root / 'FINAL_IDENTITY.json').write_text(json.dumps(identity, indent=2, sort_keys=True) + '\n')
(root / 'RELEASE_NOTES.md').write_text('''# Atlas ROS v7.4.0\n\nAtlas ROS v7.4.0 introduces the Feature Delivery Acceleration Foundation: versioned feature contracts, canonical development validation tiers, deterministic receipts, shadow-only impact analysis, runtime/tooling isolation, declarative fixtures and workflows, lean draft CI, build-once packaging, and documented manual fallback.\n\nProduction activation is separate from immutable publication. Until canonical GitHub and Notion authority activation and final readback complete, Atlas ROS v7.3.0 remains Active.\n\nImmediate rollback after activation: Atlas ROS v7.3.0. Required production integrations remain exactly GitHub, Notion, and Todoist. Google Drive remains optional and non-authoritative.\n''')
PY
stage publication-assets-assembled

python -m venv verify-v740
verify-v740/bin/python -m pip install --disable-pip-version-check final-publication/atlas_ros-7.4.0-py3-none-any.whl
verify-v740/bin/python -c "import atlas_ros; assert atlas_ros.__version__ == '7.4.0'"
verify-v740/bin/atlas status --json > final-evidence/v740-status.json
verify-v740/bin/atlas verify --json > final-evidence/v740-verify.json
verify-v740/bin/atlas-dev explain-impact unknown.file > final-evidence/v740-impact.json
stage candidate-clean-install-passed

mkdir -p rollback-v730
gh release download "$ROLLBACK_TAG" --repo "$GITHUB_REPOSITORY" --dir rollback-v730
(cd rollback-v730 && sha256sum -c CHECKSUMS.sha256)
rollback_wheel="$(find rollback-v730 -name 'atlas_ros-7.3.0*.whl' -print -quit)"
test -n "$rollback_wheel"
python -m venv rollback-clean
rollback-clean/bin/python -m pip install --disable-pip-version-check "$rollback_wheel"
rollback-clean/bin/python -c "import atlas_ros; assert atlas_ros.__version__ == '7.3.0'"
rollback-clean/bin/atlas status --json > final-evidence/rollback-v730-status.json
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
    --title "Atlas ROS v7.4.0" \
    --notes-file final-publication/RELEASE_NOTES.md
  git fetch --tags --force
  test "$(git rev-list -n 1 "$RELEASE_TAG")" = "$FINAL_MANIFEST_COMMIT"
  mkdir -p release-readback/assets
  gh release view "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" \
    --json tagName,targetCommitish,isDraft,isPrerelease,url > release-readback/release.json
  gh release download "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" --dir release-readback/assets
  (cd release-readback/assets && sha256sum -c CHECKSUMS.sha256)
  release_wheel="$(find release-readback/assets -name 'atlas_ros-7.4.0*.whl' -print -quit)"
  test -n "$release_wheel"
  python -m venv release-readback-clean
  release-readback-clean/bin/python -m pip install --disable-pip-version-check "$release_wheel"
  release-readback-clean/bin/python -c "import atlas_ros; assert atlas_ros.__version__ == '7.4.0'"
  release-readback-clean/bin/atlas status --json > release-readback/status.json
  release-readback-clean/bin/atlas verify --json > release-readback/verify.json
  python - <<'PY'
import json
import os
from pathlib import Path
release = json.loads(Path('release-readback/release.json').read_text())
assert release['tagName'] == os.environ['RELEASE_TAG']
assert release['targetCommitish'] == os.environ['FINAL_MANIFEST_COMMIT']
assert release['isDraft'] is False
assert release['isPrerelease'] is False
Path('release-readback/PUBLICATION_READBACK.json').write_text(json.dumps({
    'schema_version': '1.0',
    'status': 'passed',
    'release_version': '7.4.0',
    'tag': os.environ['RELEASE_TAG'],
    'tag_target': os.environ['FINAL_MANIFEST_COMMIT'],
    'package_source_commit': os.environ['PACKAGE_SOURCE_COMMIT'],
    'artifact_id': int(os.environ['FINAL_ARTIFACT_ID']),
    'provider_writes_outside_github_release': 0,
    'authority_activated': False,
    'notion_schema_changed': False,
}, indent=2, sort_keys=True) + '\n')
PY
  stage immutable-publication-readback-passed
else
  ! gh release view "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" >/dev/null 2>&1
  test -z "$(git ls-remote --tags origin "refs/tags/${RELEASE_TAG}")"
  stage authorized-publication-rehearsal-passed
fi
