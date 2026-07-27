#!/usr/bin/env bash
set -euo pipefail

: "${GH_TOKEN:?GH_TOKEN is required}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
: "${GITHUB_RUN_ID:?GITHUB_RUN_ID is required}"
CANDIDATE_SHA="${CANDIDATE_SHA:-$(git rev-parse HEAD)}"
BASELINE_TAG="v6.1.1"
HISTORICAL_ROLLBACK_TAG="v6.1.0"
ATLAS_VERSION="$(python - <<'PY'
import tomllib
from pathlib import Path
print(tomllib.loads(Path('pyproject.toml').read_text(encoding='utf-8'))['project']['version'])
PY
)"
test "$ATLAS_VERSION" = "6.2.0rc1"
ATLAS_DISTRIBUTION="atlas_ros"
ATLAS_SDIST="${ATLAS_DISTRIBUTION}-${ATLAS_VERSION}.tar.gz"
ATLAS_WHEEL="${ATLAS_DISTRIBUTION}-${ATLAS_VERSION}-py3-none-any.whl"
ATLAS_SOURCE_DIR="${ATLAS_DISTRIBUTION}-${ATLAS_VERSION}"

rm -rf candidate-evidence publication candidate-source baseline-assets baseline-source \
  historical-rollback-assets rollback-source clean-candidate restore-v611 restore-v610 dist build
mkdir -p candidate-evidence/test-results candidate-evidence/benchmarks publication

ruff check .
python scripts/validate_architecture.py
mypy src

rm -f release/CHECKSUMS.sha256
atlas release checksums --root . --checksum-file release/CHECKSUMS.sha256
atlas release verify --root . --checksum-file release/CHECKSUMS.sha256

pytest \
  --junitxml=candidate-evidence/test-results/pytest.xml \
  --cov-report=json:candidate-evidence/test-results/coverage.json

python scripts/evaluate_classification_intelligence.py \
  --dataset benchmarks/classification-intelligence-v1.json \
  --output candidate-evidence/benchmarks/classification-intelligence.json
python scripts/evaluate_knowledge_management.py \
  --dataset benchmarks/knowledge-management-v2.json \
  --output candidate-evidence/benchmarks/knowledge-management.json
python scripts/evaluate_semantic_fidelity.py \
  --dataset benchmarks/semantic-fidelity-v1.json \
  --output candidate-evidence/benchmarks/semantic-fidelity.json
python scripts/evaluate_reasoning_coherence.py \
  --dataset benchmarks/reasoning-coherence-v1.json \
  --output candidate-evidence/benchmarks/reasoning-coherence.json
python scripts/evaluate_execution_planning.py \
  --dataset benchmarks/execution-planning-v1.json \
  --output candidate-evidence/benchmarks/execution-planning.json
python scripts/evaluate_execution_orchestration.py \
  --dataset benchmarks/execution-orchestration-v1.json \
  --output candidate-evidence/benchmarks/execution-orchestration.json
python scripts/evaluate_canonical_reconciliation.py \
  --dataset benchmarks/canonical-reconciliation-v1.json \
  --output candidate-evidence/benchmarks/canonical-reconciliation.json
python scripts/evaluate_adaptive_input_processing.py \
  --dataset benchmarks/adaptive-input-processing-v1.json \
  --output candidate-evidence/benchmarks/adaptive-input-processing.json

python scripts/scan_candidate_secrets.py \
  --root . \
  --output candidate-evidence/secret-scan.json

python -m build
test -f "dist/$ATLAS_SDIST"
test -f "dist/$ATLAS_WHEEL"
sha256sum "dist/$ATLAS_SDIST" "dist/$ATLAS_WHEEL" \
  > candidate-evidence/candidate-artifacts.sha256

