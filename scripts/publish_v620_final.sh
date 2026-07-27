#!/usr/bin/env bash
set -euo pipefail

: "${GH_TOKEN:?GH_TOKEN is required}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
: "${GITHUB_EVENT_NAME:?GITHUB_EVENT_NAME is required}"
: "${GITHUB_REF_NAME:?GITHUB_REF_NAME is required}"
: "${GITHUB_SHA:?GITHUB_SHA is required}"
: "${SOURCE_COMMIT:?SOURCE_COMMIT is required}"
: "${CANDIDATE_COMMIT:?CANDIDATE_COMMIT is required}"
: "${CANDIDATE_MERGE_COMMIT:?CANDIDATE_MERGE_COMMIT is required}"
: "${CANDIDATE_ARTIFACT_ID:?CANDIDATE_ARTIFACT_ID is required}"
: "${CANDIDATE_ARTIFACT_DIGEST:?CANDIDATE_ARTIFACT_DIGEST is required}"
: "${CANDIDATE_WHEEL_SHA256:?CANDIDATE_WHEEL_SHA256 is required}"
: "${FULL_VALIDATION_RECORD:?FULL_VALIDATION_RECORD is required}"
: "${PROMOTION_DECISION:?PROMOTION_DECISION is required}"
: "${RELEASE_TAG:?RELEASE_TAG is required}"
: "${ROLLBACK_TAG:?ROLLBACK_TAG is required}"
: "${HISTORICAL_ROLLBACK_TAG:?HISTORICAL_ROLLBACK_TAG is required}"
PUBLISH="${PUBLISH:-false}"

ATLAS_VERSION="$(python - <<'PY'
import tomllib
from pathlib import Path
print(tomllib.loads(Path('pyproject.toml').read_text(encoding='utf-8'))['project']['version'])
PY
)"
test "$ATLAS_VERSION" = "6.2.0"
test "$(python - <<'PY'
from pathlib import Path
import re
text = Path('src/atlas_ros/__init__.py').read_text(encoding='utf-8')
print(re.search(r'__version__ = "([^"]+)"', text).group(1))
PY
)" = "6.2.0"
test "$(git rev-parse HEAD)" = "$SOURCE_COMMIT"
git merge-base --is-ancestor "$CANDIDATE_COMMIT" HEAD
git merge-base --is-ancestor "$CANDIDATE_MERGE_COMMIT" HEAD
if [[ "$PUBLISH" == "true" ]]; then
  test "$GITHUB_EVENT_NAME" = "push"
  test "$GITHUB_REF_NAME" = "main"
  test "$SOURCE_COMMIT" = "$GITHUB_SHA"
fi

rm -rf final-evidence audit rollback-v611 rollback-v610 baseline-source \
  dist build final-publication final-source final-wheel restore-v611 restore-v610 \
  release-readback release-readback-wheel
mkdir -p final-evidence/benchmarks final-evidence/test-results audit

ruff check .
python scripts/validate_architecture.py
mypy src
pytest \
  --junitxml=final-evidence/test-results/pytest.xml \
  --cov-report=json:final-evidence/test-results/coverage.json
python scripts/evaluate_classification_intelligence.py \
  --dataset benchmarks/classification-intelligence-v1.json \
  --output final-evidence/benchmarks/classification-intelligence.json
python scripts/evaluate_knowledge_management.py \
  --dataset benchmarks/knowledge-management-v2.json \
  --output final-evidence/benchmarks/knowledge-management.json
python scripts/evaluate_semantic_fidelity.py \
  --dataset benchmarks/semantic-fidelity-v1.json \
  --output final-evidence/benchmarks/semantic-fidelity.json
python scripts/evaluate_reasoning_coherence.py \
  --dataset benchmarks/reasoning-coherence-v1.json \
  --output final-evidence/benchmarks/reasoning-coherence.json
python scripts/evaluate_execution_planning.py \
  --dataset benchmarks/execution-planning-v1.json \
  --output final-evidence/benchmarks/execution-planning.json
