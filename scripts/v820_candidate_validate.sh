#!/usr/bin/env bash
set -euo pipefail

mode="${1:-lean}"
case "$mode" in
  lean|full) ;;
  *) echo "unsupported validation mode: $mode" >&2; exit 2 ;;
esac

: "${CANDIDATE_COMMIT:?CANDIDATE_COMMIT is required}"
test "$(git rev-parse HEAD)" = "$CANDIDATE_COMMIT"

mkdir -p build dist clean-install restoration
rm -rf build/v820-runtime secret-scan-root

git rev-parse HEAD > build/SOURCE_COMMIT.txt
git ls-tree -r --full-tree HEAD > build/SOURCE_TREE.txt
export SOURCE_DATE_EPOCH="$(git show -s --format=%ct "$CANDIDATE_COMMIT")"

echo "v820_stage=static_validation"
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
pytest --no-cov -q \
  tests/unit/test_v700_contract_compiler.py \
  tests/unit/test_v700_contract_schemas.py
python scripts/validate_documentation_authority.py
python scripts/validate_dependency_lock.py
python scripts/validate_vulnerability_exceptions.py

echo "v820_stage=targeted_acceptance"
pytest --no-cov -q \
  tests/unit/test_v820_natural_comment_reconciliation.py \
  tests/unit/test_v820_composite_reconciliation.py \
  tests/unit/test_reconciliation_state.py \
  tests/unit/test_w04_reconciliation.py \
  tests/unit/test_v800_task_update_delegation.py \
  tests/unit/test_v810_context_aware_clarification.py \
  tests/integration/test_v810_attended_clarification_workflow.py \
  tests/test_execution_reconciliation_service.py
python scripts/v820_validate_natural_comment.py \
  --output build/V820_NATURAL_COMMENT_EVIDENCE.json

if [[ "$mode" == "lean" ]]; then
  echo "v820_stage=lean_complete"
  exit 0
fi

echo "v820_stage=full_test_suite"
pytest \
  --junitxml=build/V820_TEST_RESULTS.xml \
  --cov=atlas_ros \
  --cov-report=term \
  --cov-report=json:build/V820_COVERAGE.json

python - <<'PY'
import hashlib
import json
from pathlib import Path

schema_path = Path('release/V820_RECONCILIATION_STATE_SCHEMA_READBACK.json')
evidence = json.loads(schema_path.read_text())
expected = {
    'Cursor', 'Event ID', 'Execution Surface', 'Notes',
    'Processed At', 'State Key', 'State Type', 'Status',
}
if evidence.get('production_writes') != 0:
    raise RuntimeError('production write count is not zero')
if evidence.get('destructive_operations') != 0:
    raise RuntimeError('destructive operation count is not zero')
if set(evidence.get('writable_properties', [])) != expected:
    raise RuntimeError('live reconciliation-state writable-property readback mismatch')
Path('build/V820_SCHEMA_READBACK_SHA256.txt').write_text(
    hashlib.sha256(schema_path.read_bytes()).hexdigest() + '\n'
)
receipt = {
    'destructive_operations': 0,
    'event_envelope_property': 'Notes',
    'local_sqlite_migration': 'additive runtime initialization',
    'production_notion_migration_required': False,
    'production_notion_schema_changes': 0,
}
Path('build/V820_NO_MIGRATION_RECEIPT.json').write_text(
    json.dumps(receipt, indent=2, sort_keys=True) + '\n'
)
PY

echo "v820_stage=security_and_dependency_audits"
mkdir -p secret-scan-root
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

