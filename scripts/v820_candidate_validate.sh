#!/usr/bin/env bash
set -euo pipefail

mode="${1:-lean}"
mkdir -p build dist clean-install restoration

test "$(git rev-parse HEAD)" = "${CANDIDATE_COMMIT:?CANDIDATE_COMMIT is required}"
git rev-parse HEAD > build/SOURCE_COMMIT.txt
git ls-tree -r --full-tree HEAD > build/SOURCE_TREE.txt
export SOURCE_DATE_EPOCH="$(git show -s --format=%ct "$CANDIDATE_COMMIT")"

ruff check .
mypy --strict \
  src/atlas_ros/adapters/todoist_command_source.py \
  src/atlas_ros/capabilities/operational_awareness/command_lifecycle/natural_delegation.py \
  src/atlas_ros/capabilities/operational_awareness/command_lifecycle/planner.py \
  src/atlas_ros/capabilities/operational_awareness/command_lifecycle/task_update_normalizer.py \
  src/atlas_ros/reconciliation/comment_lifecycle.py \
  src/atlas_ros/reconciliation/composite.py \
  src/atlas_ros/reconciliation/state.py
python scripts/validate_architecture.py
python scripts/validate_devtools_boundary.py
python scripts/validate_legacy_isolation.py
pytest --no-cov -q tests/unit/test_v700_contract_compiler.py tests/unit/test_v700_contract_schemas.py
python scripts/validate_documentation_authority.py
python scripts/validate_dependency_lock.py
python scripts/validate_vulnerability_exceptions.py

pytest --no-cov -q \
  tests/unit/test_v820_natural_comment_reconciliation.py \
  tests/unit/test_v820_composite_reconciliation.py \
  tests/unit/test_reconciliation_state.py \
  tests/unit/test_w04_reconciliation.py \
  tests/unit/test_v800_task_update_delegation.py \
  tests/unit/test_v810_context_aware_clarification.py \
  tests/integration/test_v810_attended_clarification_workflow.py \
  tests/test_execution_reconciliation_service.py
python scripts/v820_validate_natural_comment.py --output build/V820_NATURAL_COMMENT_EVIDENCE.json

if [[ "$mode" == "lean" ]]; then
  exit 0
fi

pytest --junitxml=build/V820_TEST_RESULTS.xml \
  --cov=atlas_ros \
  --cov-report=term \
  --cov-report=json:build/V820_COVERAGE.json

python - <<'PY'
import hashlib
import json
from pathlib import Path

path = Path('release/V820_RECONCILIATION_STATE_SCHEMA_READBACK.json')
evidence = json.loads(path.read_text())
assert evidence['production_writes'] == 0
assert evidence['destructive_operations'] == 0
assert set(evidence['writable_properties']) == {
    'Cursor', 'Event ID', 'Execution Surface', 'Notes',
    'Processed At', 'State Key', 'State Type', 'Status',
}
Path('build/V820_SCHEMA_READBACK_SHA256.txt').write_text(
    hashlib.sha256(path.read_bytes()).hexdigest() + '\n'
)
receipt = {
    'production_notion_schema_changes': 0,
    'production_notion_migration_required': False,
    'destructive_operations': 0,
    'event_envelope_property': 'Notes',
    'local_sqlite_migration': 'additive runtime initialization',
}
Path('build/V820_NO_MIGRATION_RECEIPT.json').write_text(
    json.dumps(receipt, indent=2, sort_keys=True) + '\n'
)
PY

rm -rf secret-scan-root
mkdir secret-scan-root
while IFS= read -r -d '' file; do
  mkdir -p "secret-scan-root/$(dirname "$file")"
  cp "$file" "secret-scan-root/$file"
done < <(git diff --name-only -z --diff-filter=ACMR origin/main...HEAD -- \
  '*.cfg' '*.ini' '*.json' '*.md' '*.py' '*.sh' '*.toml' '*.txt' '*.yaml' '*.yml')
