from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED = (
    "final_release_verified",
    "production_source_verified",
    "release_index_v6_active",
    "system_state_v6_active",
    "manifest_v6_active",
    "integrations_current",
    "registry_matches_notion",
    "notion_matches_registry",
    "promotion_decision_active",
    "full_validation_passed",
    "rollback_v5_6_immutable",
)


def evaluate(snapshot: dict[str, bool], *, production: bool = False) -> dict[str, object]:
    checks = {name: bool(snapshot.get(name, False)) for name in REQUIRED}
    settled = all(checks.values())
    if not production and settled:
        raise ValueError("dry-run mode cannot report post-promotion success")
    return {
        "mode": "production" if production else "dry-run",
        "checks": checks,
        "settled": settled,
        "fail_closed": not settled,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot", type=Path, nargs="?")
    parser.add_argument("--mode", choices=("dry-run", "production"))
    parser.add_argument("--production", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    production = args.production or args.mode == "production"
    snapshot = (
        json.loads(args.snapshot.read_text(encoding="utf-8"))
        if args.snapshot
        else {}
    )
    report = evaluate(
        snapshot,
        production=production,
    )
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    if report["fail_closed"] and args.production:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
