#!/usr/bin/env bash
set -euo pipefail

: "${GH_TOKEN:?GH_TOKEN is required}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
: "${GITHUB_RUN_ID:?GITHUB_RUN_ID is required}"

CANDIDATE_SHA="${CANDIDATE_SHA:-$(git rev-parse HEAD)}"
ATLAS_VERSION="$(python - <<'PY'
import tomllib
from pathlib import Path
print(tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]["version"])
PY
)"
test "$ATLAS_VERSION" = "7.0.0rc1"
test "$(python -c 'import atlas_ros; print(atlas_ros.__version__)')" = "$ATLAS_VERSION"
test "$(git rev-parse HEAD)" = "$CANDIDATE_SHA"

rm -rf v700-candidate-evidence v700-publication dist build clean-v700 restore-v650 restore-v620 v650-assets v620-assets
mkdir -p v700-candidate-evidence/test-results v700-candidate-evidence/benchmarks v700-publication

ruff check .
python scripts/validate_architecture.py
mypy src
pytest --junitxml=v700-candidate-evidence/test-results/pytest.xml \
  --cov-report=json:v700-candidate-evidence/test-results/coverage.json
python scripts/evaluate_execution_planning.py \
  --dataset benchmarks/execution-planning-v1.json \
  --output v700-candidate-evidence/benchmarks/execution-planning.json
python scripts/scan_candidate_secrets.py \
  --root . --output v700-candidate-evidence/secret-scan.json

python - <<'PY'
import hashlib
import subprocess
from pathlib import Path

output = Path("v700-candidate-evidence/SOURCE_MANIFEST.sha256")
paths = subprocess.check_output(["git", "ls-files", "-z"]).split(b"\0")
lines = []
for raw in paths:
    if not raw:
        continue
    path = Path(raw.decode("utf-8"))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    lines.append(f"{digest}  {path.as_posix()}")
output.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

python -m build
SDIST="atlas_ros-${ATLAS_VERSION}.tar.gz"
WHEEL="atlas_ros-${ATLAS_VERSION}-py3-none-any.whl"
test -f "dist/$SDIST"
test -f "dist/$WHEEL"
sha256sum "dist/$SDIST" "dist/$WHEEL" > v700-candidate-evidence/CANDIDATE_ARTIFACTS.sha256

python -m venv clean-v700
clean-v700/bin/python -m pip install --disable-pip-version-check "dist/$WHEEL"
clean-v700/bin/python - <<'PY'
import atlas_ros
from atlas_ros.application import AttendedExecutionService, CanonicalProcessingCoordinator
from atlas_ros.contracts.authority import IntegrationInventorySnapshot, SystemStateSnapshot
from atlas_ros.contracts.execution import AuthorizedExecutionPlan, PipelineRunEnvelope
from atlas_ros.kernel import RuntimeKernel

assert atlas_ros.__version__ == "7.0.0rc1"
assert all(
    (
        AttendedExecutionService,
        AuthorizedExecutionPlan,
        CanonicalProcessingCoordinator,
        IntegrationInventorySnapshot,
        PipelineRunEnvelope,
        RuntimeKernel,
        SystemStateSnapshot,
    )
)
PY

gh release download v6.5.0 --repo "$GITHUB_REPOSITORY" \
  --pattern 'atlas_ros-6.5.0*.whl' --dir v650-assets
gh release download v6.2.0 --repo "$GITHUB_REPOSITORY" \
  --pattern 'atlas_ros-6.2.0*.whl' --dir v620-assets
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

cp release/RELEASE_SCOPE_V700.md v700-candidate-evidence/RELEASE_SCOPE.md
cp release/RELEASE_NOTES_V700.md v700-candidate-evidence/RELEASE_NOTES.md
export CANDIDATE_SHA GITHUB_RUN_ID ATLAS_VERSION SDIST WHEEL
python - <<'PY'
import hashlib
import json
import os
import tomllib
from datetime import UTC, datetime
from pathlib import Path

