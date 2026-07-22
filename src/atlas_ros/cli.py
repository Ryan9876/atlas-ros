from __future__ import annotations

import argparse
import getpass
import json
import os
from pathlib import Path

from atlas_ros.adapters.notion import LiveNotionAdapter
from atlas_ros.adapters.todoist import LiveTodoistAdapter
from atlas_ros.domain.models import Action
from atlas_ros.intelligence.calibration import (
    IntelligenceCalibrationEngine,
    load_calibration_cases,
    load_calibration_report,
    load_intelligence_judgments,
)
from atlas_ros.intelligence.dataset import validate_files
from atlas_ros.intelligence.evaluation import BenchmarkRunner
from atlas_ros.intelligence.io import load_results
from atlas_ros.release.tooling import checksums, inventory, verify
from atlas_ros.runtime.database import RuntimeDatabase
from atlas_ros.workflows import (
    CaptureService,
    DecompositionService,
    TodoistReconciliationService,
    TodoistService,
)
from atlas_ros.workflows.reconciliation_state import NotionReconciliationStateStore


def runtime() -> RuntimeDatabase:
    root = Path(os.environ.get("ATLAS_RUNTIME_DIR", Path.cwd() / ".atlas-runtime"))
    database = RuntimeDatabase(root / "runtime.db")
    database.initialize()
    return database


def status() -> None:
    print(
        "runtime status: production-capable attended executable; "
        "live release authority must be resolved from Google Drive and Notion"
    )


def initialize(json_output: bool = False) -> None:
    payload = {
        "status": "runtime_initialized",
        "writes": False,
        "authority": "live-authority-read-required",
    }
    print(
        json.dumps(payload)
        if json_output
        else "Runtime initialized locally; no production authority was modified."
    )


def capture(content: str, source: str = "cli") -> None:
    item = CaptureService(runtime()).capture(content, source)
    print(item.model_dump_json())


def decompose(
    action_id: str,
    title: str,
    owner: str = "",
    definition_of_done: str = "",
    execution_ready: bool = False,
    delegation_reviewed: bool = False,
    delegated_work_required: bool = False,
    delegated_work: bool = False,
) -> None:
    report = DecompositionService().readiness(
        Action(
            id=action_id,
            title=title,
            owner=owner,
            definition_of_done=definition_of_done,
            execution_ready=execution_ready,
            delegation_reviewed=delegation_reviewed or delegated_work,
            delegated_work_required=delegated_work_required,
            delegated_work_present=delegated_work,
        )
    )
    print(report.model_dump_json())


def todoist_plan(
    action_id: str,
    title: str,
    owner: str,
    definition_of_done: str,
    execution_ready: bool = True,
    delegation_reviewed: bool = True,
    delegated_work_required: bool = False,
    delegated_work: bool = False,
) -> None:
    plan = TodoistService().plan(
        Action(
            id=action_id,
            title=title,
            owner=owner,
            definition_of_done=definition_of_done,
            execution_ready=execution_ready,
            delegation_reviewed=delegation_reviewed or delegated_work,
            delegated_work_required=delegated_work_required,
            delegated_work_present=delegated_work,
        )
    )
    print(json.dumps(plan.__dict__))


def todoist_apply() -> None:
    raise PermissionError(
        "Direct W03 apply is not exposed by this CLI; use the attended connector workflow."
    )


