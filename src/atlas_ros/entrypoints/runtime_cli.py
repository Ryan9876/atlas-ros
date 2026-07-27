"""Lightweight runtime CLI that avoids importing evaluation and release tooling."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence
from importlib import import_module
from typing import Any


def _call(module_name: str, function_name: str, *args: Any, **kwargs: Any) -> None:
    module = import_module(module_name)
    function: Callable[..., Any] = getattr(module, function_name)
    function(*args, **kwargs)


def status(*, json_output: bool = False) -> None:
    payload = {
        "status": "candidate_runtime_available",
        "release": "7.0.0rc1",
        "authority_model": "7.0",
        "writes": False,
        "production_authority": "live-read-required",
    }
    print(json.dumps(payload, sort_keys=True) if json_output else "Atlas ROS v7.0.0rc1 candidate runtime; live authority read required.")


def initialize(*, json_output: bool = False) -> None:
    payload = {
        "status": "initialization_adapter_required",
        "authority": "github-first-four-authority-verification",
        "writes": False,
    }
    print(json.dumps(payload, sort_keys=True) if json_output else "Initialization requires GitHub and Notion authority readers; no writes performed.")


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="atlas")
    sub = parser.add_subparsers(dest="command", required=True)

    status_parser = sub.add_parser("status")
    status_parser.add_argument("--json", action="store_true")
    init_parser = sub.add_parser("initialize")
    init_parser.add_argument("--json", action="store_true")

    capture_parser = sub.add_parser("capture")
    capture_parser.add_argument("content")
    capture_parser.add_argument("--source", default="cli")
    capture_parser.add_argument("--due-date", default="")
    capture_parser.add_argument("--delegate-to", default="")
    capture_parser.add_argument("--context", default="")

    sub.add_parser("plan")
    sub.add_parser("execute")
    sub.add_parser("reconcile")
    connectivity_parser = sub.add_parser("connectivity")
    connectivity_parser.add_argument("--keychain", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "status":
        status(json_output=args.json)
    elif args.command == "initialize":
        initialize(json_output=args.json)
    elif args.command == "capture":
        _call(
            "atlas_ros.cli",
            "capture",
            args.content,
            args.source,
            args.due_date,
            args.delegate_to,
            args.context,
        )
    elif args.command == "connectivity":
        _call("atlas_ros.cli", "connectivity_check", args.keychain)
    elif args.command == "plan":
        raise PermissionError("Planning requires an explicit governed input contract.")
    elif args.command == "execute":
        raise PermissionError("Execution requires an exact attended authorization transaction.")
    elif args.command == "reconcile":
        raise PermissionError("Reconciliation requires explicit provider configuration and readback.")


if __name__ == "__main__":
    main()
