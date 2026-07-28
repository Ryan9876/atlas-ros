#!/usr/bin/env bash
set -euo pipefail

: "${GH_TOKEN:?GH_TOKEN is required}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
: "${FINAL_SHA:?FINAL_SHA is required}"
: "${DECISION_RECORD_URL:?DECISION_RECORD_URL is required}"

VERSION="$(python - <<'PY'
import tomllib
from pathlib import Path
print(tomllib.loads(Path('pyproject.toml').read_text(encoding='utf-8'))['project']['version'])
PY
)"
test "$VERSION" = "7.0.1"
test "$(python -c 'import atlas_ros; print(atlas_ros.__version__)')" = "$VERSION"
test "$(git rev-parse HEAD)" = "$FINAL_SHA"
test -f release/RELEASE_MANIFEST_V701.md

grep -Fq 'Integration Inventory authority: https://app.notion.com/p/8ba4fafb5ce244ef9add3013aff3746b' release/RELEASE_MANIFEST_V701.md
grep -Fq 'google_drive_bootstrap_forbidden: true' governance/release-policy.yaml
grep -Fq 'required_production_integrations:' governance/release-policy.yaml
grep -Fq 'google_drive_is_forbidden' policies/authority/bootstrap.yaml

if gh api "repos/${GITHUB_REPOSITORY}/git/ref/tags/v7.0.1" >/dev/null 2>&1; then
  echo 'v7.0.1 tag already exists before authorization' >&2
  exit 1
fi
if gh release view v7.0.1 --repo "$GITHUB_REPOSITORY" >/dev/null 2>&1; then
  echo 'v7.0.1 release already exists before authorization' >&2
  exit 1
fi

rm -rf \
  v701-evidence \
  v701-publication \
  dist \
  build \
  clean-v701 \
  restore-v700 \
  restore-v650 \
  v700-assets \
  v650-assets
mkdir -p v701-evidence/staged-authority v701-publication

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
Path('v701-evidence/SOURCE_MANIFEST.sha256').write_text(
    '\n'.join(lines) + '\n', encoding='utf-8'
)
PY

python -m build
SDIST="atlas_ros-${VERSION}.tar.gz"
WHEEL="atlas_ros-${VERSION}-py3-none-any.whl"
test -f "dist/$SDIST"
test -f "dist/$WHEEL"
sha256sum "dist/$SDIST" "dist/$WHEEL" > v701-evidence/FINAL_ARTIFACTS.sha256

python -m venv clean-v701
clean-v701/bin/python -m pip install --disable-pip-version-check "dist/$WHEEL"
clean-v701/bin/python - <<'PY'
from importlib.metadata import version
import atlas_ros

assert version('atlas-ros') == '7.0.1'
assert atlas_ros.__version__ == '7.0.1'
PY
clean-v701/bin/atlas status --json > v701-evidence/RUNTIME_STATUS.json
clean-v701/bin/atlas verify --json > v701-evidence/RUNTIME_VERIFY.json

mkdir -p v700-assets v650-assets
gh release download v7.0.0 --repo "$GITHUB_REPOSITORY" --dir v700-assets
gh release download v6.5.0 --repo "$GITHUB_REPOSITORY" --dir v650-assets
(cd v700-assets && sha256sum -c CHECKSUMS.sha256)
(cd v650-assets && sha256sum -c CHECKSUMS.sha256)
V700_WHEEL="$(find v700-assets -name 'atlas_ros-7.0.0*.whl' -print -quit)"
V650_WHEEL="$(find v650-assets -name 'atlas_ros-6.5.0*.whl' -print -quit)"
test -n "$V700_WHEEL"
test -n "$V650_WHEEL"
python -m venv restore-v700
restore-v700/bin/python -m pip install --disable-pip-version-check "$V700_WHEEL"
restore-v700/bin/python -c "import atlas_ros; assert atlas_ros.__version__ == '7.0.0'"
python -m venv restore-v650
restore-v650/bin/python -m pip install --disable-pip-version-check "$V650_WHEEL"
restore-v650/bin/python -c "import atlas_ros; assert atlas_ros.__version__ == '6.5.0'"