mkdir -p candidate-source
tar -xzf "dist/$ATLAS_SDIST" -C candidate-source
test -f "candidate-source/$ATLAS_SOURCE_DIR/release/CHECKSUMS.sha256"
PYTHONPATH="candidate-source/$ATLAS_SOURCE_DIR/src" python - <<'PY'
import json
import os
from pathlib import Path
from atlas_ros.release.tooling import verify
root = Path('candidate-source') / os.environ.get('ATLAS_SOURCE_DIR', 'atlas_ros-6.2.0rc1')
errors = verify(root, root / 'release' / 'CHECKSUMS.sha256')
Path('candidate-evidence/source-restoration.json').write_text(
    json.dumps({'valid': not errors, 'errors': errors}, indent=2), encoding='utf-8'
)
if errors:
    raise SystemExit(1)
PY

python -m venv clean-candidate
clean-candidate/bin/python -m pip install --disable-pip-version-check "dist/$ATLAS_WHEEL"
clean-candidate/bin/python - <<'PY'
import atlas_ros
from atlas_ros.engines import AdaptiveInputProcessingPipelineV62
assert atlas_ros.__version__ == '6.2.0rc1'
result = AdaptiveInputProcessingPipelineV62().process(
    'Task = arista cloud vision code upgrade automation pilot.'
)
assert result.outcomes.primary.text == 'Launch the Arista CloudVision code-upgrade automation pilot'
assert result.provider_writes == 0
assert result.execution_authorized is False
assert result.verify_digest()
PY

mkdir -p baseline-assets historical-rollback-assets baseline-source rollback-source
gh release download "$BASELINE_TAG" \
  --repo "$GITHUB_REPOSITORY" \
  --pattern 'atlas_ros-6.1.1*.tar.gz' \
  --pattern 'atlas_ros-6.1.1*.whl' \
  --dir baseline-assets
gh release download "$HISTORICAL_ROLLBACK_TAG" \
  --repo "$GITHUB_REPOSITORY" \
  --pattern 'atlas_ros-6.1.0*.tar.gz' \
  --pattern 'atlas_ros-6.1.0*.whl' \
  --dir historical-rollback-assets
BASELINE_SDIST="$(find baseline-assets -type f -name 'atlas_ros-6.1.1*.tar.gz' -print -quit)"
ROLLBACK_SDIST="$(find historical-rollback-assets -type f -name 'atlas_ros-6.1.0*.tar.gz' -print -quit)"
BASELINE_WHEEL="$(find baseline-assets -type f -name 'atlas_ros-6.1.1*.whl' -print -quit)"
ROLLBACK_WHEEL="$(find historical-rollback-assets -type f -name 'atlas_ros-6.1.0*.whl' -print -quit)"
test -n "$BASELINE_SDIST"
test -n "$ROLLBACK_SDIST"
test -n "$BASELINE_WHEEL"
test -n "$ROLLBACK_WHEEL"
tar -xzf "$BASELINE_SDIST" -C baseline-source
tar -xzf "$ROLLBACK_SDIST" -C rollback-source
BASELINE_SOURCE="$(find baseline-source -mindepth 1 -maxdepth 1 -type d -print -quit)"
ROLLBACK_SOURCE="$(find rollback-source -mindepth 1 -maxdepth 1 -type d -print -quit)"
test -n "$BASELINE_SOURCE"
test -n "$ROLLBACK_SOURCE"

python scripts/compare_v62_performance.py \
  --baseline-source "$BASELINE_SOURCE" \
  --output candidate-evidence/performance-comparison.json \
  --iterations 100 \
  --warmup 20 \
  --max-regression 0.20

python -m venv restore-v611
restore-v611/bin/python -m pip install --disable-pip-version-check "$BASELINE_WHEEL"
restore-v611/bin/python - <<'PY'
from importlib.metadata import version
import atlas_ros
assert version('atlas-ros') == '6.1.1'
assert atlas_ros.__version__ == '6.1.1'
PY
python -m venv restore-v610
restore-v610/bin/python -m pip install --disable-pip-version-check "$ROLLBACK_WHEEL"
restore-v610/bin/python - <<'PY'
import json
from importlib.metadata import version
from pathlib import Path
import atlas_ros