python scripts/evaluate_execution_orchestration.py \
  --dataset benchmarks/execution-orchestration-v1.json \
  --output final-evidence/benchmarks/execution-orchestration.json
python scripts/evaluate_canonical_reconciliation.py \
  --dataset benchmarks/canonical-reconciliation-v1.json \
  --output final-evidence/benchmarks/canonical-reconciliation.json
python scripts/evaluate_adaptive_input_processing.py \
  --dataset benchmarks/adaptive-input-processing-v1.json \
  --output final-evidence/benchmarks/adaptive-input-processing.json
python scripts/scan_candidate_secrets.py \
  --root . \
  --output final-evidence/secret-scan.json
python scripts/validate_dependency_lock.py requirements.runtime.lock
python scripts/validate_vulnerability_exceptions.py
pip-audit --disable-pip --require-hashes --no-deps \
  --vulnerability-service pypi \
  --requirement requirements.runtime.lock \
  --format json \
  --output audit/pip-audit-pypi.json
pip-audit --disable-pip --require-hashes --no-deps \
  --vulnerability-service osv \
  --requirement requirements.runtime.lock \
  --format json \
  --output audit/pip-audit-osv.json
python scripts/evaluate_dependency_audit.py \
  audit/pip-audit-pypi.json audit/pip-audit-osv.json
cp -R audit final-evidence/

mkdir -p rollback-v611 rollback-v610 baseline-source
gh release download "$ROLLBACK_TAG" \
  --repo "$GITHUB_REPOSITORY" \
  --pattern 'atlas_ros-6.1.1*.tar.gz' \
  --pattern 'atlas_ros-6.1.1*.whl' \
  --dir rollback-v611
gh release download "$HISTORICAL_ROLLBACK_TAG" \
  --repo "$GITHUB_REPOSITORY" \
  --pattern 'atlas_ros-6.1.0*.whl' \
  --dir rollback-v610
baseline_archive="$(find rollback-v611 -type f -name 'atlas_ros-6.1.1*.tar.gz' -print -quit)"
test -n "$baseline_archive"
tar -xzf "$baseline_archive" -C baseline-source
baseline_root="$(find baseline-source -mindepth 1 -maxdepth 1 -type d -print -quit)"
test -n "$baseline_root"
python scripts/compare_v62_performance.py \
  --baseline-source "$baseline_root" \
  --output final-evidence/performance-comparison.json \
  --iterations 100 \
  --warmup 20 \
  --max-regression 0.20

rm -f release/CHECKSUMS.sha256
atlas release checksums --root . --checksum-file release/CHECKSUMS.sha256
atlas release verify --root . --checksum-file release/CHECKSUMS.sha256
python -m build
test -f dist/atlas_ros-6.2.0.tar.gz
test -f dist/atlas_ros-6.2.0-py3-none-any.whl
mkdir -p final-publication
cp dist/atlas_ros-6.2.0.tar.gz final-publication/
cp dist/atlas_ros-6.2.0-py3-none-any.whl final-publication/
cp release/RELEASE_NOTES_V620.md final-publication/
cp release/RELEASE_SCOPE_V620.md final-publication/
cp release/SBOM_V620_CURRENT.cdx.json final-publication/SBOM.cdx.json
cp release/CHECKSUMS.sha256 final-publication/SOURCE_CHECKSUMS.sha256
cp -R final-evidence final-publication/evidence

mkdir final-source
tar -xzf final-publication/atlas_ros-6.2.0.tar.gz -C final-source
source_root="$(find final-source -mindepth 1 -maxdepth 1 -type d -print -quit)"
test -n "$source_root"
SOURCE_ROOT="$source_root" PYTHONPATH="$source_root/src" python - <<'PY'
from pathlib import Path
import os
from atlas_ros.release.tooling import verify
root = Path(os.environ['SOURCE_ROOT'])
errors = verify(root, root / 'release' / 'CHECKSUMS.sha256')
if errors:
    raise SystemExit(errors)
