#!/usr/bin/env bash
set -euo pipefail

: "${CANDIDATE_COMMIT:?CANDIDATE_COMMIT is required}"
test "$(git rev-parse HEAD)" = "$CANDIDATE_COMMIT"
candidate_version="$(PYTHONPATH=src python -c 'from atlas_ros import __version__; print(__version__)')"
test "$candidate_version" = "8.2.1"

mkdir -p build dist
git rev-parse HEAD > build/V821_SOURCE_COMMIT.txt
git ls-tree -r --full-tree HEAD > build/V821_SOURCE_TREE.txt

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

rm -rf dist
python -m build
test -f "dist/atlas_ros-${candidate_version}.tar.gz"
test -f "dist/atlas_ros-${candidate_version}-py3-none-any.whl"
sha256sum dist/* > build/V821_PACKAGE_CHECKSUMS.sha256
python - <<'PY'
import hashlib
import json
from pathlib import Path

def digest(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

receipt = {
    "schema_version": "v821-candidate-validation-v1",
    "candidate_commit": Path("build/V821_SOURCE_COMMIT.txt").read_text().strip(),
    "version": "8.2.1",
    "production_provider_writes": 0,
    "w04_restored_or_written": False,
    "publication_authorized": False,
    "authority_activation_authorized": False,
    "source_sha256": digest("dist/atlas_ros-8.2.1.tar.gz"),
    "wheel_sha256": digest("dist/atlas_ros-8.2.1-py3-none-any.whl"),
}
Path("build/V821_VALIDATION_RECEIPT.json").write_text(
    json.dumps(receipt, indent=2, sort_keys=True) + "\n"
)
PY
sha256sum build/V821_VALIDATION_RECEIPT.json build/V821_PACKAGE_CHECKSUMS.sha256 \
  > build/V821_EVIDENCE_CHECKSUMS.sha256
