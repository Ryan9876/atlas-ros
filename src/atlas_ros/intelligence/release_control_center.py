from __future__ import annotations

import hashlib
import html
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import cast

from pydantic import BaseModel, ConfigDict, Field

from atlas_ros.intelligence.release_readiness import GateStatus
from atlas_ros.intelligence.validation_workbench import WorkbenchDecision, WorkbenchReport


class ControlCenterStatus(StrEnum):
    BLOCKED = "blocked"
    CANDIDATE_READY = "candidate_ready"


class GateSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    not_run: int = Field(ge=0)
    blocking_open: int = Field(ge=0)
    total: int = Field(ge=0)


class ControlCenterSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    release_id: str
    run_id: str
    generated_at: datetime
    status: ControlCenterStatus
    promotion_authorized: bool = False
    active_release: str
    rollback_release: str
    summary: GateSummary
    blocker_queue: tuple[str, ...]
    gate_rows: tuple[Mapping[str, object], ...]
    artifacts: tuple[Mapping[str, object], ...]
    report_fingerprint: str
    intelligence_health: Mapping[str, object] = Field(default_factory=dict)

    @property
    def fingerprint(self) -> str:
        payload = self.model_dump(mode="json", exclude={"generated_at"})
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


class ReleaseControlCenter:
    """Builds a read-only release dashboard from workbench evidence."""

    def __init__(self, *, active_release: str, rollback_release: str) -> None:
        self.active_release = active_release
        self.rollback_release = rollback_release

    def snapshot(self, report: WorkbenchReport) -> ControlCenterSnapshot:
        passed = sum(r.status is GateStatus.PASS for r in report.results)
        failed = sum(r.status is GateStatus.FAIL for r in report.results)
        not_run = sum(r.status is GateStatus.NOT_RUN for r in report.results)
        blockers = tuple(
            f"{r.name}: {r.reason or r.status.value}"
            for r in report.results
            if r.blocking and r.status is not GateStatus.PASS
        )
        status = (
            ControlCenterStatus.CANDIDATE_READY
            if report.decision is WorkbenchDecision.VALIDATED and not blockers
            else ControlCenterStatus.BLOCKED
        )
        rows = tuple(
            {
                "gate": r.name,
                "status": r.status.value,
                "blocking": r.blocking,
                "duration_seconds": r.duration_seconds,
                "reason": r.reason or "",
                "log_path": r.log_path or "",
                "evidence": list(r.evidence),
            }
            for r in report.results
        )
        artifacts = tuple(a.model_dump(mode="json") for a in report.artifacts)
        return ControlCenterSnapshot(
            release_id=report.release_id,
            run_id=report.run_id,
            generated_at=datetime.now(UTC),
            status=status,
            promotion_authorized=False,
            active_release=self.active_release,
            rollback_release=self.rollback_release,
            summary=GateSummary(
                passed=passed,
                failed=failed,
                not_run=not_run,
                blocking_open=len(blockers),
                total=len(report.results),
            ),
            blocker_queue=blockers,
            gate_rows=rows,
            artifacts=artifacts,
            report_fingerprint=report.fingerprint,
        )

    @staticmethod
    def _badge(status: str) -> str:
        cls = {"pass": "ok", "fail": "bad", "not_run": "warn"}.get(status, "neutral")
        return f'<span class="badge {cls}">{html.escape(status)}</span>'

    def render_html(self, snapshot: ControlCenterSnapshot) -> str:
        gate_rows = "\n".join(
            "<tr>"
            f"<td>{html.escape(str(row['gate']))}</td>"
            f"<td>{self._badge(str(row['status']))}</td>"
            f"<td>{'Yes' if row['blocking'] else 'No'}</td>"
            f"<td>{float(cast(float | int | str, row['duration_seconds'])):.3f}s</td>"
            f"<td>{html.escape(str(row['reason']))}</td>"
            "</tr>"
            for row in snapshot.gate_rows
        )
        blockers = (
            "".join(f"<li>{html.escape(item)}</li>" for item in snapshot.blocker_queue)
            or "<li>None</li>"
        )
        artifacts = "\n".join(
            "<tr>"
            f"<td>{html.escape(str(a['relative_path']))}</td>"
            f"<td><code>{html.escape(str(a['sha256']))}</code></td>"
            f"<td>{int(cast(int | str, a['size_bytes'])):,}</td>"
            "</tr>"
            for a in snapshot.artifacts
        )
        intelligence_panel = ""
        if snapshot.intelligence_health:
            health_rows = "".join(
                f"<tr><td>{html.escape(str(key))}</td><td>{html.escape(str(value))}</td></tr>"
                for key, value in sorted(snapshot.intelligence_health.items())
            )
            intelligence_panel = (
                '<section class="card section"><h2>Intelligence calibration</h2>'
                "<table><thead><tr><th>Metric</th><th>Value</th></tr></thead>"
                f"<tbody>{health_rows}</tbody></table></section>"
            )
        status_class = "ok" if snapshot.status is ControlCenterStatus.CANDIDATE_READY else "bad"
        return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Atlas ROS Release Control Center</title>
