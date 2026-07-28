#!/usr/bin/env bash
set -euo pipefail

: "${GH_TOKEN:?GH_TOKEN is required}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
: "${GITHUB_RUN_ID:?GITHUB_RUN_ID is required}"
: "${FINAL_SHA:?FINAL_SHA is required}"
: "${CANDIDATE_SHA:?CANDIDATE_SHA is required}"
: "${CANDIDATE_MERGE_COMMIT:?CANDIDATE_MERGE_COMMIT is required}"
: "${CANDIDATE_ARTIFACT_ID:?CANDIDATE_ARTIFACT_ID is required}"
: "${CANDIDATE_ARTIFACT_DIGEST:?CANDIDATE_ARTIFACT_DIGEST is required}"
: "${EXACT_ARTIFACT_ID:?EXACT_ARTIFACT_ID is required}"
: "${EXACT_ARTIFACT_DIGEST:?EXACT_ARTIFACT_DIGEST is required}"
: "${CONTROLLER_ARTIFACT_ID:?CONTROLLER_ARTIFACT_ID is required}"
: "${CONTROLLER_ARTIFACT_DIGEST:?CONTROLLER_ARTIFACT_DIGEST is required}"
: "${DECISION_RECORD_URL:?DECISION_RECORD_URL is required}"
: "${REVIEW_RECORD_URL:?REVIEW_RECORD_URL is required}"

ATLAS_VERSION="$(python - <<'PY'
import tomllib
from pathlib import Path
print(tomllib.loads(Path('pyproject.toml').read_text(encoding='utf-8'))['project']['version'])
PY
)"
test "$ATLAS_VERSION" = "7.0.0"
test "$(python -c 'import atlas_ros; print(atlas_ros.__version__)')" = "$ATLAS_VERSION"
test "$(git rev-parse HEAD)" = "$FINAL_SHA"
git merge-base --is-ancestor "$CANDIDATE_SHA" HEAD
git merge-base --is-ancestor "$CANDIDATE_MERGE_COMMIT" HEAD

rm -rf \
  v700-final-evidence \
  v700-final-publication \
  prior-candidate \
  prior-exact \
  prior-controller \
  dist \
  build \
  clean-v700-final \
  restore-v650 \
  restore-v620 \
  v650-assets \
  v620-assets
mkdir -p v700-final-evidence v700-final-publication

verify_artifact() {
  local artifact_id="$1"
  local artifact_digest="${2#sha256:}"
  local destination="$3"
  local archive="$destination.zip"
  gh api "repos/${GITHUB_REPOSITORY}/actions/artifacts/${artifact_id}/zip" > "$archive"
  echo "${artifact_digest}  ${archive}" | sha256sum -c -
  mkdir -p "$destination"
  unzip -q "$archive" -d "$destination"
}

verify_artifact "$CANDIDATE_ARTIFACT_ID" "$CANDIDATE_ARTIFACT_DIGEST" prior-candidate
verify_artifact "$EXACT_ARTIFACT_ID" "$EXACT_ARTIFACT_DIGEST" prior-exact
verify_artifact "$CONTROLLER_ARTIFACT_ID" "$CONTROLLER_ARTIFACT_DIGEST" prior-controller

candidate_checksums="$(find prior-candidate -name PUBLICATION_CHECKSUMS.sha256 -print -quit)"
exact_checksums="$(find prior-exact -name EXACT_ARTIFACT_CHECKSUMS.sha256 -print -quit)"
controller_checksums="$(find prior-controller -name FINAL_CONTROLLER_CHECKSUMS.sha256 -print -quit)"
test -n "$candidate_checksums"
test -n "$exact_checksums"
test -n "$controller_checksums"
(
  cd "$(dirname "$candidate_checksums")"
  sha256sum -c PUBLICATION_CHECKSUMS.sha256
  cd evidence
  sha256sum -c EVIDENCE_CHECKSUMS.sha256
)
(cd "$(dirname "$exact_checksums")" && sha256sum -c EXACT_ARTIFACT_CHECKSUMS.sha256)
(cd "$(dirname "$controller_checksums")" && sha256sum -c FINAL_CONTROLLER_CHECKSUMS.sha256)

