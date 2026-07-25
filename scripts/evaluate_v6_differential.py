from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

FIXTURE = r"""
import json
from atlas_ros.domain.models import Action
{imports}

action = Action(
    id="A-1",
    title="Prepare Team Operating Model",
    owner="Ryan",
    definition_of_done="Reviewed operating model is approved",
    execution_ready=True,
    delegation_reviewed=True,
)
plan = TodoistService().plan(action)
command = parse_atlas_command("@atlas checkpoint 2026-08-01")
print(json.dumps({{
    "action_id": plan.action_id,
    "project": plan.project,
    "subtasks": plan.subtasks,
    "section": plan.routing.selected_section if plan.routing else "",
    "description": task_description(action.title, action.definition_of_done),
    "command_kind": command.kind if command else "",
    "command_argument": command.argument if command else "",
}}, sort_keys=True))
"""


def _run(source: Path, *, historical: bool) -> dict[str, Any]:
    imports = (
        "from atlas_ros.workflows.w03_todoist import TodoistService, task_description\n"
        "from atlas_ros.workflows.w04_reconciliation import parse_atlas_command"
        if historical
        else "from atlas_ros.services.todoist_execution import TodoistService, task_description\n"
        "from atlas_ros.reconciliation.service import parse_atlas_command"
    )
    env = dict(os.environ)
    dependencies = Path(__file__).resolve().parents[1] / ".venv/lib/python3.12/site-packages"
    env["PYTHONPATH"] = f"{source / 'src'}:{dependencies}"
    completed = subprocess.run(
        [sys.executable, "-c", FIXTURE.format(imports=imports)],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return json.loads(completed.stdout)


def evaluate(rollback_source: Path) -> dict[str, Any]:
    candidate_source = Path(__file__).resolve().parents[1]
    historical = _run(rollback_source, historical=True)
    semantic = _run(candidate_source, historical=False)
    differences = {
        key: {"v5.6": historical.get(key), "v6": semantic.get(key)}
        for key in sorted(set(historical) | set(semantic))
        if historical.get(key) != semantic.get(key)
    }
    return {
        "baseline": "Atlas ROS v5.6.0",
        "candidate": "Atlas ROS v6.0.0rc1",
        "compared_fields": len(set(historical) | set(semantic)),
        "unexplained_differences": differences,
        "unexplained_drift_count": len(differences),
        "objective_preserved": historical["description"] == semantic["description"],
        "hierarchy_and_task_count_preserved": historical["subtasks"] == semantic["subtasks"],
        "section_routing_preserved": historical["section"] == semantic["section"],
        "command_parsing_preserved": (
            historical["command_kind"],
            historical["command_argument"],
        )
        == (semantic["command_kind"], semantic["command_argument"]),
        "live_provider_writes": 0,
        "eligible": not differences,
    }


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rollback-source", required=True, type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("differential-evidence/V600_DIFFERENTIAL_REPORT.json"),
    )
    args = parser.parse_args(argv)
    report = evaluate(args.rollback_source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True))
    if not report["eligible"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
