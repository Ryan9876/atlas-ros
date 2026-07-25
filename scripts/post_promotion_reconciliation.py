from __future__ import annotations

import argparse
import json
from pathlib import Path

from atlas_ros.release.post_promotion import evaluate_post_promotion


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
    report = evaluate_post_promotion(
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