export CANDIDATE_SHA CANDIDATE_MERGE_COMMIT CANDIDATE_ARTIFACT_ID EXACT_ARTIFACT_ID CONTROLLER_ARTIFACT_ID
python - <<'PY'
import json
import os
from pathlib import Path


def read_one(root: str, name: str) -> dict:
    paths = list(Path(root).rglob(name))
    if len(paths) != 1:
        raise RuntimeError(f'expected exactly one {name} under {root}; found {len(paths)}')
    return json.loads(paths[0].read_text(encoding='utf-8'))

candidate = read_one('prior-candidate', 'FINAL_IDENTITY_CANDIDATE.json')
exact = read_one('prior-exact', 'EXACT_ARTIFACT_VALIDATION.json')
controller = read_one('prior-controller', 'V700_FINAL_CONTROLLER_VALIDATION.json')

assert candidate['release_version'] == '7.0.0rc1'
assert candidate['candidate_commit'] == os.environ['CANDIDATE_SHA']
assert exact['candidate_sha'] == os.environ['CANDIDATE_SHA']
assert exact['candidate_artifact_id'] == os.environ['CANDIDATE_ARTIFACT_ID']
assert exact['status'] in {'passed', 'passed_with_findings'}
assert exact['provider_writes'] == 0
assert controller['candidate_sha'] == os.environ['CANDIDATE_SHA']
assert controller['final_source_commit'] == os.environ['CANDIDATE_SHA']
assert controller['status'] == 'validated_not_authorized'
assert controller['provider_writes'] == 0
PY

python - <<'PY'
import hashlib
import subprocess
from pathlib import Path

paths = subprocess.check_output(['git', 'ls-files', '-z']).split(b'\0')
lines = []
for raw in paths:
    if not raw:
        continue
    path = Path(raw.decode('utf-8'))
    lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.as_posix()}")
Path('v700-final-evidence/SOURCE_MANIFEST.sha256').write_text(
    '\n'.join(lines) + '\n', encoding='utf-8'
)
PY

python -m build
SDIST="atlas_ros-${ATLAS_VERSION}.tar.gz"
WHEEL="atlas_ros-${ATLAS_VERSION}-py3-none-any.whl"
test -f "dist/$SDIST"
test -f "dist/$WHEEL"
sha256sum "dist/$SDIST" "dist/$WHEEL" > v700-final-evidence/FINAL_ARTIFACTS.sha256

python -m venv clean-v700-final
clean-v700-final/bin/python -m pip install --disable-pip-version-check "dist/$WHEEL"
clean-v700-final/bin/python - <<'PY'
from importlib.metadata import version
import atlas_ros
from atlas_ros.application import (
    AttendedExecutionService,
    CanonicalAttendedPipeline,
    CanonicalProcessingCoordinator,
)
from atlas_ros.kernel import RuntimeKernel

assert version('atlas-ros') == '7.0.0'
assert atlas_ros.__version__ == '7.0.0'
assert all((AttendedExecutionService, CanonicalAttendedPipeline, CanonicalProcessingCoordinator, RuntimeKernel))
PY
clean-v700-final/bin/atlas status --json > v700-final-evidence/FINAL_RUNTIME_STATUS.json
clean-v700-final/bin/atlas verify --json > v700-final-evidence/FINAL_RUNTIME_VERIFY.json

mkdir -p v650-assets v620-assets
gh release download v6.5.0 --repo "$GITHUB_REPOSITORY" --dir v650-assets
gh release download v6.2.0 --repo "$GITHUB_REPOSITORY" --dir v620-assets
(cd v650-assets && sha256sum -c CHECKSUMS.sha256)
(cd v620-assets && sha256sum -c CHECKSUMS.sha256)
V650_WHEEL="$(find v650-assets -name 'atlas_ros-6.5.0*.whl' -print -quit)"
V620_WHEEL="$(find v620-assets -name 'atlas_ros-6.2.0*.whl' -print -quit)"
test -n "$V650_WHEEL"
test -n "$V620_WHEEL"
python -m venv restore-v650
restore-v650/bin/python -m pip install --disable-pip-version-check "$V650_WHEEL"
restore-v650/bin/python -c "import atlas_ros; assert atlas_ros.__version__ == '6.5.0'"
python -m venv restore-v620
restore-v620/bin/python -m pip install --disable-pip-version-check "$V620_WHEEL"
restore-v620/bin/python -c "import atlas_ros; assert atlas_ros.__version__ == '6.2.0'"

