from __future__ import annotations

import argparse
import json
from pathlib import Path

from atlas_ros.intelligence.validation_workbench import ReleaseValidationWorkbench, package_evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Atlas ROS Release Validation Workbench")
    parser.add_argument("--release-id", default="Atlas ROS v5.0")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-root", type=Path)
    parser.add_argument(
        "--manual-evidence",
        type=Path,
        help="JSON mapping of manual gate names to evidence references",
    )
    parser.add_argument("--package", action="store_true")
    args = parser.parse_args()
    evidence = {}
    if args.manual_evidence:
        evidence = json.loads(args.manual_evidence.read_text(encoding="utf-8"))
    workbench = ReleaseValidationWorkbench(args.project_root, args.output_root)
    report = workbench.run(release_id=args.release_id, manual_evidence=evidence)
    run_dir = workbench.output_root / report.run_id
    if args.package:
        package_evidence(run_dir, workbench.output_root / f"{report.run_id}-evidence.zip")
    print(report.model_dump_json(indent=2))
    return 0 if report.decision.value == "validated" else 2


if __name__ == "__main__":
    raise SystemExit(main())