python scripts/compare_v700_performance.py \
  --candidate-python clean-v701/bin/python \
  --baseline-python restore-v700/bin/python \
  --baseline-version 7.0.0 \
  --dataset benchmarks/execution-planning-v1.json \
  --iterations 7 \
  --max-regression 0.10 \
  --output v701-evidence/V701_V700_PERFORMANCE.json

export VERSION FINAL_SHA SDIST WHEEL DECISION_RECORD_URL
python - <<'PY'
import hashlib
import json
import os
import tomllib
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from atlas_ros.contracts.authority import (
    IntegrationInventorySnapshot,
    IntegrationStatusSnapshot,
    SystemStateSnapshot,
)
from atlas_ros.kernel.bootstrap import initialize_full
from atlas_ros.kernel.digests import sha256_digest
from tools.release.authority_compiler import (
    ActiveReleaseSpec,
    AuthorityCompilationSpec,
    RollbackReleaseSpec,
    compile_authority,
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


version = os.environ['VERSION']
commit = os.environ['FINAL_SHA']
manifest_path = Path('release/RELEASE_MANIFEST_V701.md')
manifest = manifest_path.read_text(encoding='utf-8')
source = Path('dist') / os.environ['SDIST']
wheel = Path('dist') / os.environ['WHEEL']
source_sha = digest(source)
wheel_sha = digest(wheel)
manifest_sha = sha256_digest(manifest)

compiled = compile_authority(
    AuthorityCompilationSpec(
        active=ActiveReleaseSpec(
            version=version,
            immutable_commit=commit,
            tag=f'v{version}',
            manifest_path=manifest_path.as_posix(),
            manifest_url=(
                f'https://github.com/{os.environ.get("GITHUB_REPOSITORY", "Ryan9876/atlas-ros")}'
                f'/blob/{commit}/{manifest_path.as_posix()}'
            ),
            manifest_sha256=manifest_sha,
            release_url=f'https://github.com/Ryan9876/atlas-ros/releases/tag/v{version}',
            source_sha256=source_sha,
            wheel_sha256=wheel_sha,
        ),
        rollback=RollbackReleaseSpec(
            version='6.5.0',
            immutable_commit='bb6d6fea70d6824c9bc6a42e63ba36cc88029260',
            tag='v6.5.0',
            release_url='https://github.com/Ryan9876/atlas-ros/releases/tag/v6.5.0',
        ),
        historical_rollbacks=(
            RollbackReleaseSpec(
                version='6.2.0',
                immutable_commit='863d5ddf9ebd4723200166cf31c7acd93ebec54f',
                tag='v6.2.0',
                release_url='https://github.com/Ryan9876/atlas-ros/releases/tag/v6.2.0',
            ),
        ),
        notion_system_state_url='https://app.notion.com/p/3a0b8344ad2c81d1b545d0266b7cd809',
        last_promotion_transaction_id='candidate-v7.0.1-not-authorized',
        last_verified_at=datetime.now(UTC).isoformat(),
    )
)
staged = Path('v701-evidence/staged-authority')
(staged / 'AUTHORITY.json').write_text(compiled.authority_json, encoding='utf-8')
(staged / 'RELEASE_INDEX.md').write_text(compiled.release_index_markdown, encoding='utf-8')


class Reader:
    def read_text(self, path: PurePosixPath, *, ref: str) -> str:
        if path.as_posix() == 'governance/AUTHORITY.json' and ref == 'HEAD':
            return compiled.authority_json
        if path.as_posix() == 'governance/RELEASE_INDEX.md' and ref == 'HEAD':
            return compiled.release_index_markdown
        if path.as_posix() == manifest_path.as_posix() and ref == commit:
            return manifest
        raise KeyError((path.as_posix(), ref))


class DynamicReader:
    def read_system_state(self, url: str) -> SystemStateSnapshot:
        return SystemStateSnapshot(
            active_version=version,
            immediate_rollback_version='6.5.0',
            authority_model_version='7.0',
            published_workspace_valid=True,
            last_verified_at=datetime.now(UTC),
        )

    def read_integration_inventory(self, url: str) -> IntegrationInventorySnapshot:
        def item(name: str, required: bool, connection: str = 'connected') -> IntegrationStatusSnapshot:
            return IntegrationStatusSnapshot(
                name=name,
                required=required,
                connection_status=connection,
                approval_status='approved',
                acceptance_status='passed',
                current=True,
                least_privilege_verified=True,
            )
        return IntegrationInventorySnapshot(
            integrations=(
                item('GitHub', True),
                item('Notion', True),
                item('Todoist', True),
                item('Google Drive', False, 'disconnected'),
            ),
            last_verified_at=datetime.now(UTC),
        )


context = initialize_full(Reader(), DynamicReader())
assert context.active_version == version

project = tomllib.loads(Path('pyproject.toml').read_text(encoding='utf-8'))['project']
sbom = {
    'bomFormat': 'CycloneDX',
    'specVersion': '1.5',
    'version': 1,
    'metadata': {
        'component': {'type': 'application', 'name': project['name'], 'version': version},
    },
    'components': [
        {'type': 'library', 'name': dependency.split('>=', 1)[0].split('<', 1)[0], 'version': 'governed-by-requirements.runtime.lock'}
        for dependency in project['dependencies']
    ],
}
Path('v701-evidence/SBOM.cdx.json').write_text(
    json.dumps(sbom, indent=2, sort_keys=True) + '\n', encoding='utf-8'
)
identity = {
    'schema_version': '1.0',
    'release_version': version,
    'candidate_commit': commit,
    'source': {'name': source.name, 'sha256': source_sha},
    'wheel': {'name': wheel.name, 'sha256': wheel_sha},
    'immutable_manifest': {
        'path': manifest_path.as_posix(),
        'sha256': manifest_sha,
    },
    'authority_json_sha256': compiled.authority_sha256,
    'release_index_sha256': compiled.release_index_sha256,
    'required_integrations': ['GitHub', 'Notion', 'Todoist'],
    'google_drive_required': False,
    'google_drive_read_during_initialization': False,
    'immediate_rollback': {
        'version': '6.5.0',
        'commit': 'bb6d6fea70d6824c9bc6a42e63ba36cc88029260',
    },
    'historical_rollback': {
        'version': '6.2.0',
        'commit': '863d5ddf9ebd4723200166cf31c7acd93ebec54f',
    },
    'decision_record_url': os.environ['DECISION_RECORD_URL'],
    'provider_writes': 0,
    'production_authorized': False,
    'published': False,
    'authority_activated': False,
}
Path('v701-evidence/FINAL_IDENTITY_CANDIDATE.json').write_text(
    json.dumps(identity, indent=2, sort_keys=True) + '\n', encoding='utf-8'
)
controller = {
    'schema_version': '1.0',
    'status': 'validated_not_authorized',
    'release_version': version,
    'candidate_commit': commit,
    'required_integrations': ['GitHub', 'Notion', 'Todoist'],
    'google_drive_initialization_role': 'forbidden',
    'package_checksums_passed': True,
    'clean_install_passed': True,
    'v700_restoration_passed': True,
    'v650_restoration_passed': True,
    'provider_writes': 0,
    'blocking_conditions': [
        'candidate pull request must be merged',
        'exact package must receive separate Ryan production authorization',
        'immutable publication and independent readback must pass',
        'live GitHub and Notion authority activation must pass',
    ],
}
Path('v701-evidence/V701_FINAL_CONTROLLER_VALIDATION.json').write_text(
    json.dumps(controller, indent=2, sort_keys=True) + '\n', encoding='utf-8'
)
PY

cp "dist/$SDIST" "dist/$WHEEL" v701-publication/
cp release/RELEASE_MANIFEST_V701.md v701-publication/
cp release/RELEASE_NOTES_V701.md v701-publication/
cp release/RELEASE_SCOPE_V701.md v701-publication/
cp v701-evidence/FINAL_IDENTITY_CANDIDATE.json v701-publication/
cp v701-evidence/SBOM.cdx.json v701-publication/

(cd v701-evidence && find . -type f ! -name EVIDENCE_CHECKSUMS.sha256 -print0 | sort -z | xargs -0 sha256sum > EVIDENCE_CHECKSUMS.sha256 && sha256sum -c EVIDENCE_CHECKSUMS.sha256)
(cd v701-publication && find . -type f ! -name CHECKSUMS.sha256 -print0 | sort -z | xargs -0 sha256sum > CHECKSUMS.sha256 && sha256sum -c CHECKSUMS.sha256)