python scripts/scan_candidate_secrets.py \
  --root secret-scan-root \
  --output build/V820_SECRET_SCAN.json
pip-audit --disable-pip --require-hashes --no-deps --timeout 15 \
  --progress-spinner off --vulnerability-service pypi \
  --requirement requirements.runtime.lock --format json \
  --output build/V820_PIP_AUDIT_PYPI.json
pip-audit --disable-pip --require-hashes --no-deps --timeout 15 \
  --progress-spinner off --vulnerability-service osv \
  --requirement requirements.runtime.lock --format json \
  --output build/V820_PIP_AUDIT_OSV.json
python scripts/evaluate_dependency_audit.py \
  build/V820_PIP_AUDIT_PYPI.json \
  build/V820_PIP_AUDIT_OSV.json

rm -rf dist
python -m build
test -f dist/atlas_ros-8.2.0.tar.gz
test -f dist/atlas_ros-8.2.0-py3-none-any.whl
test "$(find dist -maxdepth 1 -type f | wc -l)" -eq 2
printf '1\n' > build/BUILD_COUNT.txt
sha256sum dist/* > build/PACKAGE_CHECKSUMS.sha256

for kind in sdist wheel; do
  package=dist/atlas_ros-8.2.0.tar.gz
  [[ "$kind" == wheel ]] && package=dist/atlas_ros-8.2.0-py3-none-any.whl
  python -m venv "clean-install/$kind"
  "clean-install/$kind/bin/python" -m pip install --disable-pip-version-check "$package"
  "clean-install/$kind/bin/python" -c \
    "import atlas_ros; assert atlas_ros.__version__ == '8.2.0'"
  "clean-install/$kind/bin/atlas" status --json > "build/${kind}-status.json"
  "clean-install/$kind/bin/atlas" verify --json > "build/${kind}-verify.json"
done

git fetch --no-tags origin main:refs/remotes/origin/main
git show origin/main:governance/AUTHORITY.json > build/LIVE_AUTHORITY.json
python - <<'PY' > build/RESTORATION_ENV
import json
from pathlib import Path
authority = json.loads(Path('build/LIVE_AUTHORITY.json').read_text())
active = authority['active_release']
rollback = authority['immediate_rollback']
assert active['status'] == 'Active'
for field in ('version', 'tag', 'immutable_commit', 'manifest_path', 'manifest_sha256'):
    assert active.get(field), (field, active)
for field in ('version', 'tag', 'immutable_commit'):
    assert rollback.get(field), (field, rollback)
assert active['immutable_commit'] != rollback['immutable_commit']
for key, value in {
    'ACTIVE_VERSION': active['version'],
    'ACTIVE_TAG': active['tag'],
    'ACTIVE_COMMIT': active['immutable_commit'],
    'ACTIVE_MANIFEST_PATH': active['manifest_path'],
    'ACTIVE_MANIFEST_SHA256': active['manifest_sha256'],
    'ACTIVE_SOURCE_SHA256': active['source_sha256'],
    'ACTIVE_WHEEL_SHA256': active['wheel_sha256'],
    'ROLLBACK_VERSION': rollback['version'],
    'ROLLBACK_TAG': rollback['tag'],
    'ROLLBACK_COMMIT': rollback['immutable_commit'],
}.items():
    print(f'{key}={value}')
PY
source build/RESTORATION_ENV

git merge-base --is-ancestor "$ACTIVE_COMMIT" "$CANDIDATE_COMMIT"

test "$(git rev-list -n 1 "$ACTIVE_TAG")" = "$ACTIVE_COMMIT"
test "$(git rev-list -n 1 "$ROLLBACK_TAG")" = "$ROLLBACK_COMMIT"
git show "$ACTIVE_COMMIT:$ACTIVE_MANIFEST_PATH" > build/ACTIVE_RELEASE_MANIFEST.md
test "$(sha256sum build/ACTIVE_RELEASE_MANIFEST.md | cut -d' ' -f1)" = "$ACTIVE_MANIFEST_SHA256"
rollback_manifest="$(
  git ls-tree -r --name-only "$ROLLBACK_COMMIT" -- release |
  while IFS= read -r path; do
    case "$path" in
      release/RELEASE_MANIFEST_*.md)
        if git show "$ROLLBACK_COMMIT:$path" | grep -Fq "Release version: \`$ROLLBACK_VERSION\`"; then
          printf '%s\n' "$path"
          break
        fi
        ;;
    esac
  done
)"
test -n "$rollback_manifest"
git show "$ROLLBACK_COMMIT:$rollback_manifest" > build/ROLLBACK_RELEASE_MANIFEST.md
rollback_source_sha="$(sed -n 's/^- Source distribution SHA-256: `\([0-9a-f]\{64\}\)`.*/\1/p' build/ROLLBACK_RELEASE_MANIFEST.md)"
rollback_wheel_sha="$(sed -n 's/^- Wheel SHA-256: `\([0-9a-f]\{64\}\)`.*/\1/p' build/ROLLBACK_RELEASE_MANIFEST.md)"
test -n "$rollback_source_sha"
test -n "$rollback_wheel_sha"
active_dir="restoration/active-${ACTIVE_VERSION}"
rollback_dir="restoration/rollback-${ROLLBACK_VERSION}"
mkdir -p "$active_dir" "$rollback_dir"
gh release download "$ACTIVE_TAG" --repo "$GITHUB_REPOSITORY" --dir "$active_dir"
gh release download "$ROLLBACK_TAG" --repo "$GITHUB_REPOSITORY" --dir "$rollback_dir"
active_sdist="$(find "$active_dir" -maxdepth 1 -type f -name "atlas_ros-${ACTIVE_VERSION}.tar.gz" -print -quit)"
active_wheel="$(find "$active_dir" -maxdepth 1 -type f -name "atlas_ros-${ACTIVE_VERSION}-py3-none-any.whl" -print -quit)"
rollback_sdist="$(find "$rollback_dir" -maxdepth 1 -type f -name "atlas_ros-${ROLLBACK_VERSION}.tar.gz" -print -quit)"
rollback_wheel="$(find "$rollback_dir" -maxdepth 1 -type f -name "atlas_ros-${ROLLBACK_VERSION}-py3-none-any.whl" -print -quit)"
test "$(sha256sum "$active_sdist" | cut -d' ' -f1)" = "$ACTIVE_SOURCE_SHA256"
test "$(sha256sum "$active_wheel" | cut -d' ' -f1)" = "$ACTIVE_WHEEL_SHA256"
test "$(sha256sum "$rollback_sdist" | cut -d' ' -f1)" = "$rollback_source_sha"
test "$(sha256sum "$rollback_wheel" | cut -d' ' -f1)" = "$rollback_wheel_sha"
printf '%s\n' "$ACTIVE_COMMIT" > build/ACTIVE_RESTORATION_COMMIT.txt
printf '%s\n' "$ROLLBACK_COMMIT" > build/ROLLBACK_RESTORATION_COMMIT.txt
printf '%s\n' "$rollback_manifest" > build/ROLLBACK_MANIFEST_PATH.txt

