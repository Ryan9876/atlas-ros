from __future__ import annotations

import json
from pathlib import Path

from atlas_ros.intelligence.models import EvaluationCase, EvaluationResult


def load_cases(path: Path) -> tuple[EvaluationCase, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("evaluation case file must contain a JSON list")
    return tuple(EvaluationCase.model_validate(item) for item in payload)


def load_results(path: Path) -> tuple[EvaluationResult, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("evaluation result file must contain a JSON list")
    return tuple(EvaluationResult.model_validate(item) for item in payload)