def todoist_reconcile(*, apply: bool, full: bool, task_id: str, keychain: bool) -> None:
    account = os.environ.get("USER") or getpass.getuser()
    if keychain:
        notion = LiveNotionAdapter.from_keychain(account)
        todoist = LiveTodoistAdapter.from_keychain(account)
    else:
        notion = LiveNotionAdapter.from_environment()
        todoist = LiveTodoistAdapter.from_environment()
    action_source = os.environ.get("ATLAS_ACTION_DATA_SOURCE_ID", "")
    if not action_source:
        raise ValueError("ATLAS_ACTION_DATA_SOURCE_ID is required")
    database = runtime()
    shared_state_id = os.environ.get("ATLAS_RECONCILIATION_STATE_DATA_SOURCE_ID", "")
    state_store = (
        NotionReconciliationStateStore(notion, shared_state_id) if shared_state_id else None
    )
    service = TodoistReconciliationService(
        notion,
        todoist,
        database,
        action_data_source_id=action_source,
        execution_step_data_source_id=os.environ.get("ATLAS_EXECUTION_STEP_DATA_SOURCE_ID", ""),
        delegated_work_data_source_id=os.environ.get("ATLAS_DELEGATED_WORK_DATA_SOURCE_ID", ""),
        blocker_data_source_id=os.environ.get("ATLAS_BLOCKER_DATA_SOURCE_ID", ""),
        operations_data_source_id=os.environ.get("ATLAS_OPERATIONS_DATA_SOURCE_ID", ""),
        state_store=state_store,
    )
    plan = service.plan(full=full, task_id=task_id)
    payload: dict[str, object] = {
        "mode": "apply" if apply else "dry-run",
        "generated_at": plan.generated_at.isoformat(),
        "mutations": [
            {
                "type": mutation.mutation_type.value,
                "notion_page_id": mutation.notion_page_id,
                "todoist_task_id": mutation.todoist_task_id,
                "summary": mutation.summary,
                "properties": mutation.properties,
            }
            for mutation in plan.mutations
        ],
        "ignored": list(plan.ignored),
        "conflicts": list(plan.conflicts),
    }
    if apply:
        payload["result"] = service.apply(plan, confirmed=True).__dict__
    print(json.dumps(payload, default=str))


def connectivity_check(keychain: bool) -> None:
    account = os.environ.get("USER") or getpass.getuser()
    if keychain:
        if not account:
            raise ValueError("USER is required when --keychain is used")
        notion = LiveNotionAdapter.from_keychain(account)
        todoist = LiveTodoistAdapter.from_keychain(account)
    else:
        notion = LiveNotionAdapter.from_environment()
        todoist = LiveTodoistAdapter.from_environment()
    notion_identity = notion.get_current_user()
    projects = todoist.list_projects()
    print(
        json.dumps(
            {
                "valid": True,
                "writes": False,
                "notion_identity_confirmed": isinstance(notion_identity.get("id"), str),
                "todoist_project_count": len(projects),
            }
        )
    )



def intelligence_evaluate(results_file: Path) -> None:
    report = BenchmarkRunner().run(load_results(results_file))
    print(report.model_dump_json())


def intelligence_calibrate(cases_file: Path, judgments_file: Path) -> None:
    report = IntelligenceCalibrationEngine().run(
        load_calibration_cases(cases_file),
        load_intelligence_judgments(judgments_file),
    )
    print(report.model_dump_json())


def intelligence_compare_calibration(baseline_file: Path, current_file: Path) -> None:
    report = IntelligenceCalibrationEngine().compare_regression(
        load_calibration_report(baseline_file),
        load_calibration_report(current_file),
    )
    print(report.model_dump_json())


def intelligence_validate_set(cases_file: Path, results_file: Path | None) -> None:
    validation = validate_files(cases_file, results_file)
    print(json.dumps({
        "valid": validation.valid,
        "case_count": validation.case_count,
        "result_count": validation.result_count,
        "covered_dimensions": [item.value for item in validation.covered_dimensions],
        "errors": list(validation.errors),
    }))
    if not validation.valid:
        raise ValueError("intelligence evaluation set validation failed")


def release_inventory(root: Path = Path(".")) -> None:
    print("\n".join(path.relative_to(root).as_posix() for path in inventory(root)))


