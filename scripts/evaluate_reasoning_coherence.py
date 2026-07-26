from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from atlas_ros.contracts import ConfidenceDimensionV1
from atlas_ros.domain.models import Capture
from atlas_ros.engines import (
    KnowledgeCompositionEngine,
    ManagementReasoningEngine,
    ManagementStructureEngine,
    ReasoningCoherenceGate,
)
from atlas_ros.models import load_default_registries


def _fingerprint(reasoning: Any, management: Any) -> dict[str, Any]:
    return {
        "primary_outcome": management.primary_outcome,
        "current_actions": [item.title for item in management.execution_candidates],
        "delegated_actions": [item.title for item in management.delegated_outcomes],
        "conditional_actions": [item.title for item in management.conditional_outcomes],
        "planning_model": reasoning.selected_planning_model_id,
        "responsibility_domain": reasoning.responsibility_domain,
        "workstream": reasoning.workstream,
        "requires_human_decision": reasoning.requires_human_decision,
        "summary": management.user_facing_summary,
    }


def _mutate(reasoning: Any, mutation: str) -> Any:
    if mutation == "high_model_unresolved":
        return reasoning.model_copy(
            update={"responsibility_domain": "unresolved", "workstream": "Needs Clarification"}
        )
    if mutation == "no_review_clarification":
        return reasoning.model_copy(
            update={
                "requires_human_decision": False,
                "rationale": ("Needs clarification before routing.",),
                "user_facing_summary": "Clarification is required before execution.",
            }
        )
    if mutation == "routing_mismatch":
        return reasoning.model_copy(update={"destination": "Portfolio Projects"})
    if mutation == "inaccurate_explanation":
        return reasoning.model_copy(
            update={"user_facing_summary": "Atlas needs clarification before execution."}
        )
    if mutation == "low_material_responsibility":
        dimensions = tuple(
            ConfidenceDimensionV1(
                **{
                    **item.model_dump(),
                    "score": 0.40,
                    "requires_attended_review": False,
                }
            )
            if item.dimension == "responsibility_resolution"
            else item
            for item in reasoning.confidence_dimensions
        )
        return reasoning.model_copy(update={"confidence_dimensions": dimensions})
    if mutation == "nonblocking_reference_gap":
        return reasoning.model_copy(
            update={
                "reference_context": (
                    *reasoning.reference_context,
                    "Unresolved reference-only note.",
                )
            }
        )
    raise ValueError(f"unsupported mutation: {mutation}")


def evaluate(dataset: Path) -> dict[str, Any]:
    payload = json.loads(dataset.read_text(encoding="utf-8"))
    engine = ManagementReasoningEngine()
    gate = ReasoningCoherenceGate()
    models, modules = load_default_registries()
    composer = KnowledgeCompositionEngine(modules, models)
    structurer = ManagementStructureEngine(models)
    cloudvision: list[dict[str, Any]] = []
    fingerprints: set[str] = set()
    for case in payload["cloudvision_cases"]:
        reasoning = engine.reason_v4(Capture(content=case["input"]))
        result = gate.evaluate(reasoning)
        knowledge = composer.compose_v2(reasoning)
        management = structurer.structure_v3(reasoning, knowledge)
        fingerprint = json.dumps(_fingerprint(reasoning, management), sort_keys=True)
        fingerprints.add(fingerprint)
        dimensions = {item.dimension: item for item in reasoning.confidence_dimensions}
        passed = (
            result.passed
            and not result.review_required
            and result.verify_digest()
            and reasoning.responsibility_domain == "project_delivery"
            and reasoning.workstream == "Active Projects"
            and not reasoning.requires_human_decision
            and dimensions["planning_model"].score >= 0.95
            and dimensions["responsibility_resolution"].score >= 0.85
            and "needs clarification" not in reasoning.user_facing_summary.casefold()
            and "clarification is required" not in reasoning.user_facing_summary.casefold()
            and management.reasoning_coherence is not None
            and management.reasoning_coherence.passed
        )
        cloudvision.append(
            {"id": case["id"], "passed": passed, **_fingerprint(reasoning, management)}
        )

    cross_domain: list[dict[str, Any]] = []
    for case in payload["cross_domain_cases"]:
        reasoning = engine.reason_v4(Capture(content=case["input"]))
        result = gate.evaluate(reasoning)
        passed = (
            result.passed
            and not result.review_required
            and reasoning.selected_planning_model_id == "controlled-technology-pilot"
            and reasoning.responsibility_domain == "project_delivery"
            and reasoning.workstream == "Active Projects"
        )
        cross_domain.append({"id": case["id"], "passed": passed})

    contradictions: list[dict[str, Any]] = []
    base = engine.reason_v4(
        Capture(content="Launch the Arista CloudVision code-upgrade automation pilot")
    )
    for case in payload["contradiction_cases"]:
        mutated = _mutate(base, case["mutation"])
        result = gate.evaluate(mutated)
        expected_review = bool(case["expected_review"])
        passed = result.review_required == expected_review and result.verify_digest()
        contradictions.append(
            {
                "id": case["id"],
                "passed": passed,
                "review_required": result.review_required,
                "failed_conditions": [
                    item.condition for item in result.conditions if not item.passed
                ],
            }
        )

    results = [*cloudvision, *cross_domain, *contradictions]
    invariant = len(fingerprints) == 1
    eligible = all(item["passed"] for item in results) and invariant
    return {
        "benchmark": payload["benchmark"],
        "cases": len(results),
        "passed": sum(1 for item in results if item["passed"]),
        "cloudvision_invariant": invariant,
        "provider_writes": 0,
        "eligible": eligible,
        "cloudvision": cloudvision,
        "cross_domain": cross_domain,
        "contradictions": contradictions,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset", type=Path, default=Path("benchmarks/reasoning-coherence-v1.json")
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reasoning-coherence-evidence/REASONING_COHERENCE_REPORT.json"),
    )
    args = parser.parse_args()
    report = evaluate(args.dataset)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    if not report["eligible"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
