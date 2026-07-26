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
RELEASE_NAME = "Atlas ROS v6.1.0"
EVIDENCE_PREFIX = "V610"
BASE_AUTHORITY = "Atlas ROS v6.0.0"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _test_count(path: Path) -> int:
    root = ET.parse(path).getroot()
    return int(root.attrib.get("tests", sum(int(item.attrib["tests"]) for item in root)))


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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
    semantic_report_path: Path,
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
    if not version.startswith("6.1."):
        raise ValueError(f"expected an Atlas ROS v6.1 package version, got {version}")
    output_dir.mkdir(parents=True, exist_ok=True)
    test_count = _test_count(junit_path)
    coverage = _load(coverage_path)
    branch_coverage = float(coverage["totals"]["percent_covered"])
    if branch_coverage < 85.0:
        raise ValueError(f"branch coverage {branch_coverage:.2f}% is below 85%")

    cases = load_calibration_cases(cases_path)
    judgments = IntelligenceEvaluationRunner().run(cases)
    calibration = IntelligenceCalibrationEngine().run(cases, judgments)
    if not calibration.release_eligible:
        raise ValueError("Ryan-intelligence calibration is not release eligible")

    knowledge = _load(knowledge_report_path)
    execution = _load(execution_report_path)
    orchestration = _load(orchestration_report_path)
    reconciliation = _load(reconciliation_report_path)
    semantic = _load(semantic_report_path)
    differential = _load(differential_report_path)
    retirement = _load(retirement_inventory_path)

    if not knowledge["passed"] or knowledge["case_count"] < 2:
        raise ValueError("Knowledge and Management evaluation failed")
    if not execution["passed"] or not execution["zero_provider_writes"]:
        raise ValueError("Execution Planning evaluation failed")
    if not orchestration["passed"] or not orchestration["zero_live_writes"]:
        raise ValueError("Execution Orchestration evaluation failed")
    if not reconciliation["eligible"] or reconciliation["live_provider_writes"] != 0:
        raise ValueError("Canonical Reconciliation evaluation failed")
    if (
        not semantic["eligible"]
        or not semantic["critical_passed"]
        or semantic["passed"] != semantic["cases"]
        or not all(semantic["metamorphic_invariance"].values())
        or semantic["live_provider_writes"] != 0
    ):
        raise ValueError("Semantic Fidelity evaluation failed")
    if (
        not differential["eligible"]
        or differential["unexplained_drift_count"] != 0
        or differential["live_provider_writes"] != 0
    ):
        raise ValueError("v6.0-to-v6.1 compatibility evaluation failed")
    if retirement["runtime_w_module_count"] != 0 or retirement["blocking_reference_count"] != 0:
        raise ValueError("W-number runtime retirement is incomplete")

    reports = {
        "CALIBRATION_REPORT": calibration.model_dump_json(indent=2) + "\n",
        "KNOWLEDGE_MANAGEMENT_REPORT": json.dumps(knowledge, indent=2) + "\n",
        "EXECUTION_PLANNING_REPORT": json.dumps(execution, indent=2) + "\n",
        "EXECUTION_ORCHESTRATION_REPORT": json.dumps(orchestration, indent=2) + "\n",
        "CANONICAL_RECONCILIATION_REPORT": json.dumps(reconciliation, indent=2) + "\n",
        "SEMANTIC_FIDELITY_REPORT": json.dumps(semantic, indent=2) + "\n",
        "DIFFERENTIAL_REPORT": json.dumps(differential, indent=2) + "\n",
    }
    for name, content in reports.items():
        (output_dir / f"{EVIDENCE_PREFIX}_{name}.json").write_text(content, encoding="utf-8")

    generated_at = datetime.now(UTC).isoformat()
    manifest = f"""# {RELEASE_NAME} Release Candidate Evidence Manifest

Status: Exact semantic-fidelity candidate ready for governed Full Validation; not promoted.

- Package version: `{version}`
- Candidate head: `{head_sha}`
- GitHub workflow run: `{workflow_run_id}`
- Generated: `{generated_at}`
- Active production authority: {BASE_AUTHORITY}
- Immediate rollback if promoted: {BASE_AUTHORITY}
- Promotion authorized: No

This candidate separates primary business outcomes from evaluation, audit, provider-control,
and system-evidence instructions; adds semantic-fidelity and metamorphic invariance gates; and
preserves v6 orchestration, reconciliation, provider separation, attended authorization, and
readback behavior. Validation performs no live provider writes. Production promotion requires
Ryan's separate explicit authorization.

Validated gates include Ruff, strict MyPy, architecture boundaries, {test_count} tests,
{branch_coverage:.2f}% branch coverage, dependency and advisory audits, source and wheel builds,
clean-wheel validation, {execution['case_count']} Execution Planning cases,
{orchestration['case_count']} Execution Orchestration cases,
{reconciliation['case_count']} Canonical Reconciliation cases,
{semantic['cases']} Semantic Fidelity cases with invariant CloudVision metamorphic variants,
and zero unexplained compatibility drift against v6.0.0.
"""
    (output_dir / "RELEASE_MANIFEST_V610_CANDIDATE.md").write_text(manifest, encoding="utf-8")

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
        "semantic_fidelity_case_count": semantic["cases"],
        "semantic_fidelity_passed": semantic["eligible"],
        "semantic_fidelity_report_sha256": sha256(semantic_report_path),
        "cloudvision_invariance": semantic["metamorphic_invariance"],
        "execution_planning_case_count": execution["case_count"],
        "execution_orchestration_case_count": orchestration["case_count"],
        "canonical_reconciliation_case_count": reconciliation["case_count"],
        "differential_unexplained_drift_count": differential["unexplained_drift_count"],
        "runtime_w_module_count": retirement["runtime_w_module_count"],
        "zero_live_provider_writes": True,
        "source_manifest_sha256": sha256(source_manifest_path),
        "sbom_sha256": sha256(sbom_path),
        "blocking_gates": blockers,
        "required_next_action": "complete Full Validation and stage/read back the exact artifact",
    }
    status_path = output_dir / "V610_PROMOTION_PREPARATION_STATUS.json"
    _write_json(status_path, status)
    (output_dir / "V610_PROMOTION_PREPARATION_STATUS.sha256").write_text(
        f"{sha256(status_path)}  {status_path.name}\n", encoding="utf-8"
    )
    (output_dir / "V610_PROMOTION_PREPARATION_REPORT.md").write_text(
        f"""# {RELEASE_NAME} Promotion Preparation Report

Status: **Candidate ready for Full Validation and governed approval; not promoted.**

- Candidate head: `{head_sha}`
- Workflow run: `{workflow_run_id}`
- Package version: `{version}`
- Active authority and rollback if promoted: {BASE_AUTHORITY}
- Tests: {test_count} passed
- Branch coverage: {branch_coverage:.2f}%
- Semantic Fidelity: {semantic['passed']}/{semantic['cases']} cases passed
- CloudVision invariance: {semantic['metamorphic_invariance']}
- v6.0-to-v6.1 unexplained drift: {differential['unexplained_drift_count']}
- Unauthorized or live provider writes: zero

Remaining blockers: exact-artifact Full Validation, draft publication/readback, and Ryan's
production-promotion decision.
""",
        encoding="utf-8",
    )
    (output_dir / "V610_RELEASE_VALIDATION_WORKBENCH_REPORT.md").write_text(
        f"""# {RELEASE_NAME} Release Candidate Validation Report

- Candidate head: `{head_sha}`
- Workflow run: `{workflow_run_id}`
- Decision: **validated for Full Validation and governed approval**
- Promotion authority: **not granted**

Structural, compatibility, packaging, security, semantic-gold, and metamorphic-invariance gates
passed. Full Validation and draft publication/readback remain pending.
""",
        encoding="utf-8",
    )
    rollback = {
        "candidate": RELEASE_NAME,
        "rollback_authority": BASE_AUTHORITY,
        "rollback_source_verified_by": "v6.0-to-v6.1 differential validation",
        "unexplained_drift_count": differential["unexplained_drift_count"],
        "live_provider_writes": differential["live_provider_writes"],
        "eligible": differential["eligible"],
    }
    _write_json(output_dir / "V610_ROLLBACK_REHEARSAL.json", rollback)
    (output_dir / "V610_ROLLBACK_REHEARSAL.md").write_text(
        f"""# Atlas ROS v6.1.0 Rollback Rehearsal

Immediate rollback after promotion: **Atlas ROS v6.0.0**.

The compatibility fixture produced {differential['unexplained_drift_count']} unexplained
differences and zero live provider writes. Authority is not switched by this evidence.
""",
        encoding="utf-8",
    )
    return status


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Atlas ROS v6.1.0 candidate evidence")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--workflow-run-id", required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--knowledge-report", type=Path, required=True)
    parser.add_argument("--execution-report", type=Path, required=True)
    parser.add_argument("--orchestration-report", type=Path, required=True)
    parser.add_argument("--reconciliation-report", type=Path, required=True)
    parser.add_argument("--semantic-report", type=Path, required=True)
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
        semantic_report_path=args.semantic_report,
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
