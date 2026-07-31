#!/usr/bin/env bash
set -euo pipefail

: "${CANDIDATE_COMMIT:?CANDIDATE_COMMIT is required}"
test "$(git rev-parse HEAD)" = "$CANDIDATE_COMMIT"
candidate_version="$(PYTHONPATH=src python -c 'from atlas_ros import __version__; print(__version__)')"
test "$candidate_version" = "8.2.1"

mkdir -p build dist clean-install restoration secret-scan-root
git rev-parse HEAD > build/V821_SOURCE_COMMIT.txt
git ls-tree -r --full-tree HEAD > build/V821_SOURCE_TREE.txt
export SOURCE_DATE_EPOCH="$(git show -s --format=%ct "$CANDIDATE_COMMIT")"

ruff check \
  src/atlas_ros/reconciliation/state.py \
  src/atlas_ros/reconciliation/baseline.py \
  src/atlas_ros/reconciliation/service.py \
  src/atlas_ros/cli.py \
  tests/unit/test_reconciliation_state.py \
  tests/unit/test_production_baseline.py
mypy --strict \
  src/atlas_ros/reconciliation/state.py \
  src/atlas_ros/reconciliation/baseline.py \
  src/atlas_ros/reconciliation/service.py \
  src/atlas_ros/cli.py
PYTHONPATH=src python scripts/validate_architecture.py
PYTHONPATH=src python scripts/validate_devtools_boundary.py
PYTHONPATH=src python scripts/validate_legacy_isolation.py
PYTHONPATH=src python scripts/validate_documentation_authority.py
PYTHONPATH=src python scripts/validate_dependency_lock.py
PYTHONPATH=src python scripts/validate_vulnerability_exceptions.py

pytest --junitxml=build/V821_TEST_RESULTS.xml \
  --cov=atlas_ros --cov-branch --cov-report=json:build/V821_COVERAGE.json

while IFS= read -r -d '' file; do
  mkdir -p "secret-scan-root/$(dirname "$file")"
  cp "$file" "secret-scan-root/$file"
done < <(git diff --name-only -z --diff-filter=ACMR origin/main...HEAD -- \
  '*.cfg' '*.ini' '*.json' '*.md' '*.py' '*.sh' '*.toml' '*.txt' '*.yaml' '*.yml')
python scripts/scan_candidate_secrets.py \
  --root secret-scan-root --output build/V821_SECRET_SCAN.json
pip-audit --disable-pip --require-hashes --no-deps --timeout 15 \
  --progress-spinner off --vulnerability-service pypi \
  --requirement requirements.runtime.lock --format json \
  --output build/V821_PIP_AUDIT_PYPI.json
pip-audit --disable-pip --require-hashes --no-deps --timeout 15 \
  --progress-spinner off --vulnerability-service osv \
  --requirement requirements.runtime.lock --format json \
  --output build/V821_PIP_AUDIT_OSV.json
python scripts/evaluate_dependency_audit.py \
  build/V821_PIP_AUDIT_PYPI.json build/V821_PIP_AUDIT_OSV.json

