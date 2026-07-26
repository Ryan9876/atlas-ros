from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from atlas_ros.domain.models import Capture
from atlas_ros.engines import (
    KnowledgeCompositionEngine,
    ManagementReasoningEngine,
    ManagementStructureEngine,
)
from atlas_ros.models import load_default_registries
from atlas_ros.planning import SemanticExecutionPlanner


def evaluate(dataset: Path) -> dict[str, Any]:
    payload = json.loads(dataset.read_text(encoding="utf-8"))
    models, modules = load_default_registries()
    results: list[dict[str, Any]] = []
    family_fingerprints: dict[str, set[str]] = {}
    for case in payload["cases"]:
        reasoning = ManagementReasoningEngine().reason_v4(Capture(content=case["input"]))
        knowledge = KnowledgeCompositionEngine(modules, models).compose_v2(reasoning)
        management = ManagementStructureEngine(models).structure_v3(reasoning, knowledge)
        plan = SemanticExecutionPlanner().plan(
            management,
            action_id=f"benchmark:{case['id']}",
            destination_intent=reasoning.destination,
        )
        parent = plan.parent_outcome.title if plan.parent_outcome else None
        subtasks = [step.title for step in plan.projected_steps]
        expected_review = bool(case["expected_review"])
        passed = (
            parent == case["expected_parent"]
            and subtasks == case["expected_subtasks"]
            and plan.semantic_fidelity.review_required == expected_review
            and plan.verify_digest()
            and plan.semantic_fidelity.verify_digest()
            and all(decision.verify_digest() for decision in plan.projection_decisions)
            and plan.authorized is False
        )
        family = case.get("family")
        if family:
            family_fingerprints.setdefault(family, set()).add(
                plan.semantic_fidelity.business_plan_fingerprint
            )
        results.append(
            {
                "id": case["id"],
                "critical": bool(case.get("critical", False)),
                "passed": passed,
                "parent": parent,
                "subtasks": subtasks,
                "review_required": plan.semantic_fidelity.review_required,
                "business_plan_fingerprint": (
                    plan.semantic_fidelity.business_plan_fingerprint
                ),
                "failed_conditions": [
                    condition.condition
                    for condition in plan.semantic_fidelity.conditions
                    if not condition.passed
                ],
            }
        )
    invariance = {
        family: len(fingerprints) == 1
        for family, fingerprints in family_fingerprints.items()
    }
    critical_passed = all(item["passed"] for item in results if item["critical"])
    eligible = critical_passed and all(invariance.values())
    return {
        "benchmark": payload["benchmark"],
        "cases": len(results),
        "passed": sum(1 for item in results if item["passed"]),
        "critical_passed": critical_passed,
        "metamorphic_invariance": invariance,
        "live_provider_writes": 0,
        "eligible": eligible,
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset", type=Path, default=Path("benchmarks/semantic-fidelity-v1.json")
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("semantic-fidelity-evidence/SEMANTIC_FIDELITY_REPORT.json"),
    )
    args = parser.parse_args()
    report = evaluate(args.dataset)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, sort_keys=True))
    if not report["eligible"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