python -m scripts.validate_v650_rollback_evidence \
  --repository-root . \
  --source-commit bb6d6fea70d6824c9bc6a42e63ba36cc88029260 \
  --release-assets-dir v650-assets \
  --clean-install-version 6.5.0 \
  --restoration-passed \
  --metadata-exception-record-url https://app.notion.com/p/3aab8344ad2c81efad29c12b9b132374 \
  --output v700-final-evidence/V650_ROLLBACK_EVIDENCE.json \
  2>&1 | tee v700-final-evidence/V650_ROLLBACK_RECONCILIATION.log

python scripts/compare_v700_performance.py \
  --candidate-python clean-v700-final/bin/python \
  --baseline-python restore-v650/bin/python \
  --dataset benchmarks/execution-planning-v1.json \
  --iterations 7 \
  --max-regression 0.10 \
  --output v700-final-evidence/V700_FINAL_V650_PERFORMANCE.json

python -m scripts.validate_v700_drive_folder_tree \
  --input release/v700-drive-folder-traversal.json \
  --output v700-final-evidence/V700_DRIVE_FOLDER_TREE.json
python -m scripts.validate_v700_current_drive_authority \
  --input release/v700-current-drive-authority-migration.json \
  --output v700-final-evidence/V700_CURRENT_DRIVE_AUTHORITY.json
python -m tools.release.drive_migration_cli compile \
  release/v700-drive-migration-inventory.json \
  v700-final-evidence/V700_CURRENT_DRIVE_MIGRATION_LEDGER.json \
  > v700-final-evidence/V700_CURRENT_DRIVE_MIGRATION_SUMMARY.json
python -m scripts.validate_v700_pre_v6_deletion_plan \
  --plan release/v700-pre-v6-deletion-plan.json \
  --folder-tree release/v700-drive-folder-traversal.json \
  --output v700-final-evidence/V700_PRE_V6_DELETION_PLAN.json
python -m scripts.validate_v700_pre_v6_exclusion_review \
  --review release/v700-pre-v6-exclusion-review.json \
  --plan release/v700-pre-v6-deletion-plan.json \
  --folder-tree release/v700-drive-folder-traversal.json \
  --output v700-final-evidence/V700_PRE_V6_EXCLUSION_REVIEW.json

export FINAL_SHA ATLAS_VERSION SDIST WHEEL \
  CANDIDATE_ARTIFACT_DIGEST EXACT_ARTIFACT_DIGEST CONTROLLER_ARTIFACT_DIGEST \
  DECISION_RECORD_URL REVIEW_RECORD_URL
python - <<'PY'
import hashlib
import json
import os
import tomllib
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from tools.release.final_controller import FinalPackageEvidence, compile_final_controller
from tools.release.rollback_evidence import load_receipt


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

root = Path('v700-final-evidence')
dist = Path('dist')
source = dist / os.environ['SDIST']
wheel = dist / os.environ['WHEEL']
source_sha = digest(source)
wheel_sha = digest(wheel)
ledger = json.loads((root / 'V700_CURRENT_DRIVE_MIGRATION_LEDGER.json').read_text(encoding='utf-8'))
rollback = load_receipt(root / 'V650_ROLLBACK_EVIDENCE.json')
performance = json.loads((root / 'V700_FINAL_V650_PERFORMANCE.json').read_text(encoding='utf-8'))
project = tomllib.loads(Path('pyproject.toml').read_text(encoding='utf-8'))['project']