PY

python -m venv final-wheel
final-wheel/bin/python -m pip install --disable-pip-version-check \
  final-publication/atlas_ros-6.2.0-py3-none-any.whl
final-wheel/bin/python - <<'PY'
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

v611_wheel="$(find rollback-v611 -type f -name 'atlas_ros-6.1.1*.whl' -print -quit)"
v610_wheel="$(find rollback-v610 -type f -name 'atlas_ros-6.1.0*.whl' -print -quit)"
test -n "$v611_wheel"
test -n "$v610_wheel"
python -m venv restore-v611
restore-v611/bin/python -m pip install --disable-pip-version-check "$v611_wheel"
restore-v611/bin/python -c "from importlib.metadata import version; import atlas_ros; assert version('atlas-ros') == '6.1.1'; assert atlas_ros.__version__ == '6.1.1'"
python -m venv restore-v610
restore-v610/bin/python -m pip install --disable-pip-version-check "$v610_wheel"
restore-v610/bin/python - <<'PY'
import json
from importlib.metadata import version
from pathlib import Path
import atlas_ros
distribution_version = version('atlas-ros')
module_version = getattr(atlas_ros, '__version__', '')
assert distribution_version == '6.1.0'
assert module_version
Path('final-publication/evidence/rollback-restoration.json').write_text(
    json.dumps(
        {
            'immediate_rollback': 'v6.1.1',
            'immediate_rollback_restored': True,
            'immediate_rollback_distribution_version': '6.1.1',
            'immediate_rollback_module_version': '6.1.1',
            'historical_rollback': 'v6.1.0',
            'historical_rollback_restored': True,
            'historical_rollback_distribution_version': distribution_version,
            'historical_rollback_module_version': module_version,
            'historical_identity_matches': module_version == distribution_version,
            'historical_identity_warning': '' if module_version == distribution_version else (
                'Immutable v6.1.0 distribution metadata is 6.1.0 while '
                'atlas_ros.__version__ differs; historical assets remain unchanged.'
            ),
        },
        indent=2,
        sort_keys=True,
    ),
    encoding='utf-8',
)
PY

wheel_sha="$(sha256sum final-publication/atlas_ros-6.2.0-py3-none-any.whl | awk '{print $1}')"
source_sha="$(sha256sum final-publication/atlas_ros-6.2.0.tar.gz | awk '{print $1}')"
export wheel_sha source_sha
python - <<'PY'
import json
import os
from pathlib import Path
publication = Path('final-publication')
identity = {
    'release': 'v6.2.0',
    'source_commit': os.environ['SOURCE_COMMIT'],
    'candidate_commit': os.environ['CANDIDATE_COMMIT'],
    'candidate_merge_commit': os.environ['CANDIDATE_MERGE_COMMIT'],
    'candidate_artifact_id': os.environ['CANDIDATE_ARTIFACT_ID'],
    'candidate_artifact_digest': os.environ['CANDIDATE_ARTIFACT_DIGEST'],
    'candidate_wheel_sha256': os.environ['CANDIDATE_WHEEL_SHA256'],
    'final_wheel_sha256': os.environ['wheel_sha'],
    'final_source_sha256': os.environ['source_sha'],
    'full_validation': os.environ['FULL_VALIDATION_RECORD'],
    'promotion_decision': os.environ['PROMOTION_DECISION'],
    'immediate_rollback': os.environ['ROLLBACK_TAG'],
    'historical_rollback': os.environ['HISTORICAL_ROLLBACK_TAG'],
    'provider_writes': 0,
}
(publication / 'FINAL_IDENTITY.json').write_text(
    json.dumps(identity, indent=2, sort_keys=True), encoding='utf-8'
)
(publication / 'RELEASE_MANIFEST.md').write_text(
    f'''# Atlas ROS v6.2.0 Release Manifest

Status: Final production release authorized by {identity['promotion_decision']} and published only after governed final-controller validation and readback.

- Package version: `6.2.0`
- Validated candidate head: `{identity['candidate_commit']}`
- Candidate merge commit: `{identity['candidate_merge_commit']}`
- Production source and final tag target: `{identity['source_commit']}`
- Validated candidate artifact ID: `{identity['candidate_artifact_id']}`
- Validated candidate artifact digest: `{identity['candidate_artifact_digest']}`
- Validated candidate wheel SHA-256: `{identity['candidate_wheel_sha256']}`
- Final wheel SHA-256: `{identity['final_wheel_sha256']}`
- Final source SHA-256: `{identity['final_source_sha256']}`
- Governed Full Validation: `{identity['full_validation']}`
- Promotion decision: `{identity['promotion_decision']}`
- Immediate immutable rollback: Atlas ROS v6.1.1
- Historical rollback retained: Atlas ROS v6.1.0
- Provider writes during validation: `0`

## Authority model

GitHub is canonical for source, architecture, policy, schema, runbook, release, validation, restoration, and historical software records. Notion remains the live dynamic management authority. Todoist remains the attended execution authority. The fixed Google Drive Release Index remains the initialization bootstrap.

Required production integrations remain Google Drive, Notion, and Todoist. Integration Inventory authority: https://app.notion.com/p/8ba4fafb5ce244ef9add3013aff3746b

## Release scope

Atlas ROS v6.2.0 implements the fourteen-capability adaptive input-processing and planning architecture while preserving provider-free reasoning, attended execution, the v6.1.1 CloudVision business plan, canonical reconciliation, rollback, historical immutability, and fail-closed behavior.

The readable published workspace is valid only after the release tag, source and wheel assets, checksums, SBOM, benchmark evidence, restoration evidence, final identity, and publication readback are verified. Secrets and private signing material are excluded.
''',
    encoding='utf-8',
)
PY

