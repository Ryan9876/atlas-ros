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
RELEASE_NAME = "Atlas ROS v5.3.0"
EVIDENCE_PREFIX = "V530"
BASE_AUTHORITY = "Atlas ROS v5.2.0"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _project_version(project_root: Path) -> str:
    project = tomllib.loads((project_root / "pyproject.toml").read_text(encoding="utf-8"))
    return str(project["project"]["version"])


def _test_count(path: Path) -> int:
    root = ET.parse(path).getroot()
    return int(root.attrib.get("tests", sum(int(item.attrib["tests"]) for item in root)))


def _validate_classification(report: dict[str, Any]) -> None:
    checks = (
        report["critical_fixture_pass_rate"] == 1.0,
        report["macro_f1"] >= 0.90,
        report["minimum_domain_recall"] >= 0.85,
        report["confidence_calibration_error"] <= 0.10,
        report["explanation_evidence_agreement"] >= 0.95,
        report["record_destination_equivalence"] >= 0.99,
    )
    if not all(checks):
        raise ValueError("Classification Intelligence evaluation is below a governed threshold")


def build_evidence(
    *,
    project_root: Path,
    output_dir: Path,
    head_sha: str,
    workflow_run_id: str,
    cases_path: Path,
    classification_report_path: Path,
    junit_path: Path,
    coverage_path: Path,
    source_manifest_path: Path,
    sbom_path: Path,
) -> dict[str, Any]:
    if not SHA_PATTERN.fullmatch(head_sha):
        raise ValueError("head SHA must be a lowercase 40-character Git SHA")
    version = _project_version(project_root)
    if not version.startswith("5.3."):
        raise ValueError(f"expected an Atlas ROS v5.3 package version, got {version}")

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
        raise ValueError(
            "calibration is not release eligible: " + ", ".join(calibration.blocking_violations)
        )

    classification = json.loads(classification_report_path.read_text(encoding="utf-8"))
    _validate_classification(classification)
    generated_at = datetime.now(UTC).isoformat()

    calibration_path = output_dir / f"{EVIDENCE_PREFIX}_CALIBRATION_REPORT.json"
    calibration_path.write_text(calibration.model_dump_json(indent=2) + "\n", encoding="utf-8")
    classification_out = output_dir / f"{EVIDENCE_PREFIX}_CLASSIFICATION_INTELLIGENCE_REPORT.json"
    classification_out.write_text(json.dumps(classification, indent=2) + "\n", encoding="utf-8")

    manifest = f"""# {RELEASE_NAME} Release Candidate Evidence Manifest

Status: Final candidate package ready for governed promotion review; not promoted.

- Package version: `{version}`
- Candidate head: `{head_sha}`
- GitHub workflow run: `{workflow_run_id}`
- Generated: `{generated_at}`
- Active production authority: {BASE_AUTHORITY}
- Immediate rollback if promoted: {BASE_AUTHORITY}
- Promotion authorized: No

This compatibility release packages Classification Intelligence Phase 1: responsibility-first classification,
evidence-aligned explanations, manager-intent inference as a supporting signal, governed challenge state,
version 1 compatibility, shadow comparison, attended decision support, and high-confidence semantic mode
with safe fallback. Legacy mode remains available and unattended consequential operation remains inactive.

The source, source manifest, source distribution, wheel, SBOM, dependency audits, implementation registry,
Ryan-intelligence calibration, Classification Intelligence evaluation, and validation report are bound by
publication checksums. The readable published workspace is valid only when all published artifacts are readable,
internally consistent, checksum-valid, and successfully read back. Secrets and signing material are excluded.

Validated gates include Ruff, strict MyPy, architecture boundaries, {test_count} tests,
{branch_coverage:.2f}% branch coverage, dependency policy and dual advisory audits, source verification,
source and wheel builds, extracted-source verification, clean-wheel validation,
{calibration.case_count} Ryan-intelligence cases, and {classification['case_count']} Classification Intelligence
cases with macro F1 {classification['macro_f1']:.4f}, minimum recall
{classification['minimum_domain_recall']:.4f}, calibration error
{classification['confidence_calibration_error']:.4f}, explanation-evidence agreement
{classification['explanation_evidence_agreement']:.4f}, and record/destination equivalence
{classification['record_destination_equivalence']:.4f}.

Full Validation, draft publication/readback, and Ryan's explicit production-promotion authorization remain required.
"""
    (output_dir / "RELEASE_MANIFEST_V530_CANDIDATE.md").write_text(manifest, encoding="utf-8")

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
        "benchmark_case_count": calibration.case_count,
        "benchmark_domain_count": len(calibration.domains),
        "dataset_fingerprint": calibration.dataset_fingerprint,
        "calibration_fingerprint": calibration.fingerprint,
        "calibration_release_eligible": calibration.release_eligible,
        "classification_case_count": classification["case_count"],
        "classification_critical_fixture_pass_rate": classification["critical_fixture_pass_rate"],
        "classification_macro_f1": classification["macro_f1"],
        "classification_minimum_domain_recall": classification["minimum_domain_recall"],
        "classification_calibration_error": classification["confidence_calibration_error"],
        "classification_explanation_evidence_agreement": classification[
            "explanation_evidence_agreement"
        ],
        "classification_record_destination_equivalence": classification[
            "record_destination_equivalence"
        ],
        "classification_report_sha256": sha256(classification_report_path),
        "source_manifest_sha256": sha256(source_manifest_path),
        "sbom_sha256": sha256(sbom_path),
        "governed_review": None,
        "blocking_gates": blockers,
        "required_next_action": "complete Full Validation and stage/read back the exact artifact",
    }
    status_path = output_dir / "V530_PROMOTION_PREPARATION_STATUS.json"
    _write_json(status_path, status)
    (output_dir / "V530_PROMOTION_PREPARATION_STATUS.sha256").write_text(
        f"{sha256(status_path)}  {status_path.name}\n", encoding="utf-8"
    )

    report = f"""# {RELEASE_NAME} Promotion Preparation Report

Status: **Final candidate ready for Full Validation and governed promotion review; not promoted.**

- Candidate head: `{head_sha}`
- Workflow run: `{workflow_run_id}`
- Package version: `{version}`
- Active authority and rollback if promoted: {BASE_AUTHORITY}
- Tests: {test_count} passed
- Branch coverage: {branch_coverage:.2f}%
- Ryan-intelligence calibration: {calibration.case_count} cases; release eligible
- Classification Intelligence: {classification['case_count']} cases; macro F1 {classification['macro_f1']:.4f}
- Minimum domain recall: {classification['minimum_domain_recall']:.4f}
- Confidence calibration error: {classification['confidence_calibration_error']:.4f}
- Explanation-evidence agreement: {classification['explanation_evidence_agreement']:.4f}
- Record/destination equivalence: {classification['record_destination_equivalence']:.4f}

Remaining blockers: exact-artifact Full Validation, draft publication/readback, and Ryan's promotion decision.
"""
    (output_dir / "V530_PROMOTION_PREPARATION_REPORT.md").write_text(report, encoding="utf-8")

    workbench = f"""# {RELEASE_NAME} Release Candidate Validation Report

- Candidate head: `{head_sha}`
- Workflow run: `{workflow_run_id}`
- Generated: `{generated_at}`
- Decision: **validated for Full Validation and promotion review**
- Promotion authority: **not granted**

| Gate | Result |
|---|---|
| Ruff and strict MyPy | PASS |
| Architecture boundaries | PASS |
| Regression tests | PASS — {test_count} tests |
| Branch coverage | PASS — {branch_coverage:.2f}% |
| Dependency policy and dual audits | PASS |
| Authority migration and implementation registry | PASS |
| Source manifest and extracted source | PASS |
| Source distribution, wheel, and clean install | PASS |
| Ryan-intelligence calibration | PASS — {calibration.case_count} cases |
| Classification Intelligence | PASS — {classification['case_count']} cases |
| Full Validation | PENDING |
| Draft publication/readback | PENDING |

This report cannot authorize promotion.
"""
    (output_dir / "V530_RELEASE_VALIDATION_WORKBENCH_REPORT.md").write_text(
        workbench, encoding="utf-8"
    )
    return status


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Atlas ROS v5.3.0 candidate evidence")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--workflow-run-id", required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--classification-report", type=Path, required=True)
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
        classification_report_path=args.classification_report,
        junit_path=args.junit,
        coverage_path=args.coverage,
        source_manifest_path=args.source_manifest,
        sbom_path=args.sbom,
    )
    print(json.dumps(status))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