identity = {
    'schema_version': '1.0',
    'release_version': '7.0.0',
    'final_source_commit': os.environ['FINAL_SHA'],
    'candidate_commit': os.environ['CANDIDATE_SHA'],
    'candidate_merge_commit': os.environ['CANDIDATE_MERGE_COMMIT'],
    'candidate_artifact': {
        'id': os.environ['CANDIDATE_ARTIFACT_ID'],
        'digest': os.environ['CANDIDATE_ARTIFACT_DIGEST'].removeprefix('sha256:'),
    },
    'exact_artifact': {
        'id': os.environ['EXACT_ARTIFACT_ID'],
        'digest': os.environ['EXACT_ARTIFACT_DIGEST'].removeprefix('sha256:'),
    },
    'candidate_controller_artifact': {
        'id': os.environ['CONTROLLER_ARTIFACT_ID'],
        'digest': os.environ['CONTROLLER_ARTIFACT_DIGEST'].removeprefix('sha256:'),
    },
    'source': {'name': source.name, 'sha256': source_sha},
    'wheel': {'name': wheel.name, 'sha256': wheel_sha},
    'drive_migration_ledger_sha256': ledger['ledger_sha256'],
    'v650_rollback_evidence_sha256': rollback.evidence_digest,
    'immediate_rollback': {
        'version': '6.5.0',
        'commit': 'bb6d6fea70d6824c9bc6a42e63ba36cc88029260',
    },
    'historical_rollback': {
        'version': '6.2.0',
        'commit': '863d5ddf9ebd4723200166cf31c7acd93ebec54f',
    },
    'decision_record_url': os.environ['DECISION_RECORD_URL'],
    'review_record_url': os.environ['REVIEW_RECORD_URL'],
    'provider_writes': 0,
    'production_authorized': False,
    'published': False,
    'authority_activated': False,
}
(root / 'FINAL_IDENTITY.json').write_text(
    json.dumps(identity, indent=2, sort_keys=True) + '\n', encoding='utf-8'
)

controller = compile_final_controller(
    FinalPackageEvidence(
        candidate_version='7.0.0rc1',
        candidate_commit=os.environ['CANDIDATE_SHA'],
        final_source_commit=os.environ['FINAL_SHA'],
        candidate_pr_merged=True,
        candidate_artifact_id=os.environ['CANDIDATE_ARTIFACT_ID'],
        candidate_artifact_digest=os.environ['CANDIDATE_ARTIFACT_DIGEST'].removeprefix('sha256:'),
        source_sha256=source_sha,
        wheel_sha256=wheel_sha,
        standard_ci_passed=True,
        architecture_validation_passed=True,
        candidate_validation_passed=True,
        exact_artifact_validation_passed=True,
        drive_migration_ledger_complete=True,
        drive_migration_ledger_sha256=ledger['ledger_sha256'],
        live_authority_readback_complete=False,
        required_integrations_ready=True,
        v650_rollback_restored=True,
        v650_rollback_evidence_reconciled=True,
        v650_rollback_evidence_sha256=rollback.evidence_digest,
        review_record_url=os.environ['REVIEW_RECORD_URL'],
        decision_record_url=os.environ['DECISION_RECORD_URL'],
        exact_package_authorization_id=None,
        provider_writes_during_validation=0,
    ),
    transaction_id=f"final-package-v700-{os.environ['FINAL_SHA'][:12]}",
)
expected = {
    'live authority readback has not passed',
    'exact-package Ryan authorization is required',
}
if controller.status != 'blocked' or set(controller.blockers) != expected:
    raise RuntimeError(f'unexpected final-controller blockers: {controller.blockers}')
(root / 'FINAL_PUBLICATION_CONTROLLER_PLAN.json').write_text(
    json.dumps(asdict(controller), indent=2, sort_keys=True) + '\n', encoding='utf-8'
)

status = {
    'schema_version': '1.0',
    'release': 'Atlas ROS v7.0.0',
    'status': 'final_package_validated_not_authorized',
    'final_source_commit': os.environ['FINAL_SHA'],
    'workflow_run_id': os.environ['GITHUB_RUN_ID'],
    'source_sha256': source_sha,
    'wheel_sha256': wheel_sha,
    'performance_gate': performance['status'],
    'candidate_pr_merged': True,
    'active_production_release': 'v6.5.0',
    'intended_immediate_rollback_after_promotion': 'v6.5.0',
    'historical_rollback_release': 'v6.2.0',
    'provider_writes': 0,
    'production_authorized': False,
    'published': False,
    'authority_activated': False,
    'generated_at': datetime.now(UTC).isoformat(),
}
(root / 'V700_FINAL_PACKAGE_STATUS.json').write_text(
    json.dumps(status, indent=2, sort_keys=True) + '\n', encoding='utf-8'
)

