"""Evaluation entry point isolated from the production runtime command."""

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
    parser = argparse.ArgumentParser(prog="atlas-evaluate")
    sub = parser.add_subparsers(dest="command", required=True)
    evaluate = sub.add_parser("results")
    evaluate.add_argument("results_file", type=Path)
    validate = sub.add_parser("validate-set")
    validate.add_argument("cases_file", type=Path)
    validate.add_argument("--results-file", type=Path)
    args = parser.parse_args(argv)
    if args.command == "results":
        _call("intelligence_evaluate", args.results_file)
    elif args.command == "validate-set":
        _call("intelligence_validate_set", args.cases_file, args.results_file)


if __name__ == "__main__":
    main()