root = Path("v700-candidate-evidence")
dist = Path("dist")
version = os.environ["ATLAS_VERSION"]
sdist = os.environ["SDIST"]
wheel = os.environ["WHEEL"]

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]
status = {
    "release": "Atlas ROS v7.0.0rc1",
    "status": "candidate_validated_not_promoted",
    "candidate_sha": os.environ["CANDIDATE_SHA"],
    "workflow_run_id": os.environ["GITHUB_RUN_ID"],
    "source_distribution": sdist,
    "source_sha256": digest(dist / sdist),
    "wheel": wheel,
    "wheel_sha256": digest(dist / wheel),
    "active_production_release": "v6.5.0",
    "immediate_rollback_release": "v6.2.0",
    "active_production_restored": True,
    "immediate_rollback_restored": True,
    "google_drive_required_for_restoration": False,
    "provider_writes": 0,
    "production_promotion_authorized": False,
    "final_tag_created": False,
    "final_release_published": False,
    "authority_activated": False,
    "drive_retired": False,
    "generated_at": datetime.now(UTC).isoformat(),
}
status_path = root / "V700_CANDIDATE_STATUS.json"
status_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")

identity = {
    "schema_version": "1.0",
    "release_version": version,
    "candidate_commit": status["candidate_sha"],
    "workflow_run_id": status["workflow_run_id"],
    "source": {"name": sdist, "sha256": status["source_sha256"]},
    "wheel": {"name": wheel, "sha256": status["wheel_sha256"]},
    "production_baseline": {
        "version": "6.5.0",
        "commit": "bb6d6fea70d6824c9bc6a42e63ba36cc88029260",
    },
    "immediate_rollback": {
        "version": "6.2.0",
        "commit": "863d5ddf9ebd4723200166cf31c7acd93ebec54f",
    },
    "provider_writes": 0,
    "promotion_authorized": False,
}
(root / "FINAL_IDENTITY_CANDIDATE.json").write_text(
    json.dumps(identity, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)

components = [
    {
        "type": "library",
        "name": dependency.split("<", 1)[0].split(">", 1)[0].split("=", 1)[0],
        "version": dependency,
    }
    for dependency in project["dependencies"]
]
sbom = {
    "bomFormat": "CycloneDX",
    "specVersion": "1.5",
    "serialNumber": f"urn:uuid:atlas-ros-{status['candidate_sha']}",
    "version": 1,
    "metadata": {
        "timestamp": status["generated_at"],
        "component": {
            "type": "application",
            "name": "atlas-ros",
            "version": version,
            "hashes": [
                {"alg": "SHA-256", "content": status["wheel_sha256"]},
            ],
        },
    },
    "components": components,
}
(root / "SBOM.cdx.json").write_text(
    json.dumps(sbom, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)

(root / "RELEASE_MANIFEST_V700_CANDIDATE.md").write_text(
    f"""# Atlas ROS v7.0.0rc1 Candidate Manifest

Status: Validated candidate only; not promoted.

- Candidate commit: `{status['candidate_sha']}`
- Validation workflow run: `{status['workflow_run_id']}`
- Source SHA-256: `{status['source_sha256']}`
- Wheel SHA-256: `{status['wheel_sha256']}`
- Active production restored: `v6.5.0`
- Immediate rollback restored: `v6.2.0`
- Google Drive required for restoration: `false`
- Provider writes during validation: `0`
- Final production promotion: not authorized
- Final tag created: `false`
- Final GitHub Release published: `false`
- Authority activated: `false`
- Google Drive retired: `false`

This candidate cannot alter live production authority, publish the final release, create or move the final tag, retire Google Drive, or expand provider permissions without a separate exact-package production decision.
""",
    encoding="utf-8",
)
PY

(
  cd v700-candidate-evidence
  find . -type f ! -name EVIDENCE_CHECKSUMS.sha256 -print0 | sort -z |
    xargs -0 sha256sum > EVIDENCE_CHECKSUMS.sha256
  sha256sum -c EVIDENCE_CHECKSUMS.sha256
)
cp "dist/$SDIST" "dist/$WHEEL" v700-publication/
cp -R v700-candidate-evidence v700-publication/evidence
tar -czf v700-publication/Atlas_ROS_v7.0.0rc1_candidate_evidence.tar.gz \
  -C v700-publication evidence
(
  cd v700-publication
  find . -maxdepth 1 -type f ! -name PUBLICATION_CHECKSUMS.sha256 -print0 | sort -z |
    xargs -0 sha256sum > PUBLICATION_CHECKSUMS.sha256
  sha256sum -c PUBLICATION_CHECKSUMS.sha256
)