echo "v820_stage=build_once"
rm -rf dist
python -m build
test -f dist/atlas_ros-8.2.0.tar.gz
test -f dist/atlas_ros-8.2.0-py3-none-any.whl
test "$(find dist -maxdepth 1 -type f | wc -l)" -eq 2
printf '1\n' > build/BUILD_COUNT.txt
sha256sum dist/* > build/PACKAGE_CHECKSUMS.sha256

validate_install() {
  local name="$1"
  local package="$2"
  local expected_version="$3"
  local target="clean-install/$name"
  rm -rf "$target"
  python -m venv "$target"
  "$target/bin/python" -m pip install --disable-pip-version-check "$package"
  "$target/bin/python" - "$expected_version" <<'PY'
import sys
import atlas_ros
expected = sys.argv[1]
if atlas_ros.__version__ != expected:
    raise RuntimeError(
        f'installed Atlas ROS version {atlas_ros.__version__!r} != {expected!r}'
    )
PY
  "$target/bin/atlas" status --json > "build/${name}-status.json"
  "$target/bin/atlas" verify --json > "build/${name}-verify.json"
  "$target/bin/python" - "build/${name}-status.json" "build/${name}-verify.json" "$expected_version" <<'PY'
import json
import sys
from pathlib import Path
status = json.loads(Path(sys.argv[1]).read_text())
verify = json.loads(Path(sys.argv[2]).read_text())
expected = sys.argv[3]
if status.get('version') != expected:
    raise RuntimeError(f'status version mismatch: {status!r}')
if verify.get('version') != expected or verify.get('valid') is not True:
    raise RuntimeError(f'verify result mismatch: {verify!r}')
if status.get('provider_writes') != 0 or verify.get('writes') is not False:
    raise RuntimeError('installed runtime verification reported writes')
PY
}

echo "v820_stage=candidate_clean_install"
validate_install candidate-sdist dist/atlas_ros-8.2.0.tar.gz 8.2.0
validate_install candidate-wheel dist/atlas_ros-8.2.0-py3-none-any.whl 8.2.0

echo "v820_stage=live_authority_resolution"
git fetch --no-tags origin main:refs/remotes/origin/main
git show origin/main:governance/AUTHORITY.json > build/LIVE_AUTHORITY.json
python - <<'PY' > build/RESTORATION_ENV
import json
from pathlib import Path


def require_text(mapping: dict[str, object], field: str, scope: str) -> str:
    value = mapping.get(field)
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f'missing or invalid {scope}.{field}: {value!r}')
    return value


authority = json.loads(Path('build/LIVE_AUTHORITY.json').read_text())
active = authority.get('active_release')
rollback = authority.get('immediate_rollback')
if not isinstance(active, dict):
    raise RuntimeError('live authority active_release is missing or invalid')
if not isinstance(rollback, dict):
    raise RuntimeError('live authority immediate_rollback is missing or invalid')
if active.get('status') != 'Active':
    raise RuntimeError(f"live active release status is not Active: {active.get('status')!r}")
values = {
    'ACTIVE_VERSION': require_text(active, 'version', 'active_release'),
    'ACTIVE_TAG': require_text(active, 'tag', 'active_release'),
    'ACTIVE_COMMIT': require_text(active, 'immutable_commit', 'active_release'),
    'ACTIVE_MANIFEST_PATH': require_text(active, 'manifest_path', 'active_release'),
    'ACTIVE_MANIFEST_SHA256': require_text(active, 'manifest_sha256', 'active_release'),
    'ACTIVE_SOURCE_SHA256': require_text(active, 'source_sha256', 'active_release'),
    'ACTIVE_WHEEL_SHA256': require_text(active, 'wheel_sha256', 'active_release'),
    'ROLLBACK_VERSION': require_text(rollback, 'version', 'immediate_rollback'),
    'ROLLBACK_TAG': require_text(rollback, 'tag', 'immediate_rollback'),
    'ROLLBACK_COMMIT': require_text(rollback, 'immutable_commit', 'immediate_rollback'),
}
if values['ACTIVE_COMMIT'] == values['ROLLBACK_COMMIT']:
    raise RuntimeError('active and immediate rollback commits are identical')
for key, value in values.items():
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
  while IFS= read -r candidate; do
    case "$candidate" in
      release/RELEASE_MANIFEST_*.md)
        if git show "$ROLLBACK_COMMIT:$candidate" | grep -Fq "Release version: \`$ROLLBACK_VERSION\`"; then
          printf '%s\n' "$candidate"
          break
        fi
        ;;
    esac
  done
)"
test -n "$rollback_manifest"
git show "$ROLLBACK_COMMIT:$rollback_manifest" > build/ROLLBACK_RELEASE_MANIFEST.md
python - <<'PY' > build/ROLLBACK_PACKAGE_ENV
import re
from pathlib import Path
text = Path('build/ROLLBACK_RELEASE_MANIFEST.md').read_text()
for key, label in {
    'ROLLBACK_SOURCE_SHA256': 'Source distribution SHA-256',
    'ROLLBACK_WHEEL_SHA256': 'Wheel SHA-256',
}.items():
    match = re.search(rf'^- {re.escape(label)}: `([0-9a-f]{{64}})`', text, re.MULTILINE)
    if match is None:
        raise RuntimeError(f'rollback manifest missing {label}')
    print(f'{key}={match.group(1)}')
PY
source build/ROLLBACK_PACKAGE_ENV

active_dir="restoration/active-${ACTIVE_VERSION}"
rollback_dir="restoration/rollback-${ROLLBACK_VERSION}"
rm -rf "$active_dir" "$rollback_dir"
mkdir -p "$active_dir" "$rollback_dir"
gh release download "$ACTIVE_TAG" --repo "$GITHUB_REPOSITORY" --dir "$active_dir"
gh release download "$ROLLBACK_TAG" --repo "$GITHUB_REPOSITORY" --dir "$rollback_dir"
active_sdist="$(find "$active_dir" -maxdepth 1 -type f -name "atlas_ros-${ACTIVE_VERSION}.tar.gz" -print -quit)"
active_wheel="$(find "$active_dir" -maxdepth 1 -type f -name "atlas_ros-${ACTIVE_VERSION}-py3-none-any.whl" -print -quit)"
rollback_sdist="$(find "$rollback_dir" -maxdepth 1 -type f -name "atlas_ros-${ROLLBACK_VERSION}.tar.gz" -print -quit)"
rollback_wheel="$(find "$rollback_dir" -maxdepth 1 -type f -name "atlas_ros-${ROLLBACK_VERSION}-py3-none-any.whl" -print -quit)"
test -n "$active_sdist" && test -n "$active_wheel"
test -n "$rollback_sdist" && test -n "$rollback_wheel"
test "$(sha256sum "$active_sdist" | cut -d' ' -f1)" = "$ACTIVE_SOURCE_SHA256"
test "$(sha256sum "$active_wheel" | cut -d' ' -f1)" = "$ACTIVE_WHEEL_SHA256"
test "$(sha256sum "$rollback_sdist" | cut -d' ' -f1)" = "$ROLLBACK_SOURCE_SHA256"
test "$(sha256sum "$rollback_wheel" | cut -d' ' -f1)" = "$ROLLBACK_WHEEL_SHA256"

echo "v820_stage=active_and_rollback_clean_install"
validate_install active-wheel "$active_wheel" "$ACTIVE_VERSION"
validate_install rollback-wheel "$rollback_wheel" "$ROLLBACK_VERSION"
printf '%s\n' "$ACTIVE_COMMIT" > build/ACTIVE_RESTORATION_COMMIT.txt
printf '%s\n' "$ROLLBACK_COMMIT" > build/ROLLBACK_RESTORATION_COMMIT.txt
printf '%s\n' "$rollback_manifest" > build/ROLLBACK_MANIFEST_PATH.txt

echo "v820_stage=receipt_generation"
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
percent = float(coverage['totals']['percent_covered'])
if percent < 85.0:
    raise RuntimeError(f'coverage {percent} is below 85.0')
root = ET.parse('build/V820_TEST_RESULTS.xml').getroot()
tests = int(root.attrib.get('tests', 0))
failures = int(root.attrib.get('failures', 0))
errors = int(root.attrib.get('errors', 0))
skipped = int(root.attrib.get('skipped', 0))
if tests <= 0 or failures or errors or skipped:
    raise RuntimeError(
        f'invalid test receipt: tests={tests}, failures={failures}, '
        f'errors={errors}, skipped={skipped}'
    )
receipt = {
    'active_restoration_commit': os.environ['ACTIVE_COMMIT'],
    'active_restoration_version': os.environ['ACTIVE_VERSION'],
    'authority_activation_authorized': False,
    'build_count': 1,
    'candidate_commit': source_commit,
    'errors': errors,
    'failures': failures,
    'notion_writes': 0,
    'production_schema_changes': 0,
    'provider_writes': 0,
    'publication_authorized': False,
    'rollback_restoration_commit': os.environ['ROLLBACK_COMMIT'],
    'rollback_restoration_version': os.environ['ROLLBACK_VERSION'],
    'schema_version': 'v820-candidate-receipt-v1',
    'skipped': skipped,
    'tests': tests,
    'todoist_writes': 0,
    'total_coverage': percent,
    'version': '8.2.0',
}
Path('build/V820_VALIDATION_RECEIPT.json').write_text(
    json.dumps(receipt, indent=2, sort_keys=True) + '\n'
)
sbom = {
    'SPDXID': 'SPDXRef-DOCUMENT',
    'creationInfo': {
        'created': datetime.fromtimestamp(
            int(os.environ['SOURCE_DATE_EPOCH']), UTC
        ).isoformat().replace('+00:00', 'Z'),
        'creators': ['Tool: atlas-ros-v820-candidate-workflow'],
    },
    'dataLicense': 'CC0-1.0',
    'documentNamespace': f'https://atlas-ros.local/sbom/{source_commit}',
    'name': 'atlas-ros-8.2.0',
    'packages': [{
        'SPDXID': 'SPDXRef-Package-atlas-ros',
        'downloadLocation': 'NOASSERTION',
        'filesAnalyzed': False,
        'licenseConcluded': 'NOASSERTION',
        'licenseDeclared': 'NOASSERTION',
        'name': 'atlas-ros',
        'versionInfo': '8.2.0',
    }],
    'spdxVersion': 'SPDX-2.3',
}
Path('build/V820_SBOM.spdx.json').write_text(
    json.dumps(sbom, indent=2, sort_keys=True) + '\n'
)
source_tree = digest('build/SOURCE_TREE.txt')
Path('build/SOURCE_TREE_SHA256.txt').write_text(source_tree + '\n')
index = {
    'build_count': 1,
    'candidate_commit': source_commit,
    'live_schema_readback_sha256': digest(
        'release/V820_RECONCILIATION_STATE_SCHEMA_READBACK.json'
    ),
    'natural_comment_evidence_sha256': digest(
        'build/V820_NATURAL_COMMENT_EVIDENCE.json'
    ),
    'no_migration_receipt_sha256': digest(
        'build/V820_NO_MIGRATION_RECEIPT.json'
    ),
    'sbom_sha256': digest('build/V820_SBOM.spdx.json'),
    'source_sha256': digest('dist/atlas_ros-8.2.0.tar.gz'),
    'source_tree_sha256': source_tree,
    'validation_receipt_sha256': digest(
        'build/V820_VALIDATION_RECEIPT.json'
    ),
    'wheel_sha256': digest('dist/atlas_ros-8.2.0-py3-none-any.whl'),
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

echo "v820_stage=full_validation_complete"