tar -czf final-publication/Atlas_ROS_v6.2.0_final_evidence.tar.gz \
  -C final-publication evidence
rm -rf final-publication/evidence
(
  cd final-publication
  find . -maxdepth 1 -type f ! -name CHECKSUMS.sha256 -print0 | sort -z | \
    xargs -0 sha256sum > CHECKSUMS.sha256
  sha256sum -c CHECKSUMS.sha256
)

if [[ "$PUBLISH" == "true" ]]; then
  if gh release view "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" >/dev/null 2>&1; then
    echo "Release $RELEASE_TAG already exists; refusing overwrite" >&2
    exit 1
  fi
  mapfile -d '' release_assets < <(
    find final-publication -maxdepth 1 -type f -print0 | sort -z
  )
  gh release create "$RELEASE_TAG" "${release_assets[@]}" \
    --repo "$GITHUB_REPOSITORY" \
    --target "$SOURCE_COMMIT" \
    --title "Atlas ROS v6.2.0" \
    --notes-file release/RELEASE_NOTES_V620.md

  git fetch --tags --force
  test "$(git rev-list -n 1 "$RELEASE_TAG")" = "$SOURCE_COMMIT"
  mkdir release-readback
  gh release download "$RELEASE_TAG" \
    --repo "$GITHUB_REPOSITORY" \
    --dir release-readback
  (cd release-readback && sha256sum -c CHECKSUMS.sha256)
  python -m venv release-readback-wheel
  release-readback-wheel/bin/python -m pip install --disable-pip-version-check \
    release-readback/atlas_ros-6.2.0-py3-none-any.whl
  release-readback-wheel/bin/python -c "from importlib.metadata import version; import atlas_ros; assert version('atlas-ros') == '6.2.0'; assert atlas_ros.__version__ == '6.2.0'"
  gh release view "$RELEASE_TAG" \
    --repo "$GITHUB_REPOSITORY" \
    --json tagName,targetCommitish,isDraft,isPrerelease,url \
    > final-publication/RELEASE_READBACK.json
  sha256sum final-publication/RELEASE_READBACK.json \
    > final-publication/RELEASE_READBACK.sha256
fi