distribution_version = version('atlas-ros')
module_version = getattr(atlas_ros, '__version__', '')
assert distribution_version == '6.1.0'
assert module_version
identity_matches = module_version == distribution_version
warning = '' if identity_matches else (
    'The immutable v6.1.0 rollback wheel has distribution metadata 6.1.0 but '
    f'atlas_ros.__version__ reports {module_version}; restoration remains installable '
    'and the pre-existing identity drift is recorded without modifying historical assets.'
)
Path('candidate-evidence/rollback-restoration.json').write_text(
    json.dumps(
        {
            'production_baseline': 'v6.1.1',
            'production_baseline_restored': True,
            'production_baseline_distribution_version': '6.1.1',
            'production_baseline_module_version': '6.1.1',
            'historical_immediate_rollback': 'v6.1.0',
            'historical_rollback_restored': True,
            'historical_rollback_distribution_version': distribution_version,
            'historical_rollback_module_version': module_version,
            'historical_rollback_identity_matches': identity_matches,
            'historical_rollback_identity_warning': warning,
        },
        indent=2,
        sort_keys=True,
    ),
    encoding='utf-8',
)
PY

cp release/SBOM_V620_CURRENT.cdx.json candidate-evidence/SBOM.cdx.json
cp release/RELEASE_SCOPE_V620.md candidate-evidence/
cp release/RELEASE_NOTES_V620.md candidate-evidence/
cp release/CHECKSUMS.sha256 candidate-evidence/SOURCE_CHECKSUMS.sha256

export CANDIDATE_SHA GITHUB_RUN_ID ATLAS_SDIST ATLAS_WHEEL
python - <<'PY'
import hashlib
import json
import os
from pathlib import Path

evidence = Path('candidate-evidence')
restoration = json.loads((evidence / 'rollback-restoration.json').read_text(encoding='utf-8'))
warning = restoration['historical_rollback_identity_warning']
warnings = [warning] if warning else []
status = {
    'release': 'Atlas ROS v6.2.0rc1',
    'status': 'candidate_validated_not_promoted',
    'candidate_sha': os.environ['CANDIDATE_SHA'],
    'workflow_run_id': os.environ['GITHUB_RUN_ID'],
    'source_distribution': os.environ['ATLAS_SDIST'],
    'wheel': os.environ['ATLAS_WHEEL'],
    'provider_writes': 0,
    'production_promotion_authorized': False,
    'production_baseline': 'v6.1.1',
    'historical_rollback': 'v6.1.0',
    'warnings': warnings,
}
status_path = evidence / 'V620_CANDIDATE_STATUS.json'
status_path.write_text(json.dumps(status, indent=2, sort_keys=True), encoding='utf-8')
digest = hashlib.sha256(status_path.read_bytes()).hexdigest()
(evidence / 'V620_CANDIDATE_STATUS.sha256').write_text(
    f'{digest}  {status_path.name}\n', encoding='utf-8'
)
warning_line = (
    f'- Historical rollback identity warning: {warning}\n'
    if warning
    else '- Historical rollback package identity: matched\n'
)
(evidence / 'RELEASE_MANIFEST_V620_CANDIDATE.md').write_text(
    f'''# Atlas ROS v6.2.0rc1 Candidate Manifest

Status: Validated release candidate; not promoted.

- Candidate commit: `{status["candidate_sha"]}`
- Validation workflow run: `{status["workflow_run_id"]}`
- Source distribution: `{status["source_distribution"]}`
- Wheel: `{status["wheel"]}`
- Production baseline restored: `v6.1.1`
- Historical rollback distribution restored: `v6.1.0`
{warning_line}- Provider writes during provider-free validation: `0`
- Final production promotion: not authorized

The candidate must not update the fixed Drive Release Index, Notion System State, immutable production tag, GitHub Release, or rollback state without a separate explicit Ryan authorization.
''',
    encoding='utf-8',
)
PY

find candidate-evidence -type f -print0 | sort -z | xargs -0 sha256sum \
  > candidate-evidence/EVIDENCE_CHECKSUMS.sha256
cp "dist/$ATLAS_SDIST" publication/
cp "dist/$ATLAS_WHEEL" publication/
cp -R candidate-evidence publication/evidence
tar -czf publication/Atlas_ROS_v6.2.0rc1_candidate_evidence.tar.gz \
  -C publication evidence
sha256sum publication/* > publication/PUBLICATION_CHECKSUMS.sha256
