from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from atlas_ros.domain.models import Capture
from atlas_ros.engines import ManagementReasoningEngine


def _safe_divide(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def evaluate(dataset_path: Path) -> dict[str, Any]:
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    cases = payload["cases"]
    engine = ManagementReasoningEngine()
    labels = sorted({str(case["expected_responsibility_domain"]) for case in cases})
    confusion: dict[str, dict[str, int]] = {
        label: {candidate: 0 for candidate in labels + ["unresolved"]} for label in labels
    }
    results: list[dict[str, Any]] = []
    calibration_error = 0.0
    explanation_agreement = 0
    record_destination_matches = 0
    critical_passes = 0
    critical_count = 0

    for case in cases:
        reasoning = engine.reason_v2(Capture(content=str(case["content"])))
        expected = str(case["expected_responsibility_domain"])
        predicted = reasoning.responsibility_domain
        confusion[expected].setdefault(predicted, 0)
        confusion[expected][predicted] += 1
        correct = (
            predicted == expected
            and reasoning.workstream == case["expected_workstream"]
            and reasoning.classification == case["expected_classification"]
        )
        if bool(case.get("critical")):
            critical_count += 1
            critical_passes += int(correct)
        calibration_error += abs(reasoning.confidence - float(correct))
        record_destination_matches += int(
            reasoning.classification == case["expected_classification"]
            and reasoning.destination == case["expected_destination"]
        )
        rationale = reasoning.rationale[0] if reasoning.rationale else ""
        explanation_agreement += int(
            reasoning.workstream in rationale and bool(reasoning.decisive_evidence)
        )
        results.append(
            {
                "id": case["id"],
                "expected_domain": expected,
                "predicted_domain": predicted,
                "expected_workstream": case["expected_workstream"],
                "predicted_workstream": reasoning.workstream,
                "expected_classification": case["expected_classification"],
                "predicted_classification": reasoning.classification,
                "expected_destination": case["expected_destination"],
                "predicted_destination": reasoning.destination,
                "confidence": reasoning.confidence,
                "correct": correct,
                "requires_human_decision": reasoning.requires_human_decision,
            }
        )

    metrics: dict[str, dict[str, float]] = defaultdict(dict)
    f1_values: list[float] = []
    recall_values: list[float] = []
    for label in labels:
        true_positive = confusion[label].get(label, 0)
        false_negative = sum(confusion[label].values()) - true_positive
        false_positive = sum(
            confusion[other].get(label, 0) for other in labels if other != label
        )
        precision = _safe_divide(true_positive, true_positive + false_positive)
        recall = _safe_divide(true_positive, true_positive + false_negative)
        f1 = _safe_divide(2 * precision * recall, precision + recall)
        metrics[label] = {"precision": precision, "recall": recall, "f1": f1}
        f1_values.append(f1)
        recall_values.append(recall)

    report = {
        "dataset_id": payload["dataset_id"],
        "case_count": len(cases),
        "critical_fixture_pass_rate": _safe_divide(critical_passes, critical_count),
        "macro_f1": sum(f1_values) / len(f1_values),
        "minimum_domain_recall": min(recall_values),
        "confidence_calibration_error": calibration_error / len(cases),
        "explanation_evidence_agreement": explanation_agreement / len(cases),
        "record_destination_equivalence": record_destination_matches / len(cases),
        "per_domain": metrics,
        "confusion_matrix": confusion,
        "results": results,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("benchmarks/classification-intelligence-v1.json"),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = evaluate(args.dataset)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    thresholds_pass = (
        report["critical_fixture_pass_rate"] == 1.0
        and report["macro_f1"] >= 0.90
        and report["minimum_domain_recall"] >= 0.85
        and report["confidence_calibration_error"] <= 0.10
        and report["explanation_evidence_agreement"] >= 0.95
        and report["record_destination_equivalence"] >= 0.99
    )
    return 0 if thresholds_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
