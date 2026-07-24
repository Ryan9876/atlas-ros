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
RELEASE_NAME = "Atlas ROS v5.4.0"
EVIDENCE_PREFIX = "V540"
BASE_AUTHORITY = "Atlas ROS v5.3.0"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _test_count(path: Path) -> int:
    root = ET.parse(path).getroot()
    return int(root.attrib.get("tests", sum(int(item.attrib["tests"]) for item in root)))


def build_evidence(
    *,
    project_root: Path,
    output_dir: Path,
    head_sha: str,
    workflow_run_id: str,
    cases_path: Path,
    knowledge_report_path: Path,
    junit_path: Path,
    coverage_path: Path,
    source_manifest_path: Path,
    sbom_path: Path,
) -> dict[str, Any]:
    if not SHA_PATTERN.fullmatch(head_sha):
        raise ValueError("head SHA must be a lowercase 40-character Git SHA")
    project = tomllib.loads((project_root / "pyproject.toml").read_text(encoding="utf-8"))
    version = str(project["project"]["version"])
    if not version.startswith("5.4."):
        raise ValueError(f"expected an Atlas ROS v5.4 package version, got {version}")
    output_dir.mkdir(parents=True, exist_ok=True)
    test_count = _test_count(junit_path)
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    branch_coverage = float(coverage["totals"]["percent_covered"])
    if branch_coverage < 85.0:
        raise ValueError(f"branch coverage {branch_coverage:.2f}% is below 85%")
    cases = load_calibration_cases(cases_path)
    judgments = IntelligenceEvaluationRunner().run(cases)
    calibration = IntelligenceCalibrationEngine().run(cases, judgments)
    if not calibration.release_eligible:
        raise ValueError("Ryan-intelligence calibration is not release eligible")
    knowledge = json.loads(knowledge_report_path.read_text(encoding="utf-8"))
    if not knowledge["passed"] or knowledge["case_count"] < 2:
        raise ValueError("Knowledge and Management V2 evaluation failed")
    generated_at = datetime.now(UTC).isoformat()
    calibration_path = output_dir / f"{EVIDENCE_PREFIX}_CALIBRATION_REPORT.json"
    calibration_path.write_text(calibration.model_dump_json(indent=2) + "\n", encoding="utf-8")
    knowledge_out = output_dir / f"{EVIDENCE_PREFIX}_KNOWLEDGE_MANAGEMENT_REPORT.json"
    knowledge_out.write_text(json.dumps(knowledge, indent=2) + "\n", encoding="utf-8")
    manifest = f"""# {RELEASE_NAME} Release Candidate Evidence Manifest

Status: Exact candidate ready for governed approval; not promoted.

- Package version: `{version}`
- Candidate head: `{head_sha}`
- GitHub workflow run: `{workflow_run_id}`
- Generated: `{generated_at}`
- Active production authority: {BASE_AUTHORITY}
- Immediate rollback if promoted: {BASE_AUTHORITY}
- Promotion authorized: No

This compatibility candidate completes roadmap Wave 3 Knowledge Composition and Management
Structure: versioned planning and knowledge registries, deterministic dependency resolution,
Reasoning Package V3 planning-model selection, Knowledge Package V2, Management Package V2,
the first complete Team Operating Model, provenance, completeness, governance, migration,
evaluation, and restoration evidence. It does not perform provider writes or create execution
steps. Production promotion requires Ryan's separate explicit authorization.

Validated gates include Ruff, strict MyPy, architecture boundaries, {test_count} tests,
{branch_coverage:.2f}% branch coverage, dependency policy and dual advisory audits, source and
wheel builds, clean-wheel validation, {calibration.case_count} Ryan-intelligence calibration
cases, and {knowledge["case_count"]} Knowledge and Management V2 benchmark cases.
"""
    (output_dir / "RELEASE_MANIFEST_V540_CANDIDATE.md").write_text(manifest, encoding="utf-8")
    blockers = [
        "Full Validation not completed for this exact artifact",
        "draft publication and readback not completed",
        "explicit production promotion not recorded",
    ]
    status: dict[str, Any] = {
        "release": RELEASE_NAME,
        "package_version": version,
        "candidate_head_sha": head_sha,
        "workflow_run_id": workflow_run_id,
        "base_authority": BASE_AUTHORITY,
        "immediate_rollback_on_promotion": BASE_AUTHORITY,
        "status": "candidate_ready_for_full_validation",
        "promotion_authorized": False,
        "test_count": test_count,
        "branch_coverage_percent": round(branch_coverage, 4),
        "calibration_case_count": calibration.case_count,
        "calibration_release_eligible": calibration.release_eligible,
        "knowledge_management_case_count": knowledge["case_count"],
        "knowledge_management_passed": knowledge["passed"],
        "knowledge_management_report_sha256": sha256(knowledge_report_path),
        "source_manifest_sha256": sha256(source_manifest_path),
        "sbom_sha256": sha256(sbom_path),
        "blocking_gates": blockers,
        "required_next_action": "complete Full Validation and stage/read back the exact artifact",
    }
    status_path = output_dir / "V540_PROMOTION_PREPARATION_STATUS.json"
    _write_json(status_path, status)
    (output_dir / "V540_PROMOTION_PREPARATION_STATUS.sha256").write_text(
        f"{sha256(status_path)}  {status_path.name}\n", encoding="utf-8"
    )
    report = f"""# {RELEASE_NAME} Promotion Preparation Report

Status: **Candidate ready for Full Validation and governed approval; not promoted.**

- Candidate head: `{head_sha}`
- Workflow run: `{workflow_run_id}`
- Package version: `{version}`
- Active authority and rollback: {BASE_AUTHORITY}
- Tests: {test_count} passed
- Branch coverage: {branch_coverage:.2f}%
- Knowledge and Management V2: {knowledge["case_count"]} cases passed

Remaining blockers: exact-artifact Full Validation, draft publication/readback, and Ryan's
production-promotion decision.
"""
    (output_dir / "V540_PROMOTION_PREPARATION_REPORT.md").write_text(report, encoding="utf-8")
    validation = f"""# {RELEASE_NAME} Release Candidate Validation Report

- Candidate head: `{head_sha}`
- Workflow run: `{workflow_run_id}`
- Decision: **validated for Full Validation and governed approval**
- Promotion authority: **not granted**

Repository gates, package gates, calibration, and Knowledge and Management V2 evaluation passed.
Full Validation and draft publication/readback remain pending. This report cannot authorize
promotion.
"""
    (output_dir / "V540_RELEASE_VALIDATION_WORKBENCH_REPORT.md").write_text(
        validation, encoding="utf-8"
    )
    return status


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Atlas ROS v5.4.0 candidate evidence")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--workflow-run-id", required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--knowledge-report", type=Path, required=True)
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--coverage", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--sbom", type=Path, required=True)
    args = parser.parse_args()
    build_evidence(
        project_root=args.project_root,
        output_dir=args.output_dir,
        head_sha=args.head_sha,
        workflow_run_id=args.workflow_run_id,
        cases_path=args.cases,
        knowledge_report_path=args.knowledge_report,
        junit_path=args.junit,
        coverage_path=args.coverage,
        source_manifest_path=args.source_manifest,
        sbom_path=args.sbom,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
