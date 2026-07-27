"""Release-tool entry point isolated from the normal runtime CLI."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from importlib import import_module
from pathlib import Path
from typing import Any, Callable


def _call(function_name: str, *args: Any) -> None:
    module = import_module("atlas_ros.cli")
    function: Callable[..., Any] = getattr(module, function_name)
    function(*args)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="atlas-release")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("inventory", "checksums", "verify"):
        command = sub.add_parser(name)
        command.add_argument("--root", type=Path, default=Path("."))
        command.add_argument(
            "--checksum-file",
            type=Path,
            default=Path("release/CHECKSUMS.sha256"),
        )
    args = parser.parse_args(argv)
    if args.command == "inventory":
        _call("release_inventory", args.root)
    elif args.command == "checksums":
        _call("release_checksums", args.root, args.checksum_file)
    elif args.command == "verify":
        _call("release_verify", args.root, args.checksum_file)


if __name__ == "__main__":
    main()
