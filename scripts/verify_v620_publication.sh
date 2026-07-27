#!/usr/bin/env bash
set -euo pipefail

: "${GH_TOKEN:?GH_TOKEN is required}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
RELEASE_TAG="v6.2.0"
EXPECTED_SOURCE="863d5ddf9ebd4723200166cf31c7acd93ebec54f"

rm -rf publication-readback publication-verification publication-wheel
mkdir -p publication-readback publication-verification

gh release view "$RELEASE_TAG" \
  --repo "$GITHUB_REPOSITORY" \
  --json tagName,targetCommitish,isDraft,isPrerelease,url,createdAt,publishedAt \
  > publication-verification/RELEASE_METADATA.json
python - <<'PY'
import json
from pathlib import Path
metadata = json.loads(
    Path('publication-verification/RELEASE_METADATA.json').read_text(encoding='utf-8')
)
assert metadata['tagName'] == 'v6.2.0'
assert metadata['targetCommitish'] == '863d5ddf9ebd4723200166cf31c7acd93ebec54f'
assert metadata['isDraft'] is False
assert metadata['isPrerelease'] is False
PY

gh release download "$RELEASE_TAG" \
  --repo "$GITHUB_REPOSITORY" \
  --dir publication-readback

required=(
  CHECKSUMS.sha256
  FINAL_IDENTITY.json
  RELEASE_MANIFEST.md
  RELEASE_NOTES_V620.md
  RELEASE_SCOPE_V620.md
  SBOM.cdx.json
  SOURCE_CHECKSUMS.sha256
  Atlas_ROS_v6.2.0_final_evidence.tar.gz
  atlas_ros-6.2.0-py3-none-any.whl
  atlas_ros-6.2.0.tar.gz
)
for name in "${required[@]}"; do
  test -f "publication-readback/$name"
done
(
  cd publication-readback
  sha256sum -c CHECKSUMS.sha256
)

python -m venv publication-wheel
publication-wheel/bin/python -m pip install --disable-pip-version-check \
  publication-readback/atlas_ros-6.2.0-py3-none-any.whl
publication-wheel/bin/python - <<'PY'
from importlib.metadata import version
import atlas_ros
from atlas_ros.engines import AdaptiveInputProcessingPipelineV62
assert version('atlas-ros') == '6.2.0'
assert atlas_ros.__version__ == '6.2.0'
result = AdaptiveInputProcessingPipelineV62().process(
    'Task = arista cloud vision code upgrade automation pilot.'
)
assert result.outcomes.primary.text == 'Launch the Arista CloudVision code-upgrade automation pilot'
assert result.provider_writes == 0
assert result.execution_authorized is False
assert result.verify_digest()
PY

mkdir -p publication-verification/evidence

tar -xzf publication-readback/Atlas_ROS_v6.2.0_final_evidence.tar.gz \
  -C publication-verification/evidence

python - <<'PY'
import hashlib
import json
from pathlib import Path

root = Path('publication-readback')
verification = Path('publication-verification')
identity = json.loads((root / 'FINAL_IDENTITY.json').read_text(encoding='utf-8'))
metadata = json.loads((verification / 'RELEASE_METADATA.json').read_text(encoding='utf-8'))

expected_source = '863d5ddf9ebd4723200166cf31c7acd93ebec54f'
assert identity['release'] == 'v6.2.0'
assert identity['source_commit'] == expected_source
assert identity['candidate_commit'] == '6e18b270d125c297309915fb8cde545bc65ee5e1'
assert identity['candidate_merge_commit'] == 'bc927a7d8c149d81e3372a3e6abfc220f557de6d'
assert identity['full_validation'] == 'V4V-44'
assert identity['promotion_decision'] == 'V4D-35'
assert identity['immediate_rollback'] == 'v6.1.1'
assert identity['provider_writes'] == 0
assert metadata['tagName'] == 'v6.2.0'
assert metadata['targetCommitish'] == expected_source
assert metadata['isDraft'] is False
assert metadata['isPrerelease'] is False

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

wheel_sha = sha256(root / 'atlas_ros-6.2.0-py3-none-any.whl')
source_sha = sha256(root / 'atlas_ros-6.2.0.tar.gz')
assert wheel_sha == identity['final_wheel_sha256']
assert source_sha == identity['final_source_sha256']

manifest = (root / 'RELEASE_MANIFEST.md').read_text(encoding='utf-8')
assert expected_source in manifest
assert 'Immediate immutable rollback: Atlas ROS v6.1.1' in manifest
sbom = json.loads((root / 'SBOM.cdx.json').read_text(encoding='utf-8'))
assert sbom['metadata']['component']['version'] == '6.2.0'

rollback = json.loads(
    (verification / 'evidence' / 'rollback-restoration.json').read_text(encoding='utf-8')
)
assert rollback['immediate_rollback'] == 'v6.1.1'
assert rollback['immediate_rollback_restored'] is True
assert rollback['historical_rollback_restored'] is True
performance = json.loads(
    (verification / 'evidence' / 'performance-comparison.json').read_text(encoding='utf-8')
)
assert performance['passed'] is True

report = {
    'release': 'v6.2.0',
    'tag_target': expected_source,
    'release_url': metadata['url'],
    'published_at': metadata['publishedAt'],
    'final_wheel_sha256': wheel_sha,
    'final_source_sha256': source_sha,
    'final_identity': identity,
    'immediate_rollback': rollback,
    'performance': performance,
    'all_required_assets_present': True,
    'asset_checksums_verified': True,
    'clean_install_verified': True,
    'cloudvision_regression_verified': True,
    'readable_published_workspace_valid': True,
}
(verification / 'PUBLICATION_VERIFICATION.json').write_text(
    json.dumps(report, indent=2, sort_keys=True), encoding='utf-8'
)
PY

(
  cd publication-verification
  find . -type f ! -name VERIFICATION_CHECKSUMS.sha256 -print0 | sort -z | \
    xargs -0 sha256sum > VERIFICATION_CHECKSUMS.sha256
  sha256sum -c VERIFICATION_CHECKSUMS.sha256
)
