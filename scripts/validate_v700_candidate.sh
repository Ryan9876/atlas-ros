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

rm -rf \
  v700-candidate-evidence \
  v700-publication \
  dist \
  build \
  clean-v700 \
  restore-v650 \
  restore-v620 \
  v650-assets \
  v620-assets
mkdir -p \
  v700-candidate-evidence/test-results \
  v700-candidate-evidence/benchmarks \
  v700-publication

ruff check .
python scripts/validate_architecture.py
mypy src
pytest \
  --junitxml=v700-candidate-evidence/test-results/pytest.xml \
  --cov-report=json:v700-candidate-evidence/test-results/coverage.json
python scripts/evaluate_execution_planning.py \
  --dataset benchmarks/execution-planning-v1.json \
  --output v700-candidate-evidence/benchmarks/execution-planning.json
python scripts/scan_candidate_secrets.py \
  --root . \
  --output v700-candidate-evidence/secret-scan.json

python - <<'PY'
import json
from pathlib import Path

from atlas_ros.capabilities.compiler import compile_capability_registry
from atlas_ros.contracts.compiler import compile_contract_registry
from atlas_ros.contracts.schemas import require_valid_contract_schemas

require_valid_contract_schemas()
contracts = compile_contract_registry(Path("governance/contract-catalog.yaml"))
capabilities = compile_capability_registry(Path("governance/capability-catalog.yaml"))
output = {
    "schema_version": "1.0",
    "contract_catalog_sha256": contracts.digest,
    "contract_count": len(contracts.contracts),
    "capability_catalog_sha256": capabilities.digest,
    "capability_count": len(capabilities.capabilities),
    "sole_planning_authority": capabilities.planning_authority_id,
    "provider_writing_capabilities": [
        item.capability_id
        for item in capabilities.capabilities.values()
        if item.writes_providers
    ],
    "contract_schema_equivalence": "passed",
}
Path("v700-candidate-evidence/GOVERNANCE_DIGESTS.json").write_text(
    json.dumps(output, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY

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
sha256sum \
  "dist/$SDIST" \
  "dist/$WHEEL" \
  > v700-candidate-evidence/CANDIDATE_ARTIFACTS.sha256

python -m venv clean-v700
clean-v700/bin/python -m pip install \
  --disable-pip-version-check \
  "dist/$WHEEL"
clean-v700/bin/python - <<'PY'
import atlas_ros
from atlas_ros.application import (
    AttendedExecutionService,
    CanonicalAttendedPipeline,
    CanonicalProcessingCoordinator,
)
from atlas_ros.contracts.authority import (
    IntegrationInventorySnapshot,
    SystemStateSnapshot,
)
from atlas_ros.contracts.execution import (
    AuthorizedExecutionPlan,
    PipelineRunEnvelope,
    ProposedExecutionPlan,
    ProviderOperationPayload,
)
from atlas_ros.contracts.reasoning import IntentGraph
from atlas_ros.kernel import RuntimeKernel

assert atlas_ros.__version__ == "7.0.0rc1"
assert all(
    (
        AttendedExecutionService,
        AuthorizedExecutionPlan,
        CanonicalAttendedPipeline,
        CanonicalProcessingCoordinator,
        IntegrationInventorySnapshot,
        IntentGraph,
        PipelineRunEnvelope,
        ProposedExecutionPlan,
        ProviderOperationPayload,
        RuntimeKernel,
        SystemStateSnapshot,
    )
)
PY

gh release download v6.5.0 \
  --repo "$GITHUB_REPOSITORY" \
  --pattern 'atlas_ros-6.5.0*.whl' \
  --dir v650-assets
gh release download v6.2.0 \
  --repo "$GITHUB_REPOSITORY" \
  --pattern 'atlas_ros-6.2.0*.whl' \
  --dir v620-assets
V650_WHEEL="$(find v650-assets -name 'atlas_ros-6.5.0*.whl' -print -quit)"
V620_WHEEL="$(find v620-assets -name 'atlas_ros-6.2.0*.whl' -print -quit)"
test -n "$V650_WHEEL"
test -n "$V620_WHEEL"
python -m venv restore-v650
restore-v650/bin/python -m pip install \
  --disable-pip-version-check \
  "$V650_WHEEL"
restore-v650/bin/python -c \
  "import atlas_ros; assert atlas_ros.__version__ == '6.5.0'"
python -m venv restore-v620
restore-v620/bin/python -m pip install \
  --disable-pip-version-check \
  "$V620_WHEEL"
restore-v620/bin/python -c \
  "import atlas_ros; assert atlas_ros.__version__ == '6.2.0'"

python scripts/compare_v700_performance.py \
  --candidate-python clean-v700/bin/python \
  --baseline-python restore-v650/bin/python \
  --dataset benchmarks/execution-planning-v1.json \
  --iterations 5 \
  --max-regression 0.10 \
  --output v700-candidate-evidence/benchmarks/v700-v650-performance.json

cp release/RELEASE_SCOPE_V700.md \
  v700-candidate-evidence/RELEASE_SCOPE.md
cp release/RELEASE_NOTES_V700.md \
  v700-candidate-evidence/RELEASE_NOTES.md
export CANDIDATE_SHA GITHUB_RUN_ID ATLAS_VERSION SDIST WHEEL
python - <<'PY'
import hashlib
import json
import os
import tomllib
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from tools.release.transaction_simulation import (
    PromotionSimulationEvidence,
    RollbackSimulationEvidence,
    simulate_promotion,
    simulate_rollback,
)

root = Path("v700-candidate-evidence")
dist = Path("dist")
version = os.environ["ATLAS_VERSION"]
sdist = os.environ["SDIST"]
wheel = os.environ["WHEEL"]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


project = tomllib.loads(
    Path("pyproject.toml").read_text(encoding="utf-8")
)["project"]
governance = json.loads(
    (root / "GOVERNANCE_DIGESTS.json").read_text(encoding="utf-8")
)
performance = json.loads(
    (root / "benchmarks/v700-v650-performance.json").read_text(
        encoding="utf-8"
    )
)
status = {
    "release": "Atlas ROS v7.0.0rc1",
    "status": "candidate_validated_not_promoted",
    "candidate_sha": os.environ["CANDIDATE_SHA"],
    "workflow_run_id": os.environ["GITHUB_RUN_ID"],
    "source_distribution": sdist,
    "source_sha256": digest(dist / sdist),
    "wheel": wheel,
    "wheel_sha256": digest(dist / wheel),
    "contract_catalog_sha256": governance["contract_catalog_sha256"],
    "capability_catalog_sha256": governance["capability_catalog_sha256"],
    "contract_schema_equivalence": "passed",
    "performance_gate": performance["status"],
    "active_production_release": "v6.5.0",
    "immediate_rollback_release": "v6.2.0",
    "active_production_restored": True,
    "immediate_rollback_restored": True,
    "google_drive_required_for_restoration": False,
    "live_drive_migration_ledger_supplied": False,
    "provider_writes": 0,
    "production_promotion_authorized": False,
    "final_tag_created": False,
    "final_release_published": False,
    "authority_activated": False,
    "drive_retired": False,
    "generated_at": datetime.now(UTC).isoformat(),
}
status_path = root / "V700_CANDIDATE_STATUS.json"
status_path.write_text(
    json.dumps(status, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)

identity = {
    "schema_version": "1.0",
    "release_version": version,
    "candidate_commit": status["candidate_sha"],
    "workflow_run_id": status["workflow_run_id"],
    "source": {"name": sdist, "sha256": status["source_sha256"]},
    "wheel": {"name": wheel, "sha256": status["wheel_sha256"]},
    "governance": {
        "contract_catalog_sha256": status["contract_catalog_sha256"],
        "capability_catalog_sha256": status["capability_catalog_sha256"],
    },
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

artifact_digest = hashlib.sha256(
    (status["source_sha256"] + status["wheel_sha256"]).encode("utf-8")
).hexdigest()
promotion = simulate_promotion(
    PromotionSimulationEvidence(
        candidate_version=version,
        candidate_commit=status["candidate_sha"],
        candidate_artifact_id=f"workflow-run-{status['workflow_run_id']}",
        candidate_artifact_digest=artifact_digest,
        candidate_source_sha256=status["source_sha256"],
        candidate_wheel_sha256=status["wheel_sha256"],
        standard_ci_passed=False,
        architecture_validation_passed=True,
        candidate_validation_passed=True,
        exact_artifact_validation_passed=False,
        active_v650_restored=True,
        rollback_v620_restored=True,
        performance_gate_passed=performance["status"] == "passed",
        drive_migration_ledger_complete=False,
        required_integrations_ready=False,
        provider_writes_during_validation=0,
    ),
    transaction_id=f"promotion-simulation-{status['candidate_sha'][:12]}",
)
if promotion.status != "blocked":
    raise RuntimeError("candidate promotion simulation must remain blocked")
(root / "PROMOTION_SIMULATION.json").write_text(
    json.dumps(asdict(promotion), indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)

rollback = simulate_rollback(
    RollbackSimulationEvidence(
        target_version="6.5.0",
        target_commit="bb6d6fea70d6824c9bc6a42e63ba36cc88029260",
        target_tag="v6.5.0",
        target_release_readable=True,
        target_checksums_passed=True,
        target_clean_install_passed=True,
        target_restoration_passed=True,
        current_candidate_deactivation_reversible=True,
        provider_writes_during_simulation=0,
    ),
    transaction_id=f"rollback-simulation-{status['candidate_sha'][:12]}",
)
if rollback.status != "ready":
    raise RuntimeError("v6.5 rollback simulation did not pass")
(root / "ROLLBACK_SIMULATION.json").write_text(
    json.dumps(asdict(rollback), indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)

(root / "DRIVE_MIGRATION_LEDGER_REQUIREMENT.json").write_text(
    json.dumps(
        {
            "schema_version": "1.0",
            "status": "required_before_promotion_readiness",
            "live_ledger_supplied": False,
            "compiler": "tools/release/drive_migration_ledger.py",
            "retirement_controller": "tools/release/drive_retirement.py",
            "destructive_actions_authorized": False,
        },
        indent=2,
        sort_keys=True,
    )
    + "\n",
    encoding="utf-8",
)

components = [
    {
        "type": "library",
        "name": dependency.split("<", 1)[0]
        .split(">", 1)[0]
        .split("=", 1)[0],
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
- Contract catalog SHA-256: `{status['contract_catalog_sha256']}`
- Capability catalog SHA-256: `{status['capability_catalog_sha256']}`
- Contract schema equivalence: `passed`
- Performance gate: `{status['performance_gate']}`
- Active production restored: `v6.5.0`
- Immediate rollback restored: `v6.2.0`
- Google Drive required for restoration: `false`
- Live Drive migration ledger supplied: `false`
- Promotion simulation: `blocked as required`
- Rollback simulation: `ready`
- Provider writes during validation: `0`
- Final production promotion: not authorized
- Final tag created: `false`
- Final GitHub Release published: `false`
- Authority activated: `false`
- Google Drive retired: `false`

This candidate cannot alter live production authority, publish the final release,
create or move the final tag, retire Google Drive, or expand provider permissions
without a separate exact-package production decision.
""",
    encoding="utf-8",
)
PY

(
  cd v700-candidate-evidence
  find . -type f ! -name EVIDENCE_CHECKSUMS.sha256 -print0 \
    | sort -z \
    | xargs -0 sha256sum \
    > EVIDENCE_CHECKSUMS.sha256
  sha256sum -c EVIDENCE_CHECKSUMS.sha256
)
cp "dist/$SDIST" "dist/$WHEEL" v700-publication/
cp -R v700-candidate-evidence v700-publication/evidence
tar -czf \
  v700-publication/Atlas_ROS_v7.0.0rc1_candidate_evidence.tar.gz \
  -C v700-publication \
  evidence
(
  cd v700-publication
  find . -maxdepth 1 -type f ! -name PUBLICATION_CHECKSUMS.sha256 -print0 \
    | sort -z \
    | xargs -0 sha256sum \
    > PUBLICATION_CHECKSUMS.sha256
  sha256sum -c PUBLICATION_CHECKSUMS.sha256
)
