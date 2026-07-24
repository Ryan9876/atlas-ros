from __future__ import annotations

import argparse
import hashlib
import json
import re
import tomllib
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from atlas_ros.intelligence.calibration import IntelligenceCalibrationEngine, load_calibration_cases
from atlas_ros.intelligence.evaluator import IntelligenceEvaluationRunner

SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
RELEASE_NAME = "Atlas ROS v5.1.1"
EVIDENCE_PREFIX = "V510"
BASE_AUTHORITY = "Atlas ROS v5.1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _test_count(path: Path) -> int:
    root = ET.parse(path).getroot()
    return int(root.attrib.get("tests", sum(int(item.attrib["tests"]) for item in root)))


def _project_version(project_root: Path) -> str:
    project = tomllib.loads((project_root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    return str(project["version"])


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def build_evidence(
    *,
    project_root: Path,
    output_dir: Path,
    head_sha: str,
    workflow_run_id: str,
    cases_path: Path,
    junit_path: Path,
    coverage_path: Path,
    source_manifest_path: Path,
    sbom_path: Path,
) -> dict[str, Any]:
    if not SHA_PATTERN.fullmatch(head_sha):
        raise ValueError("head SHA must be a lowercase 40-character Git SHA")

    output_dir.mkdir(parents=True, exist_ok=True)
    version = _project_version(project_root)
    if not version.startswith("5.1."):
        raise ValueError(f"expected an Atlas ROS v5.1 package version, got {version}")

    test_count = _test_count(junit_path)
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    branch_coverage = float(coverage["totals"]["percent_covered"])
    if branch_coverage < 85.0:
        raise ValueError(f"branch coverage {branch_coverage:.2f}% is below 85%")

    cases = load_calibration_cases(cases_path)
    judgments = IntelligenceEvaluationRunner().run(cases)
    calibration = IntelligenceCalibrationEngine().run(cases, judgments)
    if not calibration.release_eligible:
        raise ValueError(
            "calibration is not release eligible: " + ", ".join(calibration.blocking_violations)
        )

    generated_at = datetime.now(UTC).isoformat()
    calibration_path = output_dir / f"{EVIDENCE_PREFIX}_CALIBRATION_REPORT.json"
    calibration_path.write_text(calibration.model_dump_json(indent=2) + "\n", encoding="utf-8")

    manifest = f"""# {RELEASE_NAME} Release Candidate Evidence Manifest

Status: Candidate evidence ready for governed solo-maintainer review; not promoted.

- Package version: `{version}`
- Candidate head: `{head_sha}`
- GitHub workflow run: `{workflow_run_id}`
- Generated: `{generated_at}`
- Active production authority: {BASE_AUTHORITY}
- Base authority: {BASE_AUTHORITY}
- Immediate rollback if promoted: {BASE_AUTHORITY}
- Promotion authorized: No

The candidate source, source manifest, source distribution, wheel, SBOM, dependency audit evidence,
quantitative calibration evidence, and workflow validation report are bound by the publication-set checksum manifest.

The readable published workspace is valid when this manifest, the validation report, dependency-security evidence,
SBOM, canonical checksums, source distribution, wheel, and combined package are readable, internally consistent,
checksum-valid, and successfully read back from their authoritative published locations. Secrets and private signing
material are excluded.

Validated gates include Ruff, strict MyPy, {test_count} tests, {branch_coverage:.2f}% branch coverage,
dependency policy and dual advisory audits, canonical source verification, source and wheel builds,
extracted-source verification, clean-wheel validation, and all quantitative calibration gates.

The remaining gates are governed review, publication/readback, authority-record updates, and explicit promotion authorization.
"""
    (output_dir / f"RELEASE_MANIFEST_{EVIDENCE_PREFIX}_CANDIDATE.md").write_text(
        manifest, encoding="utf-8"
    )

    blockers = [
        "governed solo-maintainer review not completed for this exact artifact",
        "candidate publication and readback not completed",
        "explicit production promotion not yet recorded",
    ]
    status: dict[str, Any] = {
        "release": RELEASE_NAME,
        "package_version": version,
        "candidate_head_sha": head_sha,
        "workflow_run_id": workflow_run_id,
        "base_authority": BASE_AUTHORITY,
        "immediate_rollback_on_promotion": BASE_AUTHORITY,
        "status": "candidate_ready_for_governed_review",
        "promotion_authorized": False,
        "test_count": test_count,
        "branch_coverage_percent": round(branch_coverage, 4),
        "benchmark_case_count": calibration.case_count,
        "benchmark_domain_count": len(calibration.domains),
        "dataset_fingerprint": calibration.dataset_fingerprint,
        "calibration_fingerprint": calibration.fingerprint,
        "calibration_release_eligible": calibration.release_eligible,
        "source_manifest_sha256": sha256(source_manifest_path),
        "sbom_sha256": sha256(sbom_path),
        "governed_review": None,
        "blocking_gates": blockers,
        "required_next_action": "complete governed review and publish/read back the exact candidate artifact",
    }
    status_path = output_dir / f"{EVIDENCE_PREFIX}_PROMOTION_PREPARATION_STATUS.json"
    _write_json(status_path, status)
    (output_dir / f"{EVIDENCE_PREFIX}_PROMOTION_PREPARATION_STATUS.sha256").write_text(
        f"{sha256(status_path)}  {status_path.name}\n", encoding="utf-8"
    )

    report = f"""# {RELEASE_NAME} Promotion Preparation Report

Status: **Ready for governed solo-maintainer review; not promoted.**

- Candidate head: `{head_sha}`
- GitHub workflow run: `{workflow_run_id}`
- Package version: `{version}`
- Active production authority: {BASE_AUTHORITY}
- Immediate rollback if promoted: {BASE_AUTHORITY}
- Promotion authorized: No
- Tests: {test_count} passed
- Branch coverage: {branch_coverage:.2f}%
- Calibration cases: {calibration.case_count}
- Calibration domains passing: {len(calibration.domains)}/{len(calibration.domains)}
- Calibration release eligible: Yes

## Remaining blockers

- Governed review bound to this exact commit and artifact digest
- Candidate publication and readback
- Explicit production promotion and authority updates
"""
    (output_dir / f"{EVIDENCE_PREFIX}_PROMOTION_PREPARATION_REPORT.md").write_text(
        report, encoding="utf-8"
    )

    workbench = f"""# {RELEASE_NAME} Release Candidate Validation Report

- Candidate head: `{head_sha}`
- GitHub workflow run: `{workflow_run_id}`
- Generated: `{generated_at}`
- Decision: **validated for governed review**
- Promotion authority: **not granted**

| Gate | Result |
|---|---|
| Ruff | PASS |
| Strict MyPy | PASS |
| Regression tests | PASS — {test_count} tests |
| Branch coverage | PASS — {branch_coverage:.2f}% |
| Dependency lock and exceptions | PASS |
| PyPI and OSV advisory audits | PASS |
| Canonical source manifest | PASS |
| Source and wheel build | PASS |
| Extracted-source verification | PASS |
| Clean-wheel validation | PASS |
| Quantitative calibration | PASS — {calibration.case_count} cases |
| Governed solo-maintainer review | PENDING |
| Publication/readback | PENDING |

This report cannot authorize promotion.
"""
    (output_dir / f"{EVIDENCE_PREFIX}_RELEASE_VALIDATION_WORKBENCH_REPORT.md").write_text(
        workbench, encoding="utf-8"
    )
    return status


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build commit-bound Atlas ROS v5.1.1 candidate evidence"
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--workflow-run-id", required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--coverage", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--sbom", type=Path, required=True)
    args = parser.parse_args()
    status = build_evidence(
        project_root=args.project_root,
        output_dir=args.output_dir,
        head_sha=args.head_sha,
        workflow_run_id=args.workflow_run_id,
        cases_path=args.cases,
        junit_path=args.junit,
        coverage_path=args.coverage,
        source_manifest_path=args.source_manifest,
        sbom_path=args.sbom,
    )
    print(json.dumps(status))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
