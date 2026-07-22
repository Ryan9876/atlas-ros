from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from atlas_ros.intelligence.release_control_center import ControlCenterStatus, ReleaseControlCenter
from atlas_ros.intelligence.release_readiness import GateStatus
from atlas_ros.intelligence.validation_workbench import GateResult, WorkbenchDecision, WorkbenchReport


def report(status: GateStatus, decision: WorkbenchDecision) -> WorkbenchReport:
    now = datetime.now(UTC)
    result = GateResult(name="tests", status=status, blocking=True, started_at=now, completed_at=now, duration_seconds=1, reason=None if status is GateStatus.PASS else "not complete")
    return WorkbenchReport(release_id="Atlas ROS v5.0", run_id="r1", started_at=now, completed_at=now, decision=decision, results=(result,), blocking_reasons=() if status is GateStatus.PASS else ("tests",), artifacts=(), environment={})


def test_blocked_snapshot_never_authorizes_promotion() -> None:
    center = ReleaseControlCenter(active_release="v4.5.3", rollback_release="v4.5.2")
    snapshot = center.snapshot(report(GateStatus.NOT_RUN, WorkbenchDecision.BLOCKED))
    assert snapshot.status is ControlCenterStatus.BLOCKED
    assert snapshot.promotion_authorized is False
    assert snapshot.summary.blocking_open == 1


def test_validated_snapshot_is_candidate_ready_not_promoted() -> None:
    center = ReleaseControlCenter(active_release="v4.5.3", rollback_release="v4.5.2")
    snapshot = center.snapshot(report(GateStatus.PASS, WorkbenchDecision.VALIDATED))
    assert snapshot.status is ControlCenterStatus.CANDIDATE_READY
    assert snapshot.promotion_authorized is False


def test_build_emits_self_contained_dashboard(tmp_path: Path) -> None:
    source = tmp_path / "report.json"
    source.write_text(report(GateStatus.PASS, WorkbenchDecision.VALIDATED).model_dump_json(), encoding="utf-8")
    out = tmp_path / "dashboard"
    snapshot = ReleaseControlCenter(active_release="v4.5.3", rollback_release="v4.5.2").build(source, out)
    assert (out / "index.html").is_file()
    assert (out / "release-control-center.json").is_file()
    assert (out / "CONTROL_CENTER_FINGERPRINT.sha256").read_text().strip() == snapshot.fingerprint
    assert "Promotion authority: <strong>NOT GRANTED</strong>" in (out / "index.html").read_text()


def test_dashboard_includes_intelligence_calibration_panel(tmp_path: Path) -> None:
    source = tmp_path / "report.json"
    source.write_text(report(GateStatus.PASS, WorkbenchDecision.VALIDATED).model_dump_json(), encoding="utf-8")
    intelligence = tmp_path / "intelligence.json"
    intelligence.write_text(
        '{"release_eligible": true, "overall_accuracy": 0.96, "overall_macro_f1": 0.95, "overall_expected_calibration_error": 0.04, "overall_hallucination_rate": 0.0}',
        encoding="utf-8",
    )
    out = tmp_path / "dashboard"
    ReleaseControlCenter(active_release="v4.5.3", rollback_release="v4.5.2").build(source, out, intelligence)
    html = (out / "index.html").read_text(encoding="utf-8")
    assert "Intelligence calibration" in html
    assert "overall_accuracy" in html
