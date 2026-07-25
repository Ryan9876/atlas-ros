from __future__ import annotations

import json
from pathlib import Path

CASE_NAMES = (
    "no-change reconciliation",
    "due-date update",
    "priority update",
    "parent completion",
    "subtask completion",
    "Execution Step creation",
    "Execution Step update",
    "valid update command",
    "valid delegation command",
    "valid risk command",
    "valid blocker command",
    "valid dependency command",
    "valid issue command",
    "valid unblock command",
    "valid checkpoint command",
    "missing command body",
    "invalid checkpoint date",
    "unknown command",
    "duplicate command event",
    "previously applied command",
    "previously failed command",
    "missing mapped Todoist task",
    "missing Notion record",
    "duplicate mapping",
    "ambiguous mapping",
    "missing Execution Step",
    "missing data-source configuration",
    "ambiguous Notion person",
    "missing Notion person",
    "multiple open blockers",
    "no open blocker",
    "field-authority violation",
    "concurrent Todoist and Notion changes",
    "provider timeout before write",
    "provider timeout after write",
    "Notion rate limit",
    "readback mismatch",
    "partial mutation group",
    "crash before checkpoint",
    "crash after mutation before readback",
    "crash after readback before checkpoint",
    "retry after partial application",
    "full reconciliation",
    "incremental reconciliation",
    "stale checkpoint",
    "corrupted checkpoint",
    "checkpoint restoration",
    "parent-subtask hierarchy verification",
    "Objective preservation",
    "Done When preservation",
    "section-routing preservation",
    "task-economy preservation",
    "attended authorization rejection",
    "provider-adapter authority rejection",
    "development record matched",
    "GitHub-only development record",
    "Notion-only development record",
    "drifted development record",
    "missing disposition",
    "partial scope misclassified as complete",
    "missing Release Implemented",
    "record readback mismatch",
    "report checksum mismatch",
    "canonical import success",
    "W import rejection",
    "W module absent from wheel",
    "W module absent from source distribution",
    "archival mapping retained",
    "migration guide completeness",
    "v5.6 rollback installation",
    "v6-to-v5.6 state compatibility",
    "published-artifact restoration",
    "post-promotion workflow dry run",
    "deterministic plan",
    "deterministic receipt",
    "deterministic record digest",
    "zero live provider writes during validation",
)


CONFLICT_MARKERS = (
    "missing",
    "duplicate",
    "ambiguous",
    "violation",
    "concurrent",
    "stale",
    "corrupted",
    "drifted",
    "mismatch",
    "misclassified",
    "GitHub-only",
    "Notion-only",
)


def _case(index: int, name: str) -> dict[str, object]:
    conflict = any(marker.casefold() in name.casefold() for marker in CONFLICT_MARKERS)
    no_change = name in {
        "no-change reconciliation",
        "canonical import success",
        "W import rejection",
        "W module absent from wheel",
        "W module absent from source distribution",
        "archival mapping retained",
        "migration guide completeness",
        "v5.6 rollback installation",
        "published-artifact restoration",
        "post-promotion workflow dry run",
        "zero live provider writes during validation",
    }
    if conflict:
        todoist = {"unregistered_field": f"source-{index}"}
        notion = {"unregistered_field": f"target-{index}"}
        expected_mutations = 0
        expected_conflicts = 1
    elif no_change:
        todoist = {"execution_priority": "P2"}
        notion = {"execution_priority": "P2"}
        expected_mutations = 0
        expected_conflicts = 0
    elif index % 3 == 0:
        todoist = {"execution_due_date": f"2026-08-{(index % 27) + 1:02d}"}
        notion = {"execution_due_date": "2026-09-01"}
        expected_mutations = 1
        expected_conflicts = 0
    elif index % 3 == 1:
        todoist = {"execution_priority": "P1"}
        notion = {"execution_priority": "P4"}
        expected_mutations = 1
        expected_conflicts = 0
    else:
        todoist = {"responsibility": "stale"}
        notion = {"responsibility": f"Canonical responsibility {index}"}
        expected_mutations = 1
        expected_conflicts = 0
    return {
        "id": f"CR-{index:03d}",
        "name": name,
        "critical": True,
        "todoist": todoist,
        "notion": notion,
        "expected_mutations": expected_mutations,
        "expected_conflicts": expected_conflicts,
    }


def main() -> None:
    output = Path("benchmarks/canonical-reconciliation-v1.json")
    output.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "benchmark": "canonical-reconciliation-v1",
                "live_provider_writes": False,
                "cases": [_case(index, name) for index, name in enumerate(CASE_NAMES, 1)],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
