from __future__ import annotations

import argparse
from pathlib import Path

from atlas_ros.intelligence.release_control_center import ReleaseControlCenter


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the read-only Atlas ROS Release Control Center"
    )
    parser.add_argument("report", type=Path)
    parser.add_argument("--output", type=Path, default=Path("release-control-center"))
    parser.add_argument("--active-release", default="Atlas ROS v4.5.3")
    parser.add_argument("--rollback-release", default="Atlas ROS v4.5.2")
    parser.add_argument("--intelligence-report", type=Path)
    args = parser.parse_args()
    center = ReleaseControlCenter(
        active_release=args.active_release, rollback_release=args.rollback_release
    )
    snapshot = center.build(args.report, args.output, args.intelligence_report)
    print(f"status={snapshot.status.value} output={args.output} fingerprint={snapshot.fingerprint}")
    return 0 if snapshot.status.value == "candidate_ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