python - <<'PY'
import hashlib
import json
import os
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

def digest(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

source_commit = Path('build/SOURCE_COMMIT.txt').read_text().strip()
coverage = json.loads(Path('build/V820_COVERAGE.json').read_text())
root = ET.parse('build/V820_TEST_RESULTS.xml').getroot()
tests = int(root.attrib.get('tests', 0))
failures = int(root.attrib.get('failures', 0))
errors = int(root.attrib.get('errors', 0))
skipped = int(root.attrib.get('skipped', 0))
assert tests > 0 and failures == 0 and errors == 0 and skipped == 0
receipt = {
    'schema_version': 'v820-candidate-receipt-v1',
    'candidate_commit': source_commit,
    'version': '8.2.0',
    'build_count': 1,
    'tests': tests,
    'failures': failures,
    'errors': errors,
    'skipped': skipped,
    'total_coverage': coverage['totals']['percent_covered'],
    'provider_writes': 0,
    'todoist_writes': 0,
    'notion_writes': 0,
    'production_schema_changes': 0,
    'active_restoration_version': os.environ['ACTIVE_VERSION'],
    'active_restoration_commit': os.environ['ACTIVE_COMMIT'],
    'rollback_restoration_version': os.environ['ROLLBACK_VERSION'],
    'rollback_restoration_commit': os.environ['ROLLBACK_COMMIT'],
    'publication_authorized': False,
    'authority_activation_authorized': False,
}
Path('build/V820_VALIDATION_RECEIPT.json').write_text(
    json.dumps(receipt, indent=2, sort_keys=True) + '\n'
)
sbom = {
    'spdxVersion': 'SPDX-2.3',
    'dataLicense': 'CC0-1.0',
    'SPDXID': 'SPDXRef-DOCUMENT',
    'name': 'atlas-ros-8.2.0',
    'documentNamespace': f'https://atlas-ros.local/sbom/{source_commit}',
    'creationInfo': {
        'created': datetime.fromtimestamp(int(os.environ['SOURCE_DATE_EPOCH']), UTC).isoformat().replace('+00:00', 'Z'),
        'creators': ['Tool: atlas-ros-v820-candidate-workflow'],
    },
    'packages': [{
        'name': 'atlas-ros',
        'SPDXID': 'SPDXRef-Package-atlas-ros',
        'versionInfo': '8.2.0',
        'downloadLocation': 'NOASSERTION',
        'filesAnalyzed': False,
        'licenseConcluded': 'NOASSERTION',
        'licenseDeclared': 'NOASSERTION',
    }],
}
Path('build/V820_SBOM.spdx.json').write_text(
    json.dumps(sbom, indent=2, sort_keys=True) + '\n'
)
source_tree = digest('build/SOURCE_TREE.txt')
Path('build/SOURCE_TREE_SHA256.txt').write_text(source_tree + '\n')
index = {
    'candidate_commit': source_commit,
    'source_sha256': digest('dist/atlas_ros-8.2.0.tar.gz'),
    'wheel_sha256': digest('dist/atlas_ros-8.2.0-py3-none-any.whl'),
    'sbom_sha256': digest('build/V820_SBOM.spdx.json'),
    'validation_receipt_sha256': digest('build/V820_VALIDATION_RECEIPT.json'),
    'natural_comment_evidence_sha256': digest('build/V820_NATURAL_COMMENT_EVIDENCE.json'),
    'no_migration_receipt_sha256': digest('build/V820_NO_MIGRATION_RECEIPT.json'),
    'live_schema_readback_sha256': digest('release/V820_RECONCILIATION_STATE_SCHEMA_READBACK.json'),
    'source_tree_sha256': source_tree,
    'build_count': 1,
}
Path('build/V820_PACKAGE_INDEX.json').write_text(
    json.dumps(index, indent=2, sort_keys=True) + '\n'
)
PY
sha256sum \
  build/V820_VALIDATION_RECEIPT.json \
  build/V820_NATURAL_COMMENT_EVIDENCE.json \
  build/V820_NO_MIGRATION_RECEIPT.json \
  build/V820_SBOM.spdx.json \
  build/V820_PACKAGE_INDEX.json \
  release/V820_RECONCILIATION_STATE_SCHEMA_READBACK.json \
  > build/EVIDENCE_CHECKSUMS.sha256
sha256sum -c build/PACKAGE_CHECKSUMS.sha256
sha256sum -c build/EVIDENCE_CHECKSUMS.sha256