<style>
:root{{--bg:#0b1020;--panel:#151c31;--text:#edf2ff;--muted:#9ca8c7;--line:#2a3555;--ok:#33d17a;--bad:#ff6b6b;--warn:#f6c85f;--accent:#78a9ff}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 system-ui,sans-serif}}
main{{max-width:1280px;margin:auto;padding:28px}} h1{{margin:0 0 6px;font-size:30px}} h2{{margin-top:0}} .muted{{color:var(--muted)}}
.grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:22px 0}} .card{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px}}
.metric{{font-size:28px;font-weight:750}} .badge{{display:inline-block;padding:3px 9px;border-radius:999px;font-weight:700}} .ok{{color:var(--ok)}} .bad{{color:var(--bad)}} .warn{{color:var(--warn)}} .badge.ok{{background:#123b2a}} .badge.bad{{background:#481f2a}} .badge.warn{{background:#443815}}
table{{width:100%;border-collapse:collapse}} th,td{{padding:10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}} th{{color:var(--muted)}} code{{font-size:12px;overflow-wrap:anywhere}}
.section{{margin-top:18px}} .status{{font-size:20px;font-weight:800}} ul{{margin-bottom:0}} @media(max-width:800px){{.grid{{grid-template-columns:1fr 1fr}}}}
</style></head><body><main>
<h1>Atlas ROS Release Control Center</h1><div class="muted">Read-only evidence dashboard · Run {html.escape(snapshot.run_id)}</div>
<div class="section card"><div class="status {status_class}">{html.escape(snapshot.status.value.replace("_", " ").upper())}</div>
<p>Development release: <strong>{html.escape(snapshot.release_id)}</strong> · Active production: <strong>{html.escape(snapshot.active_release)}</strong> · Rollback: <strong>{html.escape(snapshot.rollback_release)}</strong></p>
<p>Promotion authority: <strong>NOT GRANTED</strong></p></div>
<div class="grid">
<div class="card"><div class="muted">Passed</div><div class="metric ok">{snapshot.summary.passed}</div></div>
<div class="card"><div class="muted">Failed</div><div class="metric bad">{snapshot.summary.failed}</div></div>
<div class="card"><div class="muted">Not run</div><div class="metric warn">{snapshot.summary.not_run}</div></div>
<div class="card"><div class="muted">Open blockers</div><div class="metric bad">{snapshot.summary.blocking_open}</div></div>
</div>
<section class="card section"><h2>Blocker queue</h2><ol>{blockers}</ol></section>
<section class="card section"><h2>Validation gates</h2><table><thead><tr><th>Gate</th><th>Status</th><th>Blocking</th><th>Duration</th><th>Reason</th></tr></thead><tbody>{gate_rows}</tbody></table></section>
{intelligence_panel}<section class="card section"><h2>Evidence artifacts</h2><table><thead><tr><th>Artifact</th><th>SHA-256</th><th>Bytes</th></tr></thead><tbody>{artifacts}</tbody></table></section>
<section class="card section"><h2>Integrity and boundary</h2><p>Workbench fingerprint: <code>{snapshot.report_fingerprint}</code></p><p>Control-center fingerprint: <code>{snapshot.fingerprint}</code></p><p>This dashboard is informational and cannot create a Candidate, authorize promotion, modify release records, or promote a release.</p></section>
</main></body></html>"""

    def build(
        self,
        report_path: Path,
        output_dir: Path,
        intelligence_report_path: Path | None = None,
    ) -> ControlCenterSnapshot:
        report = WorkbenchReport.model_validate_json(report_path.read_text(encoding="utf-8"))
        snapshot = self.snapshot(report)
        if intelligence_report_path is not None:
            payload = json.loads(intelligence_report_path.read_text(encoding="utf-8"))
            snapshot = snapshot.model_copy(
                update={
                    "intelligence_health": {
                        "release_eligible": payload.get("release_eligible", False),
                        "overall_accuracy": payload.get("overall_accuracy", "n/a"),
                        "macro_f1": payload.get("overall_macro_f1", "n/a"),
                        "calibration_error": payload.get(
                            "overall_expected_calibration_error", "n/a"
                        ),
                        "hallucination_rate": payload.get("overall_hallucination_rate", "n/a"),
                        "fingerprint": hashlib.sha256(
                            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
                        ).hexdigest(),
                    }
                }
            )
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "release-control-center.json").write_text(
            snapshot.model_dump_json(indent=2), encoding="utf-8"
        )
        (output_dir / "index.html").write_text(self.render_html(snapshot), encoding="utf-8")
        (output_dir / "CONTROL_CENTER_FINGERPRINT.sha256").write_text(
            snapshot.fingerprint + "\n", encoding="utf-8"
        )
        return snapshot
