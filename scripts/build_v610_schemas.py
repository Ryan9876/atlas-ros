from __future__ import annotations

import json
from pathlib import Path

from atlas_ros.contracts import (
    ExecutionCandidateV3,
    ExecutionPlanV3,
    IntentPartitionV1,
    ManagementPackageV3,
    ProjectionDecisionV3,
    ReasoningPackageV4,
    SemanticFidelityResultV1,
)

MODELS = {
    "intent/intent-partition-v1.schema.json": IntentPartitionV1,
    "reasoning-package-v4.schema.json": ReasoningPackageV4,
    "management-package-v3.schema.json": ManagementPackageV3,
    "execution/execution-candidate-v3.schema.json": ExecutionCandidateV3,
    "execution/projection-decision-v3.schema.json": ProjectionDecisionV3,
    "execution/execution-plan-v3.schema.json": ExecutionPlanV3,
    "semantic/semantic-fidelity-result-v1.schema.json": SemanticFidelityResultV1,
}


def main() -> None:
    root = Path("schemas")
    for relative, model in MODELS.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        schema = model.model_json_schema()
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["$id"] = f"https://atlas-ros.local/schemas/{relative}"
        target.write_text(
            json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
