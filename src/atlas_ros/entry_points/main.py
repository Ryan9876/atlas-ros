"""Lightweight Atlas runtime command dispatcher."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from atlas_ros import __version__

CANDIDATE_VERSION = "7.6.0"
ACTIVE_PRODUCTION_VERSION = "7.5.2"


class RuntimeCommandError(RuntimeError):
    """Raised when a runtime command cannot safely execute in the current surface."""


def status(*, json_output: bool = False) -> None:
    """Report installed runtime identity without loading providers or release tooling."""
    payload = {
        "status": "candidate_runtime_available",
        "version": __version__,
        "authority_model_version": "7.0",
        "active_production_version": ACTIVE_PRODUCTION_VERSION,
        "production_authority_changed": False,
        "provider_writes": False,
    }
    if json_output:
        print(json.dumps(payload, sort_keys=True))
        return
    print(
        f"Atlas ROS {__version__} candidate runtime is installed; "
        f"Atlas ROS {ACTIVE_PRODUCTION_VERSION} remains Active and no provider writes "
        "were performed."
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
            "Todoist liveness reader",
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
    """Verify only the installed candidate identity; release verification is separate."""
    payload = {
        "valid": __version__ == CANDIDATE_VERSION,
        "scope": "installed_candidate_runtime_identity",
        "version": __version__,
        "active_production_version": ACTIVE_PRODUCTION_VERSION,
        "writes": False,
    }
    if json_output:
        print(json.dumps(payload, sort_keys=True))
        return
    if not payload["valid"]:
        raise RuntimeCommandError(
            f"installed runtime identity is not Atlas ROS v{CANDIDATE_VERSION}"
        )
    print(
        f"Installed candidate identity verified: Atlas ROS {__version__}; "
        f"Active production remains {ACTIVE_PRODUCTION_VERSION}; writes: 0."
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="atlas")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("status", "initialize", "verify"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--json", action="store_true")
    subparsers.add_parser("process")
    subparsers.add_parser("plan")
    subparsers.add_parser("execute")
    subparsers.add_parser("awareness")
    subparsers.add_parser("lifecycle")
    return parser


def _dispatch_status(arguments: Sequence[str]) -> None:
    args = _parser().parse_args(["status", *arguments])
    status(json_output=args.json)


def _dispatch_initialize(arguments: Sequence[str]) -> None:
    args = _parser().parse_args(["initialize", *arguments])
    initialize(json_output=args.json)


def _dispatch_verify(arguments: Sequence[str]) -> None:
    args = _parser().parse_args(["verify", *arguments])
    verify(json_output=args.json)


def _dispatch_process(arguments: Sequence[str]) -> None:
    if arguments:
        raise RuntimeCommandError("process does not accept arguments in the candidate surface")
    raise RuntimeCommandError(
        "process is not exposed until the canonical capability pipeline is bound"
    )


def _dispatch_plan(arguments: Sequence[str]) -> None:
    if arguments:
        raise RuntimeCommandError("plan does not accept arguments in the candidate surface")
    raise RuntimeCommandError(
        "plan is not exposed until the canonical capability pipeline is bound"
    )


def _dispatch_execute(arguments: Sequence[str]) -> None:
    if arguments:
        raise RuntimeCommandError("execute does not accept arguments in the candidate surface")
    raise RuntimeCommandError(
        "execution requires an immutable authorized plan and configured provider adapter"
    )


def _dispatch_awareness(arguments: Sequence[str]) -> None:
    from atlas_ros.entry_points.awareness import main as awareness_main

    awareness_main(arguments)


def _dispatch_lifecycle(arguments: Sequence[str]) -> None:
    from atlas_ros.entry_points.lifecycle import main as lifecycle_main

    lifecycle_main(arguments)


_COMMANDS = {
    "status": _dispatch_status,
    "initialize": _dispatch_initialize,
    "verify": _dispatch_verify,
    "process": _dispatch_process,
    "plan": _dispatch_plan,
    "execute": _dispatch_execute,
    "awareness": _dispatch_awareness,
    "lifecycle": _dispatch_lifecycle,
}


def main(argv: Sequence[str] | None = None) -> None:
    """Dispatch canonical commands without legacy or release-tooling fallbacks."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments:
        _parser().print_help()
        raise SystemExit(2)
    command, *remaining = arguments
    handler = _COMMANDS.get(command)
    if handler is None:
        _parser().error(f"unknown command: {command}")
    handler(remaining)


if __name__ == "__main__":
    main()
