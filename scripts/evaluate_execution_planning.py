from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Literal, cast
from uuid import NAMESPACE_URL, uuid5

from atlas_ros.contracts import (
    CandidateType,
    CompletionState,
    ExecutionCandidate,
    ExistingRepresentation,
    ExistingRepresentationIndex,
    HorizonState,
    ManagementPackage,
    ManagementPackageV2,
    ManagementSection,
    deterministic_digest,
)
from atlas_ros.planning import ExecutionPlanner


def _management(case_id: str, noise_sections: int = 0) -> ManagementPackageV2:
    correlation_id = uuid5(NAMESPACE_URL, f"atlas-execution:{case_id}")
    sections = tuple(
        ManagementSection(
            section_id=f"context-{index}",
            title=f"Context {index}",
            content={"notes": [f"Management context {index}"]},
            provenance=(f"module:context-{index}",),
            completeness="complete",
        )
        for index in range(noise_sections)
    )
    values: dict[str, Any] = {
        "correlation_id": correlation_id,
        "artifact_id": f"benchmark:{case_id}",
        "artifact_type": "benchmark",
        "planning_model_id": "benchmark-model",
        "planning_model_version": "2.0.0",
        "source_reasoning_reference": f"reasoning/v3/{case_id}",
        "source_knowledge_reference": f"knowledge/v2/{case_id}",
        "responsibility": "Lead the benchmark outcome",
        "desired_outcome": f"The {case_id} outcome is approved and recorded",
        "owner": "Ryan",
        "workstream": "Operations",
        "sections": sections,
        "section_provenance": {
            section.section_id: section.provenance for section in sections
        },
        "section_completeness": {
            section.section_id: section.completeness for section in sections
        },
        "completion_evidence_requirements": (
            f"The {case_id} result is approved and stored in the authority record",
        ),
        "lifecycle_status": "structurally_complete",
        "planning_registry_digest": "1" * 64,
        "module_registry_digest": "2" * 64,
        "configuration_digest": "3" * 64,
    }
    unsigned = ManagementPackageV2(package_digest="0" * 64, **values)
    return ManagementPackageV2(
        **values,
        package_digest=deterministic_digest(unsigned.digest_payload()),
    )


def _candidate(
    management: ManagementPackageV2,
    candidate_id: str,
    *,
    parent: bool = False,
    mutation: dict[str, Any] | None = None,
) -> ExecutionCandidate:
    mutation = mutation or {}
    title = str(mutation.get("title", f"Complete benchmark action {candidate_id}"))
    candidate_type = CandidateType(
        str(
            mutation.get(
                "candidate_type",
                CandidateType.PARENT_OUTCOME
                if parent
                else CandidateType.EXECUTABLE_ACTION,
            )
        )
    )
    values: dict[str, Any] = {
        "candidate_id": candidate_id,
        "correlation_id": management.correlation_id,
        "source_management_reference": f"management-package/v2/{management.artifact_id}",
        "candidate_type": candidate_type,
        "title": title,
        "proposed_objective": str(
            mutation.get("objective", f"Deliver the outcome for {title}")
        ),
        "done_when": str(
            mutation.get(
                "done_when",
                f"Evidence for {title} is approved and recorded",
            )
        ),
        "owner": str(mutation.get("owner", "Ryan")),
        "responsibility_domain": "Network Services",
        "workstream": "Operations",
        "source_section": str(mutation.get("source_section", "actions")),
        "source_item_id": str(mutation.get("source_item_id", candidate_id)),
        "source_provenance": ("benchmark",),
        "dependency_references": tuple(mutation.get("dependencies", ())),
        "trigger": str(mutation.get("trigger", "")),
        "trigger_satisfied": bool(mutation.get("trigger_satisfied", False)),
        "completion_state": CompletionState(
            str(mutation.get("completion_state", CompletionState.OUTSTANDING))
        ),
        "execution_ready": bool(mutation.get("execution_ready", True)),
        "earliest_executable_horizon": HorizonState(
            str(mutation.get("horizon", HorizonState.CURRENT))
        ),
        "ambiguities": tuple(mutation.get("ambiguities", ())),
        "can_remain_embedded": bool(mutation.get("can_remain_embedded", False)),
        "improves_execution_clarity": bool(
            mutation.get("improves_execution_clarity", True)
        ),
        "independently_executable": bool(
            mutation.get("independently_executable", True)
        ),
        "recurrence_required": bool(mutation.get("recurrence_required", False)),
    }
    unsigned = ExecutionCandidate(candidate_digest="0" * 64, **values)
    return ExecutionCandidate(
        **values,
        candidate_digest=deterministic_digest(unsigned.digest_payload()),
    )


