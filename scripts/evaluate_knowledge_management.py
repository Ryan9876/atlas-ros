from __future__ import annotations

import argparse
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from atlas_ros.contracts import PlanningModelCandidate, ReasoningPackageV3
from atlas_ros.engines import KnowledgeCompositionEngine, ManagementStructureEngine
from atlas_ros.models import load_default_registries


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Knowledge and Management V2")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cases = json.loads(args.dataset.read_text(encoding="utf-8"))["cases"]
    models, modules = load_default_registries()
    results: list[dict[str, object]] = []
    for case in cases:
        case_id = str(case["case_id"])
        reasoning = ReasoningPackageV3(
            correlation_id=uuid5(NAMESPACE_URL, f"atlas:{case_id}"),
            source_component="evaluation.knowledge_management",
            classification="action",
            destination="action_records",
            normalized_intent="Create a governed team operating model",
            management_pattern="Operational Excellence",
            candidate_planning_models=(
                PlanningModelCandidate(
                    model_id="team-operating-model",
                    version_constraint="^2.0.0",
                    confidence=1.0,
                    rationale="Benchmark fixture selection.",
                ),
            ),
            selected_planning_model_id="team-operating-model",
            selected_planning_model_version_constraint="^2.0.0",
            selection_method="user_selected",
            selection_confidence=1.0,
            selection_rationale="Benchmark fixture selection.",
            known_inputs=case["known_inputs"],
        )
        knowledge = KnowledgeCompositionEngine(modules, models).compose_v2(reasoning)
        management = ManagementStructureEngine(models).structure_v2(reasoning, knowledge)
        expected_missing = case.get("expected_missing_context")
        minimum_missing = case.get("minimum_missing_context", 0)
        passed = (
            management.lifecycle_status == case["expected_lifecycle"]
            and len(management.sections) == case["expected_sections"]
            and (
                expected_missing is None
                or len(knowledge.missing_context_requirements) == expected_missing
            )
            and len(knowledge.missing_context_requirements) >= minimum_missing
            and knowledge.verify_digest()
            and management.verify_digest()
        )
        results.append(
            {
                "case_id": case_id,
                "passed": passed,
                "lifecycle": management.lifecycle_status,
                "section_count": len(management.sections),
                "missing_context_count": len(knowledge.missing_context_requirements),
                "knowledge_digest": knowledge.package_digest,
                "management_digest": management.package_digest,
            }
        )
    report = {
        "dataset_version": 1,
        "passed": all(item["passed"] for item in results),
        "case_count": len(results),
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