def release_checksums(
    root: Path = Path("."), target: Path = Path("release/CHECKSUMS.sha256")
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    checksums(root, target)
    print(target)


def release_verify(
    root: Path = Path("."), checksum_file: Path = Path("release/CHECKSUMS.sha256")
) -> None:
    errors = verify(root, checksum_file)
    if errors:
        raise ValueError(json.dumps({"valid": False, "mismatches": errors}))
    print('{"valid":true}')


def main() -> None:
    parser = argparse.ArgumentParser(prog="atlas")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    init = sub.add_parser("initialize")
    init.add_argument("--json", action="store_true")
    cap = sub.add_parser("capture")
    cap.add_argument("content")
    cap.add_argument("--source", default="cli")
    todoist_cmd = sub.add_parser("todoist")
    todoist_sub = todoist_cmd.add_subparsers(dest="todoist_command", required=True)
    reconcile = todoist_sub.add_parser("reconcile")
    reconcile.add_argument("--apply", action="store_true")
    reconcile.add_argument("--full", action="store_true")
    reconcile.add_argument("--task", default="")
    reconcile.add_argument("--keychain", action="store_true")
    connectivity = sub.add_parser("connectivity")
    connectivity.add_argument("--keychain", action="store_true")
    dec = sub.add_parser("decompose")
    dec.add_argument("action_id")
    dec.add_argument("title")
    dec.add_argument("--owner", default="")
    dec.add_argument("--definition-of-done", default="")
    dec.add_argument("--execution-ready", action="store_true")
    dec.add_argument("--delegation-reviewed", action="store_true")
    dec.add_argument("--delegated-work-required", action="store_true")
    dec.add_argument("--delegated-work", action="store_true")
    intelligence = sub.add_parser("intelligence")
    intelligence_sub = intelligence.add_subparsers(dest="intelligence_command", required=True)
    evaluate = intelligence_sub.add_parser("evaluate")
    evaluate.add_argument("results_file", type=Path)
    validate_set = intelligence_sub.add_parser("validate-set")
    validate_set.add_argument("cases_file", type=Path)
    validate_set.add_argument("--results-file", type=Path)
    calibrate = intelligence_sub.add_parser("calibrate")
    calibrate.add_argument("cases_file", type=Path)
    calibrate.add_argument("judgments_file", type=Path)
    compare_calibration = intelligence_sub.add_parser("compare-calibration")
    compare_calibration.add_argument("baseline_file", type=Path)
    compare_calibration.add_argument("current_file", type=Path)
    rel = sub.add_parser("release")
    relsub = rel.add_subparsers(dest="release_command")
    for command in ("inventory", "checksums", "verify"):
        rp = relsub.add_parser(command)
        rp.add_argument("--root", type=Path, default=Path("."))
        rp.add_argument("--checksum-file", type=Path, default=Path("release/CHECKSUMS.sha256"))
    args = parser.parse_args()
    if args.command == "status":
        status()
    elif args.command == "initialize":
        initialize(args.json)
    elif args.command == "capture":
        capture(args.content, args.source)
    elif args.command == "todoist" and args.todoist_command == "reconcile":
        todoist_reconcile(
            apply=args.apply, full=args.full, task_id=args.task, keychain=args.keychain
        )
    elif args.command == "connectivity":
        connectivity_check(args.keychain)
    elif args.command == "intelligence" and args.intelligence_command == "evaluate":
        intelligence_evaluate(args.results_file)
    elif args.command == "intelligence" and args.intelligence_command == "validate-set":
        intelligence_validate_set(args.cases_file, args.results_file)
    elif args.command == "intelligence" and args.intelligence_command == "calibrate":
        intelligence_calibrate(args.cases_file, args.judgments_file)
    elif args.command == "intelligence" and args.intelligence_command == "compare-calibration":
        intelligence_compare_calibration(args.baseline_file, args.current_file)
    elif args.command == "decompose":
        decompose(
            args.action_id,
            args.title,
            args.owner,
            args.definition_of_done,
            args.execution_ready,
            args.delegation_reviewed,
            args.delegated_work_required,
            args.delegated_work,
        )
    elif args.command == "release" and args.release_command == "inventory":
        release_inventory(args.root)
    elif args.command == "release" and args.release_command == "checksums":
        release_checksums(args.root, args.checksum_file)
    elif args.command == "release" and args.release_command == "verify":
        release_verify(args.root, args.checksum_file)


if __name__ == "__main__":
    main()
