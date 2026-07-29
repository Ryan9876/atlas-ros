"""On-demand read-only Operational Awareness command surface."""
from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from atlas_ros.capabilities.operational_awareness import (
    CommitmentIntelligence,
    ExecutionContextService,
    OperatingBriefService,
    OperationalSnapshotBuilder,
    WorkGraphHygieneService,
    WorkStateIntelligence,
)
from atlas_ros.contracts.operational_awareness import (
    NormalizedOperationalRecordV1,
    OperationalSnapshotV1,
)
from atlas_ros.policy.operational_awareness import load_operational_awareness_policy


def _load_snapshot(path: str, *, scope: str = "work") -> OperationalSnapshotV1:
    payload = json.loads(Path(path).read_text())
    policy = load_operational_awareness_policy()
    if isinstance(payload, dict) and payload.get("contract_id") == "atlas.operational-snapshot":
        return OperationalSnapshotV1.model_validate(payload)
    rows = payload.get("records", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("input must be an OperationalSnapshotV1 or a JSON record list")
    records = tuple(NormalizedOperationalRecordV1.model_validate(item) for item in rows)
    return OperationalSnapshotBuilder(policy).build(
        records,
        scope=scope,
        authority_identities=("fixture:authorized-input",),
        generated_at=datetime.now(UTC),
    )


def _emit(value: Any, *, output_format: str) -> None:
    if output_format == "json":
        model_dump = getattr(value, "model_dump", None)
        payload = model_dump(mode="json") if callable(model_dump) else value
        print(json.dumps(payload, sort_keys=True, indent=2))
        return
    if hasattr(value, "highest_value_next_action"):
        action = value.highest_value_next_action
        print("Operational Awareness Brief")
        print(f"Highest-value next action: {action.conclusion if action else 'None'}")
        for label, items in (
            ("Decisions", value.decisions_requiring_ryan),
            ("Blockers", value.new_or_worsened_blockers),
            ("Delegated follow-up", value.delegated_work_requiring_follow_up),
            ("Commitment risk", value.overdue_or_at_risk_commitments),
            ("State warnings", value.stale_or_contradictory_work_state),
            ("Completions", value.material_completions),
        ):
            if items:
                print(f"{label}: " + " | ".join(item.conclusion for item in items))
        print(value.safe_to_ignore_summary)
        print(value.overflow_summary)
        return
    if hasattr(value, "desired_outcome"):
        print(f"Outcome: {value.desired_outcome}")
        print(f"State: {value.effective_work_state.value}")
        print(f"Next: {value.recommended_next_action or 'No next action'}")
        if value.stale_context_warning:
            print(f"Warning: {value.stale_context_warning}")
        print("Evidence: " + ", ".join(value.relevant_records_and_evidence))
        return
    if isinstance(value, tuple):
        for item in value:
            print(f"{item.severity.value}: {item.rule_id}: {item.proposed_disposition}")
        return
    print(value)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="atlas awareness")
    commands = parser.add_subparsers(dest="command", required=True)
    brief = commands.add_parser("brief")
    brief.add_argument("--input", required=True)
    brief.add_argument("--previous")
    brief.add_argument("--scope", default="work")
    brief.add_argument("--format", choices=("human", "json"), default="human")
    for name in ("context", "resume"):
        item = commands.add_parser(name)
        item.add_argument("record_reference")
        item.add_argument("--input", required=True)
        item.add_argument("--format", choices=("human", "json"), default="human")
    hygiene = commands.add_parser("hygiene")
    hygiene_commands = hygiene.add_subparsers(dest="hygiene_command", required=True)
    scan = hygiene_commands.add_parser("scan")
    scan.add_argument("--input", required=True)
    scan.add_argument("--format", choices=("human", "json"), default="human")
    propose = hygiene_commands.add_parser("propose")
    propose.add_argument("finding_id")
    propose.add_argument("--input", required=True)
    propose.add_argument("--format", choices=("human", "json"), default="json")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    policy = load_operational_awareness_policy()
    if args.command == "brief":
        snapshot = _load_snapshot(args.input, scope=args.scope)
        previous = _load_snapshot(args.previous, scope=args.scope) if args.previous else None
        states = WorkStateIntelligence(policy).estimate_all(snapshot)
        commitments = CommitmentIntelligence(policy).assess_all(snapshot, states)
        _emit(
            OperatingBriefService(policy).generate(
                snapshot, states, commitments, previous=previous
            ),
            output_format=args.format,
        )
        return
    snapshot = _load_snapshot(args.input)
    states = WorkStateIntelligence(policy).estimate_all(snapshot)
    if args.command in {"context", "resume"}:
        service = ExecutionContextService(policy)
        value = (
            service.build(snapshot, states, record_id=args.record_reference)
            if args.command == "context"
            else service.resume(snapshot, states, record_id=args.record_reference)
        )
        _emit(value, output_format=args.format)
        return
    service = WorkGraphHygieneService(policy)
    findings = service.scan(snapshot, states)
    if args.hygiene_command == "scan":
        _emit(findings, output_format=args.format)
        return
    finding = next((item for item in findings if item.finding_id == args.finding_id), None)
    if finding is None:
        raise SystemExit(f"unknown hygiene finding: {args.finding_id}")
    _emit(service.propose(finding), output_format=args.format)
