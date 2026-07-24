from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module():
    script = Path("scripts/build_v500_candidate_evidence.py")
    spec = importlib.util.spec_from_file_location("build_v500_candidate_evidence", script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_candidate_evidence_is_bound_to_current_commit(tmp_path: Path) -> None:
    module = _load_module()
    junit = tmp_path / "pytest.xml"
    junit.write_text(
        '<testsuites tests="243" failures="0" errors="0" skipped="0"></testsuites>',
        encoding="utf-8",
    )
    coverage = tmp_path / "coverage.json"
    coverage.write_text(
        json.dumps({"totals": {"percent_covered": 89.12}}),
        encoding="utf-8",
    )
    output = tmp_path / "evidence"
    head_sha = "a" * 40

    status = module.build_evidence(
        project_root=Path.cwd(),
        output_dir=output,
        head_sha=head_sha,
        workflow_run_id="30000000000",
        cases_path=Path("benchmarks/ryan-intelligence-evaluation-set-v1.json"),
        junit_path=junit,
        coverage_path=coverage,
        source_manifest_path=Path("release/CHECKSUMS.sha256"),
        sbom_path=Path("release/SBOM_V500_CURRENT.cdx.json"),
    )

    manifest = (output / "RELEASE_MANIFEST_V500_CANDIDATE.md").read_text()
    report = (output / "V500_RELEASE_VALIDATION_WORKBENCH_REPORT.md").read_text()
    assert status["candidate_head_sha"] == head_sha
    assert status["status"] == "candidate_ready_for_governed_review"
    assert status["test_count"] == 243
    assert status["calibration_release_eligible"] is True
    assert head_sha in manifest
    assert "Atlas ROS v5.0 Release Candidate" in manifest
    assert "243 tests" in report
    assert "507f694" not in json.dumps(status)


def test_workflow_uses_source_head_not_pull_request_merge_sha() -> None:
    workflow = Path(".github/workflows/release-candidate.yml").read_text()

    assert "github.event.pull_request.head.sha || github.sha" in workflow
    assert '--head-sha "${ATLAS_CANDIDATE_SHA}"' in workflow