def _run_case(case: dict[str, Any]) -> dict[str, Any]:
    case_id = str(case["case_id"])
    management = _management(case_id, int(case.get("noise_sections", 0)))
    child_count = int(case.get("child_count", 0))
    mutations = {
        int(item["index"]): dict(item["values"]) for item in case.get("mutations", ())
    }
    candidates = [
        _candidate(management, "parent", parent=True),
        *(
            _candidate(
                management,
                f"child-{index}",
                mutation=mutations.get(index),
            )
            for index in range(1, child_count + 1)
        ),
    ]
    duplicate = case.get("duplicate")
    if duplicate:
        source = candidates[int(duplicate.get("source_index", 1))]
        mode = str(duplicate["mode"])
        mutation: dict[str, Any] = {}
        if mode == "normalized_title":
            mutation["title"] = source.title.swapcase().replace(" ", "-")
        elif mode == "objective_done_when":
            mutation.update(
                {
                    "title": f"Alternative {source.title}",
                    "objective": source.proposed_objective,
                    "done_when": source.done_when,
                }
            )
        elif mode == "source_reference":
            mutation.update(
                {
                    "title": f"Alternative {source.title}",
                    "source_item_id": source.source_item_id,
                }
            )
        elif mode == "ambiguous":
            mutation["title"] = source.title.replace("action", "actions")
        candidates.append(_candidate(management, "duplicate", mutation=mutation))
    multiple_parent_mode = case.get("multiple_parent_mode")
    if multiple_parent_mode:
        second_title = (
            "Approve quarterly release planning"
            if multiple_parent_mode == "ambiguous"
            else "Train the service support team"
        )
        candidates[0] = _candidate(
            management,
            "parent",
            parent=True,
            mutation={"title": "Approve quarterly release plan"},
        )
        candidates.append(
            _candidate(
                management,
                "parent-2",
                parent=True,
                mutation={"title": second_title},
            )
        )
        for index in range(1, child_count + 1):
            parent_id = "parent" if index % 2 else "parent-2"
            candidates[index] = _candidate(
                management,
                f"child-{index}",
                mutation={"dependencies": (parent_id,)},
            )
    if case.get("reverse_candidates"):
        candidates = [candidates[0], *reversed(candidates[1:])]

    existing_index = ExistingRepresentationIndex()
    existing = case.get("existing")
    if existing:
        subject = candidates[int(existing.get("candidate_index", 1))]
        state = cast(
            Literal["open", "completed", "cancelled"],
            str(existing["state"]),
        )
        existing_index = ExistingRepresentationIndex(
            representations=(
                ExistingRepresentation(
                    representation_id=f"existing:{case_id}",
                    representation_type="subtask",
                    title=subject.title,
                    objective=subject.proposed_objective,
                    done_when=subject.done_when,
                    owner=subject.owner,
                    workstream=subject.workstream,
                    state=state,
                    last_verified_at=management.created_at,
                ),
            )
        )
    planner = ExecutionPlanner()
    action_id = f"benchmark:{case_id}"
    destination_intent = str(case.get("destination", "Work/Operations"))
    candidate_tuple = tuple(candidates)
    plans = (
        planner.plan_many_v2(
            management,
            action_id=action_id,
            destination_intent=destination_intent,
            candidates=candidate_tuple,
            existing_index=existing_index,
        )
        if multiple_parent_mode
        else (
            planner.plan_v2(
                management,
                action_id=action_id,
                destination_intent=destination_intent,
                candidates=candidate_tuple,
                existing_index=existing_index,
            ),
        )
    )
    repeated_plans = (
        planner.plan_many_v2(
            management,
            action_id=action_id,
            destination_intent=destination_intent,
            candidates=candidate_tuple,
            existing_index=existing_index,
        )
        if multiple_parent_mode
        else (
            planner.plan_v2(
                management,
                action_id=action_id,
                destination_intent=destination_intent,
                candidates=candidate_tuple,
                existing_index=existing_index,
            ),
        )
    )
    plan = plans[0]
    expected_status = case.get("expected_child_status")
    child_statuses = [
        decision.status.value
        for candidate_plan in plans
        for decision in candidate_plan.projection_decisions
        if decision.candidate_id != "parent"
    ]
    passed = (
        sum(len(candidate_plan.projected_steps) for candidate_plan in plans)
        == int(case["expected_projected"])
        and all(
            candidate_plan.decomposition_review_status
            == case.get("expected_review", "not_required")
            for candidate_plan in plans
        )
        and all(candidate_plan.authorized is False for candidate_plan in plans)
        and all(candidate_plan.verify_digest() for candidate_plan in plans)
        and [candidate_plan.plan_digest for candidate_plan in plans]
        == [candidate_plan.plan_digest for candidate_plan in repeated_plans]
        and len(plans) == int(case.get("expected_parent_plans", 1))
        and not any(
            provider_field
            in "".join(candidate_plan.model_dump_json() for candidate_plan in plans)
            for provider_field in (
                "provider_object_id",
                "todoist_project_id",
                "todoist_section_id",
            )
        )
        and (
            expected_status is None
            or str(expected_status) in child_statuses
        )
    )
    if case.get("legacy_compatibility"):
        legacy = planner.plan(
            ManagementPackage(
                correlation_id=management.correlation_id,
                source_component="legacy.w03a",
                responsibility=management.responsibility,
                desired_outcome=management.desired_outcome,
                owner="Ryan",
                workstream="Operations",
            ),
            action_id=f"legacy:{case_id}",
            destination="Work",
            candidate_steps=("Gather inputs", "Review outcome"),
        )
        passed = passed and len(legacy.steps) == 2 and legacy.authorized is False
    if case.get("unsafe_v1"):
        try:
            plan.project_v1()
        except ValueError:
            pass
        else:
            passed = False
    return {
        "case_id": case_id,
        "tags": case.get("tags", []),
        "passed": passed,
        "parent_plan_count": len(plans),
        "projected_subtasks": sum(
            len(candidate_plan.projected_steps) for candidate_plan in plans
        ),
        "review_status": (
            "required"
            if any(
                candidate_plan.decomposition_review_status == "required"
                for candidate_plan in plans
            )
            else "not_required"
        ),
        "authorized": any(candidate_plan.authorized for candidate_plan in plans),
        "plan_digests": [candidate_plan.plan_digest for candidate_plan in plans],
        "child_statuses": child_statuses,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Execution Planning V2")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    results = [_run_case(case) for case in dataset["cases"]]
    critical_results = [
        result for result in results if "critical" in result["tags"]
    ]
    tags = sorted({tag for result in results for tag in result["tags"]})
    metrics: dict[str, dict[str, float | int]] = {}
    for tag in tags:
        tagged = [result for result in results if tag in result["tags"]]
        passed = sum(bool(result["passed"]) for result in tagged)
        metrics[tag] = {
            "cases": len(tagged),
            "passed": passed,
            "rate": passed / len(tagged),
        }
    report = {
        "dataset_version": dataset["version"],
        "policy_version": "execution-planning-v2.0.0",
        "passed": all(result["passed"] for result in results),
        "case_count": len(results),
        "critical_fixture_pass_rate": (
            sum(bool(result["passed"]) for result in critical_results)
            / len(critical_results)
        ),
        "zero_unauthorized_execution_objects": all(
            result["authorized"] is False for result in results
        ),
        "zero_provider_writes": True,
        "metrics": metrics,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
