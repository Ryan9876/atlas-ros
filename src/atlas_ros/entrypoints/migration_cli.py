"""Migration entry point isolated from normal runtime execution."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import asdict

from atlas_ros.release.authority_migration import (
    build_drive_inventory,
    load_drive_items,
)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="atlas-migrate")
    sub = parser.add_subparsers(dest="command", required=True)
    drive = sub.add_parser("drive-inventory")
    drive.add_argument("input_file")
    drive.add_argument("--source-folder-id", required=True)
    drive.add_argument("--bootstrap-file-id", required=True)
    args = parser.parse_args(argv)
    if args.command == "drive-inventory":
        report = build_drive_inventory(
            load_drive_items(args.input_file),
            source_folder_id=args.source_folder_id,
            bootstrap_file_id=args.bootstrap_file_id,
        )
        print(json.dumps(asdict(report), default=str, sort_keys=True))


if __name__ == "__main__":
    main()
