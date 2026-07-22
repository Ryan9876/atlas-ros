from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from atlas_ros.intelligence.calibration import (
    load_calibration_cases,
    load_calibration_report,
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: prepare_v500_promotion.py CASES CALIBRATION_REPORT OUTPUT_DIR"
        )

    cases_path = Path(sys.argv[1])
    report_path = Path(sys.argv[2])
    output_dir = Path(sys.argv[3])
    output_dir.mkdir(parents=True, exist_ok=True)

    cases = load_calibration_cases(cases_path)
    report = load_calibration_report(report_path)
    blockers: list[str] = []

    if len(cases) < 50:
        blockers.append("benchmark corpus has fewer than 50 cases")
    if not report.release_eligible:
        blockers.extend(
            report.blocking_violations
            or ("calibration report not release eligible",)
        )

    status = "candidate_ready_for_independent_review" if not blockers else "blocked"
    payload = {
        "release": "Atlas ROS v5.0",
        "base_authority": "Atlas ROS v4.5.3",
        "rollback": "Atlas ROS v4.5.3",
        "status": status,
        "promotion_authorized": False,
        "case_count": len(cases),
        "dataset_fingerprint": report.dataset_fingerprint,
        "calibration_fingerprint": report.fingerprint,
        "blockers": blockers,
        "required_next_action": (
            "independent reviewer approval and full provisioned CI"
        ),
    }

    target = output_dir / "V500_PROMOTION_READINESS.json"
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    checksum_path = output_dir / "V500_PROMOTION_READINESS.sha256"
    checksum_path.write_text(
        f"{sha(target)}  {target.name}\n",
        encoding="utf-8",
    )
    print(json.dumps(payload))
    return 0 if not blockers else 2


if __name__ == "__main__":
    raise SystemExit(main())
