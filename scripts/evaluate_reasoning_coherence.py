from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from atlas_ros.contracts import deterministic_digest
from atlas_ros.domain.models import Capture
from atlas_ros.engines import ManagementReasoningEngine, ReasoningCoherenceGate


def _mutate(reasoning: Any, mutation: str) -> Any:
    payload = reasoning.model_dump(mode="python")
    if mutation == "unresolved_responsibility":
        payload.update(
            {
                "selected_planning_model_id": "single-business-outcome",
                "selection_confidence": 0.95,
                "responsibility_domain": "unresolved",
                "workstream": "Active Projects",
                "classification": "project",
                "destination": "Portfolio Projects",
                "confidence": 0.95,
                "rationale": ("The business outcome is otherwise fully specified.",),
                "requires_human_decision": False,
            }
        )
    elif mutation == "clarification_language":
        payload.update(
            {
                "selected_planning_model_id": "single-business-outcome",
                "selection_confidence": 0.95,
                "responsibility_domain": "project_delivery",
                "workstream": "Active Projects",
                "classification": "project",
                "destination": "Portfolio Projects",
                "confidence": 0.95,
                "rationale": ("Clarification required before proceeding.",),
                "requires_human_decision": False,
            }
        )
    elif mutation == "routing_conflict":
        payload.update(
            {
                "selected_planning_model_id": "single-business-outcome",
                "selection_confidence": 0.95,
                "responsibility_domain": "project_delivery",
                "workstream": "Active Projects",
                "classification": "needs_clarification",
                "destination": "Needs Clarification",
                "confidence": 0.95,
                "rationale": ("The business outcome is fully specified.",),
                "requires_human_decision": False,
            }
        )
    elif mutation == "inaccurate_explanation":
        payload.update(
            {
                "selected_planning_model_id": "single-business-outcome",
                "selection_confidence": 0.95,
                "responsibility_domain": "project_delivery",
                "workstream": "Active Projects",
                "classification": "project",
                "destination": "Portfolio Projects",
                "confidence": 0.95,
                "rationale": ("This valid plan still requires clarification.",),
                "requires_human_decision": False,
            }
        )
    elif mutation == "low_material_confidence":
        payload.update(
            {
                "selected_planning_model_id": "single-business-outcome",
                "selection_confidence": 0.95,
                "responsibility_domain": "project_delivery",
                "workstream": "Active Projects",
                "classification": "project",
                "destination": "Portfolio Projects",
                "confidence": 0.20,
                "rationale": ("Responsibility evidence is materially weak.",),
                "requires_human_decision": False,
            }
        )
    elif mutation == "nonblocking_reference_gap":
        payload["known_inputs"] = {
            **payload["known_inputs"],
            "nonblocking_reference_gap": "A reference-only source was unavailable.",
        }
    else:
        raise ValueError(f"unsupported mutation: {mutation}")
    return reasoning.__class__.model_validate(payload)


def evaluate(dataset: Path) -> dict[str, Any]:
    payload = json.loads(dataset.read_text(encoding="utf-8"))
    engine = ManagementReasoningEngine()
    gate = ReasoningCoherenceGate()
    results: list[dict[str, Any]] = []
    family_fingerprints: dict[str, set[str]] = {}
    for case in payload["cases"]:
        reasoning, coherence = engine.reason_v4_with_coherence(
            Capture(content=case.get("input", payload["base_input"]))
        )
        mutation = case.get("mutation")
        if mutation:
            mutated = _mutate(reasoning, mutation)
            reasoning, coherence = gate.apply(mutated)
        expected_passed = bool(case["expected_passed"])
        metadata = {
            "planning_model": reasoning.selected_planning_model_id,
            "classification": reasoning.classification,
            "destination": reasoning.destination,
            "responsibility_domain": reasoning.responsibility_domain,
            "workstream": reasoning.workstream,
            "requires_human_decision": reasoning.requires_human_decision,
            "explanation": coherence.explanation,
        }
        expected_metadata = case.get("expected_metadata", {})
        metadata_matches = all(metadata.get(key) == value for key, value in expected_metadata.items())
        passed = (
            coherence.passed == expected_passed
            and coherence.review_required == (not expected_passed)
            and reasoning.requires_human_decision == (not expected_passed)
            and metadata_matches
            and coherence.verify_digest()
            and coherence.provider_writes == 0
        )
        family = case.get("family")
        fingerprint = deterministic_digest(metadata)
        if family:
            family_fingerprints.setdefault(family, set()).add(fingerprint)
        results.append(
            {
                "id": case["id"],
                "critical": bool(case.get("critical", True)),
                "passed": passed,
                "coherence_passed": coherence.passed,
                "review_required": coherence.review_required,
                "metadata": metadata,
                "metadata_fingerprint": fingerprint,
                "failed_conditions": [
                    condition.condition for condition in coherence.conditions if not condition.passed
                ],
                "low_confidence_dimensions": [
                    subject.value for subject in coherence.low_confidence_dimensions
                ],
                "provider_writes": coherence.provider_writes,
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
        "metadata_invariance": invariance,
        "live_provider_writes": 0,
        "eligible": eligible,
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("benchmarks/reasoning-coherence-v1.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reasoning-coherence-evidence/REASONING_COHERENCE_REPORT.json"),
    )
    args = parser.parse_args()
    report = evaluate(args.dataset)
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
