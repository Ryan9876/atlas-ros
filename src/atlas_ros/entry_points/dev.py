"""Development-only CLI for the Feature Delivery Toolkit."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

import yaml

from atlas_ros.devtools_cli.contracts import (
    FeatureDefinitionOfDoneV1,
    FeatureImplementationContractV1,
)
from atlas_ros.devtools_cli.impact import assess_changes
from atlas_ros.devtools_cli.validation import validate, write_receipt


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="atlas dev")
    sub = parser.add_subparsers(dest="dev_command", required=True)
    validate_parser = sub.add_parser("validate")
    validate_parser.add_argument(
        "--tier",
        choices=("edit", "feature", "branch", "candidate"),
        required=True,
    )
    validate_parser.add_argument("--execute", action="store_true")
    validate_parser.add_argument("--changed", nargs="*", default=[])
    validate_parser.add_argument("--receipt", type=Path)
    impact = sub.add_parser("explain-impact")
    impact.add_argument("paths", nargs="*")
    readiness = sub.add_parser("release-readiness")
    readiness.add_argument("--dod", type=Path, required=True)
    contract = sub.add_parser("compile-contract")
    contract.add_argument("spec", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    if args.dev_command == "validate":
        receipt = validate(
            args.tier,
            execute=args.execute,
            changed_paths=tuple(args.changed),
        )
        if args.receipt:
            write_receipt(receipt, args.receipt)
        print(json.dumps(asdict(receipt), sort_keys=True))
        if receipt.checks_failed:
            raise SystemExit(1)
        return
    if args.dev_command == "explain-impact":
        print(assess_changes(args.paths).model_dump_json())
        return
    if args.dev_command == "release-readiness":
        dod = FeatureDefinitionOfDoneV1.model_validate(
            yaml.safe_load(args.dod.read_text())
        )
        missing = dod.missing()
        payload = {
            "feature_id": dod.feature_id,
            "missing": missing,
            "ready": not missing,
        }
        print(json.dumps(payload))
        if missing:
            raise SystemExit(1)
        return
    contract = FeatureImplementationContractV1.model_validate(
        yaml.safe_load(args.spec.read_text())
    )
    print(json.dumps(contract.implementation_summary(), sort_keys=True))