components = [
    {
        'type': 'library',
        'name': dependency.split('<', 1)[0].split('>', 1)[0].split('=', 1)[0],
        'version': dependency,
    }
    for dependency in project['dependencies']
]
sbom = {
    'bomFormat': 'CycloneDX',
    'specVersion': '1.5',
    'serialNumber': f"urn:uuid:atlas-ros-final-{os.environ['FINAL_SHA']}",
    'version': 1,
    'metadata': {
        'timestamp': status['generated_at'],
        'component': {
            'type': 'application',
            'name': 'atlas-ros',
            'version': '7.0.0',
            'hashes': [{'alg': 'SHA-256', 'content': wheel_sha}],
        },
    },
    'components': components,
}
(root / 'SBOM.cdx.json').write_text(
    json.dumps(sbom, indent=2, sort_keys=True) + '\n', encoding='utf-8'
)

manifest = f"""# Atlas ROS v7.0.0 Final Package Manifest

Status: exact final package validated; production authorization and publication pending.

- Final source commit: `{os.environ['FINAL_SHA']}`
- Candidate commit: `{os.environ['CANDIDATE_SHA']}`
- Candidate merge commit: `{os.environ['CANDIDATE_MERGE_COMMIT']}`
- Candidate artifact ID: `{os.environ['CANDIDATE_ARTIFACT_ID']}`
- Candidate artifact digest: `{os.environ['CANDIDATE_ARTIFACT_DIGEST'].removeprefix('sha256:')}`
- Exact-artifact ID: `{os.environ['EXACT_ARTIFACT_ID']}`
- Exact-artifact digest: `{os.environ['EXACT_ARTIFACT_DIGEST'].removeprefix('sha256:')}`
- Candidate-controller artifact ID: `{os.environ['CONTROLLER_ARTIFACT_ID']}`
- Candidate-controller artifact digest: `{os.environ['CONTROLLER_ARTIFACT_DIGEST'].removeprefix('sha256:')}`
- Final source SHA-256: `{source_sha}`
- Final wheel SHA-256: `{wheel_sha}`
- Drive ledger SHA-256: `{ledger['ledger_sha256']}`
- v6.5 rollback evidence SHA-256: `{rollback.evidence_digest}`
- Performance gate: `{performance['status']}`
- Provider writes during final-package validation: `0`
- Production authorization: pending
- Publication: not performed
- Authority activation: not performed
- Intended immediate rollback after promotion: `v6.5.0`

The exact package remains fail-closed until live authority readback is bound and Ryan separately authorizes this exact final source and artifact identity.
"""
(root / 'RELEASE_MANIFEST.md').write_text(manifest, encoding='utf-8')
PY

cp "dist/$SDIST" "dist/$WHEEL" v700-final-publication/
cp release/RELEASE_NOTES_V700.md v700-final-publication/RELEASE_NOTES.md
cp release/RELEASE_SCOPE_V700.md v700-final-publication/RELEASE_SCOPE.md
cp v700-final-evidence/FINAL_IDENTITY.json v700-final-publication/
cp v700-final-evidence/RELEASE_MANIFEST.md v700-final-publication/
cp v700-final-evidence/SBOM.cdx.json v700-final-publication/

(
  cd v700-final-evidence
  find . -type f ! -name FINAL_EVIDENCE_CHECKSUMS.sha256 -print0 | sort -z |
    xargs -0 sha256sum > FINAL_EVIDENCE_CHECKSUMS.sha256
  sha256sum -c FINAL_EVIDENCE_CHECKSUMS.sha256
)
tar -czf v700-final-publication/Atlas_ROS_v7.0.0_final_evidence.tar.gz \
  -C v700-final-evidence .
(
  cd v700-final-publication
  find . -maxdepth 1 -type f ! -name CHECKSUMS.sha256 -print0 | sort -z |
    xargs -0 sha256sum > CHECKSUMS.sha256
  sha256sum -c CHECKSUMS.sha256
)
