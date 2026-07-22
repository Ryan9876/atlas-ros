from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from atlas_ros.intelligence.release_readiness import GateStatus


class GateKind(StrEnum):
    COMMAND = "command"
    FILE = "file"
    MANUAL = "manual"


class GateDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    kind: GateKind = GateKind.COMMAND
    command: tuple[str, ...] = ()
    required_executable: str | None = None
    required_path: str | None = None
    blocking: bool = True
    timeout_seconds: int = Field(default=900, ge=1)
    description: str = ""

    @model_validator(mode="after")
    def validate_definition(self) -> GateDefinition:
        if self.kind is GateKind.COMMAND and not self.command:
            raise ValueError("command gate requires command")
        if self.kind is GateKind.FILE and not self.required_path:
            raise ValueError("file gate requires required_path")
        return self


class GateResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    status: GateStatus
    blocking: bool
    started_at: datetime
    completed_at: datetime
    duration_seconds: float = Field(ge=0)
    command: tuple[str, ...] = ()
    exit_code: int | None = None
    log_path: str | None = None
    evidence: tuple[str, ...] = ()
    reason: str | None = None


class EvidenceArtifact(BaseModel):
    model_config = ConfigDict(frozen=True)

    relative_path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)


class WorkbenchDecision(StrEnum):
    BLOCKED = "blocked"
    VALIDATED = "validated"


class WorkbenchReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    release_id: str
    run_id: str
    started_at: datetime
    completed_at: datetime
    decision: WorkbenchDecision
    results: tuple[GateResult, ...]
    blocking_reasons: tuple[str, ...]
    artifacts: tuple[EvidenceArtifact, ...]
    environment: Mapping[str, str]

    @property
    def fingerprint(self) -> str:
        payload = self.model_dump(mode="json", exclude={"started_at", "completed_at"})
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


DEFAULT_GATES: tuple[GateDefinition, ...] = (
    GateDefinition(
        name="ruff",
        command=(sys.executable, "-m", "ruff", "check", "."),
        required_executable="ruff",
    ),
    GateDefinition(
        name="mypy_strict",
        command=(sys.executable, "-m", "mypy", "src"),
        required_executable="mypy",
    ),
    GateDefinition(name="tests", command=(sys.executable, "-m", "pytest")),
    GateDefinition(
        name="source_wheel_build",
        command=(sys.executable, "-m", "build"),
        required_executable="build",
    ),
    GateDefinition(
        name="dependency_lock", command=(sys.executable, "scripts/validate_dependency_lock.py")
    ),
    GateDefinition(
        name="vulnerability_exceptions",
        command=(sys.executable, "scripts/validate_vulnerability_exceptions.py"),
    ),
    GateDefinition(
        name="dependency_security",
        command=(sys.executable, "-m", "pip_audit", "-r", "requirements.runtime.lock"),
        required_executable="pip_audit",
    ),
    GateDefinition(
        name="benchmark_corpus",
        kind=GateKind.FILE,
        required_path="config/intelligence-evaluation.yaml",
    ),
    GateDefinition(
        name="candidate_preparation",
        kind=GateKind.FILE,
        required_path="docs/CANDIDATE_PREPARATION.md",
    ),
    GateDefinition(
        name="independent_review",
        kind=GateKind.MANUAL,
        description="Independent architecture, security, and governance review.",
    ),
)


