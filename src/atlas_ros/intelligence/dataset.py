from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from atlas_ros.intelligence.io import load_cases, load_results
from atlas_ros.intelligence.models import EvaluationCase, EvaluationDimension, EvaluationResult


@dataclass(frozen=True)
class EvaluationSetPolicy:
    minimum_cases: int = 12
    minimum_cases_per_dimension: int = 2
    required_dimensions: frozenset[EvaluationDimension] = frozenset(EvaluationDimension)


@dataclass(frozen=True)
class EvaluationSetValidation:
    case_count: int
    result_count: int
    covered_dimensions: tuple[EvaluationDimension, ...]
    errors: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.errors


class EvaluationSetValidator:
    def __init__(self, policy: EvaluationSetPolicy | None = None) -> None:
        self.policy = policy or EvaluationSetPolicy()

    def validate(
        self,
        cases: tuple[EvaluationCase, ...],
        results: tuple[EvaluationResult, ...] = (),
    ) -> EvaluationSetValidation:
        errors: list[str] = []
        case_ids = [case.id for case in cases]
        if len(cases) < self.policy.minimum_cases:
            errors.append(f"evaluation set requires at least {self.policy.minimum_cases} cases")
        duplicate_ids = sorted(case_id for case_id, count in Counter(case_ids).items() if count > 1)
        if duplicate_ids:
            errors.append(f"duplicate case ids: {', '.join(duplicate_ids)}")

        dimension_counts: Counter[EvaluationDimension] = Counter()
        for case in cases:
            dimension_counts.update(case.dimensions)
            if not case.source_refs:
                errors.append(f"{case.id}: at least one source reference is required")

        missing = sorted(
            self.policy.required_dimensions - set(dimension_counts), key=lambda item: item.value
        )
        if missing:
            errors.append("missing dimensions: " + ", ".join(item.value for item in missing))
        for dimension in sorted(self.policy.required_dimensions, key=lambda item: item.value):
            count = dimension_counts[dimension]
            if count < self.policy.minimum_cases_per_dimension:
                errors.append(
                    f"{dimension.value}: requires at least "
                    f"{self.policy.minimum_cases_per_dimension} cases; found {count}"
                )

        if results:
            result_ids = [result.case_id for result in results]
            duplicates = sorted(
                case_id for case_id, count in Counter(result_ids).items() if count > 1
            )
            if duplicates:
                errors.append(f"duplicate result case ids: {', '.join(duplicates)}")
            unknown = sorted(set(result_ids) - set(case_ids))
            missing_results = sorted(set(case_ids) - set(result_ids))
            if unknown:
                errors.append(f"results reference unknown cases: {', '.join(unknown)}")
            if missing_results:
                errors.append(f"cases without results: {', '.join(missing_results)}")

        return EvaluationSetValidation(
            case_count=len(cases),
            result_count=len(results),
            covered_dimensions=tuple(sorted(dimension_counts, key=lambda item: item.value)),
            errors=tuple(errors),
        )


def validate_files(cases_path: Path, results_path: Path | None = None) -> EvaluationSetValidation:
    cases = load_cases(cases_path)
    results = load_results(results_path) if results_path else ()
    return EvaluationSetValidator().validate(cases, results)
