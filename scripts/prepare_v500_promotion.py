from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from atlas_ros.intelligence.calibration import (
    load_calibration_cases,
    load_calibration_report,
)


GOVERNED_REVIEW_PATHS = {"independent", "solo_maintainer"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_governed_review(path: Path | None) -> dict[str, Any] | None:
    """Load and validate optional governed-review evidence.

    The preparation command remains backward compatible: without a review file it
    reports that the candidate is ready for governed review. Supplying approved
    evidence allows the output to record that the governed-review gate is met.
    """
    if path is None:
        return None

    review = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "path",
        "reviewer",
        "status",
        "evidence_reference",
        "reviewed_head_sha",
        "checklist_evidence",
    }
    missing = sorted(required - review.keys())
    if missing:
        missing_fields = ", ".join(missing)
        raise ValueError(f"governed review evidence missing fields: {missing_fields}")
    if review["path"] not in GOVERNED_REVIEW_PATHS:
        raise ValueError("governed review path must be independent or solo_maintainer")
    if review["status"] != "approved":
        raise ValueError("governed review evidence must have approved status")
    if review["path"] == "solo_maintainer" and not review["checklist_evidence"]:
        raise ValueError("solo-maintainer review requires checklist evidence")
    return review


def main() -> int:
    if len(sys.argv) not in {4, 5}:
        raise SystemExit(
            "usage: prepare_v500_promotion.py CASES CALIBRATION_REPORT OUTPUT_DIR "
            "[GOVERNED_REVIEW_JSON]"
        )

    cases_path = Path(sys.argv[1])
    report_path = Path(sys.argv[2])
    output_dir = Path(sys.argv[3])
    review_path = Path(sys.argv[4]) if len(sys.argv) == 5 else None
    output_dir.mkdir(parents=True, exist_ok=True)

    cases = load_calibration_cases(cases_path)
    report = load_calibration_report(report_path)
    governed_review = load_governed_review(review_path)
    blockers: list[str] = []

    if len(cases) < 50:
        blockers.append("benchmark corpus has fewer than 50 cases")
    if not report.release_eligible:
        blockers.extend(
            report.blocking_violations or ("calibration report not release eligible",)
        )

    if blockers:
        status = "blocked"
        required_next_action = "resolve blocking validation gates"
    elif governed_review is None:
        status = "candidate_ready_for_governed_review"
        required_next_action = "complete governed review and full provisioned CI"
    else:
        status = "proposable_candidate"
        required_next_action = (
            "verify full provisioned CI and request explicit promotion authorization"
        )

    payload = {
        "release": "Atlas ROS v5.0",
        "base_authority": "Atlas ROS v4.5.3",
        "rollback": "Atlas ROS v4.5.3",
        "status": status,
        "promotion_authorized": False,
        "case_count": len(cases),
        "dataset_fingerprint": report.dataset_fingerprint,
        "calibration_fingerprint": report.fingerprint,
        "governed_review": governed_review,
        "blockers": blockers,
        "required_next_action": required_next_action,
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
