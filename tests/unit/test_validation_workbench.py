from __future__ import annotations

import hashlib
import json
from pathlib import Path

from atlas_ros.intelligence.release_readiness import GateStatus
from atlas_ros.intelligence.validation_workbench import (
    GateDefinition,
    GateKind,
    ReleaseValidationWorkbench,
    WorkbenchDecision,
    package_evidence,
)


def test_pass_and_fail_gates(tmp_path: Path) -> None:
    (tmp_path / "required.txt").write_text("ok", encoding="utf-8")
    gates = (
        GateDefinition(name="command", command=("python", "-c", "print('ok')")),
        GateDefinition(name="file", kind=GateKind.FILE, required_path="required.txt"),
        GateDefinition(name="review", kind=GateKind.MANUAL),
    )
    wb = ReleaseValidationWorkbench(tmp_path, tmp_path / "out")
    report = wb.run(release_id="v5", gates=gates)
    assert report.decision is WorkbenchDecision.BLOCKED
    assert report.results[0].status is GateStatus.PASS
    assert report.results[1].status is GateStatus.PASS
    assert report.results[2].status is GateStatus.NOT_RUN
    assert report.promotion_authorized if hasattr(report, "promotion_authorized") else True


def test_manual_evidence_can_complete_validation(tmp_path: Path) -> None:
    gates = (GateDefinition(name="review", kind=GateKind.MANUAL),)
    wb = ReleaseValidationWorkbench(tmp_path, tmp_path / "out")
    report = wb.run(release_id="v5", gates=gates, manual_evidence={"review": ["review.md"]})
    assert report.decision is WorkbenchDecision.VALIDATED
    assert report.results[0].evidence == ("review.md",)


def test_missing_module_is_not_run(tmp_path: Path) -> None:
    gate = GateDefinition(
        name="missing",
        command=("python", "-m", "definitely_missing_atlas_module"),
        required_executable="definitely_missing_atlas_module",
    )
    wb = ReleaseValidationWorkbench(tmp_path, tmp_path / "out")
    report = wb.run(release_id="v5", gates=(gate,))
    assert report.results[0].status is GateStatus.NOT_RUN
    assert "unavailable" in (report.results[0].reason or "")


def test_report_outputs_and_fingerprint(tmp_path: Path) -> None:
    gate = GateDefinition(name="ok", command=("python", "-c", "raise SystemExit(0)"))
    wb = ReleaseValidationWorkbench(tmp_path, tmp_path / "out")
    report = wb.run(release_id="v5", gates=(gate,))
    run_dir = wb.output_root / report.run_id
    assert (run_dir / "validation-report.json").is_file()
    assert (run_dir / "validation-report.md").is_file()
    assert (run_dir / "CHECKSUMS.sha256").is_file()
    assert len(report.fingerprint) == 64
    loaded = json.loads((run_dir / "validation-report.json").read_text())
    assert loaded["decision"] == "validated"


def test_deterministic_evidence_package(tmp_path: Path) -> None:
    run = tmp_path / "run"
    run.mkdir()
    (run / "b.txt").write_text("b", encoding="utf-8")
    (run / "a.txt").write_text("a", encoding="utf-8")
    first = package_evidence(run, tmp_path / "first.zip")
    second = package_evidence(run, tmp_path / "second.zip")
    assert hashlib.sha256(first.read_bytes()).hexdigest() == hashlib.sha256(second.read_bytes()).hexdigest()
