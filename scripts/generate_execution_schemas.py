from __future__ import annotations

import json
from pathlib import Path

from atlas_ros.contracts import ExecutionCandidate, ExecutionPlanV2, ProjectionDecision


def main() -> int:
    schemas = {
        "execution-candidate-v2.schema.json": ExecutionCandidate.model_json_schema(),
        "projection-decision-v2.schema.json": ProjectionDecision.model_json_schema(),
        "execution-plan-v2.schema.json": ExecutionPlanV2.model_json_schema(),
    }
    root = Path("schemas/execution")
    root.mkdir(parents=True, exist_ok=True)
    for name, schema in schemas.items():
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["$id"] = f"https://atlas-ros.local/schemas/execution/{name}"
        (root / name).write_text(
            json.dumps(schema, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
