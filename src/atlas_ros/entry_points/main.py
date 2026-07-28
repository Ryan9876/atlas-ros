"""Lightweight Atlas runtime command dispatcher."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from atlas_ros import __version__


class RuntimeCommandError(RuntimeError):
    """Raised when a runtime command cannot safely execute in the current surface."""


def status(*, json_output: bool = False) -> None:
    """Report installed runtime identity without loading providers or release tooling."""
    payload = {
        "status": "final_runtime_available",
        "version": __version__,
        "authority_model_version": "7.0",
        "production_authority_changed": False,
        "provider_writes": False,
    }
    if json_output:
        print(json.dumps(payload, sort_keys=True))
        return
    print(
        f"Atlas ROS {__version__} final runtime is installed; "
        "production authority is unchanged and no provider writes were performed."
    )


def initialize(*, json_output: bool = False) -> None:
    """Fail closed when the CLI has no configured immutable and dynamic readers."""
    payload = {
        "status": "initialization_blocked",
        "reason": "authority_readers_not_configured",
        "required": [
            "GitHub authority reader",
            "Notion System State reader",
            "Notion Integration Inventory reader",
        ],
        "writes": False,
    }
    if json_output:
        print(json.dumps(payload, sort_keys=True))
        return
    print(
        "INITIALIZATION BLOCKED: configured GitHub and Notion authority readers "
        "are required; no production state was inferred or changed."
    )


def verify(*, json_output: bool = False) -> None:
    """Verify only the installed runtime identity; release verification is separate."""
    payload = {
        "valid": __version__ == "7.0.0",
        "scope": "installed_runtime_identity",
        "version": __version__,
        "writes": False,
    }
    if json_output:
        print(json.dumps(payload, sort_keys=True))
        return
    if not payload["valid"]:
        raise RuntimeCommandError("installed runtime identity is not the final v7.0.0 release")
    print(f"Installed runtime identity verified: Atlas ROS {__version__}; writes: 0.")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="atlas")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("status", "initialize", "verify"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--json", action="store_true")
    subparsers.add_parser("process")
    subparsers.add_parser("plan")
    subparsers.add_parser("execute")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Dispatch lightweight commands and lazily load compatibility commands."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments:
        _parser().print_help()
        raise SystemExit(2)

    command = arguments[0]
    if command not in {"status", "initialize", "verify", "process", "plan", "execute"}:
        from atlas_ros.entry_points._legacy import forward_legacy

        forward_legacy()
        return

    args = _parser().parse_args(arguments)
    if args.command == "status":
        status(json_output=args.json)
    elif args.command == "initialize":
        initialize(json_output=args.json)
    elif args.command == "verify":
        verify(json_output=args.json)
    elif args.command == "execute":
        raise RuntimeCommandError(
            "execution requires an immutable authorized plan and configured provider adapter"
        )
    else:
        raise RuntimeCommandError(
            f"{args.command} is not exposed until the canonical capability pipeline is bound"
        )


if __name__ == "__main__":
    main()