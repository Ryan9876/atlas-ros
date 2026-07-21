from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

import yaml


def _exceptions(path: Path) -> set[tuple[str, str, str]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    today = dt.date.today()
    approved: set[tuple[str, str, str]] = set()
    for item in data.get("exceptions", []):
        expires = dt.date.fromisoformat(str(item["expires_on"]))
        if expires >= today:
            approved.add(
                (
                    str(item["vulnerability_id"]).casefold(),
                    str(item["package"]).casefold(),
                    str(item["affected_version"]),
                )
            )
    return approved


def _load_report(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    dependencies = payload.get("dependencies") if isinstance(payload, dict) else payload
    if not isinstance(dependencies, list):
        raise ValueError(f"{path}: missing pip-audit dependencies array")
    return dependencies


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument(
        "--exceptions",
        type=Path,
        default=Path("security/vulnerability-exceptions.yml"),
    )
    parser.add_argument("--summary", type=Path, default=Path("audit/audit-summary.json"))
    args = parser.parse_args()

    approved = _exceptions(args.exceptions)
    valid_reports: list[str] = []
    invalid_reports: dict[str, str] = {}
    findings: list[dict[str, str | bool]] = []

    for report in args.reports:
        try:
            dependencies = _load_report(report)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            invalid_reports[str(report)] = str(exc)
            continue
        valid_reports.append(str(report))
        for dependency in dependencies:
            name = str(dependency.get("name", ""))
            version = str(dependency.get("version", ""))
            for vulnerability in dependency.get("vulns", []):
                vulnerability_id = str(vulnerability.get("id", ""))
                is_approved = (vulnerability_id.casefold(), name.casefold(), version) in approved
                findings.append(
                    {
                        "vulnerability_id": vulnerability_id,
                        "package": name,
                        "version": version,
                        "approved": is_approved,
                    }
                )

    unapproved = [finding for finding in findings if not finding["approved"]]
    summary = {
        "generated_on": dt.datetime.now(dt.UTC).isoformat(),
        "valid_reports": valid_reports,
        "invalid_reports": invalid_reports,
        "finding_count": len(findings),
        "approved_finding_count": len(findings) - len(unapproved),
        "unapproved_finding_count": len(unapproved),
        "findings": findings,
        "release_gate_passed": bool(valid_reports) and not unapproved,
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if not valid_reports:
        raise SystemExit("dependency audit failed: no valid current-service JSON report")
    if unapproved:
        detail = ", ".join(
            f"{item['vulnerability_id']}:{item['package']}=={item['version']}"
            for item in unapproved
        )
        raise SystemExit(f"dependency audit failed: unapproved vulnerabilities: {detail}")
    print(f"dependency audit passed using {len(valid_reports)} current-service report(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