class ReleaseValidationWorkbench:
    """Run validation gates and emit evidence without promotion authority."""

    def __init__(self, project_root: Path, output_root: Path | None = None) -> None:
        self.project_root = project_root.resolve()
        self.output_root = (output_root or self.project_root / "validation-output").resolve()

    @staticmethod
    def _module_available(name: str) -> bool:
        probe = subprocess.run(
            [
                sys.executable,
                "-c",
                "import importlib.util; "
                f"raise SystemExit(0 if importlib.util.find_spec('{name}') else 1)",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        return probe.returncode == 0

    def _run_gate(self, gate: GateDefinition, run_dir: Path) -> GateResult:
        started = datetime.now(UTC)
        monotonic_start = time.monotonic()
        log_path = run_dir / "logs" / f"{gate.name}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        status = GateStatus.NOT_RUN
        reason: str | None = None
        exit_code: int | None = None
        evidence: tuple[str, ...] = ()

        if gate.kind is GateKind.MANUAL:
            reason = "manual evidence not supplied"
            log_path.write_text(reason + "\n", encoding="utf-8")
        elif gate.kind is GateKind.FILE:
            required = self.project_root / str(gate.required_path)
            if required.is_file():
                status = GateStatus.PASS
                evidence = (str(required.relative_to(self.project_root)),)
                log_path.write_text(f"verified file: {required}\n", encoding="utf-8")
            else:
                status = GateStatus.FAIL
                reason = f"required file missing: {gate.required_path}"
                log_path.write_text(reason + "\n", encoding="utf-8")
        else:
            module = gate.required_executable
            if module and not self._module_available(module):
                reason = f"required Python module unavailable: {module}"
                log_path.write_text(reason + "\n", encoding="utf-8")
            else:
                env = os.environ.copy()
                env.setdefault("PYTHONHASHSEED", "0")
                try:
                    proc = subprocess.run(
                        list(gate.command),
                        cwd=self.project_root,
                        env=env,
                        capture_output=True,
                        text=True,
                        timeout=gate.timeout_seconds,
                        check=False,
                    )
                    exit_code = proc.returncode
                    log_path.write_text(
                        "$ "
                        + " ".join(gate.command)
                        + "\n\nSTDOUT\n"
                        + proc.stdout
                        + "\nSTDERR\n"
                        + proc.stderr,
                        encoding="utf-8",
                    )
                    status = GateStatus.PASS if proc.returncode == 0 else GateStatus.FAIL
                    if status is GateStatus.FAIL:
                        reason = f"command exited with code {proc.returncode}"
                except subprocess.TimeoutExpired as exc:
                    status = GateStatus.FAIL
                    reason = f"command timed out after {gate.timeout_seconds}s"
                    log_path.write_text(str(exc), encoding="utf-8")

        completed = datetime.now(UTC)
        return GateResult(
            name=gate.name,
            status=status,
            blocking=gate.blocking,
            started_at=started,
            completed_at=completed,
            duration_seconds=round(time.monotonic() - monotonic_start, 6),
            command=gate.command,
            exit_code=exit_code,
            log_path=str(log_path.relative_to(run_dir)),
            evidence=evidence,
            reason=reason,
        )

    @staticmethod
    def _digest(path: Path, root: Path) -> EvidenceArtifact:
        data = path.read_bytes()
        return EvidenceArtifact(
            relative_path=str(path.relative_to(root)),
            sha256=hashlib.sha256(data).hexdigest(),
            size_bytes=len(data),
        )

    @staticmethod
    def _markdown(report: WorkbenchReport) -> str:
        lines = [
            f"# Release Validation Workbench — {report.release_id}",
            "",
            f"- Run ID: `{report.run_id}`",
            f"- Decision: **{report.decision.value}**",
            f"- Fingerprint: `{report.fingerprint}`",
            "- Promotion authority: **not granted**",
            "",
            "## Gate results",
            "",
            "| Gate | Status | Blocking | Reason |",
            "|---|---|---:|---|",
        ]
        for result in report.results:
            lines.append(
                f"| {result.name} | {result.status.value} | "
                f"{'yes' if result.blocking else 'no'} | "
                f"{result.reason or ''} |"
            )
        lines.extend(["", "## Blocking reasons", ""])
        lines.extend(f"- {reason}" for reason in report.blocking_reasons)
        if not report.blocking_reasons:
            lines.append("- None")
        lines.extend(
            [
                "",
                "## Boundary",
                "",
                "This report validates evidence only. It cannot create a Candidate "
                "or promote a release.",
                "",
            ]
        )
        return "\n".join(lines)

    def run(
        self,
        *,
        release_id: str,
        gates: Sequence[GateDefinition] = DEFAULT_GATES,
        manual_evidence: Mapping[str, Sequence[str]] | None = None,
    ) -> WorkbenchReport:
        started = datetime.now(UTC)
        run_id = started.strftime("%Y%m%dT%H%M%SZ")
        run_dir = self.output_root / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        manual_evidence = manual_evidence or {}

        results: list[GateResult] = []
        for gate in gates:
            if gate.kind is GateKind.MANUAL and manual_evidence.get(gate.name):
                now = datetime.now(UTC)
                results.append(
                    GateResult(
                        name=gate.name,
                        status=GateStatus.PASS,
                        blocking=gate.blocking,
                        started_at=now,
                        completed_at=now,
                        duration_seconds=0,
                        evidence=tuple(manual_evidence[gate.name]),
                        reason=None,
                    )
                )
            else:
                results.append(self._run_gate(gate, run_dir))

        blocking_reasons = tuple(
            f"{result.name}: {result.reason or result.status.value}"
            for result in results
            if result.blocking and result.status is not GateStatus.PASS
        )
        decision = WorkbenchDecision.BLOCKED if blocking_reasons else WorkbenchDecision.VALIDATED
        completed = datetime.now(UTC)
        preliminary = WorkbenchReport(
            release_id=release_id,
            run_id=run_id,
            started_at=started,
            completed_at=completed,
            decision=decision,
            results=tuple(results),
            blocking_reasons=blocking_reasons,
            artifacts=(),
            environment={
                "python": sys.version.split()[0],
                "platform": sys.platform,
                "project_root": str(self.project_root),
            },
        )
        json_path = run_dir / "validation-report.json"
        md_path = run_dir / "validation-report.md"
        json_path.write_text(preliminary.model_dump_json(indent=2), encoding="utf-8")
        md_path.write_text(self._markdown(preliminary), encoding="utf-8")

        artifact_paths = sorted(path for path in run_dir.rglob("*") if path.is_file())
        artifacts = tuple(self._digest(path, run_dir) for path in artifact_paths)
        report = preliminary.model_copy(update={"artifacts": artifacts})
        json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        md_path.write_text(self._markdown(report), encoding="utf-8")
        checksums = "\n".join(f"{a.sha256}  {a.relative_path}" for a in report.artifacts) + "\n"
        (run_dir / "CHECKSUMS.sha256").write_text(checksums, encoding="utf-8")
        (run_dir / "REPORT_FINGERPRINT.sha256").write_text(
            report.fingerprint + "\n", encoding="utf-8"
        )
        return report


def package_evidence(run_dir: Path, destination: Path) -> Path:
    """Create a deterministic zip archive of a completed evidence directory."""
    import zipfile

    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(run_dir.rglob("*")):
            if not path.is_file():
                continue
            info = zipfile.ZipInfo(str(path.relative_to(run_dir)))
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    return destination
