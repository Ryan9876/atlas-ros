"""Explicit attended command interpretation and planning CLI."""
from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from atlas_ros.application.command_lifecycle import CommandLifecycleCoordinator
from atlas_ros.contracts.operational_awareness import (
    AuthoritativeSystem,
    CommandSourceRefV1,
    OperationalSnapshotV1,
)
from atlas_ros.planning.operational_awareness import OperationalLifecycleExecutionPlanner
from atlas_ros.policy.operational_awareness import load_operational_awareness_policy


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="atlas lifecycle")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("interpret", "plan"):
        item = sub.add_parser(name)
        item.add_argument("--command-text", required=True)
        item.add_argument("--source-task-id", required=True)
        item.add_argument("--source-revision", required=True)
        item.add_argument("--parent-task-id")
        item.add_argument("--snapshot", required=True)
        item.add_argument("--format", choices=("human", "json"), default="json")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    snapshot = OperationalSnapshotV1.model_validate(json.loads(Path(args.snapshot).read_text()))
    source = CommandSourceRefV1.create(
        source_provider=AuthoritativeSystem.TODOIST,
        source_task_id=args.source_task_id,
        source_task_revision=args.source_revision,
        source_command_text=args.command_text,
        parent_task_id=args.parent_task_id,
    )
    result = CommandLifecycleCoordinator(
        load_operational_awareness_policy(), OperationalLifecycleExecutionPlanner()
    ).prepare(
        source, snapshot
    )
    value = result.interpretation if args.command == "interpret" else result
    if args.format == "human":
        print(f"Command: {result.command.command_type.value}")
        print(f"Blocked: {bool(result.interpretation.blockers)}")
        if result.interpretation.blockers:
            print("Blockers: " + "; ".join(result.interpretation.blockers))
        elif result.canonical_plan is not None:
            print(f"Exact operations: {len(result.canonical_plan.operations)}")
            print(f"Plan digest: {result.canonical_plan.plan_digest}")
            print("Provider writes: 0")
        return
    if hasattr(value, "model_dump"):
        payload = value.model_dump(mode="json")
    else:
        payload = {
            "command": result.command.model_dump(mode="json"),
            "interpretation": result.interpretation.model_dump(mode="json"),
            "lifecycle_plan": (
                result.lifecycle_plan.model_dump(mode="json")
                if result.lifecycle_plan
                else None
            ),
            "canonical_plan": (
                result.canonical_plan.model_dump(mode="json")
                if result.canonical_plan
                else None
            ),
            "receipt": result.receipt.model_dump(mode="json"),
        }
    print(json.dumps(payload, sort_keys=True, indent=2))
