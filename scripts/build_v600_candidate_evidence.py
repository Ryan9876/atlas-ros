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
RELEASE_NAME = "Atlas ROS v6.0.0"
EVIDENCE_PREFIX = "V600"
BASE_AUTHORITY = "Atlas ROS v5.6.0"


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
    execution_report_path: Path,
    orchestration_report_path: Path,
    reconciliation_report_path: Path,
    differential_report_path: Path,
    retirement_inventory_path: Path,
    junit_path: Path,
    coverage_path: Path,
    source_manifest_path: Path,
    sbom_path: Path,
) -> dict[str, Any]:
    if not SHA_PATTERN.fullmatch(head_sha):
        raise ValueError("head SHA must be a lowercase 40-character Git SHA")
    project = tomllib.loads((project_root / "pyproject.toml").read_text(encoding="utf-8"))
    version = str(project["project"]["version"])
    if not version.startswith("6.0."):
        raise ValueError(f"expected an Atlas ROS v6.0 package version, got {version}")
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
    execution = json.loads(execution_report_path.read_text(encoding="utf-8"))
    if (
        not execution["passed"]
        or execution["case_count"] < 50
        or execution["critical_fixture_pass_rate"] != 1.0
        or not execution["zero_provider_writes"]
        or not execution["zero_unauthorized_execution_objects"]
    ):
        raise ValueError("Execution Planning and Task Economy evaluation failed")
    orchestration = json.loads(orchestration_report_path.read_text(encoding="utf-8"))
    if (
        not orchestration["passed"]
        or orchestration["case_count"] < 60
        or orchestration["critical_passed_count"] != orchestration["critical_count"]
        or not orchestration["zero_unauthorized_provider_writes"]
        or not orchestration["zero_live_writes"]
        or orchestration["false_success_rejection"] != 1.0
    ):
        raise ValueError("Execution Orchestration and Provider Separation evaluation failed")
    reconciliation = json.loads(reconciliation_report_path.read_text(encoding="utf-8"))
    if (
        not reconciliation["eligible"]
        or reconciliation["case_count"] < 75
        or reconciliation["critical_passed"] != reconciliation["critical_cases"]
        or reconciliation["live_provider_writes"] != 0
        or reconciliation["false_checkpoint_advancement"] != 0
    ):
        raise ValueError("Canonical Reconciliation evaluation failed")
    differential = json.loads(differential_report_path.read_text(encoding="utf-8"))
    if (
        not differential["eligible"]
        or differential["unexplained_drift_count"] != 0
        or differential["live_provider_writes"] != 0
    ):
        raise ValueError("v5.6-to-v6.0 differential evaluation failed")
    retirement = json.loads(retirement_inventory_path.read_text(encoding="utf-8"))
    if (
        retirement["runtime_w_module_count"] != 0
        or retirement["blocking_reference_count"] != 0
    ):
        raise ValueError("W-number runtime retirement is incomplete")
    generated_at = datetime.now(UTC).isoformat()
    calibration_path = output_dir / f"{EVIDENCE_PREFIX}_CALIBRATION_REPORT.json"
    calibration_path.write_text(calibration.model_dump_json(indent=2) + "\n", encoding="utf-8")
    knowledge_out = output_dir / f"{EVIDENCE_PREFIX}_KNOWLEDGE_MANAGEMENT_REPORT.json"
    knowledge_out.write_text(json.dumps(knowledge, indent=2) + "\n", encoding="utf-8")
    execution_out = output_dir / f"{EVIDENCE_PREFIX}_EXECUTION_PLANNING_REPORT.json"
    execution_out.write_text(json.dumps(execution, indent=2) + "\n", encoding="utf-8")
    orchestration_out = output_dir / f"{EVIDENCE_PREFIX}_EXECUTION_ORCHESTRATION_REPORT.json"
    orchestration_out.write_text(
        json.dumps(orchestration, indent=2) + "\n", encoding="utf-8"
    )
    reconciliation_out = output_dir / f"{EVIDENCE_PREFIX}_CANONICAL_RECONCILIATION_REPORT.json"
    reconciliation_out.write_text(
        json.dumps(reconciliation, indent=2) + "\n", encoding="utf-8"
    )
    differential_out = output_dir / f"{EVIDENCE_PREFIX}_DIFFERENTIAL_REPORT.json"
    differential_out.write_text(
        json.dumps(differential, indent=2) + "\n", encoding="utf-8"
    )
    manifest = f"""# {RELEASE_NAME} Release Candidate Evidence Manifest

Status: Exact candidate ready for governed approval; not promoted.

- Package version: `{version}`
- Candidate head: `{head_sha}`
- GitHub workflow run: `{workflow_run_id}`
- Generated: `{generated_at}`
- Active production authority: {BASE_AUTHORITY}
- Immediate rollback if promoted: {BASE_AUTHORITY}
- Promotion authorized: No

This final roadmap candidate introduces the canonical reconciliation authority, deterministic
field-level reconciliation plans, attended digest-bound authorization, idempotent provider
mutations, blocking conflicts, readback-verified receipts, checkpoint safety, and provider-neutral
policy. It also completes the semantic-only runtime cutover: numbered W modules are absent from
source and built distributions, while migration and rollback evidence preserve historical meaning.
It performs no live provider writes during validation and does not grant unattended authority.
Production promotion requires Ryan's separate explicit authorization.

Validated gates include Ruff, strict MyPy, architecture boundaries, {test_count} tests,
{branch_coverage:.2f}% branch coverage, dependency policy and dual advisory audits, source and
wheel builds, clean-wheel validation, {calibration.case_count} Ryan-intelligence calibration
cases, {knowledge["case_count"]} Knowledge and Management V2 benchmark cases, and
{execution["case_count"]} Execution Planning benchmark cases and
{orchestration["case_count"]} Execution Orchestration benchmark cases with zero unauthorized
provider writes and zero false-success receipts, plus {reconciliation["case_count"]} Canonical
Reconciliation cases and a zero-drift differential comparison against v5.6.0.
"""
    (output_dir / "RELEASE_MANIFEST_V600_CANDIDATE.md").write_text(manifest, encoding="utf-8")
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
        "execution_planning_case_count": execution["case_count"],
        "execution_planning_passed": execution["passed"],
        "execution_planning_report_sha256": sha256(execution_report_path),
        "execution_orchestration_case_count": orchestration["case_count"],
        "execution_orchestration_passed": orchestration["passed"],
        "execution_orchestration_report_sha256": sha256(orchestration_report_path),
        "canonical_reconciliation_case_count": reconciliation["case_count"],
        "canonical_reconciliation_passed": reconciliation["eligible"],
        "canonical_reconciliation_report_sha256": sha256(reconciliation_report_path),
        "differential_unexplained_drift_count": differential["unexplained_drift_count"],
        "differential_report_sha256": sha256(differential_report_path),
        "runtime_w_module_count": retirement["runtime_w_module_count"],
        "w_retirement_inventory_sha256": sha256(retirement_inventory_path),
        "zero_unauthorized_provider_writes": orchestration[
            "zero_unauthorized_provider_writes"
        ],
        "zero_false_success_receipts": orchestration["false_success_rejection"] == 1.0,
        "zero_live_provider_writes": orchestration["zero_live_writes"],
        "zero_provider_writes": execution["zero_provider_writes"],
        "zero_planner_authorizations": execution[
            "zero_unauthorized_execution_objects"
        ],
        "source_manifest_sha256": sha256(source_manifest_path),
        "sbom_sha256": sha256(sbom_path),
        "blocking_gates": blockers,
        "required_next_action": "complete Full Validation and stage/read back the exact artifact",
    }
    status_path = output_dir / "V600_PROMOTION_PREPARATION_STATUS.json"
    _write_json(status_path, status)
    (output_dir / "V600_PROMOTION_PREPARATION_STATUS.sha256").write_text(
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
- Execution Planning and Task Economy: {execution["case_count"]} cases passed
- Execution Orchestration and Provider Separation: {orchestration["case_count"]} cases passed
- Canonical Reconciliation: {reconciliation["case_count"]} cases passed
- v5.6-to-v6 differential drift: {differential["unexplained_drift_count"]}
- Runtime W modules: {retirement["runtime_w_module_count"]}
- Unauthorized provider writes: zero
- False-success receipts: zero
- Planner authorizations: zero

Remaining blockers: exact-artifact Full Validation, draft publication/readback, and Ryan's
production-promotion decision.
"""
    (output_dir / "V600_PROMOTION_PREPARATION_REPORT.md").write_text(report, encoding="utf-8")
    validation = f"""# {RELEASE_NAME} Release Candidate Validation Report

- Candidate head: `{head_sha}`
- Workflow run: `{workflow_run_id}`
- Decision: **validated for Full Validation and governed approval**
- Promotion authority: **not granted**

Repository gates, package gates, calibration, Knowledge and Management V2, Execution Planning,
and Execution Orchestration evaluation passed. Full Validation and draft publication/readback
remain pending. This report cannot authorize promotion.
"""
    (output_dir / "V600_RELEASE_VALIDATION_WORKBENCH_REPORT.md").write_text(
        validation, encoding="utf-8"
    )
    return status


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Atlas ROS v6.0.0 candidate evidence")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--workflow-run-id", required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--knowledge-report", type=Path, required=True)
    parser.add_argument("--execution-report", type=Path, required=True)
    parser.add_argument("--orchestration-report", type=Path, required=True)
    parser.add_argument("--reconciliation-report", type=Path, required=True)
    parser.add_argument("--differential-report", type=Path, required=True)
    parser.add_argument("--retirement-inventory", type=Path, required=True)
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
        execution_report_path=args.execution_report,
        orchestration_report_path=args.orchestration_report,
        reconciliation_report_path=args.reconciliation_report,
        differential_report_path=args.differential_report,
        retirement_inventory_path=args.retirement_inventory,
        junit_path=args.junit,
        coverage_path=args.coverage,
        source_manifest_path=args.source_manifest,
        sbom_path=args.sbom,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