rm -rf dist
python -m build
test -f "dist/atlas_ros-${candidate_version}.tar.gz"
test -f "dist/atlas_ros-${candidate_version}-py3-none-any.whl"
test "$(find dist -maxdepth 1 -type f | wc -l)" -eq 2
printf '1\n' > build/V821_BUILD_COUNT.txt
sha256sum dist/* > build/V821_PACKAGE_CHECKSUMS.sha256

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
assert atlas_ros.__version__ == sys.argv[1]
PY
  "$target/bin/atlas" status --json > "build/${name}-status.json"
  "$target/bin/atlas" verify --json > "build/${name}-verify.json"
}

validate_install candidate-sdist "dist/atlas_ros-${candidate_version}.tar.gz" "$candidate_version"
validate_install candidate-wheel "dist/atlas_ros-${candidate_version}-py3-none-any.whl" "$candidate_version"

git fetch --no-tags origin main:refs/remotes/origin/main --force
git show origin/main:governance/AUTHORITY.json > build/V821_LIVE_AUTHORITY.json
python - <<'PY' > build/V821_RESTORATION_ENV
import json
from pathlib import Path
authority = json.loads(Path('build/V821_LIVE_AUTHORITY.json').read_text())
active = authority['active_release']
rollback = authority['immediate_rollback']
assert active['status'] == 'Active'
for prefix, value in [('ACTIVE', active), ('ROLLBACK', rollback)]:
    for key in ('version', 'tag', 'immutable_commit'):
        print(f"{prefix}_{key.upper()}={value[key]}")
for key in ('manifest_path', 'manifest_sha256', 'source_sha256', 'wheel_sha256'):
    print(f"ACTIVE_{key.upper()}={active[key]}")
PY
set -a
source build/V821_RESTORATION_ENV
set +a
git merge-base --is-ancestor "$ACTIVE_IMMUTABLE_COMMIT" "$CANDIDATE_COMMIT"
test "$(git rev-list -n 1 "$ACTIVE_TAG")" = "$ACTIVE_IMMUTABLE_COMMIT"
test "$(git rev-list -n 1 "$ROLLBACK_TAG")" = "$ROLLBACK_IMMUTABLE_COMMIT"
git show "$ACTIVE_IMMUTABLE_COMMIT:$ACTIVE_MANIFEST_PATH" > build/V821_ACTIVE_MANIFEST.md
test "$(sha256sum build/V821_ACTIVE_MANIFEST.md | cut -d' ' -f1)" = "$ACTIVE_MANIFEST_SHA256"
rollback_manifest="$(git ls-tree -r --name-only "$ROLLBACK_IMMUTABLE_COMMIT" -- release | \
  while IFS= read -r candidate; do
    case "$candidate" in
      release/RELEASE_MANIFEST_*.md)
        if git show "$ROLLBACK_IMMUTABLE_COMMIT:$candidate" | grep -Fq "Release version: \`$ROLLBACK_VERSION\`"; then
          printf '%s\n' "$candidate"; break
        fi ;;
    esac
  done)"
test -n "$rollback_manifest"
git show "$ROLLBACK_IMMUTABLE_COMMIT:$rollback_manifest" > build/V821_ROLLBACK_MANIFEST.md
python - <<'PY' > build/V821_ROLLBACK_PACKAGE_ENV
import re
from pathlib import Path
text = Path('build/V821_ROLLBACK_MANIFEST.md').read_text()
for key, label in {'ROLLBACK_SOURCE_SHA256':'Source distribution SHA-256', 'ROLLBACK_WHEEL_SHA256':'Wheel SHA-256'}.items():
    match = re.search(rf'^- {re.escape(label)}: `([0-9a-f]{{64}})`', text, re.MULTILINE)
    if match is None:
        raise RuntimeError(f'rollback manifest missing {label}')
    print(f'{key}={match.group(1)}')
PY
set -a
source build/V821_ROLLBACK_PACKAGE_ENV
set +a
mkdir -p "restoration/active-${ACTIVE_VERSION}" "restoration/rollback-${ROLLBACK_VERSION}"
gh release download "$ACTIVE_TAG" --repo "$GITHUB_REPOSITORY" --dir "restoration/active-${ACTIVE_VERSION}"
gh release download "$ROLLBACK_TAG" --repo "$GITHUB_REPOSITORY" --dir "restoration/rollback-${ROLLBACK_VERSION}"
active_sdist="restoration/active-${ACTIVE_VERSION}/atlas_ros-${ACTIVE_VERSION}.tar.gz"
active_wheel="restoration/active-${ACTIVE_VERSION}/atlas_ros-${ACTIVE_VERSION}-py3-none-any.whl"
rollback_sdist="restoration/rollback-${ROLLBACK_VERSION}/atlas_ros-${ROLLBACK_VERSION}.tar.gz"
rollback_wheel="restoration/rollback-${ROLLBACK_VERSION}/atlas_ros-${ROLLBACK_VERSION}-py3-none-any.whl"
test "$(sha256sum "$active_sdist" | cut -d' ' -f1)" = "$ACTIVE_SOURCE_SHA256"
test "$(sha256sum "$active_wheel" | cut -d' ' -f1)" = "$ACTIVE_WHEEL_SHA256"
test "$(sha256sum "$rollback_sdist" | cut -d' ' -f1)" = "$ROLLBACK_SOURCE_SHA256"
test "$(sha256sum "$rollback_wheel" | cut -d' ' -f1)" = "$ROLLBACK_WHEEL_SHA256"
validate_install active-wheel "$active_wheel" "$ACTIVE_VERSION"
validate_install rollback-wheel "$rollback_wheel" "$ROLLBACK_VERSION"
printf '%s\n' "$ACTIVE_IMMUTABLE_COMMIT" > build/V821_ACTIVE_RESTORATION_COMMIT.txt
printf '%s\n' "$ROLLBACK_IMMUTABLE_COMMIT" > build/V821_ROLLBACK_RESTORATION_COMMIT.txt

python - <<'PY'
import hashlib
import json
import os
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

def digest(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

coverage = json.loads(Path('build/V821_COVERAGE.json').read_text())
percent = float(coverage['totals']['percent_covered'])
if percent < 85.0:
    raise RuntimeError(f'coverage {percent} is below 85.0')
root = ET.parse('build/V821_TEST_RESULTS.xml').getroot()
suites = [root] if root.tag.endswith('testsuite') else list(root.findall('.//testsuite'))
tests = sum(int(s.attrib.get('tests', 0)) for s in suites)
failures = sum(int(s.attrib.get('failures', 0)) for s in suites)
errors = sum(int(s.attrib.get('errors', 0)) for s in suites)
skipped = sum(int(s.attrib.get('skipped', 0)) for s in suites)
if tests <= 0 or failures or errors or skipped:
    raise RuntimeError('full test receipt is not clean')
candidate = Path('build/V821_SOURCE_COMMIT.txt').read_text().strip()
receipt = {
    "schema_version": "v821-candidate-validation-v1",
    "candidate_commit": candidate,
    "version": "8.2.1",
    "build_count": 1,
    "tests": tests,
    "failures": failures,
    "errors": errors,
    "skipped": skipped,
    "total_coverage": percent,
    "production_provider_writes": 0,
    "w04_restored_or_written": False,
    "publication_authorized": False,
    "authority_activation_authorized": False,
    "active_restoration_version": os.environ['ACTIVE_VERSION'],
    "active_restoration_commit": os.environ['ACTIVE_IMMUTABLE_COMMIT'],
    "rollback_restoration_version": os.environ['ROLLBACK_VERSION'],
    "rollback_restoration_commit": os.environ['ROLLBACK_IMMUTABLE_COMMIT'],
    "source_sha256": digest("dist/atlas_ros-8.2.1.tar.gz"),
    "wheel_sha256": digest("dist/atlas_ros-8.2.1-py3-none-any.whl"),
}
Path("build/V821_VALIDATION_RECEIPT.json").write_text(
    json.dumps(receipt, indent=2, sort_keys=True) + "\n"
)
sbom = {
    'SPDXID':'SPDXRef-DOCUMENT', 'spdxVersion':'SPDX-2.3', 'dataLicense':'CC0-1.0',
    'name':'atlas-ros-8.2.1',
    'documentNamespace':f'https://atlas-ros.local/sbom/{candidate}',
    'creationInfo':{'created':datetime.fromtimestamp(int(os.environ['SOURCE_DATE_EPOCH']), UTC).isoformat().replace('+00:00','Z'), 'creators':['Tool: atlas-ros-v821-candidate-workflow']},
    'packages':[{'SPDXID':'SPDXRef-Package-atlas-ros','name':'atlas-ros','versionInfo':'8.2.1','downloadLocation':'NOASSERTION','filesAnalyzed':False,'licenseConcluded':'NOASSERTION','licenseDeclared':'NOASSERTION'}],
}
Path('build/V821_SBOM.spdx.json').write_text(json.dumps(sbom, indent=2, sort_keys=True)+'\n')
index = {
    'build_count':1, 'candidate_commit':candidate,
    'source_sha256':digest('dist/atlas_ros-8.2.1.tar.gz'),
    'wheel_sha256':digest('dist/atlas_ros-8.2.1-py3-none-any.whl'),
    'source_tree_sha256':digest('build/V821_SOURCE_TREE.txt'),
    'validation_receipt_sha256':digest('build/V821_VALIDATION_RECEIPT.json'),
    'sbom_sha256':digest('build/V821_SBOM.spdx.json'),
}
Path('build/V821_PACKAGE_INDEX.json').write_text(json.dumps(index, indent=2, sort_keys=True)+'\n')
PY
sha256sum build/V821_VALIDATION_RECEIPT.json build/V821_SBOM.spdx.json \
  build/V821_PACKAGE_INDEX.json build/V821_SECRET_SCAN.json \
  build/V821_PIP_AUDIT_PYPI.json build/V821_PIP_AUDIT_OSV.json \
  > build/V821_EVIDENCE_CHECKSUMS.sha256
sha256sum -c build/V821_PACKAGE_CHECKSUMS.sha256
sha256sum -c build/V821_EVIDENCE_CHECKSUMS.sha256
